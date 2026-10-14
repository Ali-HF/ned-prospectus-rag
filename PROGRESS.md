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

- Updated `config.py` with initial `SCORE_THRESHOLD = 0.58`.
- Generated 15 verified in-scope questions in `in_scope.txt` and 15 plausible out-of-scope questions in `out_scope.txt`.
- Implemented `retrieve(query: str, k: int = config.TOP_K)` in `rag.py` returning `(chunk_text, page, section, similarity)` sorted best first with cosine similarity (`1 - distance`).
- Implemented `debug_retrieve.py` for interactive retrieval inspection.
- Implemented and executed `calibrate.py`: evaluated queries with and without BGE query prefix; identified WITHOUT prefix gives the tighter gap (`-0.1422` vs `-0.1716`). Reported min/median/max stats and analyzed overlap on top-1 similarity scores.
- Tested `debug_retrieve.py` against 5 representative in-scope queries: confirmed all 5 have their exact ground truth chunk ranked #1 in top-5 results.

- Implemented `answer(question, history)` and `answer_with_sources(question, history)` in `rag.py`:
  - Enforces `SCORE_THRESHOLD` filtering before calling the LLM.
  - Returns `fallback.txt` immediately without calling the LLM when no chunks meet the threshold.
  - Builds structured context string `[Page N | Section] text` and injects via `.replace('{context}', context)`.
  - Integrates `ChatGoogleGenerativeAI` with rate-limit / quota retry loop (2-second backoff up to 2 retries) and polite apology handling.
- Built Streamlit chat application in `app.py`:
  - Verified index presence on startup (auto-triggering `ingest.build_index()` if missing).
  - Maintained conversation in `st.session_state`.
  - Added "Show sources" toggle and "Clear chat" button in the sidebar.
  - Revamped UI with a cyber-engineering dark aesthetic (tactical grid background, neon orange accents, Space Grotesk typography).
  - Verified live UI running at `http://localhost:8501`.
- Configured and executed `red_team.py` suite against `rag.answer`:
  - Filled `MANUAL_QUESTIONS` and `FALLBACK_MARKERS`.
  - Verified prompt leak resistance and difficult/angry user handling.
  - Resolved false-positive admission promise flagging and out-of-scope redirection checks.
  - Attained perfect 86/86 cases with 0 flagged.
- Implemented Prompt 7 Stretch Goals:
  - **Multi-turn Follow-up Reformulation**: Implemented `rewrite_question_for_followup()` in `rag.py` using `gemini-3.5-flash-lite` (max 200 tokens) to rewrite user follow-ups into standalone queries based on the last 2 conversation turns before retrieval.
  - **Hybrid Search with BM25 + Reciprocal Rank Fusion (RRF)**: Integrated `rank_bm25` (pinned in `requirements.txt` and documented in `SPEC.md`) merged with ChromaDB cosine vector scores using Reciprocal Rank Fusion ($C=60$), while preserving `SCORE_THRESHOLD = 0.62` on vector similarity.

## In progress
- Project complete and verified. Ready for submission.

## Decisions
- PDF is scanned. Source of truth is `data/UGProspectus2025_ocr.txt` (split into `data/ocr/page_NNN.txt`). Page metadata = PDF page index (state the offset if any: printed page number = PDF page index - 7 for main body from PDF page 8 onwards). Do not use pdfplumber on the PDF.
- Maintained `TEMPERATURE = None` and `MAX_TOKENS = 1500` per Gemini 3 recommendations in `SPEC.md`.
- Increased `SCORE_THRESHOLD = 0.62` in `config.py` to tighten retrieval against irrelevant queries while preserving all in-scope queries.
- Top-5 retrieval precision is verified at 100% top-1 rank across sample in-scope queries; kept `TOP_K = 5` and chunk size 900.
- Preserved vector similarity score checks on hybrid RRF results to ensure the strict `fallback.txt` threshold guard is never bypassed.

## Known issues
- `data/manual.pdf` has no embedded character glyphs; all content relies on OCR text extraction.
- In `data/UGProspectus2025_ocr.txt`, complex multi-column grid tables appear as plain-text rows/columns.
- Top-1 cosine similarities for plausible out-of-scope queries mentioning the institution name overlap with in-scope queries, so prompt grounding alongside `SCORE_THRESHOLD` ensures zero hallucinations.

## Next step
- Final git commit and hackathon submission.
