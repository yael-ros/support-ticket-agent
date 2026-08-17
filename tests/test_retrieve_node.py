"""Unit tests for agent/nodes/retrieve.py — mocked retriever, no live Chroma/embedding calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from support_agent.agent.nodes.retrieve import RETRIEVE_K, retrieve_context
from support_agent.schemas import (
    AgentState,
    Category,
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


def test_retrieve_context_writes_chunks_and_preserves_state():
    ticket = _make_ticket()
    classification = TicketClassification(category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.9)
    state = AgentState(ticket=ticket, classification=classification)

    fake_chunks = [
        RetrievedChunk(
            chunk_id="chunk-1",
            doc_id="doc-1",
            doc_title="SSO Troubleshooting",
            category=Category.IT_SUPPORT,
            text="Clear cookies and retry the SSO login.",
            score=0.9,
        )
    ]

    with patch("support_agent.agent.nodes.retrieve.retrieve", return_value=fake_chunks) as mock_retrieve:
        result = retrieve_context(state)

    assert result.retrieval_context is not None
    assert result.retrieval_context.chunks == fake_chunks
    assert "Can't log in" in result.retrieval_context.query
    assert result.classification == classification
    assert result.ticket == ticket

    mock_retrieve.assert_called_once()
    _, kwargs = mock_retrieve.call_args
    assert kwargs["k"] == RETRIEVE_K
    assert kwargs["category"] is Category.IT_SUPPORT


def test_retrieve_context_allows_empty_results():
    ticket = _make_ticket()
    classification = TicketClassification(category=Category.IT_SUPPORT, urgency=Urgency.HIGH, confidence=0.9)
    state = AgentState(ticket=ticket, classification=classification)

    with patch("support_agent.agent.nodes.retrieve.retrieve", return_value=[]):
        result = retrieve_context(state)

    assert result.retrieval_context.chunks == []


def test_retrieve_context_raises_without_classification():
    state = AgentState(ticket=_make_ticket())
    with pytest.raises(ValueError, match="classification"):
        retrieve_context(state)
