"""Unit tests for api/main.py's POST /tickets endpoint.

Mocks agent.graph.run_agent (the graph itself is exercised by
tests/test_graph.py) and api.main's module-level EmailSender instance —
no live LLM calls, no live Chroma index needed.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from support_agent.agent.providers.base import LLMCallError
from support_agent.api.main import API_KEY_ENV_VAR, RATE_LIMIT, app, limiter
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
_API_KEY = "test-shared-secret"
_AUTH_HEADERS = {"X-API-Key": _API_KEY}
_RATE_LIMIT_COUNT = int(RATE_LIMIT.split("/")[0])


@pytest.fixture(autouse=True)
def _configure_auth_and_rate_limit(monkeypatch):
    """Every test gets a known API key and a clean rate-limit bucket.

    limiter.reset() clears slowapi's (process-wide, in-memory) storage so
    one test's request count never leaks into the next test's assertions —
    same rationale as conftest.py's _clear_usage_log fixture.
    """
    monkeypatch.setenv(API_KEY_ENV_VAR, _API_KEY)
    limiter.reset()
    yield


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
            headers=_AUTH_HEADERS,
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
            "/tickets",
            headers=_AUTH_HEADERS,
            json={"subject": "Billing issue", "body": "I was double charged."},
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
        resp = client.post("/tickets", headers=_AUTH_HEADERS, json={"body": "Help please."})

    assert resp.status_code == 200
    assert resp.json()["ticket_id"] == captured_ticket["id"]
    assert captured_ticket["id"]


def test_create_ticket_missing_body_is_rejected():
    resp = client.post("/tickets", headers=_AUTH_HEADERS, json={"subject": "no body field"})
    assert resp.status_code == 422


def test_create_ticket_body_over_max_length_is_rejected():
    resp = client.post("/tickets", headers=_AUTH_HEADERS, json={"body": "x" * 5_001})
    assert resp.status_code == 422


def test_create_ticket_subject_over_max_length_is_rejected():
    resp = client.post(
        "/tickets", headers=_AUTH_HEADERS, json={"subject": "x" * 301, "body": "help"}
    )
    assert resp.status_code == 422


def test_create_ticket_llm_call_error_returns_502():
    with patch(
        "support_agent.api.main.run_agent", side_effect=LLMCallError("provider exhausted retries")
    ):
        resp = client.post("/tickets", headers=_AUTH_HEADERS, json={"body": "Help please."})

    assert resp.status_code == 502
    assert "provider exhausted retries" in resp.json()["detail"]


def test_create_ticket_without_api_key_is_rejected():
    resp = client.post("/tickets", json={"body": "Help please."})
    assert resp.status_code == 401


def test_create_ticket_with_wrong_api_key_is_rejected():
    resp = client.post(
        "/tickets", headers={"X-API-Key": "not-the-right-key"}, json={"body": "Help please."}
    )
    assert resp.status_code == 401


def test_create_ticket_with_no_server_key_configured_denies_everyone(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    resp = client.post("/tickets", headers=_AUTH_HEADERS, json={"body": "Help please."})
    assert resp.status_code == 401


def test_create_ticket_rate_limit_exceeded_returns_429():
    with (
        patch("support_agent.api.main.run_agent", side_effect=lambda t: _fake_state(t)),
        patch("support_agent.api.main._email_sender"),
    ):
        responses = [
            client.post("/tickets", headers=_AUTH_HEADERS, json={"body": "Help please."})
            for _ in range(_RATE_LIMIT_COUNT + 1)
        ]

    statuses = [r.status_code for r in responses]
    assert statuses[:_RATE_LIMIT_COUNT] == [200] * _RATE_LIMIT_COUNT
    assert statuses[_RATE_LIMIT_COUNT] == 429


def test_create_ticket_rate_limit_is_scoped_per_api_key(monkeypatch):
    """A second, distinct API key gets its own quota, not a shared one."""
    other_key = "a-second-shared-secret"
    monkeypatch.setenv(API_KEY_ENV_VAR, other_key)  # server now accepts either check below

    with (
        patch("support_agent.api.main.run_agent", side_effect=lambda t: _fake_state(t)),
        patch("support_agent.api.main._email_sender"),
    ):
        # Exhaust key #1's quota under the original key.
        monkeypatch.setenv(API_KEY_ENV_VAR, _API_KEY)
        for _ in range(_RATE_LIMIT_COUNT):
            client.post("/tickets", headers=_AUTH_HEADERS, json={"body": "Help please."})

        # A different key, once the server is configured to accept it, is not
        # affected by key #1's exhausted quota.
        monkeypatch.setenv(API_KEY_ENV_VAR, other_key)
        resp = client.post(
            "/tickets", headers={"X-API-Key": other_key}, json={"body": "Help please."}
        )

    assert resp.status_code == 200
