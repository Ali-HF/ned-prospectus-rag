# NED Guide RAG Support Bot

A RAG chatbot that answers questions grounded strictly in the NED Undergraduate Prospectus 2025, never invents facts or unauthorized admission promises, and stays composed with difficult or adversarial users.

## Tech Stack
- **PDF Extraction**: Scanned PDF parsed via OCR into `data/UGProspectus2025_ocr.txt` and split into `data/ocr/page_NNN.txt`.
- **Chunking**: LangChain `RecursiveCharacterTextSplitter` (chunk size: 900, overlap: 150) with table-aware chunk boundaries.
- **Embeddings**: `BAAI/bge-small-en-v1.5` run locally via `langchain-huggingface` (offline cached, vector dimension 384).
- **Vector Store**: ChromaDB via `langchain-chroma` in `./chroma_db` (cosine distance).
- **LLM**: Google Gemini via `langchain-google-genai` (`gemini-3.5-flash-lite`, temperature `None`, max tokens `1500`).
- **UI**: Streamlit chat interface (`app.py`).

## Quickstart

1. **Create and activate environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API key**:
   ```bash
   cp .env.example .env
   # Add your Google Gemini API key to .env:
   # GOOGLE_API_KEY=your_key_here
   ```

3. **Build vector index** (only needed once, automatically handled if missing):
   ```bash
   python ingest.py
   ```

4. **Launch Streamlit Chat UI**:
   ```bash
   streamlit run app.py
   ```

5. **Run Red-Team Evaluation**:
   ```bash
   python red_team.py --module rag --func answer
   ```
