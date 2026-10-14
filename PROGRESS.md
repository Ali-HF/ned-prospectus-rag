# Project Progress

## Done
- Set up Python 3.12 virtual environment in `.venv` with required packages.
- Migrated provider to Google Gemini (`langchain-google-genai`, `google-genai`) and pinned in `requirements.txt`.
- Downloaded and verified local embedding model `BAAI/bge-small-en-v1.5` (vector dimension 384).
- Configured `HF_HUB_OFFLINE=1` in `config.py` to ensure local embedding loads without touching the internet.
- Created configuration in `config.py` with all tunable RAG/LLM parameters and dynamic PDF path resolution (`data/manual.pdf` & `data/UGProspectus2025.pdf`).
- Created `system_prompt.txt`, `fallback.txt`, `.env.example`, `.env`, and `.gitignore`.
- Placed target prospectus in `data/manual.pdf` (and `data/UGProspectus2025.pdf`).
- Verified setup via `check_setup.py`: verified all packages import OK, embedding model produces vector length 384, and Gemini API generates response.
- Stopped active background OCR runners (`ocr_pdf.py` and `ocr_local.py`).
- Adopted `data/UGProspectus2025_ocr.txt` as official source of truth, verified 122 pages, and split into `data/ocr/page_001.txt` ... `data/ocr/page_122.txt`.
- Implemented `ingest.py` with:
  - Automatic detection of `data/ocr/page_NNN.txt` (or fallback to `data/UGProspectus2025_ocr.txt`).
  - Printed page offset resolution (`printed_page = page - 7`).
  - Cleaning recurring header/footer lines (>25% repetition threshold) and hyphenated word repair.
  - Section title tracking (e.g. `4.1 Title`, `SECTION 5`, or short ALL-CAPS lines).
  - Table-aware chunking (preserving blocks under 1500 chars, repeating header on split, boundary mid-sentence continuation handling).
  - Batch embedding with `BAAI/bge-small-en-v1.5` (offline cache, batch size 32) into ChromaDB `prospectus` collection (`hnsw:space: cosine`).
  - Generated `extracted.txt` and `chunks_debug.jsonl`.
- Executed `ingest.py`: produced 562 chunks, verified ChromaDB vector count equals exactly 562, and confirmed clean cosine similarity separation between in-domain questions (~0.71-0.73) and out-of-domain sanity checks (<0.48).

## In progress
- Ingestion complete; ready to implement retrieval and QA pipeline in `rag.py`.

## Decisions
- PDF is scanned. Source of truth is `data/UGProspectus2025_ocr.txt` (split into `data/ocr/page_NNN.txt`). Page metadata = PDF page index (state the offset if any: printed page number = PDF page index - 7 for main body from PDF page 8 onwards). Do not use pdfplumber on the PDF.
- Maintained `TEMPERATURE = None` and `MAX_TOKENS = 1500` per Gemini 3 recommendations in `SPEC.md`.

## Known issues
- `data/manual.pdf` has no embedded character glyphs; all content relies on OCR text extraction.
- In `data/UGProspectus2025_ocr.txt`, complex multi-column grid tables (e.g., fee schedules and seat allocations) appear as plain-text rows/columns or one-value-per-line rather than markdown pipe tables (`|`).

## Next step
- Implement `rag.py` exposing `answer(question: str, history: list | None = None) -> str` adhering to the prompt template and rate-limit retry requirements.
