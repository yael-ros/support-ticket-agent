"""Unit tests for evaluation/run_eval.py — mocked graph/judge/retrieval calls, no live LLM calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from support_agent.agent.eval_classification import GoldSetNotReadyError
from support_agent.agent.providers.base import ModelTier
from support_agent.agent.providers.usage import record_usage
from support_agent.evaluation.run_eval import (
    _ANTHROPIC_PRICE_PER_MILLION_TOKENS,
    _ILLUSTRATIVE_PRICE_PER_MILLION_TOKENS,
    run_full_eval,
)
from support_agent.schemas import (
    AgentState,
    Category,
    DraftResponse,
    GoldSetRow,
    GuardrailResult,
    HumanLabel,
    JudgeScore,
    RetrievalContext,
    RoutingDecision,
    Ticket,
    TicketClassification,
    Urgency,
)


def _row(ticket_id: str) -> GoldSetRow:
    return GoldSetRow(
        ticket_id=ticket_id,
        subject="subject",
        body="body",
        weak_category=Category.IT_SUPPORT,
        weak_urgency=Urgency.HIGH,
        human_label=HumanLabel(),  # confirmed correct as-is: gt == weak label
    )


def _fake_state(ticket: Ticket, *, action: str = "auto_send") -> AgentState:
    return AgentState(
        ticket=ticket,
        classification=TicketClassification(category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.9),
        retrieval_context=RetrievalContext(query="q", chunks=[]),
        draft=DraftResponse(text="draft text", grounding=[]),
        guardrail_results=[GuardrailResult(check_name="c", passed=True, reason="ok")],
        routing_decision=RoutingDecision(action=action, reason="r"),
    )


def _fake_judge_score() -> JudgeScore:
    return JudgeScore(helpfulness=4, correctness=5, tone=4, rationale="fine")


def _fake_retrieval_eval() -> dict:
    return {"n": 20, "precision_at_3": 0.5, "recall_at_5": 0.9, "misses": []}


def test_run_full_eval_refuses_when_no_rows():
    with pytest.raises(GoldSetNotReadyError):
        run_full_eval([])


def test_run_full_eval_aggregates_across_tickets():
    rows = [_row("t1"), _row("t2")]

    with (
        patch("support_agent.evaluation.run_eval.run_agent", side_effect=_fake_state),
        patch("support_agent.evaluation.run_eval.judge_response", return_value=_fake_judge_score()),
        patch("support_agent.evaluation.run_eval.run_retrieval_eval", return_value=_fake_retrieval_eval()),
    ):
        result = run_full_eval(rows)

    assert result["n_attempted"] == 2
    assert result["n_succeeded"] == 2
    assert result["n_failed"] == 0
    assert result["category"]["accuracy"] == 1.0
    assert result["urgency"]["accuracy"] == 1.0
    assert result["avg_helpfulness"] == 4.0
    assert result["avg_correctness"] == 5.0
    assert result["avg_tone"] == 4.0
    assert result["auto_send_rate"] == 1.0
    assert result["retrieval"] == _fake_retrieval_eval()
    assert result["avg_latency_seconds"] >= 0.0


def test_run_full_eval_records_failure_without_aborting_batch():
    rows = [_row("t1"), _row("t2")]

    def fake_run_agent(ticket: Ticket) -> AgentState:
        if ticket.id == "t1":
            raise RuntimeError("boom")
        return _fake_state(ticket)

    with (
        patch("support_agent.evaluation.run_eval.run_agent", side_effect=fake_run_agent),
        patch("support_agent.evaluation.run_eval.judge_response", return_value=_fake_judge_score()),
        patch("support_agent.evaluation.run_eval.run_retrieval_eval", return_value=_fake_retrieval_eval()),
    ):
        result = run_full_eval(rows)

    assert result["n_attempted"] == 2
    assert result["n_succeeded"] == 1
    assert result["n_failed"] == 1
    assert result["failures"] == [("t1", "RuntimeError: boom")]


def test_run_full_eval_auto_send_rate_reflects_mixed_routing():
    rows = [_row("t1"), _row("t2")]

    def fake_run_agent(ticket: Ticket) -> AgentState:
        action = "auto_send" if ticket.id == "t1" else "human_review"
        return _fake_state(ticket, action=action)

    with (
        patch("support_agent.evaluation.run_eval.run_agent", side_effect=fake_run_agent),
        patch("support_agent.evaluation.run_eval.judge_response", return_value=_fake_judge_score()),
        patch("support_agent.evaluation.run_eval.run_retrieval_eval", return_value=_fake_retrieval_eval()),
    ):
        result = run_full_eval(rows)

    assert result["auto_send_rate"] == 0.5


def test_run_full_eval_computes_real_cost_from_anthropic_usage():
    rows = [_row("t1")]

    def fake_run_agent(ticket: Ticket) -> AgentState:
        record_usage(provider="anthropic", tier=ModelTier.FAST, input_tokens=1_000_000, output_tokens=1_000_000)
        return _fake_state(ticket)

    with (
        patch("support_agent.evaluation.run_eval.run_agent", side_effect=fake_run_agent),
        patch("support_agent.evaluation.run_eval.judge_response", return_value=_fake_judge_score()),
        patch("support_agent.evaluation.run_eval.run_retrieval_eval", return_value=_fake_retrieval_eval()),
    ):
        result = run_full_eval(rows)

    in_rate, out_rate = _ANTHROPIC_PRICE_PER_MILLION_TOKENS[ModelTier.FAST]
    assert result["total_input_tokens"] == 1_000_000
    assert result["total_output_tokens"] == 1_000_000
    assert result["est_cost_per_ticket"] == pytest.approx(in_rate + out_rate)
    assert result["cost_is_illustrative"] is False


def test_run_full_eval_falls_back_to_illustrative_rate_for_unrecognized_provider():
    rows = [_row("t1")]

    def fake_run_agent(ticket: Ticket) -> AgentState:
        record_usage(provider="gemini", tier=ModelTier.FAST, input_tokens=1_000_000, output_tokens=1_000_000)
        return _fake_state(ticket)

    with (
        patch("support_agent.evaluation.run_eval.run_agent", side_effect=fake_run_agent),
        patch("support_agent.evaluation.run_eval.judge_response", return_value=_fake_judge_score()),
        patch("support_agent.evaluation.run_eval.run_retrieval_eval", return_value=_fake_retrieval_eval()),
    ):
        result = run_full_eval(rows)

    in_rate, out_rate = _ILLUSTRATIVE_PRICE_PER_MILLION_TOKENS[ModelTier.FAST]
    assert result["est_cost_per_ticket"] == pytest.approx(in_rate + out_rate)
    assert result["cost_is_illustrative"] is True
