"""Unit tests for agent/nodes/route.py."""

from __future__ import annotations

import pytest

from support_agent.agent.nodes.route import CONFIDENCE_THRESHOLD, route_ticket
from support_agent.schemas import (
    AgentState,
    Category,
    GuardrailResult,
    RetrievalContext,
    RetrievedChunk,
    Ticket,
    TicketClassification,
    Urgency,
)


def _make_ticket() -> Ticket:
    return Ticket(
        id="ticket-000001",
        subject="s",
        body="b",
        category=Category.IT_SUPPORT,
        urgency=Urgency.HIGH,
        language="en",
        raw_queue="IT Support",
        raw_priority="high",
    )


def _context(with_chunks: bool = True) -> RetrievalContext:
    chunks = (
        [
            RetrievedChunk(
                chunk_id="chunk-1",
                doc_id="doc-1",
                doc_title="Doc",
                category=Category.IT_SUPPORT,
                text="...",
                score=0.9,
            )
        ]
        if with_chunks
        else []
    )
    return RetrievalContext(query="q", chunks=chunks)


def _passing_results() -> list[GuardrailResult]:
    return [GuardrailResult(check_name="c", passed=True, reason="ok")]


def _make_state(*, confidence, chunks_present, guardrails_pass) -> AgentState:
    classification = TicketClassification(category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=confidence)
    results = (
        _passing_results()
        if guardrails_pass
        else [GuardrailResult(check_name="tone_check", passed=False, reason="draft is empty")]
    )
    return AgentState(
        ticket=_make_ticket(),
        classification=classification,
        retrieval_context=_context(with_chunks=chunks_present),
        guardrail_results=results,
    )


def test_routes_to_auto_send_when_everything_passes():
    state = _make_state(confidence=0.9, chunks_present=True, guardrails_pass=True)
    result = route_ticket(state)
    assert result.routing_decision.action == "auto_send"


def test_routes_to_human_review_on_low_confidence():
    state = _make_state(confidence=CONFIDENCE_THRESHOLD - 0.01, chunks_present=True, guardrails_pass=True)
    result = route_ticket(state)
    assert result.routing_decision.action == "human_review"
    assert "confidence" in result.routing_decision.reason


def test_routes_to_human_review_on_failed_guardrail():
    state = _make_state(confidence=0.9, chunks_present=True, guardrails_pass=False)
    result = route_ticket(state)
    assert result.routing_decision.action == "human_review"
    assert "guardrail" in result.routing_decision.reason


def test_routes_to_human_review_on_empty_retrieval():
    state = _make_state(confidence=0.9, chunks_present=False, guardrails_pass=True)
    result = route_ticket(state)
    assert result.routing_decision.action == "human_review"
    assert "zero chunks" in result.routing_decision.reason


def test_combines_multiple_reasons():
    state = _make_state(confidence=0.1, chunks_present=False, guardrails_pass=False)
    result = route_ticket(state)
    assert result.routing_decision.action == "human_review"
    reason = result.routing_decision.reason
    assert "confidence" in reason
    assert "guardrail" in reason
    assert "zero chunks" in reason


def test_raises_without_required_state():
    state = AgentState(ticket=_make_ticket())
    with pytest.raises(ValueError, match="classification"):
        route_ticket(state)
