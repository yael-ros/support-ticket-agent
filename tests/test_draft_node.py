"""Unit tests for agent/nodes/draft.py — mocked LLM call, no live API calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from support_agent.agent.llm_client import ModelTier
from support_agent.agent.nodes.draft import DRAFT_MAX_TOKENS, draft_response
from support_agent.schemas import (
    AgentState,
    Category,
    ClaimGrounding,
    DraftResponse,
    RetrievalContext,
    RetrievedChunk,
    Ticket,
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


def _make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        doc_title="SSO Troubleshooting",
        category=Category.IT_SUPPORT,
        text="Clear cookies and retry the SSO login.",
        score=0.9,
    )


def test_draft_response_writes_draft_and_preserves_state():
    chunk = _make_chunk()
    state = AgentState(
        ticket=_make_ticket(),
        retrieval_context=RetrievalContext(query="q", chunks=[chunk]),
    )
    fake_draft = DraftResponse(
        text="Please clear your cookies and try logging in again.",
        grounding=[ClaimGrounding(claim="clear cookies to fix SSO loop", chunk_ids=["chunk-1"])],
    )

    with patch("support_agent.agent.nodes.draft.call_structured", return_value=fake_draft) as mock_call:
        result = draft_response(state)

    assert result.draft == fake_draft
    assert result.retrieval_context == state.retrieval_context
    assert result.ticket == state.ticket

    mock_call.assert_called_once()
    _, kwargs = mock_call.call_args
    assert kwargs["response_model"] is DraftResponse
    assert kwargs["tier"] is ModelTier.STRONG
    assert kwargs["max_tokens"] == DRAFT_MAX_TOKENS
    assert "chunk-1" in kwargs["prompt"]
    assert "SSO redirect loop" in kwargs["prompt"]


def test_draft_response_raises_without_retrieval_context():
    state = AgentState(ticket=_make_ticket())
    with pytest.raises(ValueError, match="retrieval_context"):
        draft_response(state)
