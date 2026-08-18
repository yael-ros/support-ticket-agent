"""Shared metric computations reused across eval scripts.

`compute_classification_metrics` originated in agent/eval_classification.py
(Phase 3) and moved here once evaluation/run_eval.py (Phase 5) needed the
identical accuracy/F1 math against classifications produced by a full
graph run rather than a standalone classify_ticket() call — duplicating
it would have let the two scores drift out of sync with no way to tell
from the report alone.
"""

from __future__ import annotations


def compute_classification_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
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
