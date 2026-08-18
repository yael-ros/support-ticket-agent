"""Unit tests for evaluation/metrics.py's shared classification-metric computation."""

from __future__ import annotations

from support_agent.evaluation.metrics import compute_classification_metrics


def test_compute_classification_metrics_perfect_predictions():
    y_true = ["a", "b", "a", "b"]
    y_pred = ["a", "b", "a", "b"]
    result = compute_classification_metrics(y_true, y_pred, ["a", "b"])
    assert result["accuracy"] == 1.0
    assert result["macro_f1"] == 1.0
    assert result["per_class"]["a"]["support"] == 2


def test_compute_classification_metrics_all_wrong():
    y_true = ["a", "a"]
    y_pred = ["b", "b"]
    result = compute_classification_metrics(y_true, y_pred, ["a", "b"])
    assert result["accuracy"] == 0.0
    assert result["macro_f1"] == 0.0


def test_compute_classification_metrics_label_absent_from_sample_does_not_drag_down_macro_f1():
    # "c" never appears in y_true (support=0), so it's excluded from the
    # macro-F1 average rather than counting as a 0.0 for a label that
    # wasn't being tested in this sample.
    y_true = ["a", "a"]
    y_pred = ["a", "a"]
    result = compute_classification_metrics(y_true, y_pred, ["a", "c"])
    assert result["macro_f1"] == 1.0
    assert result["per_class"]["c"]["support"] == 0
