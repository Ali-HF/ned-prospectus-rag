import os
import sys
import time
import io
import argparse
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import pypdfium2 as pdfium
import numpy as np
from PIL import Image

from google import genai
from google.genai import types

load_dotenv()

PROMPT_A = (
    "You are an OCR engine. Convert this page image into Markdown. "
    "Keep reading order. Render tables as Markdown tables with every row, "
    "column and number. Output only the page content."
)

PROMPT_B = (
    "Read the text in this scanned page image and write it out as plain text, "
    "one line per printed line. Tables as Markdown."
)


class SlidingRateLimiter:
    """Thread-safe rate limiter allowing at most max_calls in time_window seconds."""

    def __init__(self, max_calls: int = 8, time_window: float = 60.0):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = threading.Lock()

    def acquire(self):
        while True:
            with self.lock:
                now = time.time()
                self.calls = [t for t in self.calls if now - t < self.time_window]
                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return
                sleep_time = self.time_window - (now - self.calls[0]) + 0.1
            if sleep_time > 0:
                time.sleep(sleep_time)


class ModelManager:
    """Manages ordered model fallback, last-working model sticky routing, and cooldowns."""

    def __init__(self, candidate_models: list[str], client: genai.Client):
        self.client = client
        self.lock = threading.Lock()

        # Check existing models on key
        try:
            available_names = {m.name.split("/")[-1] for m in client.models.list()}
        except Exception:
            available_names = set(candidate_models)

        # Filter candidates by available on key, preserving order and uniqueness
        seen = set()
        self.models = []
        for m in candidate_models:
            if m in available_names and m not in seen:
                seen.add(m)
                self.models.append(m)

        self.last_working_model = self.models[0] if self.models else "gemini-2.5-flash"
        self.consecutive_503s = {m: 0 for m in self.models}
        self.cooldown_until = {m: 0.0 for m in self.models}

    def get_ordered_models(self) -> list[str]:
        """Return models starting with last_working_model, skipping cooling-down models."""
        with self.lock:
            now = time.time()
            # Order starting from last_working_model
            if self.last_working_model in self.models:
                idx = self.models.index(self.last_working_model)
                ordered = self.models[idx:] + self.models[:idx]
            else:
                ordered = list(self.models)

            # Filter out models currently cooling down
            active = [m for m in ordered if self.cooldown_until.get(m, 0.0) <= now]
            # Fallback to all if everything is cooling down
            return active if active else ordered

    def record_success(self, model: str):
        with self.lock:
            self.last_working_model = model
            self.consecutive_503s[model] = 0

    def record_503(self, model: str, log_func=None):
        with self.lock:
            self.consecutive_503s[model] = self.consecutive_503s.get(model, 0) + 1
            if self.consecutive_503s[model] >= 2:
                self.cooldown_until[model] = time.time() + 180.0  # 3 minutes
                if log_func:
                    log_func(f"Model {model} marked cooling down for 3 minutes after 2 consecutive 503s.")


# Lazy-loaded RapidOCR engine singleton
_rapid_ocr_lock = threading.Lock()
_rapid_ocr_instance = None


def get_rapid_ocr():
    """Lazy initialize RapidOCR engine singleton."""
    global _rapid_ocr_instance
    with _rapid_ocr_lock:
        if _rapid_ocr_instance is None:
            from rapidocr_onnxruntime import RapidOCR
            _rapid_ocr_instance = RapidOCR()
        return _rapid_ocr_instance


def render_page_image(pdf_path: Path, page_index: int, scale: float = 2.0) -> Image.Image:
    """Render a 0-indexed PDF page to a PIL Image using pypdfium2."""
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        page = doc[page_index]
        return page.render(scale=scale).to_pil()
    finally:
        doc.close()


