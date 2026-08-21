"""Unit tests for api/main.py's POST /tickets endpoint.

Mocks agent.graph.run_agent (the graph itself is exercised by
tests/test_graph.py) and api.main's module-level EmailSender instance —
no live LLM calls, no live Chroma index needed.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from support_agent.agent.providers.base import LLMCallError
from support_agent.api.main import app
from support_agent.schemas import (
    AgentState,
    Category,
    ClaimGrounding,
    DraftResponse,
    GuardrailResult,
    RetrievalContext,
    RoutingDecision,
    Ticket,
    TicketClassification,
    Urgency,
)

client = TestClient(app)


def _fake_state(ticket: Ticket, *, action: str = "auto_send") -> AgentState:
    return AgentState(
        ticket=ticket,
        classification=TicketClassification(
            category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.95
        ),
        retrieval_context=RetrievalContext(query="q", chunks=[]),
        draft=DraftResponse(
            text="Please clear your cookies and try again.",
            grounding=[ClaimGrounding(claim="clear cookies", chunk_ids=["chunk-1"])],
        ),
        guardrail_results=[GuardrailResult(check_name="c", passed=True, reason="ok")],
        routing_decision=RoutingDecision(
            action=action, reason="high confidence, all guardrails passed"
        ),
    )


def test_create_ticket_auto_send_returns_response_text_and_sends_email():
    with (
        patch(
            "support_agent.api.main.run_agent",
            side_effect=lambda t: _fake_state(t, action="auto_send"),
        ),
        patch("support_agent.api.main._email_sender") as mock_sender,
    ):
        resp = client.post(
            "/tickets",
            json={
                "subject": "Can't log in",
                "body": "SSO redirect loop.",
                "customer_email": "a@example.com",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "it_support"
    assert body["urgency"] == "high"
    assert body["confidence"] == 0.95
    assert body["routing"]["action"] == "auto_send"
    assert body["response_text"] == "Please clear your cookies and try again."
    mock_sender.send.assert_called_once_with(
        to="a@example.com",
        subject="Re: Can't log in",
        body="Please clear your cookies and try again.",
    )


def test_create_ticket_human_review_returns_no_response_text_and_does_not_send():
    with (
        patch(
            "support_agent.api.main.run_agent",
            side_effect=lambda t: _fake_state(t, action="human_review"),
        ),
        patch("support_agent.api.main._email_sender") as mock_sender,
    ):
        resp = client.post(
            "/tickets", json={"subject": "Billing issue", "body": "I was double charged."}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["routing"]["action"] == "human_review"
    assert body["response_text"] is None
    mock_sender.send.assert_not_called()


def test_create_ticket_generates_id_when_not_provided():
    captured_ticket: dict = {}

    def fake_run_agent(ticket: Ticket) -> AgentState:
        captured_ticket["id"] = ticket.id
        return _fake_state(ticket)

    with (
        patch("support_agent.api.main.run_agent", side_effect=fake_run_agent),
        patch("support_agent.api.main._email_sender"),
    ):
        resp = client.post("/tickets", json={"body": "Help please."})

    assert resp.status_code == 200
    assert resp.json()["ticket_id"] == captured_ticket["id"]
    assert captured_ticket["id"]


def test_create_ticket_missing_body_is_rejected():
    resp = client.post("/tickets", json={"subject": "no body field"})
    assert resp.status_code == 422


def test_create_ticket_llm_call_error_returns_502():
    with patch(
        "support_agent.api.main.run_agent", side_effect=LLMCallError("provider exhausted retries")
    ):
        resp = client.post("/tickets", json={"body": "Help please."})

    assert resp.status_code == 502
    assert "provider exhausted retries" in resp.json()["detail"]
