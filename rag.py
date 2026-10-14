"""RAG retrieval and question answering module.

Provides retrieval of relevant prospectus chunks from ChromaDB with cosine
similarity and question answering backed by Google Gemini.
"""

from typing import Any
import re
import time
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

import config

logger = logging.getLogger(__name__)

_vectorstore: Chroma | None = None
_embeddings: HuggingFaceEmbeddings | None = None
_llm: ChatGoogleGenerativeAI | None = None


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


def get_llm() -> ChatGoogleGenerativeAI:
    """Return singleton ChatGoogleGenerativeAI instance."""
    global _llm
    if _llm is None:
        llm_kwargs: dict[str, Any] = {
            "model": config.GEMINI_MODEL,
            "max_output_tokens": config.MAX_TOKENS,
        }
        if config.TEMPERATURE is not None:
            llm_kwargs["temperature"] = config.TEMPERATURE

        _llm = ChatGoogleGenerativeAI(**llm_kwargs)
    return _llm


_rewrite_llm: ChatGoogleGenerativeAI | None = None


def get_rewrite_llm() -> ChatGoogleGenerativeAI:
    """Return singleton ChatGoogleGenerativeAI for follow-up rewriting."""
    global _rewrite_llm
    if _rewrite_llm is None:
        _rewrite_llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            max_output_tokens=200,
        )
    return _rewrite_llm


def rewrite_question_for_followup(
    question: str,
    history: list[dict[str, str]] | list[Any] | None
) -> str:
    """Rewrite follow-up question into standalone query using last 2 turns."""
    if not history:
        return question

    try:
        # Ignore initial greeting message from assistant so first user query isn't rewritten
        filtered_history = [
            item for item in history
            if not (
                (isinstance(item, dict) and item.get("role") == "assistant" and "Hello! I am" in str(item.get("content", "")))
                or (isinstance(item, (list, tuple)) and len(item) == 2 and item[0] == "assistant" and "Hello! I am" in str(item[1]))
            )
        ]
        if not filtered_history:
            return question

        # Take last 2 turns from filtered history
        recent = filtered_history[-2:]
        history_lines = []
        for item in recent:
            role = ""
            content = ""
            if isinstance(item, dict):
                role = str(item.get("role", "")).capitalize()
                content = str(item.get("content", ""))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                role = str(item[0]).capitalize()
                content = str(item[1])
            if role and content:
                history_lines.append(f"{role}: {content}")

        if not history_lines:
            return question

        history_context = "\n".join(history_lines)
        prompt = (
            "Given the following conversation history and the follow-up question, rewrite the follow-up "
            "question into a concise, standalone search question about the NED Undergraduate Prospectus 2025. "
            "Do NOT answer the question. Return ONLY the rewritten question text without quotes or explanations.\n\n"
            f"Conversation History:\n{history_context}\n\n"
            f"Follow-up Question: {question}\n\n"
            "Standalone Question:"
        )

        llm = get_rewrite_llm()
        res = llm.invoke([HumanMessage(content=prompt)])
        rewritten = _extract_text(res.content).strip().strip('"').strip("'")
        if rewritten and len(rewritten) > 3:
            return rewritten
    except Exception as exc:
        logger.warning("Follow-up rewrite failed, using original: %s", exc)

    return question


_bm25 = None
_all_chunks: list[dict[str, Any]] | None = None


def get_bm25_index():
    """Load all chunk documents from Chroma and build singleton BM25Okapi index."""
    global _bm25, _all_chunks
    if _bm25 is None or _all_chunks is None:
        try:
            from rank_bm25 import BM25Okapi
            vectorstore = get_vectorstore()
            # Fetch all documents in collection
            data = vectorstore.get(include=["documents", "metadatas"])
            docs = data.get("documents", [])
            metadatas = data.get("metadatas", [])
            _all_chunks = []
            tokenized_corpus = []
            for doc, meta in zip(docs, metadatas):
                meta = meta or {}
                _all_chunks.append({
                    "text": doc,
                    "page": meta.get("page", 0),
                    "section": meta.get("section", ""),
                })
                # Simple whitespace and punctuation tokenization for BM25
                tokens = re.findall(r"\w+", doc.lower())
                tokenized_corpus.append(tokens)

            if tokenized_corpus:
                _bm25 = BM25Okapi(tokenized_corpus)
        except Exception as exc:
            logger.warning("BM25 initialization skipped: %s", exc)
            _bm25 = None
    return _bm25, _all_chunks


