"""Document ingestion pipeline for the RAG chatbot.

Reads scanned prospectus OCR pages, cleans recurring headers/footers,
tracks sections/headings, performs table-aware chunking, embeds using
BAAI/bge-small-en-v1.5, and indexes into ChromaDB with cosine distance.
"""

import os
import re
import json
import time
from pathlib import Path
from typing import Any
from collections import Counter

from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

import config


def get_ocr_pages() -> dict[int, str]:
    """Load prospectus pages from data/ocr/page_NNN.txt or data/UGProspectus2025_ocr.txt."""
    ocr_dir = config.DATA_DIR / "ocr"
    page_files = sorted(ocr_dir.glob("page_*.txt"))
    pages: dict[int, str] = {}

    if page_files:
        print(f"Reading {len(page_files)} page files from {ocr_dir}...")
        for pf in page_files:
            try:
                num_part = pf.stem.split("_")[1]
                p_num = int(num_part)
                text = pf.read_text(encoding="utf-8").strip()
                pages[p_num] = text
            except Exception as e:
                print(f"Warning: Could not read {pf}: {e}")
        return pages

    # Fallback to monolithic OCR file
    ocr_mono = config.DATA_DIR / "UGProspectus2025_ocr.txt"
    if not ocr_mono.exists():
        raise FileNotFoundError(f"Neither {ocr_dir} nor {ocr_mono} exists.")

    print(f"Reading monolithic OCR file from {ocr_mono}...")
    content = ocr_mono.read_text(encoding="utf-8")
    lines = content.splitlines()

    marker_regex = r"^=====\s*PAGE\s*(\d+)\s*=====$"
    markers: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        m = re.match(marker_regex, line.strip(), re.IGNORECASE)
        if m:
            markers.append((int(m.group(1)), i))

    if not markers:
        raise ValueError(f"No page markers found in {ocr_mono}.")

    print(f"Detected page marker pattern: '===== PAGE N =====' ({len(markers)} markers found)")
    for idx, (p_num, line_idx) in enumerate(markers):
        start = line_idx + 1
        end = markers[idx + 1][1] if idx + 1 < len(markers) else len(lines)
        page_text = "\n".join(lines[start:end]).strip()
        pages[p_num] = page_text

    return pages


def clean_prospectus_pages(raw_pages: dict[int, str]) -> tuple[dict[int, str], list[str]]:
    """Clean pages by removing repetitive headers/footers, joining hyphens, and normalizing whitespace."""
    total_pages = len(raw_pages)
    if total_pages == 0:
        return {}, []

    # 1. Identify lines that appear on > 25% of pages or are lone page numbers
    # We ignore empty pages and table lines for repetition check
    page_lines_map: dict[int, list[str]] = {}
    for p_num, text in raw_pages.items():
        page_lines_map[p_num] = [line.strip() for line in text.splitlines()]

    line_page_counts: Counter[str] = Counter()
    for p_num, lines in page_lines_map.items():
        seen_on_page: set[str] = set()
        for line in lines:
            if not line or line.startswith("|"):
                continue
            # Strip digits and whitespace to identify recurring template lines
            norm = re.sub(r"[\d\s]+", " ", line).strip()
            # Also lowercase to match subtle OCR variations
            if norm:
                seen_on_page.add(norm.lower())
        for norm in seen_on_page:
            line_page_counts[norm] += 1

    # Candidate repeating lines (> 25% of pages)
    # Exclude structural words like course levels
    excluded_keywords = {"first year", "second year", "third year", "final year", "spring semester", "fall semester"}
    repeating_templates: set[str] = {
        tmpl for tmpl, count in line_page_counts.items()
        if (count / total_pages) > 0.25 and tmpl not in excluded_keywords
    }

    removed_samples_counter: Counter[str] = Counter()
    cleaned_pages: dict[int, str] = {}

    for p_num, lines in page_lines_map.items():
        filtered_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                filtered_lines.append("")
                continue

            # Check if line is ONLY a page number
            if re.fullmatch(r"^\d{1,3}$", stripped) or re.fullmatch(r"^[ivxlcdm]{1,4}$", stripped, re.IGNORECASE):
                removed_samples_counter[stripped] += 1
                continue

            # Check if line matches repeating header/footer template
            norm = re.sub(r"[\d\s]+", " ", stripped).strip().lower()
            if norm in repeating_templates:
                removed_samples_counter[stripped] += 1
                continue

            filtered_lines.append(line)

        page_str = "\n".join(filtered_lines)

        # 2. De-hyphenate broken words across line boundaries
        # Join ("admis-\nsion" -> "admission") but never join if next line starts with digit, bullet, or uppercase
        def hyphen_replacer(match: re.Match) -> str:
            word_part = match.group(1)
            next_start = match.group(2)
            # If next_start begins with uppercase, digit, or bullet symbol, keep hyphen
            if re.match(r"^([A-Z0-9\*\-\•\(\[])", next_start):
                return match.group(0)
            return word_part + next_start

        page_str = re.sub(r"(\b[A-Za-z]+)-\n\s*([A-Za-z0-9\*\-\•\(\[])", hyphen_replacer, page_str)

        # 3. Normalize whitespace and blank lines while preserving Markdown tables exactly
        norm_lines: list[str] = []
        for l in page_str.splitlines():
            if l.strip().startswith("|"):
                norm_lines.append(l)  # Preserve Markdown table rows exactly
            else:
                collapsed = re.sub(r"[ \t]+", " ", l)
                norm_lines.append(collapsed.strip())

        rejoined = "\n".join(norm_lines)
        rejoined = re.sub(r"\n{3,}", "\n\n", rejoined).strip()
        cleaned_pages[p_num] = rejoined

    top_removed = [f"'{line}' (x{count})" for line, count in removed_samples_counter.most_common(10)]
    return cleaned_pages, top_removed