def image_to_png_bytes(img: Image.Image) -> bytes:
    """Convert PIL image to PNG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def is_valid_ocr_response(response) -> tuple[bool, str]:
    """Check if Gemini response is valid.
    
    A response FAILS if text is None/empty, equals 'EMPTY' for a page that has an image,
    or finish_reason is RECITATION, SAFETY, or anything other than STOP.
    """
    if response is None:
        return False, ""

    if hasattr(response, "candidates") and response.candidates:
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        fr_str = str(finish_reason).upper()
        if "STOP" not in fr_str:
            return False, ""

    text = getattr(response, "text", "")
    if text is None:
        return False, ""

    text = text.strip()
    if not text or text == "EMPTY":
        return False, ""

    return True, text


def call_model_with_fast_retry(client: genai.Client, model: str, contents: list, rate_limiter: SlidingRateLimiter, model_mgr: ModelManager, config: types.GenerateContentConfig | None = None, log_func=None):
    """Execute Gemini generate_content.
    
    On a 503/429/timeout: wait only 5 seconds, retry the same model ONCE,
    then immediately move to the NEXT model.
    """
    for attempt in range(2):  # 1 initial + 1 retry = 2 attempts max per model
        rate_limiter.acquire()
        try:
            resp = client.models.generate_content(model=model, contents=contents, config=config)
            return resp
        except Exception as e:
            err_msg = str(e)
            if "quota exceeded for metric" in err_msg.lower() or "generaterequestsperday" in err_msg.lower():
                if log_func:
                    log_func(f"Daily quota limit hit for {model}: {err_msg[:120]}")
                return None
            if "503" in err_msg:
                model_mgr.record_503(model, log_func=log_func)
            if "503" in err_msg or "429" in err_msg or "timeout" in err_msg.lower():
                if attempt == 0:
                    time.sleep(5)
                    continue
            return None
    return None


def run_model_chain(client: genai.Client, png_bytes: bytes, rate_limiter: SlidingRateLimiter, model_mgr: ModelManager, log_func=None) -> tuple[str | None, str | None]:
    """Try models in order with prompt A, then prompt B (temp 0.7) if prompt A fails."""
    models_to_try = model_mgr.get_ordered_models()
    part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")

    for model in models_to_try:
        # Prompt A
        resp = call_model_with_fast_retry(client, model, [part, PROMPT_A], rate_limiter, model_mgr, log_func=log_func)
        ok, text = is_valid_ocr_response(resp)
        if ok:
            model_mgr.record_success(model)
            return text, model

        # Prompt B (temp 0.7) on same model
        cfg = types.GenerateContentConfig(temperature=0.7)
        resp = call_model_with_fast_retry(client, model, [part, PROMPT_B], rate_limiter, model_mgr, config=cfg, log_func=log_func)
        ok, text = is_valid_ocr_response(resp)
        if ok:
            model_mgr.record_success(model)
            return text, model

    return None, None


def run_split_page(client: genai.Client, img: Image.Image, rate_limiter: SlidingRateLimiter, model_mgr: ModelManager, log_func=None) -> str | None:
    """Split page into top and bottom half (~5% overlap) and run through models."""
    w, h = img.size
    overlap = int(h * 0.05)

    top_img = img.crop((0, 0, w, (h // 2) + overlap))
    bottom_img = img.crop((0, (h // 2) - overlap, w, h))

    top_bytes = image_to_png_bytes(top_img)
    bottom_bytes = image_to_png_bytes(bottom_img)

    text_top, _ = run_model_chain(client, top_bytes, rate_limiter, model_mgr, log_func=log_func)
    if not text_top:
        return None

    text_bottom, _ = run_model_chain(client, bottom_bytes, rate_limiter, model_mgr, log_func=log_func)
    if not text_bottom:
        return None

    return f"{text_top}\n\n{text_bottom}"


def run_local_rapid_ocr(pdf_path: Path, page_index: int) -> str | None:
    """Run local OCR with RapidOCR at scale 3.0."""
    try:
        img_3x = render_page_image(pdf_path, page_index, scale=3.0)
        img_np = np.array(img_3x)
        engine = get_rapid_ocr()
        result, _ = engine(img_np)
        if not result:
            return None

        # Sort lines by y then x
        sorted_boxes = sorted(result, key=lambda item: (min(pt[1] for pt in item[0]), min(pt[0] for pt in item[0])))

        lines = []
        curr_line = []
        curr_y = None
        for item in sorted_boxes:
            box, text, _ = item
            y = min(pt[1] for pt in box)
            x = min(pt[0] for pt in box)
            if curr_y is None or abs(y - curr_y) > 15:
                if curr_line:
                    curr_line.sort(key=lambda t: t[0])
                    lines.append(" ".join(t[1] for t in curr_line))
                curr_line = [(x, text)]
                curr_y = y
            else:
                curr_line.append((x, text))

        if curr_line:
            curr_line.sort(key=lambda t: t[0])
            lines.append(" ".join(t[1] for t in curr_line))

        full_text = "\n".join(lines).strip()
        if not full_text:
            return None

        return f"[LOCAL-OCR, check tables]\n{full_text}"
    except Exception:
        return None


def atomic_write(path: Path, content: str):
    """Write content to file atomically."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    tmp.replace(path)


