"""Interactive test tool for RAG chunk retrieval.

Repeatedly prompts for a question and prints the top 5 chunks with similarity,
page, and the first 200 characters of text.
"""

import sys
from rag import retrieve
import config


def main() -> None:
    """Run interactive retrieval loop."""
    print("=== Prospectus RAG Retrieval Debugger ===")
    print(f"Top K: {config.TOP_K} | Score Threshold: {config.SCORE_THRESHOLD}")
    print("Type your question and press Enter. Enter 'exit' or 'quit' to stop.\n")

    while True:
        try:
            query = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit", "q"):
            print("Goodbye.")
            break

        results = retrieve(query, k=5)
        print(f"\nTop {len(results)} chunks retrieved for: '{query}':")
        print("-" * 70)
        for i, (text, page, section, sim) in enumerate(results, 1):
            preview = text.replace("\n", " ")[:200]
            print(f"[{i}] Similarity: {sim:.4f} | Page: {page} | Section: {section or 'N/A'}")
            print(f"    Preview: {preview}...")
            print("-" * 70)
        print()


if __name__ == "__main__":
    main()
