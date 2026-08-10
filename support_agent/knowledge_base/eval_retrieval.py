"""Retrieval eval: precision@3 and recall@5 against the hand-written query set.

Each eval case has exactly one relevant document, so standard IR formulas
reduce cleanly per query:
  precision@3 = (1 if expected_doc_id in top-3 ranked unique doc_ids else 0) / 3
  recall@5    = (1 if expected_doc_id in top-5 ranked unique doc_ids else 0) / 1

Retrieval is chunk-level (`retrieve()` returns chunks, not documents), so
before scoring we collapse the ranked chunk list to a ranked list of
*unique* doc_ids (first-occurrence order) — otherwise a document with 2
chunks both landing in the top 5 would be double-counted.

Reported metrics are the mean of the per-query values above across the
full eval set. This is a real script run against the live Chroma index —
per .claude/skills/eval-harness, these numbers are never hand-written into
the report.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from support_agent.knowledge_base.retrieval_eval_set import RETRIEVAL_EVAL_SET
from support_agent.knowledge_base.retriever import retrieve

REPORT_PATH = Path(__file__).parent.parent.parent / "eval" / "results" / "retrieval_report.md"

K_FOR_RECALL = 5
K_FOR_PRECISION = 3


def _ranked_unique_doc_ids(chunks) -> list[str]:
    seen: list[str] = []
    for chunk in chunks:
        if chunk.doc_id not in seen:
            seen.append(chunk.doc_id)
    return seen


def run_retrieval_eval(eval_set: list[tuple[str, str]] = RETRIEVAL_EVAL_SET) -> dict:
    precisions: list[float] = []
    recalls: list[float] = []
    misses: list[tuple[str, str]] = []

    for query, expected_doc_id in eval_set:
        chunks = retrieve(query, k=K_FOR_RECALL)
        ranked_docs = _ranked_unique_doc_ids(chunks)

        hit_at_3 = expected_doc_id in ranked_docs[:K_FOR_PRECISION]
        hit_at_5 = expected_doc_id in ranked_docs[:K_FOR_RECALL]

        precisions.append((1 if hit_at_3 else 0) / K_FOR_PRECISION)
        recalls.append(1.0 if hit_at_5 else 0.0)

        if not hit_at_5:
            misses.append((query, expected_doc_id))

    return {
        "n": len(eval_set),
        "precision_at_3": sum(precisions) / len(precisions),
        "recall_at_5": sum(recalls) / len(recalls),
        "misses": misses,
    }


def _git_short_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-git-sha"


def write_report(results: dict, path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    sha = _git_short_sha()

    entry = (
        f"## Run: {timestamp} — {sha}\n\n"
        f"### Retrieval\n"
        f"- n = {results['n']}\n"
        f"- Precision@3: {results['precision_at_3']:.3f}\n"
        f"- Recall@5: {results['recall_at_5']:.3f}\n"
    )
    if results["misses"]:
        entry += "- Misses (expected doc not in top-5):\n"
        for query, expected_doc_id in results["misses"]:
            entry += f"  - {expected_doc_id!r} for query: {query!r}\n"
    entry += "\n"

    with path.open("a", encoding="utf-8") as f:
        f.write(entry)

    print(f"[eval_retrieval] Appended run to {path}")


if __name__ == "__main__":
    results = run_retrieval_eval()
    print(f"[eval_retrieval] n={results['n']}")
    print(f"[eval_retrieval] Precision@3: {results['precision_at_3']:.3f}")
    print(f"[eval_retrieval] Recall@5: {results['recall_at_5']:.3f}")
    if results["misses"]:
        print(f"[eval_retrieval] {len(results['misses'])} misses:")
        for query, expected_doc_id in results["misses"]:
            print(f"  - expected {expected_doc_id!r} for: {query!r}")
    write_report(results)