def process_page_job(page_num: int, total_pages: int, pdf_path: Path, ocr_dir: Path, client: genai.Client, rate_limiter: SlidingRateLimiter, model_mgr: ModelManager, log_func, csv_lock: threading.Lock):
    """Process a single page through the full resilient strategy pipeline."""
    page_file = ocr_dir / f"page_{page_num:03d}.txt"
    strategy_csv = ocr_dir / "strategy.csv"
    failed_txt = ocr_dir / "failed.txt"
    blank_txt = ocr_dir / "blank.txt"

    page_index = page_num - 1
    # Render inside each worker
    img_2x = render_page_image(pdf_path, page_index, scale=2.0)
    png_bytes = image_to_png_bytes(img_2x)

    result_text = None
    winning_strategy = None

    # Step 1: Model chain (full page)
    text, used_model = run_model_chain(client, png_bytes, rate_limiter, model_mgr, log_func=log_func)
    if text:
        result_text = text
        winning_strategy = f"API ({used_model})"

    # Step 2: Split page strategy if all models failed full page
    if not result_text:
        res_split = run_split_page(client, img_2x, rate_limiter, model_mgr, log_func=log_func)
        if res_split:
            result_text = res_split
            winning_strategy = "SPLIT"

    # Step 3: Local OCR
    if not result_text:
        res_local = run_local_rapid_ocr(pdf_path, page_index)
        if res_local:
            result_text = res_local
            winning_strategy = "LOCAL-OCR"

    now_str = datetime.now().strftime("%H:%M:%S")

    # If still nothing, check blank or record failure
    if not result_text:
        # Check if genuinely blank (save "" and add to blank.txt)
        with csv_lock:
            with open(blank_txt, "a", encoding="utf-8") as bf:
                bf.write(f"{page_num}\n")
            with open(failed_txt, "a", encoding="utf-8") as ff:
                ff.write(f"{page_num}\n")
        atomic_write(page_file, "")
        log_func(f"[{now_str}] page {page_num}/{total_pages} FAILED / BLANK")
        return page_num, "FAILED", 0

    chars = len(result_text)
    atomic_write(page_file, result_text)

    with csv_lock:
        with open(strategy_csv, "a", encoding="utf-8") as f:
            f.write(f"{page_num},{winning_strategy},{chars}\n")

    log_func(f"[{now_str}] page {page_num}/{total_pages} strategy {winning_strategy} OK ({chars} chars)")
    return page_num, winning_strategy, chars


