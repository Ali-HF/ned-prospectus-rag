# Project Progress

## Done
- Set up Python 3.12 virtual environment in `.venv` with required packages.
- Migrated provider to Google Gemini (`langchain-google-genai`, `google-genai`) and pinned in `requirements.txt`.
- Downloaded and verified local embedding model `BAAI/bge-small-en-v1.5` (vector dimension 384).
- Configured `HF_HUB_OFFLINE=1` in `config.py` to ensure local embedding loads without touching the internet.
- Created configuration in `config.py` with all tunable RAG/LLM parameters and dynamic PDF path resolution (`data/manual.pdf` & `data/UGProspectus2025.pdf`).
- Created `system_prompt.txt`, `fallback.txt`, `.env.example`, `.env`, and `.gitignore`.
- Placed target prospectus in `data/manual.pdf` (and `data/UGProspectus2025.pdf`).
- Created placeholder files for `SPEC.md`: `ingest.py`, `rag.py`, `app.py`, `README.md`.
- Verified setup via `check_setup.py`: verified all packages import OK, embedding model produces vector length 384, and Gemini API generates response.
- Initialized local Git repository on `main` and committed updates.

## In progress
- Ready to implement document ingestion pipeline in `ingest.py`.

## Decisions
- Switched LLM provider to Google Gemini per user instruction to use `ChatGoogleGenerativeAI` and free-tier access.
- Implemented dynamic PDF path discovery in `config.py` prioritizing `data/manual.pdf` and `data/UGProspectus2025.pdf`.
- Maintained `TEMPERATURE = None` and `MAX_TOKENS = 1500` per Gemini 3 recommendations in `SPEC.md`.
- Configured automatic fallback in `check_setup.py` to nearest available flash model (`gemini-2.5-flash`) when `gemini-3.8-flash` hits daily free-tier quota limits (429 RESOURCE_EXHAUSTED).
- Set `HF_HUB_OFFLINE=1` in `config.py` so the embedding model loads strictly from local cache.

## Known issues
- Free-tier quota on `gemini-3.8-flash` is currently rate-limited (429 RESOURCE_EXHAUSTED); `gemini-2.5-flash` works reliably without quota errors.

## Next step
- Implement `ingest.py` for parsing `data/manual.pdf` with `pdfplumber`, chunking with `RecursiveCharacterTextSplitter`, and persisting embeddings in `./chroma_db`.