def retrieve(
    query: str,
    k: int = config.TOP_K,
    use_prefix: bool = False
) -> list[tuple[str, int, str, float]]:
    """Retrieve top k relevant chunks using hybrid vector + BM25 reciprocal rank fusion (RRF).

    Vector similarity scores are preserved for downstream SCORE_THRESHOLD filtering.

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

    # 1. Dense vector search (fetch 2*k candidates for fusion)
    results = vectorstore.similarity_search_with_score(search_query, k=max(k * 2, 10))

    vector_candidates: dict[str, tuple[str, int, str, float]] = {}
    vector_ranks: dict[str, int] = {}
    for rank, (doc, dist) in enumerate(results, start=1):
        similarity = 1.0 - float(dist)
        meta = doc.metadata or {}
        page = meta.get("page", 0)
        section = meta.get("section", "")
        key = doc.page_content.strip()
        vector_candidates[key] = (doc.page_content, page, section, similarity)
        vector_ranks[key] = rank

    # 2. Sparse BM25 keyword search
    bm25, all_chunks = get_bm25_index()
    bm25_ranks: dict[str, int] = {}
    if bm25 and all_chunks:
        query_tokens = re.findall(r"\w+", query.lower())
        if query_tokens:
            bm25_scores = bm25.get_scores(query_tokens)
            # Get top indices
            top_bm25_indices = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True
            )[:max(k * 2, 10)]

            for bm_rank, idx in enumerate(top_bm25_indices, start=1):
                chunk = all_chunks[idx]
                key = chunk["text"].strip()
                bm25_ranks[key] = bm_rank

    # 3. Reciprocal Rank Fusion (RRF constant C = 60)
    # RRF score = 1/(60 + vector_rank) + 1/(60 + bm25_rank)
    C = 60
    fused_scores: dict[str, float] = {}
    for key, (text, page, section, sim) in vector_candidates.items():
        v_rank = vector_ranks[key]
        b_rank = bm25_ranks.get(key, 999)
        rrf_score = (1.0 / (C + v_rank)) + (1.0 / (C + b_rank))
        fused_scores[key] = rrf_score

    # Sort candidates by combined RRF score
    sorted_keys = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)[:k]

    # Return top-k tuples preserving original vector similarity
    retrieved = [vector_candidates[key] for key in sorted_keys]
    return retrieved


def load_fallback_text() -> str:
    """Read the standard fallback text from fallback.txt."""
    fallback_path = config.BASE_DIR / "fallback.txt"
    if fallback_path.exists():
        return fallback_path.read_text(encoding="utf-8").strip()
    return (
        "I couldn't find that in the NED Undergraduate Prospectus 2025, so I don't want to guess. "
        "I can help with undergraduate admissions and eligibility, merit and seat categories, "
        "programmes and departments, and fees, scholarships and hostels. For anything else, "
        "please check with the NED admissions office."
    )


def load_system_prompt_template() -> str:
    """Read system prompt template from system_prompt.txt."""
    prompt_path = config.BASE_DIR / "system_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")


def _extract_text(content: Any) -> str:
    """Safely extract plain text from Gemini AIMessage content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
        return "".join(parts).strip()
    return str(content)