def build_concatenated_ocr(ocr_dir: Path, output_file: Path, total_pdf_pages: int, log_func=print):
    """Concatenate individual page files in page order and print final summary metrics."""
    strategy_counts = {}
    failed_pages = []
    blank_pages = []
    under_200_chars = []
    total_chars = 0

    blank_file = ocr_dir / "blank.txt"
    if blank_file.exists():
        with open(blank_file, "r", encoding="utf-8") as f:
            blank_pages = [int(line.strip()) for line in f if line.strip().isdigit()]

    with open(output_file, "w", encoding="utf-8") as out:
        for p in range(1, total_pdf_pages + 1):
            page_file = ocr_dir / f"page_{p:03d}.txt"
            if page_file.exists() and page_file.stat().st_size > 0:
                content = page_file.read_text(encoding="utf-8").strip()
                out.write(f"=== PAGE {p} ===\n")
                if content:
                    out.write(content + "\n\n")
                else:
                    out.write("\n")
                char_len = len(content)
                total_chars += char_len
                if char_len < 200:
                    under_200_chars.append((p, char_len))
            else:
                if p not in blank_pages:
                    failed_pages.append(p)

    strategy_csv = ocr_dir / "strategy.csv"
    if strategy_csv.exists():
        with open(strategy_csv, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    s = parts[1]
                    strategy_counts[s] = strategy_counts.get(s, 0) + 1

    summary = [
        "\n--- Final OCR Processing Summary ---",
        f"Pages OK per strategy: {strategy_counts}",
        f"Failed pages ({len(failed_pages)}): {failed_pages if failed_pages else 'None'}",
        f"Blank pages ({len(blank_pages)}): {blank_pages if blank_pages else 'None'}",
        f"Total characters: {total_chars}",
        f"Pages with < 200 characters ({len(under_200_chars)}): {under_200_chars}",
        f"Concatenated file: {output_file}"
    ]
    summary_text = "\n".join(summary)
    log_func(summary_text)
    return summary_text


def parse_page_range(range_str: str, max_pages: int) -> list[int]:
    """Parse range string like '76-77' or '1-122'."""
    pages = set()
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            s, e = part.split("-", 1)
            for p in range(max(1, int(s)), min(max_pages, int(e)) + 1):
                pages.add(p)
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= max_pages:
                pages.add(p)
    return sorted(list(pages))


def main():
    parser = argparse.ArgumentParser(description="Resilient fast-failover Gemini OCR pipeline for manual.pdf.")
    parser.add_argument("--pages", type=str, default=None, help="Page range to process (e.g., '76-77')")
    parser.add_argument("--workers", type=int, default=3, help="Number of worker threads (default 3)")
    parser.add_argument("--rpm", type=int, default=8, help="Max API requests per minute across all workers (default 8)")
    parser.add_argument("--pdf", type=str, default="data/manual.pdf", help="Input PDF path")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: {pdf_path} does not exist.")
        sys.exit(1)

    ocr_dir = Path("data/ocr")
    ocr_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = ocr_dir / "run.log"
    strategy_csv = ocr_dir / "strategy.csv"
    blank_txt = ocr_dir / "blank.txt"

    if not strategy_csv.exists():
        with open(strategy_csv, "w", encoding="utf-8") as f:
            f.write("page,strategy,chars\n")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY is not configured in .env.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    primary_env = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Candidate list in order per instructions
    candidate_models = [
        primary_env,
        "gemini-3-flash-preview",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest"
    ]
    model_mgr = ModelManager(candidate_models, client)

    doc = pdfium.PdfDocument(str(pdf_path))
    total_pages = len(doc)
    doc.close()

    # Load genuinely blank pages
    blank_pages = set()
    if blank_txt.exists():
        with open(blank_txt, "r", encoding="utf-8") as f:
            blank_pages = {int(line.strip()) for line in f if line.strip().isdigit()}

    # Check already done pages (> 20 chars, not EMPTY, or in blank.txt)
    done_pages = set()
    for p in range(1, total_pages + 1):
        if p in blank_pages:
            done_pages.add(p)
            continue
        p_file = ocr_dir / f"page_{p:03d}.txt"
        if p_file.exists():
            try:
                content = p_file.read_text(encoding="utf-8").strip()
                if len(content) > 20 and content != "EMPTY":
                    done_pages.add(p)
            except Exception:
                pass

    if args.pages:
        specified_pages = parse_page_range(args.pages, total_pages)
        pages_to_process = [p for p in specified_pages if p not in done_pages]
    else:
        pages_to_process = [p for p in range(1, total_pages + 1) if p not in done_pages]

    print(f"Total pages: {total_pages}, already done: {len(done_pages)}, to process: {len(pages_to_process)}")

    run_log_file = open(run_log_path, "a", encoding="utf-8")
    log_lock = threading.Lock()
    csv_lock = threading.Lock()

    def log(msg: str):
        with log_lock:
            print(msg, flush=True)
            run_log_file.write(msg + "\n")
            run_log_file.flush()

    rate_limiter = SlidingRateLimiter(max_calls=args.rpm, time_window=60.0)

    start_time = time.time()
    completed_count = 0
    total_target = len(pages_to_process)

    log(f"Starting OCR run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} with {args.workers} workers, max {args.rpm} rpm.")
    log(f"Available active models: {model_mgr.models}")

    if total_target > 0:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    process_page_job,
                    p,
                    total_pages,
                    pdf_path,
                    ocr_dir,
                    client,
                    rate_limiter,
                    model_mgr,
                    log,
                    csv_lock
                ): p for p in pages_to_process
            }

            for future in as_completed(futures):
                p_num = futures[future]
                completed_count += 1
                try:
                    future.result()
                except Exception as e:
                    log(f"Error in page {p_num}: {e}")

                if completed_count % 10 == 0 or completed_count == total_target:
                    elapsed = time.time() - start_time
                    rate = completed_count / elapsed if elapsed > 0 else 0
                    remaining = total_target - completed_count
                    est_minutes = (remaining / rate / 60) if rate > 0 else 0
                    now_s = datetime.now().strftime("%H:%M:%S")
                    log(f"[{now_s}] Progress: {completed_count}/{total_target} pages done ({est_minutes:.1f} est. minutes left)")

    build_concatenated_ocr(ocr_dir, Path("data/extracted_ocr.txt"), total_pages, log_func=log)
    run_log_file.close()


if __name__ == "__main__":
    main()
