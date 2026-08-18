"""Unit tests for evaluation/llm_judge.py — mocked LLM call, no live API calls."""

from __future__ import annotations

from unittest.mock import patch

from support_agent.agent.llm_client import ModelTier
from support_agent.evaluation.llm_judge import JUDGE_MAX_TOKENS, judge_response
from support_agent.schemas import (
    Category,
    DraftResponse,
    JudgeScore,
    RetrievalContext,
    RetrievedChunk,
    Ticket,
    Urgency,
)


def _make_ticket() -> Ticket:
    return Ticket(
        id="ticket-000001",
        subject="Can't log in",
        body="SSO redirect loop.",
        category=Category.IT_SUPPORT,
        urgency=Urgency.HIGH,
        language="en",
        raw_queue="IT Support",
        raw_priority="high",
    )


def test_judge_response_returns_score_and_calls_with_expected_args():
    ticket = _make_ticket()
    chunk = RetrievedChunk(
        chunk_id="chunk-1", doc_id="doc-1", doc_title="Doc", category=Category.IT_SUPPORT, text="...", score=0.9
    )
    context = RetrievalContext(query="q", chunks=[chunk])
    draft = DraftResponse(text="Please clear your cookies.", grounding=[])

    fake_score = JudgeScore(helpfulness=4, correctness=5, tone=4, rationale="Clear and accurate.")

    with patch("support_agent.evaluation.llm_judge.call_structured", return_value=fake_score) as mock_call:
        result = judge_response(ticket, draft, context)

    assert result == fake_score
    mock_call.assert_called_once()
    _, kwargs = mock_call.call_args
    assert kwargs["response_model"] is JudgeScore
    assert kwargs["tier"] is ModelTier.STRONG
    assert kwargs["max_tokens"] == JUDGE_MAX_TOKENS
    assert "clear your cookies" in kwargs["prompt"].lower()
    assert "chunk-1" in kwargs["prompt"]
