"""RAG retrieval and question answering module.

Provides retrieval of relevant prospectus chunks from ChromaDB with cosine
similarity and answering functionality.
"""

from typing import Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

import config

_vectorstore: Chroma | None = None
_embeddings: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return singleton HuggingFaceEmbeddings instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embeddings


def get_vectorstore() -> Chroma:
    """Return singleton Chroma vectorstore instance."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            collection_name=config.COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=config.CHROMA_PERSIST_DIRECTORY,
            collection_metadata={"hnsw:space": "cosine"}
        )
    return _vectorstore


def retrieve(
    query: str,
    k: int = config.TOP_K,
    use_prefix: bool = False
) -> list[tuple[str, int, str, float]]:
    """Retrieve top k relevant chunks from ChromaDB.

    Args:
        query: User input query text.
        k: Number of chunks to retrieve (defaults to config.TOP_K).
        use_prefix: Whether to prepend bge query instruction prefix.

    Returns:
        List of tuples: (chunk_text, page, section, similarity)
        sorted best first, where similarity = 1 - cosine distance.
    """
    vectorstore = get_vectorstore()

    search_query = query
    if use_prefix:
        search_query = f"Represent this sentence for searching relevant passages: {query}"

    # Chroma returns (Document, distance) where distance is cosine distance for hnsw:space: cosine
    results = vectorstore.similarity_search_with_score(search_query, k=k)

    retrieved: list[tuple[str, int, str, float]] = []
    for doc, dist in results:
        similarity = 1.0 - float(dist)
        meta = doc.metadata or {}
        page = meta.get("page", 0)
        section = meta.get("section", "")
        retrieved.append((doc.page_content, page, section, similarity))

    # Sort best first (highest similarity first)
    retrieved.sort(key=lambda item: item[3], reverse=True)
    return retrieved


def answer(question: str, history: list | None = None) -> str:
    """Generate answer for a user question using RAG pipeline (stub for next step)."""
    # Placeholder to satisfy interface required by SPEC.md
    chunks = retrieve(question, k=config.TOP_K)
    if not chunks or chunks[0][3] < config.SCORE_THRESHOLD:
        fallback_path = config.BASE_DIR / "fallback.txt"
        if fallback_path.exists():
            return fallback_path.read_text(encoding="utf-8").strip()
        return "I am sorry, but I can only answer questions from the undergraduate prospectus."
    return chunks[0][0]
