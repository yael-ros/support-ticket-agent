"""Classification eval: accuracy and per-class F1 against the hand-reviewed gold set.

Per .claude/skills/eval-harness: before running, this checks that
data/gold_set.jsonl actually has hand-corrected rows (`human_label` is not
null). If zero rows are reviewed, `run_classification_eval` raises
`GoldSetNotReadyError` rather than silently scoring against the dataset's
own weak `queue`/`priority` labels as if they were verified ground truth.
Rows that *are* unreviewed are skipped (and counted), not treated as
correct or incorrect.

A `HumanLabel` with `category`/`urgency` left as `None` means the reviewer
confirmed the weak label was already correct, not "no opinion" — so
effective ground truth is `human_label.category or weak_category` (same
for urgency), per `schemas.HumanLabel`'s docstring.

This calls the real `classify_ticket()` node for every reviewed row, so
it's an integration-level eval of the actual classification code path —
and therefore requires a live `ANTHROPIC_API_KEY`, not a mocked one.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from support_agent.agent.nodes.classify import classify_ticket
from support_agent.data.build_gold_set import GOLD_SET_PATH, load_gold_set
from support_agent.schemas import AgentState, Category, GoldSetRow, Ticket, Urgency

REPORT_PATH = Path(__file__).parent.parent.parent / "eval" / "results" / "classification_report.md"


class GoldSetNotReadyError(Exception):
    """Raised when the gold set has no hand-corrected rows to evaluate against."""


def reviewed_rows(rows: list[GoldSetRow]) -> list[GoldSetRow]:
    return [row for row in rows if row.human_label is not None]


def effective_ground_truth(row: GoldSetRow) -> tuple[Category, Urgency]:
    """A null field inside human_label means the reviewer confirmed the weak label, not 'no opinion'."""
    if row.human_label is None:
        raise ValueError(f"Row {row.ticket_id} has no human_label; not eligible for ground truth.")
    category = row.human_label.category or row.weak_category
    urgency = row.human_label.urgency or row.weak_urgency
    return category, urgency


def _row_to_ticket(row: GoldSetRow) -> Ticket:
    return Ticket(
        id=row.ticket_id,
        subject=row.subject,
        body=row.body,
        answer=row.reference_answer,
        category=row.weak_category,
        urgency=row.weak_urgency,
        language="en",
        raw_queue=row.weak_category.value,
        raw_priority=row.weak_urgency.value,
    )


def _compute_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Accuracy plus per-class precision/recall/F1 and macro-F1.

    Macro-F1 averages over labels that actually appear in y_true (support
    > 0) — labels absent from this eval run don't drag the average down
    to 0 just for not showing up in a particular sample.
    """
    n = len(y_true)
    accuracy = sum(t == p for t, p in zip(y_true, y_pred, strict=True)) / n if n else 0.0

    per_class = {}
    f1s = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p != label)
        support = sum(1 for t in y_true if t == label)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        if support > 0:
            f1s.append(f1)

    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    return {"accuracy": accuracy, "macro_f1": macro_f1, "per_class": per_class}


def run_classification_eval(rows: list[GoldSetRow] | None = None) -> dict:
    rows = rows if rows is not None else load_gold_set()
    labeled = reviewed_rows(rows)

    if not labeled:
        raise GoldSetNotReadyError(
            f"{GOLD_SET_PATH} has 0 rows with a non-null human_label, out of {len(rows)} total. "
            "This gold set is weak supervision only until a developer hand-reviews it (see "
            "BUILD_PLAN.md Phase 1 and .claude/skills/eval-harness) — refusing to score "
            "classification accuracy against unverified labels as if they were ground truth."
        )

    category_true, category_pred = [], []
    urgency_true, urgency_pred = [], []
    confidences = []

    for row in labeled:
        gt_category, gt_urgency = effective_ground_truth(row)
        state = AgentState(ticket=_row_to_ticket(row))
        classification = classify_ticket(state).classification
        assert classification is not None

        category_true.append(gt_category.value)
        category_pred.append(classification.category.value)
        urgency_true.append(gt_urgency.value)
        urgency_pred.append(classification.urgency.value)
        confidences.append(classification.confidence)

    return {
        "n_total": len(rows),
        "n_labeled": len(labeled),
        "n_skipped_unlabeled": len(rows) - len(labeled),
        "category": _compute_metrics(category_true, category_pred, [c.value for c in Category]),
        "urgency": _compute_metrics(urgency_true, urgency_pred, [u.value for u in Urgency]),
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
    }


def _git_short_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-git-sha"


def _format_per_class_table(per_class: dict) -> str:
    lines = ["  | label | precision | recall | f1 | support |", "  |---|---|---|---|---|"]
    for label, m in per_class.items():
        lines.append(
            f"  | {label} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['support']} |"
        )
    return "\n".join(lines)


def write_report(results: dict, path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    sha = _git_short_sha()

    entry = (
        f"## Run: {timestamp} — {sha}\n\n"
        f"### Classification\n"
        f"- n = {results['n_labeled']} labeled "
        f"({results['n_skipped_unlabeled']} unlabeled rows skipped, out of {results['n_total']} total)\n"
        f"- Category accuracy: {results['category']['accuracy']:.3f}\n"
        f"- Category F1 (macro): {results['category']['macro_f1']:.3f}\n"
        f"- Urgency accuracy: {results['urgency']['accuracy']:.3f}\n"
        f"- Urgency F1 (macro): {results['urgency']['macro_f1']:.3f}\n"
        f"- Avg confidence: {results['avg_confidence']:.3f}\n\n"
        f"Category per-class:\n{_format_per_class_table(results['category']['per_class'])}\n\n"
        f"Urgency per-class:\n{_format_per_class_table(results['urgency']['per_class'])}\n\n"
    )

    with path.open("a", encoding="utf-8") as f:
        f.write(entry)

    print(f"[eval_classification] Appended run to {path}")


if __name__ == "__main__":
    try:
        eval_results = run_classification_eval()
    except GoldSetNotReadyError as exc:
        print(f"[eval_classification] BLOCKED: {exc}")
        raise SystemExit(1) from exc

    print(f"[eval_classification] n={eval_results['n_labeled']}/{eval_results['n_total']}")
    print(f"[eval_classification] Category accuracy: {eval_results['category']['accuracy']:.3f}")
    print(f"[eval_classification] Category F1 (macro): {eval_results['category']['macro_f1']:.3f}")
    print(f"[eval_classification] Urgency accuracy: {eval_results['urgency']['accuracy']:.3f}")
    print(f"[eval_classification] Urgency F1 (macro): {eval_results['urgency']['macro_f1']:.3f}")
    write_report(eval_results)
