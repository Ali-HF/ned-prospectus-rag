# RAG support chatbot: spec
Goal: a chatbot for an edtech product that answers ONLY from one PDF manual, never invents features, and stays calm with rude users.

Stack (do not substitute anything):
- PDF parsing: PDF is scanned. Source of truth is data/UGProspectus2025_ocr.txt (split into data/ocr/page_NNN.txt). Page metadata = PDF page index (state the offset if any: printed page number = PDF page index - 7 for main body from PDF page 8 onwards). Do not use pdfplumber on the PDF.
- Chunking: langchain-text-splitters RecursiveCharacterTextSplitter
- Embeddings: sentence-transformers model BAAI/bge-small-en-v1.5, run locally through langchain-huggingface
- Vector store: ChromaDB through langchain-chroma, saved in ./chroma_db, cosine distance
- Hybrid search: BM25 keyword matching via rank_bm25 merged with vector scores using Reciprocal Rank Fusion (RRF), preserving SCORE_THRESHOLD filtering on vector similarity
- LLM: Google Gemini through langchain-google-genai ChatGoogleGenerativeAI, model name from env GEMINI_MODEL (default gemini-3.8-flash). In config.py set MAX_TOKENS = 1500 (Gemini 3 models use hidden thinking tokens that count toward the limit) and TEMPERATURE = None. Only pass temperature to the model if it is not None: Google recommends leaving Gemini 3 models at their default of 1.0, and lower values can cause loops. Use the lowest thinking level the integration allows.
- UI: Streamlit
- Secrets: GOOGLE_API_KEY in .env, loaded with python-dotenv. Never hardcode keys.

Files: ingest.py, rag.py, app.py, config.py, system_prompt.txt, fallback.txt, requirements.txt (pinned versions), .env.example, .gitignore (.env, .venv, chroma_db), README.md, PROGRESS.md

Rules:
- Keep code simple and readable, with small functions and a docstring on each, so a student can explain every line.
- All tunable numbers (chunk size, overlap, top-k, score threshold, model name, temperature, max tokens) live in config.py.
- Do not add features, libraries or files that are not listed here without asking me.
- rag.py must expose: answer(question: str, history: list | None = None) -> str
- On a 429 or quota error from the API, wait 2 seconds and retry up to 2 times (the free tier has rate limits).
- At the start of EVERY task, read SPEC.md and PROGRESS.md first.
- After finishing EVERY task, update PROGRESS.md before replying.