def answer_with_sources(
    question: str,
    history: list[dict[str, str]] | list[Any] | None = None
) -> dict[str, Any]:
    """Generate an answer using RAG pipeline and return sources.

    Args:
        question: User query string.
        history: Optional conversation history. Can be list of dicts with 'role'
            and 'content' keys, or (role, content) tuples.

    Returns:
        Dictionary with:
            'answer': str
            'sources': list of (page, section, similarity) tuples
    """
    cleaned_question = question.strip() if question else ""
    if not cleaned_question:
        return {
            "answer": "Please ask a question about the NED Undergraduate Prospectus 2025.",
            "sources": []
        }

    # Follow-up query reformulation: use standalone rewritten question for retrieval only
    retrieval_query = cleaned_question
    if history:
        retrieval_query = rewrite_question_for_followup(cleaned_question, history)

    # 1. Call retrieve(retrieval_query) and keep chunks with similarity >= SCORE_THRESHOLD
    raw_chunks = retrieve(retrieval_query)
    filtered_chunks = [
        chunk for chunk in raw_chunks
        if chunk[3] >= config.SCORE_THRESHOLD
    ]

    # Conversational greetings / thanks detection for natural engagement
    q_lower = cleaned_question.lower().strip("?!.,:; ")
    greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "how are you", "how are u", "how are u doing", "how are you doing", "how are u doing today", "how are you doing today", "thanks", "thank you", "salam", "assalam o alaikum", "aao"}
    is_greeting = q_lower in greetings or any(q_lower.startswith(g + " ") for g in ["hi", "hello", "hey", "salam"])

    # 2. If none remain and not a conversational greeting, return fallback immediately WITHOUT calling LLM
    if not filtered_chunks and not is_greeting:
        return {
            "answer": load_fallback_text(),
            "sources": []
        }

    sources = [(chunk[1], chunk[2], chunk[3]) for chunk in filtered_chunks]

    # 3. Build context string: '[Page N | Section] text', separated by blank lines
    context_blocks = []
    for text, page, section, _ in filtered_chunks:
        header = f"[Page {page} | {section}]" if section else f"[Page {page}]"
        context_blocks.append(f"{header} {text.strip()}")
    context = "\n\n".join(context_blocks)

    # 4. Load system_prompt.txt and insert context with prompt.replace('{context}', context)
    prompt_template = load_system_prompt_template()
    system_prompt = prompt_template.replace("{context}", context)

    # 5. Build messages: system prompt, last 4 turns of history, then user question
    messages: list[Any] = [SystemMessage(content=system_prompt)]

    if history:
        # Take last 4 turns of history
        recent_history = history[-4:]
        for item in recent_history:
            role = ""
            content = ""
            if isinstance(item, dict):
                role = str(item.get("role", "")).lower()
                content = str(item.get("content", ""))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                role = str(item[0]).lower()
                content = str(item[1])

            if role in ("user", "human"):
                messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai", "bot"):
                messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=cleaned_question))

    # 6. Call LLM with retry loop for 429 / quota / rate limit errors
    llm = get_llm()
    max_retries = 2
    apology = (
        "I am currently experiencing high demand or temporary rate limits. "
        "Please wait a moment and try your question again."
    )

    for attempt in range(max_retries + 1):
        try:
            response = llm.invoke(messages)
            answer_text = _extract_text(response.content)
            if not answer_text:
                answer_text = apology
            return {"answer": answer_text, "sources": sources}
        except Exception as exc:
            err_str = str(exc).lower()
            is_quota_or_rate_limit = (
                "429" in err_str
                or "resource_exhausted" in err_str
                or "quota" in err_str
                or "rate" in err_str
                or "503" in err_str
                or "unavailable" in err_str
            )
            if is_quota_or_rate_limit and attempt < max_retries:
                time.sleep(2.0)
                continue
            logger.warning("LLM invocation failed: %s", exc)
            return {"answer": apology, "sources": sources}

    return {"answer": apology, "sources": sources}


def answer(question: str, history: list[dict[str, str]] | list[Any] | None = None) -> str:
    """Generate answer for a user question using RAG pipeline."""
    res = answer_with_sources(question, history)
    return res["answer"]
