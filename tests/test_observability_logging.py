"""Unit tests for observability/logging.py's log_node wrapper and per-ticket summary event.

Uses structlog.testing.capture_logs() to assert on emitted events without
touching stdout — no live LLM calls, no live Chroma index needed.
"""

from __future__ import annotations

import pytest
from structlog.testing import capture_logs

from support_agent.observability.logging import log_node, log_ticket_processed
from support_agent.schemas import (
    AgentState,
    Category,
    ClaimGrounding,
    DraftResponse,
    GuardrailResult,
    RetrievalContext,
    RetrievedChunk,
    RoutingDecision,
    Ticket,
    TicketClassification,
    Urgency,
)


def _make_ticket() -> Ticket:
    return Ticket(id="ticket-000001", subject="s", body="b")


def _full_state() -> AgentState:
    return AgentState(
        ticket=_make_ticket(),
        classification=TicketClassification(
            category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.9
        ),
        retrieval_context=RetrievalContext(
            query="q",
            chunks=[
                RetrievedChunk(
                    chunk_id="chunk-1",
                    doc_id="doc-1",
                    doc_title="Doc",
                    category=Category.IT_SUPPORT,
                    text="irrelevant for this test",
                    score=0.87,
                )
            ],
        ),
        draft=DraftResponse(
            text="Please try restarting the router.",
            grounding=[ClaimGrounding(claim="restart the router", chunk_ids=["chunk-1"])],
        ),
        guardrail_results=[GuardrailResult(check_name="tone_check", passed=True, reason="ok")],
        routing_decision=RoutingDecision(action="auto_send", reason="all checks passed"),
    )


def test_log_node_returns_the_wrapped_functions_result_unchanged():
    state = _full_state()
    sentinel = state.model_copy()

    with capture_logs():
        result = log_node("classify", lambda s: sentinel)(state)

    assert result is sentinel


def test_log_node_logs_ticket_id_node_and_latency():
    state = _full_state()

    with capture_logs() as captured:
        log_node("classify", lambda s: s)(state)

    assert len(captured) == 1
    event = captured[0]
    assert event["event"] == "node_completed"
    assert event["ticket_id"] == "ticket-000001"
    assert event["node"] == "classify"
    assert isinstance(event["latency_ms"], float)
    assert event["latency_ms"] >= 0.0


def test_log_node_classify_summary_has_category_urgency_confidence():
    with capture_logs() as captured:
        log_node("classify", lambda s: s)(_full_state())

    event = captured[0]
    assert event["category"] == "it_support"
    assert event["urgency"] == "high"
    assert event["confidence"] == 0.9


def test_log_node_retrieve_summary_has_chunk_ids_not_chunk_text():
    with capture_logs() as captured:
        log_node("retrieve", lambda s: s)(_full_state())

    event = captured[0]
    assert event["chunk_ids"] == ["chunk-1"]
    assert event["scores"] == [0.87]
    assert "irrelevant for this test" not in str(event)


def test_log_node_draft_summary_has_length_not_raw_text():
    with capture_logs() as captured:
        log_node("draft", lambda s: s)(_full_state())

    event = captured[0]
    assert event["text_length"] == len("Please try restarting the router.")
    assert event["grounded_claim_count"] == 1
    assert "Please try restarting the router." not in str(event)


def test_log_node_guardrail_check_summary_lists_each_check():
    with capture_logs() as captured:
        log_node("guardrail_check", lambda s: s)(_full_state())

    event = captured[0]
    assert event["checks"] == [{"check_name": "tone_check", "passed": True, "reason": "ok"}]


def test_log_node_route_summary_has_action_and_reason():
    with capture_logs() as captured:
        log_node("route", lambda s: s)(_full_state())

    event = captured[0]
    assert event["action"] == "auto_send"
    assert event["reason"] == "all checks passed"


def test_log_node_summary_is_empty_before_that_field_is_populated():
    bare_state = AgentState(ticket=_make_ticket())

    with capture_logs() as captured:
        log_node("classify", lambda s: s)(bare_state)

    event = captured[0]
    assert "category" not in event


def test_log_node_unknown_node_name_raises():
    with pytest.raises(KeyError):
        log_node("not_a_real_node", lambda s: s)


def test_log_ticket_processed_logs_total_latency_and_routing_action():
    with capture_logs() as captured:
        log_ticket_processed("ticket-000001", _full_state(), total_latency_ms=42.5)

    assert len(captured) == 1
    event = captured[0]
    assert event["event"] == "ticket_processed"
    assert event["ticket_id"] == "ticket-000001"
    assert event["total_latency_ms"] == 42.5
    assert event["routing_action"] == "auto_send"


def test_log_ticket_processed_handles_missing_routing_decision():
    bare_state = AgentState(ticket=_make_ticket())

    with capture_logs() as captured:
        log_ticket_processed("ticket-000001", bare_state, total_latency_ms=1.0)

    assert captured[0]["routing_action"] is None
