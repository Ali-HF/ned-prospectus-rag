import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHROMA_PERSIST_DIRECTORY = str(BASE_DIR / "chroma_db")

def get_pdf_path():
    """Locate the prospectus/manual PDF in the data directory."""
    # Preferred names
    candidates = ["UGProspectus2025.pdf", "manual.pdf", "prospectus.pdf"]
    for name in candidates:
        candidate_path = DATA_DIR / name
        if candidate_path.exists():
            return candidate_path
    # Fallback to any PDF in data/
    pdfs = list(DATA_DIR.glob("*.pdf"))
    if pdfs:
        return pdfs[0]
    return DATA_DIR / "UGProspectus2025.pdf"

PDF_PATH = get_pdf_path()

# Model & generation settings
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MAX_TOKENS = 1500
TEMPERATURE = None

# Retrieval & chunking settings
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
TOP_K = 5
SCORE_THRESHOLD = 0.40

# Embedding settings
os.environ.setdefault("HF_HUB_OFFLINE", "1")
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_MODEL_NAME = EMBEDDING_MODEL
