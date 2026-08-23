"""Unit tests for api/demo.py's unauthenticated public demo endpoint.

Mocks agent.graph.run_agent (agent behavior itself is covered by
tests/test_graph.py) — no live LLM calls, no live Chroma index needed.
Every safety rule PORTFOLIO_ADDITIONS.md requires for this endpoint gets
its own test: auth-exempt, per-IP rate limit, the global daily cap (and
its UTC-midnight reset), forced-Gemini regardless of the app's configured
provider, and that EmailSender is never invoked from here.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from support_agent.agent import llm_client
from support_agent.api import demo
from support_agent.api.main import app
from support_agent.api.rate_limit import limiter
from support_agent.schemas import (
    AgentState,
    Category,
    DraftResponse,
    GuardrailResult,
    RetrievalContext,
    RoutingDecision,
    Ticket,
    TicketClassification,
    Urgency,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """See tests/test_api.py's identical fixture for why: slowapi's storage
    is process-wide, in-memory state that must not leak between tests."""
    limiter.reset()
    yield


def _fake_state(ticket: Ticket, *, action: str = "auto_send") -> AgentState:
    return AgentState(
        ticket=ticket,
        classification=TicketClassification(
            category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.95
        ),
        retrieval_context=RetrievalContext(query="q", chunks=[]),
        draft=DraftResponse(text="Please try restarting the router.", grounding=[]),
        guardrail_results=[GuardrailResult(check_name="c", passed=True, reason="ok")],
        routing_decision=RoutingDecision(action=action, reason="r"),
    )


def test_get_demo_page_returns_html():
    resp = client.get("/demo")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Support Ticket Agent" in resp.text


def test_demo_tickets_requires_no_api_key():
    with (
        patch("support_agent.api.demo.run_agent", side_effect=lambda t: _fake_state(t)),
    ):
        resp = client.post("/demo/tickets", json={"subject": "s", "body": "b"})
    assert resp.status_code == 200


def test_demo_tickets_ignores_a_wrong_or_missing_api_key_header():
    with patch("support_agent.api.demo.run_agent", side_effect=lambda t: _fake_state(t)):
        resp = client.post(
            "/demo/tickets",
            headers={"X-API-Key": "not-a-real-key"},
            json={"subject": "s", "body": "b"},
        )
    assert resp.status_code == 200


def test_demo_tickets_response_shape_matches_tickets_endpoint():
    with patch(
        "support_agent.api.demo.run_agent", side_effect=lambda t: _fake_state(t, action="auto_send")
    ):
        resp = client.post("/demo/tickets", json={"subject": "s", "body": "b"})

    body = resp.json()
    assert body["category"] == "it_support"
    assert body["urgency"] == "high"
    assert body["confidence"] == 0.95
    assert body["routing"]["action"] == "auto_send"
    assert body["response_text"] == "Please try restarting the router."
    assert body["ticket_id"].startswith("demo-")


def test_demo_tickets_human_review_has_no_response_text():
    with patch(
        "support_agent.api.demo.run_agent",
        side_effect=lambda t: _fake_state(t, action="human_review"),
    ):
        resp = client.post("/demo/tickets", json={"subject": "s", "body": "b"})

    body = resp.json()
    assert body["routing"]["action"] == "human_review"
    assert body["response_text"] is None


def test_demo_tickets_never_calls_email_sender():
    """The most important safety property: an unauthenticated caller can
    supply an arbitrary customer_email, but the demo endpoint must never
    attempt to deliver anything through it."""
    with (
        patch(
            "support_agent.api.demo.run_agent",
            side_effect=lambda t: _fake_state(t, action="auto_send"),
        ),
        patch("support_agent.api.main._email_sender") as mock_sender,
    ):
        resp = client.post(
            "/demo/tickets",
            json={"subject": "s", "body": "b", "customer_email": "victim@example.com"},
        )

    assert resp.status_code == 200
    mock_sender.send.assert_not_called()


def test_demo_tickets_forces_gemini_regardless_of_configured_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    captured = {}

    def fake_run_agent(ticket: Ticket) -> AgentState:
        captured["provider_during_call"] = llm_client._provider_override.get()
        return _fake_state(ticket)

    with patch("support_agent.api.demo.run_agent", side_effect=fake_run_agent):
        resp = client.post("/demo/tickets", json={"subject": "s", "body": "b"})

    assert resp.status_code == 200
    assert captured["provider_during_call"] == "gemini"
    # the override must not leak into whatever runs after this request
    assert llm_client._provider_override.get() is None


def test_demo_tickets_body_over_max_length_is_rejected():
    resp = client.post("/demo/tickets", json={"body": "x" * 5_001})
    assert resp.status_code == 422


def test_demo_tickets_per_ip_rate_limit_returns_429_with_friendly_message():
    with patch("support_agent.api.demo.run_agent", side_effect=lambda t: _fake_state(t)):
        responses = [client.post("/demo/tickets", json={"body": "b"}) for _ in range(6)]

    statuses = [r.status_code for r in responses]
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429
    assert responses[5].json()["error"] == demo.DEMO_PER_IP_ERROR_MESSAGE


def test_demo_tickets_daily_cap_returns_429_with_friendly_message():
    """The daily counter increments on every attempt regardless of whether
    the per-IP limit also blocks it (it's checked first in the stacked
    decorators — see demo.py's module docstring), so 50 total POSTs from
    this test's single simulated IP is enough to exhaust it, even though
    only the first 5 individually succeed."""
    with patch("support_agent.api.demo.run_agent", side_effect=lambda t: _fake_state(t)):
        for _ in range(50):
            client.post("/demo/tickets", json={"body": "b"})
        resp = client.post("/demo/tickets", json={"body": "b"})

    assert resp.status_code == 429
    assert resp.json()["error"] == demo.DEMO_DAILY_CAP_ERROR_MESSAGE


def test_demo_daily_key_is_stable_within_the_same_utc_day():
    fixed_now = dt.datetime(2026, 6, 15, 10, 30, tzinfo=dt.UTC)
    with patch("support_agent.api.demo.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_now
        key_a = demo._demo_daily_key(None)
        key_b = demo._demo_daily_key(None)

    assert key_a == key_b == "demo-daily-2026-06-15"


def test_demo_daily_key_changes_at_the_utc_calendar_boundary():
    with patch("support_agent.api.demo.datetime") as mock_datetime:
        mock_datetime.now.return_value = dt.datetime(2026, 6, 15, 23, 59, 59, tzinfo=dt.UTC)
        key_before_midnight = demo._demo_daily_key(None)

        mock_datetime.now.return_value = dt.datetime(2026, 6, 16, 0, 0, 1, tzinfo=dt.UTC)
        key_after_midnight = demo._demo_daily_key(None)

    assert key_before_midnight != key_after_midnight


def test_demo_tickets_llm_call_error_returns_502():
    from support_agent.agent.providers.base import LLMCallError

    with patch("support_agent.api.demo.run_agent", side_effect=LLMCallError("quota exhausted")):
        resp = client.post("/demo/tickets", json={"body": "b"})

    assert resp.status_code == 502
    assert "quota exhausted" in resp.json()["detail"]
