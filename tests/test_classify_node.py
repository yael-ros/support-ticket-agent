"""Unit test for agent/nodes/classify.py, per .claude/skills/agent-conventions:
a fixed/mocked LLM response so the test doesn't depend on live API calls."""

from __future__ import annotations

from unittest.mock import patch

from support_agent.agent.llm_client import ModelTier
from support_agent.agent.nodes.classify import classify_ticket
from support_agent.schemas import AgentState, Category, Ticket, TicketClassification, Urgency


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


def test_classify_ticket_writes_classification_and_preserves_ticket():
    state = AgentState(ticket=_make_ticket())
    fake_classification = TicketClassification(
        category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.92
    )

    with patch(
        "support_agent.agent.nodes.classify.call_structured", return_value=fake_classification
    ) as mock_call:
        result = classify_ticket(state)

    assert result.classification == fake_classification
    assert result.ticket == state.ticket
    mock_call.assert_called_once()
    _, kwargs = mock_call.call_args
    assert kwargs["response_model"] is TicketClassification
    assert kwargs["tier"] is ModelTier.FAST
    assert "Can't log in" in kwargs["prompt"]
    assert "SSO redirect loop" in kwargs["prompt"]
