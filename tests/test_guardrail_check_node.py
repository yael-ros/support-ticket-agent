"""Unit tests for agent/nodes/guardrail_check.py."""

from __future__ import annotations

import pytest

from support_agent.agent.nodes.guardrail_check import GUARDRAIL_CHECKS, guardrail_check
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
        body="body",
        category=Category.IT_SUPPORT,
        urgency=Urgency.HIGH,
        language="en",
        raw_queue="IT Support",
        raw_priority="high",
    )


def _context() -> RetrievalContext:
    chunk = RetrievedChunk(
        chunk_id="chunk-1", doc_id="doc-1", doc_title="Doc", category=Category.IT_SUPPORT, text="...", score=0.9
    )
    return RetrievalContext(query="q", chunks=[chunk])


def test_guardrail_check_runs_every_registered_check():
    draft = DraftResponse(
        text="Please clear your cookies and try again.",
        grounding=[ClaimGrounding(claim="clear cookies", chunk_ids=["chunk-1"])],
    )
    state = AgentState(ticket=_make_ticket(), draft=draft, retrieval_context=_context())

    result = guardrail_check(state)

    assert result.guardrail_results is not None
    assert len(result.guardrail_results) == len(GUARDRAIL_CHECKS)
    assert all(r.passed for r in result.guardrail_results)
    assert result.draft == draft


def test_guardrail_check_records_failures_not_just_first():
    # Fails both no_unauthorized_promises and grounding_check at once.
    draft = DraftResponse(text="We will issue a full refund immediately.", grounding=[])
    state = AgentState(ticket=_make_ticket(), draft=draft, retrieval_context=_context())

    result = guardrail_check(state)

    failed = [r.check_name for r in result.guardrail_results if not r.passed]
    assert "no_unauthorized_promises" in failed
    assert "grounding_check" in failed


def test_guardrail_check_raises_without_draft():
    state = AgentState(ticket=_make_ticket(), retrieval_context=_context())
    with pytest.raises(ValueError, match="draft"):
        guardrail_check(state)
