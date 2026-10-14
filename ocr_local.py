import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import pypdfium2 as pdfium
import numpy as np
from PIL import Image

_engine_instance = None


def get_ocr_engine():
    """Initialize or reuse RapidOCR instance within each worker process."""
    global _engine_instance
    if _engine_instance is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine_instance = RapidOCR()
    return _engine_instance


def render_page_image_3x(pdf_path: Path, page_index: int) -> Image.Image:
    """Render a single page at scale 3.0."""
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        page = doc[page_index]
        return page.render(scale=3.0).to_pil()
    finally:
        doc.close()


def process_local_page(page_num: int, total_pages: int, pdf_path: str, output_dir: str) -> tuple[int, int]:
    """Render page at scale 3.0, run RapidOCR, sort by y then x, and save."""
    out_dir = Path(output_dir)
    out_file = out_dir / f"page_{page_num:03d}.txt"

    # Resumable: skip non-empty > 20 chars
    if out_file.exists() and out_file.stat().st_size > 20:
        chars = len(out_file.read_text(encoding="utf-8").strip())
        return page_num, chars

    pdf_p = Path(pdf_path)
    page_index = page_num - 1

    img_3x = render_page_image_3x(pdf_p, page_index)
    img_np = np.array(img_3x)

    engine = get_ocr_engine()
    result, _ = engine(img_np)

    if not result:
        # Blank or no text detected
        tmp = out_file.with_suffix(".tmp")
        tmp.write_text("", encoding="utf-8")
        tmp.replace(out_file)
        return page_num, 0

    # Sort boxes by top-y then left-x
    sorted_boxes = sorted(result, key=lambda item: (min(pt[1] for pt in item[0]), min(pt[0] for pt in item[0])))

    # Group into lines with a vertical threshold (15 pixels at scale 3.0)
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

    # Group lines into paragraphs where there is larger vertical spacing or empty lines
    full_text = "\n".join(lines).strip()

    # Save to temp file and rename atomically
    tmp = out_file.with_suffix(".tmp")
    tmp.write_text(full_text, encoding="utf-8")
    tmp.replace(out_file)

    chars = len(full_text)
    return page_num, chars


def parse_page_range(range_str: str, max_pages: int) -> list[int]:
    """Parse range string like '1-122'."""
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
    parser = argparse.ArgumentParser(description="Local OCR pipeline using rapidocr-onnxruntime.")
    parser.add_argument("--pages", type=str, default=None, help="Page range to process")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker processes (default 2)")
    parser.add_argument("--pdf", type=str, default="data/manual.pdf", help="Path to input PDF")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found.")
        sys.exit(1)

    out_dir = Path("data/ocr_local")
    out_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = out_dir / "run.log"

    doc = pdfium.PdfDocument(str(pdf_path))
    total_pages = len(doc)
    doc.close()

    # Check already done pages
    done_pages = set()
    for p in range(1, total_pages + 1):
        pf = out_dir / f"page_{p:03d}.txt"
        if pf.exists() and pf.stat().st_size > 20:
            done_pages.add(p)

    if args.pages:
        specified = parse_page_range(args.pages, total_pages)
        pages_to_process = [p for p in specified if p not in done_pages]
    else:
        pages_to_process = [p for p in range(1, total_pages + 1) if p not in done_pages]

    run_log = open(run_log_path, "a", encoding="utf-8")

    def log(msg: str):
        print(msg, flush=True)
        run_log.write(msg + "\n")
        run_log.flush()

    log(f"Starting local OCR at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} with {args.workers} workers.")
    log(f"Total pages: {total_pages}, already done: {len(done_pages)}, to process: {len(pages_to_process)}")

    start_time = time.time()
    completed_count = 0
    total_target = len(pages_to_process)

    if total_target > 0:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    process_local_page,
                    p,
                    total_pages,
                    str(pdf_path),
                    str(out_dir)
                ): p for p in pages_to_process
            }

            for future in as_completed(futures):
                p_num = futures[future]
                completed_count += 1
                try:
                    p_res, chars = future.result()
                    now_s = datetime.now().strftime("%H:%M:%S")
                    log(f"[{now_s}] page {p_res}/{total_pages} LOCAL OK ({chars} chars)")
                except Exception as e:
                    now_s = datetime.now().strftime("%H:%M:%S")
                    log(f"[{now_s}] page {p_num}/{total_pages} LOCAL FAILED: {e}")

                if completed_count % 10 == 0 or completed_count == total_target:
                    elapsed = time.time() - start_time
                    rate = completed_count / elapsed if elapsed > 0 else 0
                    remaining = total_target - completed_count
                    est_minutes = (remaining / rate / 60) if rate > 0 else 0
                    now_s = datetime.now().strftime("%H:%M:%S")
                    log(f"[{now_s}] Progress: {completed_count}/{total_target} pages done ({est_minutes:.1f} est. minutes left)")

    log(f"Local OCR finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_log.close()


if __name__ == "__main__":
    main()
