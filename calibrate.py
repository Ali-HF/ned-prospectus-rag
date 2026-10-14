"""Score calibration script for RAG retrieval.

Reads questions from in_scope.txt and out_scope.txt, evaluates top-1 similarity
scores with and without bge query prefix ("Represent this sentence for searching relevant passages: "),
selects the prefix setting yielding the larger separation gap, prints min/median/max
scores for both sets, checks for score overlaps, and recommends a threshold halfway between
the highest out-of-scope score and the lowest in-scope score.
"""

import statistics
from pathlib import Path
from typing import Any
from rag import retrieve


def load_questions(filepath: Path) -> list[str]:
    """Load non-empty question lines from file."""
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    lines = [line.strip() for line in filepath.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line and not line.startswith("#")]


def evaluate_set(questions: list[str], use_prefix: bool) -> list[float]:
    """Retrieve top-1 similarity score for a list of questions."""
    scores: list[float] = []
    for q in questions:
        res = retrieve(q, k=1, use_prefix=use_prefix)
        if res:
            scores.append(res[0][3])
        else:
            scores.append(0.0)
    return scores


def run_evaluation(in_questions: list[str], out_questions: list[str], use_prefix: bool) -> dict[str, Any]:
    """Run evaluation and compute summary stats."""
    in_scores = evaluate_set(in_questions, use_prefix)
    out_scores = evaluate_set(out_questions, use_prefix)

    min_in = min(in_scores) if in_scores else 0.0
    med_in = statistics.median(in_scores) if in_scores else 0.0
    max_in = max(in_scores) if in_scores else 0.0

    min_out = min(out_scores) if out_scores else 0.0
    med_out = statistics.median(out_scores) if out_scores else 0.0
    max_out = max(out_scores) if out_scores else 0.0

    gap = min_in - max_out
    return {
        "use_prefix": use_prefix,
        "in_scores": in_scores,
        "out_scores": out_scores,
        "min_in": min_in,
        "med_in": med_in,
        "max_in": max_in,
        "min_out": min_out,
        "med_out": med_out,
        "max_out": max_out,
        "gap": gap,
    }


def main() -> None:
    """Run calibration comparison and print detailed results."""
    in_path = Path("in_scope.txt")
    out_path = Path("out_scope.txt")

    in_questions = load_questions(in_path)
    out_questions = load_questions(out_path)

    print(f"Loaded {len(in_questions)} in-scope questions from {in_path}")
    print(f"Loaded {len(out_questions)} out-scope questions from {out_path}")
    print("\n" + "=" * 60)
    print("Evaluating with bge query prefix vs without prefix...")
    print("=" * 60)

    eval_without = run_evaluation(in_questions, out_questions, use_prefix=False)
    eval_with = run_evaluation(in_questions, out_questions, use_prefix=True)

    print(f"\n[Mode 1: WITHOUT Prefix]")
    print(f"  In-Scope:  min={eval_without['min_in']:.4f}, median={eval_without['med_in']:.4f}, max={eval_without['max_in']:.4f}")
    print(f"  Out-Scope: min={eval_without['min_out']:.4f}, median={eval_without['med_out']:.4f}, max={eval_without['max_out']:.4f}")
    print(f"  Gap (min_in - max_out): {eval_without['gap']:.4f}")

    print(f"\n[Mode 2: WITH Prefix]")
    print(f"  In-Scope:  min={eval_with['min_in']:.4f}, median={eval_with['med_in']:.4f}, max={eval_with['max_in']:.4f}")
    print(f"  Out-Scope: min={eval_with['min_out']:.4f}, median={eval_with['med_out']:.4f}, max={eval_with['max_out']:.4f}")
    print(f"  Gap (min_in - max_out): {eval_with['gap']:.4f}")

    # Choose whichever gives the bigger gap
    if eval_with["gap"] > eval_without["gap"]:
        best = eval_with
        best_mode_desc = "WITH prefix ('Represent this sentence for searching relevant passages: ')"
    else:
        best = eval_without
        best_mode_desc = "WITHOUT prefix"

    print("\n" + "=" * 60)
    print(f"SELECTED CONFIGURATION: {best_mode_desc}")
    print(f"Separation Gap: {best['gap']:.4f}")
    print("=" * 60)

    # Detailed per-question report for selected mode
    print("\nDetailed Per-Question Best Similarity (Top-1):")
    print("\n--- IN-SCOPE QUESTIONS ---")
    for q, s in zip(in_questions, best["in_scores"]):
        print(f"  [{s:.4f}] {q}")

    print("\n--- OUT-OF-SCOPE QUESTIONS ---")
    for q, s in zip(out_questions, best["out_scores"]):
        print(f"  [{s:.4f}] {q}")

    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    print(f"In-Scope Scores  : Min = {best['min_in']:.4f} | Median = {best['med_in']:.4f} | Max = {best['max_in']:.4f}")
    print(f"Out-Scope Scores : Min = {best['min_out']:.4f} | Median = {best['med_out']:.4f} | Max = {best['max_out']:.4f}")

    highest_out = best["max_out"]
    lowest_in = best["min_in"]
    suggested_threshold = (highest_out + lowest_in) / 2.0

    print(f"\nHighest Out-of-Scope Score : {highest_out:.4f}")
    print(f"Lowest In-Scope Score      : {lowest_in:.4f}")

    if highest_out >= lowest_in:
        print(f"\n[!] WARNING: Score ranges OVERLAP by {highest_out - lowest_in:.4f} points!")
        print(f"Recommendation: Pick a conservative threshold at or above {highest_out:.4f} to avoid hallucination.")
    else:
        print(f"\n[✓] Ranges do NOT overlap. Clean separation gap = {lowest_in - highest_out:.4f} points.")
        print(f"Suggested Threshold (halfway between {highest_out:.4f} and {lowest_in:.4f}): {suggested_threshold:.4f}")


if __name__ == "__main__":
    from typing import Any
    main()
