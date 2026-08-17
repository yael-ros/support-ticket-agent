"""Unit tests for agent/guardrails.py — every check needs a clear pass and fail case."""

from __future__ import annotations

from support_agent.agent.guardrails import (
    grounding_check,
    no_unauthorized_promises,
    pii_scrub,
    tone_check,
)
from support_agent.schemas import (
    Category,
    ClaimGrounding,
    DraftResponse,
    RetrievalContext,
    RetrievedChunk,
)


def _context(chunk_ids: list[str] | None = None) -> RetrievalContext:
    chunk_ids = chunk_ids if chunk_ids is not None else ["chunk-1"]
    chunks = [
        RetrievedChunk(
            chunk_id=cid,
            doc_id="doc-1",
            doc_title="Some Doc",
            category=Category.IT_SUPPORT,
            text="...",
            score=0.9,
        )
        for cid in chunk_ids
    ]
    return RetrievalContext(query="q", chunks=chunks)


def test_no_unauthorized_promises_passes_on_clean_draft():
    draft = DraftResponse(text="Please try restarting the sync client.", grounding=[])
    result = no_unauthorized_promises(draft, _context())
    assert result.passed
    assert result.check_name == "no_unauthorized_promises"


def test_no_unauthorized_promises_fails_on_refund_promise():
    draft = DraftResponse(text="We will issue a full refund right away.", grounding=[])
    result = no_unauthorized_promises(draft, _context())
    assert not result.passed
    assert "unauthorized-promise" in result.reason


def test_pii_scrub_passes_on_clean_draft():
    draft = DraftResponse(text="Please check your account settings page.", grounding=[])
    result = pii_scrub(draft, _context())
    assert result.passed


def test_pii_scrub_fails_on_ssn_like_pattern():
    draft = DraftResponse(text="Your SSN on file is 123-45-6789.", grounding=[])
    result = pii_scrub(draft, _context())
    assert not result.passed
    assert "Social Security" in result.reason


def test_tone_check_passes_on_professional_draft():
    draft = DraftResponse(text="Thanks for reaching out — here's how to fix that.", grounding=[])
    result = tone_check(draft, _context())
    assert result.passed


def test_tone_check_fails_on_dismissive_language():
    draft = DraftResponse(text="That's not my problem, figure it out yourself.", grounding=[])
    result = tone_check(draft, _context())
    assert not result.passed
    assert "unprofessional" in result.reason


def test_grounding_check_passes_when_claim_cites_retrieved_chunk():
    draft = DraftResponse(
        text="Clear your cookies and retry.",
        grounding=[ClaimGrounding(claim="clear cookies", chunk_ids=["chunk-1"])],
    )
    result = grounding_check(draft, _context(["chunk-1"]))
    assert result.passed


def test_grounding_check_fails_when_claim_cites_unretrieved_chunk():
    draft = DraftResponse(
        text="Clear your cookies and retry.",
        grounding=[ClaimGrounding(claim="clear cookies", chunk_ids=["chunk-999"])],
    )
    result = grounding_check(draft, _context(["chunk-1"]))
    assert not result.passed
    assert "chunk-999" in result.reason


def test_grounding_check_fails_when_text_present_but_no_grounding():
    draft = DraftResponse(text="Clear your cookies and retry.", grounding=[])
    result = grounding_check(draft, _context(["chunk-1"]))
    assert not result.passed
    assert "no grounding entries" in result.reason


def test_grounding_check_passes_when_draft_and_grounding_both_empty():
    draft = DraftResponse(text="", grounding=[])
    result = grounding_check(draft, _context([]))
    assert result.passed
