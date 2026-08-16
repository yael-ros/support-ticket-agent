from unittest.mock import patch

import pytest

from support_agent.agent.eval_classification import (
    GoldSetNotReadyError,
    _compute_metrics,
    effective_ground_truth,
    reviewed_rows,
    run_classification_eval,
)
from support_agent.schemas import (
    Category,
    GoldSetRow,
    HumanLabel,
    TicketClassification,
    Urgency,
)


def _row(ticket_id, weak_category, weak_urgency, human_label=None):
    return GoldSetRow(
        ticket_id=ticket_id,
        subject="subject",
        body="body",
        reference_answer=None,
        weak_category=weak_category,
        weak_urgency=weak_urgency,
        human_label=human_label,
    )


def test_reviewed_rows_filters_null_human_label():
    rows = [
        _row("t1", Category.IT_SUPPORT, Urgency.LOW),
        _row("t2", Category.IT_SUPPORT, Urgency.LOW, human_label=HumanLabel()),
    ]
    assert [r.ticket_id for r in reviewed_rows(rows)] == ["t2"]


def test_effective_ground_truth_confirmed_weak_label_when_human_label_fields_null():
    # An empty HumanLabel() means "reviewed, weak label confirmed correct" —
    # not "no opinion". Effective truth should fall back to the weak label.
    row = _row("t1", Category.BILLING_AND_PAYMENTS, Urgency.HIGH, human_label=HumanLabel())
    category, urgency = effective_ground_truth(row)
    assert category == Category.BILLING_AND_PAYMENTS
    assert urgency == Urgency.HIGH


def test_effective_ground_truth_uses_override_when_present():
    row = _row(
        "t1",
        Category.BILLING_AND_PAYMENTS,
        Urgency.HIGH,
        human_label=HumanLabel(category=Category.SALES_AND_PRE_SALES),
    )
    category, urgency = effective_ground_truth(row)
    assert category == Category.SALES_AND_PRE_SALES  # overridden
    assert urgency == Urgency.HIGH  # confirmed weak label


def test_effective_ground_truth_raises_for_unreviewed_row():
    row = _row("t1", Category.IT_SUPPORT, Urgency.LOW)
    with pytest.raises(ValueError, match="no human_label"):
        effective_ground_truth(row)


def test_compute_metrics_perfect_predictions():
    y_true = ["a", "b", "a", "b"]
    y_pred = ["a", "b", "a", "b"]
    result = _compute_metrics(y_true, y_pred, ["a", "b"])
    assert result["accuracy"] == 1.0
    assert result["macro_f1"] == 1.0
    assert result["per_class"]["a"]["support"] == 2


def test_compute_metrics_all_wrong():
    y_true = ["a", "a"]
    y_pred = ["b", "b"]
    result = _compute_metrics(y_true, y_pred, ["a", "b"])
    assert result["accuracy"] == 0.0
    assert result["macro_f1"] == 0.0


def test_compute_metrics_label_absent_from_sample_does_not_drag_down_macro_f1():
    # "c" never appears in y_true (support=0), so it's excluded from the
    # macro-F1 average rather than counting as a 0.0 for a label that
    # wasn't being tested in this sample.
    y_true = ["a", "a"]
    y_pred = ["a", "a"]
    result = _compute_metrics(y_true, y_pred, ["a", "c"])
    assert result["macro_f1"] == 1.0
    assert result["per_class"]["c"]["support"] == 0


def test_run_classification_eval_refuses_when_no_rows_labeled():
    rows = [_row("t1", Category.IT_SUPPORT, Urgency.LOW)]
    with pytest.raises(GoldSetNotReadyError, match="0 rows"):
        run_classification_eval(rows)


def test_run_classification_eval_skips_unlabeled_rows_and_scores_labeled_ones():
    rows = [
        _row("t1", Category.IT_SUPPORT, Urgency.LOW),  # unreviewed, must be skipped
        _row(
            "t2",
            Category.BILLING_AND_PAYMENTS,
            Urgency.HIGH,
            human_label=HumanLabel(),  # confirmed correct as-is
        ),
    ]
    fake_classification = TicketClassification(
        category=Category.BILLING_AND_PAYMENTS, urgency=Urgency.HIGH, confidence=0.8
    )

    with patch("support_agent.agent.eval_classification.classify_ticket") as mock_classify:
        mock_classify.return_value.classification = fake_classification
        results = run_classification_eval(rows)

    assert results["n_total"] == 2
    assert results["n_labeled"] == 1
    assert results["n_skipped_unlabeled"] == 1
    assert results["category"]["accuracy"] == 1.0
    assert results["urgency"]["accuracy"] == 1.0
    mock_classify.assert_called_once()