def is_heading_line(line: str) -> bool:
    """Detect section heading (e.g., '4.1 Title', 'SECTION 5 ...', or short ALL-CAPS line)."""
    s = line.strip()
    if not s or len(s) > 80:
        return False
    if s.startswith("|") or s.startswith("*"):
        return False

    # e.g., '4.1 Something', '1.2.3 Title'
    if re.match(r"^\d+(\.\d+)*\s+[A-Za-z]", s):
        return True

    # e.g., 'SECTION 5 ...' or 'CHAPTER 4 ...'
    if re.match(r"^(SECTION|CHAPTER)\s+\d+", s, re.IGNORECASE):
        return True

    # Short ALL-CAPS line with at least 3 letters
    letters = [ch for ch in s if ch.isalpha()]
    if len(letters) >= 3 and s.isupper():
        return True

    return False


def chunk_table_block(table_lines: list[str], section_title: str) -> list[str]:
    """Chunk a table block.
    
    If it fits in 1500 chars, never split it. Otherwise, split between rows
    and repeat the header row and section title at the top of every piece.
    """
    full_table_text = "\n".join(table_lines)
    if len(full_table_text) <= 1500:
        return [full_table_text]

    # Find table header
    header_lines: list[str] = []
    data_rows: list[str] = []
    is_markdown = any(l.strip().startswith("|") for l in table_lines)

    if is_markdown:
        header_lines.append(table_lines[0])
        if len(table_lines) > 1 and "---" in table_lines[1]:
            header_lines.append(table_lines[1])
            data_rows = table_lines[2:]
        else:
            data_rows = table_lines[1:]
    else:
        # Plain text table
        header_lines.append(table_lines[0])
        data_rows = table_lines[1:]

    prefix_parts = []
    if section_title:
        prefix_parts.append(section_title)
    if header_lines:
        prefix_parts.append("\n".join(header_lines))
    prefix_str = "\n".join(prefix_parts) + "\n"

    chunks: list[str] = []
    current_piece_rows: list[str] = []

    for row in data_rows:
        candidate_text = prefix_str + "\n".join(current_piece_rows + [row])
        if len(candidate_text) > 1400 and current_piece_rows:
            chunks.append(prefix_str + "\n".join(current_piece_rows))
            current_piece_rows = [row]
        else:
            current_piece_rows.append(row)

    if current_piece_rows:
        chunks.append(prefix_str + "\n".join(current_piece_rows))

    return chunks if chunks else [full_table_text]


def extract_table_and_text_blocks(page_text: str) -> list[dict[str, Any]]:
    """Segment page text into prose blocks and consecutive table blocks."""
    lines = page_text.splitlines()
    blocks: list[dict[str, Any]] = []
    curr_prose: list[str] = []
    curr_table: list[str] = []

    def flush_prose():
        if curr_prose:
            blocks.append({"type": "prose", "text": "\n".join(curr_prose).strip()})
            curr_prose.clear()

    def flush_table():
        if curr_table:
            blocks.append({"type": "table", "lines": list(curr_table)})
            curr_table.clear()

    for line in lines:
        stripped = line.strip()
        # Markdown table row
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_prose()
            curr_table.append(line)
        else:
            flush_table()
            curr_prose.append(line)

    flush_prose()
    flush_table()
    return blocks


