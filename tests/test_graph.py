"""Integration test for agent/graph.py: the whole graph wired together.

Mocks the two LLM call sites (classify.py's and draft.py's own
call_structured references) and retrieve.py's retrieve() — no live API
calls, no live Chroma index needed. This tests wiring and state
threading end to end, not any individual node's logic (see the
per-node test files for that).
"""

from __future__ import annotations

from unittest.mock import patch

from support_agent.agent.graph import build_graph, run_agent
from support_agent.schemas import (
    Category,
    ClaimGrounding,
    DraftResponse,
    RetrievedChunk,
    Ticket,
    TicketClassification,
    Urgency,
)


def _make_ticket() -> Ticket:
    return Ticket(
        id="ticket-000001",
        subject="Can't log in",
        body="I keep getting an SSO redirect loop when I try to log in.",
        category=Category.IT_SUPPORT,
        urgency=Urgency.HIGH,
        language="en",
        raw_queue="IT Support",
        raw_priority="high",
    )


def test_run_agent_auto_sends_a_clean_high_confidence_ticket():
    fake_classification = TicketClassification(category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.95)
    fake_chunk = RetrievedChunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        doc_title="SSO Troubleshooting",
        category=Category.IT_SUPPORT,
        text="Clear cookies and retry the SSO login.",
        score=0.9,
    )
    fake_draft = DraftResponse(
        text="Please clear your browser cookies and try logging in again.",
        grounding=[ClaimGrounding(claim="clear cookies to fix the SSO loop", chunk_ids=["chunk-1"])],
    )

    with (
        patch("support_agent.agent.nodes.classify.call_structured", return_value=fake_classification),
        patch("support_agent.agent.nodes.retrieve.retrieve", return_value=[fake_chunk]),
        patch("support_agent.agent.nodes.draft.call_structured", return_value=fake_draft),
    ):
        final_state = run_agent(_make_ticket())

    assert final_state.classification == fake_classification
    assert final_state.retrieval_context.chunks == [fake_chunk]
    assert final_state.draft == fake_draft
    assert final_state.guardrail_results is not None
    assert all(r.passed for r in final_state.guardrail_results)
    assert final_state.routing_decision.action == "auto_send"


def test_run_agent_routes_to_human_review_on_empty_retrieval():
    fake_classification = TicketClassification(category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.95)
    fake_draft = DraftResponse(text="A human agent will follow up with you shortly.", grounding=[])

    with (
        patch("support_agent.agent.nodes.classify.call_structured", return_value=fake_classification),
        patch("support_agent.agent.nodes.retrieve.retrieve", return_value=[]),
        patch("support_agent.agent.nodes.draft.call_structured", return_value=fake_draft),
    ):
        final_state = run_agent(_make_ticket())

    assert final_state.retrieval_context.chunks == []
    assert final_state.routing_decision.action == "human_review"
    assert "zero chunks" in final_state.routing_decision.reason


def test_build_graph_compiles():
    compiled = build_graph()
    assert compiled is not None