def create_chunks(cleaned_pages: dict[int, str]) -> list[dict[str, Any]]:
    """Split cleaned pages into chunks adhering to boundaries, table preservation, and metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks: list[dict[str, Any]] = []
    current_section = ""
    chunk_counter = 1

    sorted_pnums = sorted(cleaned_pages.keys())

    for idx, p_num in enumerate(sorted_pnums):
        text = cleaned_pages[p_num]
        if not text:
            continue

        printed_page = (p_num - config.PRINTED_PAGE_OFFSET) if p_num > config.PRINTED_PAGE_OFFSET else None
        blocks = extract_table_and_text_blocks(text)

        for block in blocks:
            if block["type"] == "table":
                table_chunks = chunk_table_block(block["lines"], current_section)
                for tc in table_chunks:
                    if len(tc.strip()) >= 40:
                        chunks.append({
                            "text": tc.strip(),
                            "page": p_num,
                            "printed_page": printed_page,
                            "section": current_section,
                            "source": "NED Undergraduate Prospectus 2025",
                            "chunk_id": f"chunk_{chunk_counter:04d}"
                        })
                        chunk_counter += 1
            else:
                prose_text = block["text"]
                # Look for headings to update current_section
                for line in prose_text.splitlines():
                    if is_heading_line(line):
                        current_section = line.strip()

                raw_chunks = splitter.split_text(prose_text)
                for rc in raw_chunks:
                    # Update heading if inside this chunk
                    for l in rc.splitlines():
                        if is_heading_line(l):
                            current_section = l.strip()

                    clean_rc = rc.strip()
                    if len(clean_rc) >= 40:
                        chunks.append({
                            "text": clean_rc,
                            "page": p_num,
                            "printed_page": printed_page,
                            "section": current_section,
                            "source": "NED Undergraduate Prospectus 2025",
                            "chunk_id": f"chunk_{chunk_counter:04d}"
                        })
                        chunk_counter += 1

        # Check mid-sentence page boundary merge:
        # If last chunk on current page ends mid-sentence and next page starts with lowercase letter
        if idx + 1 < len(sorted_pnums) and chunks:
            next_pnum = sorted_pnums[idx + 1]
            next_text = cleaned_pages[next_pnum].strip()
            last_chunk = chunks[-1]

            if last_chunk["page"] == p_num and next_text:
                ends_mid_sentence = not last_chunk["text"].rstrip().endswith((".", "!", "?", ":", "\"", "'"))
                starts_lowercase = next_text[0].islower()
                if ends_mid_sentence and starts_lowercase:
                    # Take first sentence/line from next page and append to last chunk
                    next_first_line = next_text.splitlines()[0]
                    last_chunk["text"] += " " + next_first_line
                    # Remove that line from next page's cleaned content
                    remaining_next = "\n".join(cleaned_pages[next_pnum].splitlines()[1:]).strip()
                    cleaned_pages[next_pnum] = remaining_next

    return chunks


def build_index(force: bool = True) -> Chroma:
    """Build or rebuild vector store collection in ChromaDB."""
    persist_dir = config.CHROMA_PERSIST_DIRECTORY
    collection_name = config.COLLECTION_NAME

    embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"}
    )

    if force:
        print("Rebuilding ChromaDB collection...")
        try:
            vectorstore.delete_collection()
        except Exception:
            pass
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_dir,
            collection_metadata={"hnsw:space": "cosine"}
        )

    return vectorstore


def main():
    """Execute ingestion pipeline: read, clean, chunk, embed, store, and report."""
    start_time = time.time()
    print("=== Starting Prospectus Ingestion Pipeline ===")

    # 1. Source of text
    raw_pages = get_ocr_pages()
    total_pages_read = len(raw_pages)
    empty_pages = [p for p, t in raw_pages.items() if not t.strip()]

    # 2. Clean pages
    cleaned_pages, top_removed = clean_prospectus_pages(raw_pages)

    # 3. Save extracted.txt with markers
    extracted_txt_path = Path("extracted.txt")
    with open(extracted_txt_path, "w", encoding="utf-8") as f:
        for p_num in sorted(cleaned_pages.keys()):
            f.write(f"=== PAGE {p_num} ===\n")
            p_text = cleaned_pages[p_num]
            if p_text:
                f.write(p_text + "\n\n")
            else:
                f.write("\n")
    print(f"Saved cleaned full text to {extracted_txt_path}")

    # 4. Create chunks
    chunks = create_chunks(cleaned_pages)
    num_chunks = len(chunks)
    avg_len = sum(len(c["text"]) for c in chunks) / num_chunks if num_chunks else 0
    max_len = max(len(c["text"]) for c in chunks) if num_chunks else 0

    # 5. Save chunks to chunks_debug.jsonl
    chunks_debug_path = Path("chunks_debug.jsonl")
    with open(chunks_debug_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Saved {num_chunks} chunks to {chunks_debug_path}")

    # 6. Embed and store in Chroma
    vectorstore = build_index(force=True)

    batch_size = config.EMBEDDING_BATCH_SIZE
    texts = [c["text"] for c in chunks]
    metadatas = [
        {
            "page": c["page"],
            "printed_page": c["printed_page"] if c["printed_page"] is not None else 0,
            "section": c["section"],
            "source": c["source"],
            "chunk_id": c["chunk_id"]
        }
        for c in chunks
    ]
    ids = [c["chunk_id"] for c in chunks]

    print(f"Embedding and storing {num_chunks} chunks in ChromaDB (batch size: {batch_size})...")
    with tqdm(total=num_chunks, desc="Indexing Chunks") as pbar:
        for i in range(0, num_chunks, batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            vectorstore.add_texts(texts=batch_texts, metadatas=batch_metas, ids=batch_ids)
            pbar.update(len(batch_texts))

    chroma_count = vectorstore._collection.count()
    elapsed = time.time() - start_time

    # Report
    print("\n" + "=" * 50)
    print("--- INGESTION REPORT ---")
    print(f"Pages read: {total_pages_read}")
    print(f"Empty pages ({len(empty_pages)}): {empty_pages if empty_pages else 'None'}")
    print(f"Chunks created: {num_chunks}")
    print(f"Average chunk length: {avg_len:.1f} characters")
    print(f"Max chunk length: {max_len} characters")
    print(f"Vector count in Chroma: {chroma_count} (Matches chunks: {chroma_count == num_chunks})")
    print(f"Total processing time: {elapsed:.2f} seconds")

    print("\n--- Top 10 Removed Repeating Header/Footer Templates ---")
    for r in top_removed:
        print(f"  - {r}")

    # Find 3 sample chunks: one normal, one fee, one seat
    normal_chunk = next(c for c in chunks if len(c["text"]) > 200 and "table" not in c["text"].lower() and "fee" not in c["text"].lower() and "seat" not in c["text"].lower())
    fee_chunk = next(c for c in chunks if "tuition" in c["text"].lower() and "fee" in c["text"].lower())
    seat_chunk = next(c for c in chunks if "seats" in c["text"].lower() or "self finance" in c["text"].lower())

    print("\n--- SAMPLE CHUNK 1: Normal Paragraph ---")
    print(f"ID: {normal_chunk['chunk_id']} | Page: {normal_chunk['page']} (Printed: {normal_chunk['printed_page']}) | Section: {normal_chunk['section']}")
    print(normal_chunk["text"])

    print("\n--- SAMPLE CHUNK 2: Fee Table Chunk ---")
    print(f"ID: {fee_chunk['chunk_id']} | Page: {fee_chunk['page']} (Printed: {fee_chunk['printed_page']}) | Section: {fee_chunk['section']}")
    print(fee_chunk["text"])

    print("\n--- SAMPLE CHUNK 3: Seat/Merit Table Chunk ---")
    print(f"ID: {seat_chunk['chunk_id']} | Page: {seat_chunk['page']} (Printed: {seat_chunk['printed_page']}) | Section: {seat_chunk['section']}")
    print(seat_chunk["text"])

    # 7. Sanity searches
    queries = [
        "What is the fee for Computer Systems Engineering?",
        "What is the eligibility criteria for admission?",
        "What is the weather in Paris?"
    ]

    print("\n" + "=" * 50)
    print("--- CHROMA SANITY SEARCHES (Cosine Similarity = 1 - Distance) ---")
    for q in queries:
        print(f"\nQuery: \"{q}\"")
        results = vectorstore.similarity_search_with_score(q, k=3)
        for rank, (doc, dist) in enumerate(results, start=1):
            sim = 1.0 - dist
            p_val = doc.metadata.get("page")
            pp_val = doc.metadata.get("printed_page")
            sec_val = doc.metadata.get("section")
            snippet = doc.page_content[:160].replace("\n", " ")
            print(f"  [{rank}] Sim: {sim:.4f} (dist: {dist:.4f}) | Page: {p_val} (Printed: {pp_val}) | Section: '{sec_val}'")
            print(f"      Snippet: {snippet}...")


if __name__ == "__main__":
    main()
