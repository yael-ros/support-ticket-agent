"""Guardrail checks: pure functions over a drafted response, per CLAUDE.md.

Per CLAUDE.md: "Guardrails are testable functions, not prompt
instructions. A guardrail that only exists as 'please don't do X' in a
prompt is not a guardrail." DRAFT_RESPONSE_PROMPT (agent/prompts.py)
already *asks* the model not to promise refunds or invent facts — these
functions are what actually check the model complied, deterministically
and after the fact, independent of the process that produced the draft.

Every check has the same signature —
`(draft: DraftResponse, context: RetrievalContext) -> GuardrailResult` —
even though not every check uses `context`, so agent/nodes/guardrail_check.py
can run the whole GUARDRAIL_CHECKS list uniformly. See
.claude/skills/agent-conventions for the convention this follows.
"""

from __future__ import annotations

import re

from support_agent.schemas import DraftResponse, GuardrailResult, RetrievalContext

# Deliberately simple, literal phrase matching rather than anything
# fuzzier: a guardrail's whole value is being predictable and auditable.
# False negatives (a promise phrased unusually) are expected and are what
# grounding_check and human review are the backstop for; this list isn't
# trying to be exhaustive NLP.
_PROMISE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bfull refund\b",
        r"\b100%\s*(refund|money[- ]back)\b",
        r"\bfree of charge\b",
        r"\bwe(?:'ll| will) waive\b",
        r"\bguarantee(?:d)?\b",
        r"\bcompensat(?:e|ion)\b",
        r"\bfree (?:upgrade|product|service)\b",
    ]
]


def no_unauthorized_promises(draft: DraftResponse, context: RetrievalContext) -> GuardrailResult:
    """Fails if the draft promises a refund, discount, or other concession no one authorized."""
    for pattern in _PROMISE_PATTERNS:
        if pattern.search(draft.text):
            return GuardrailResult(
                check_name="no_unauthorized_promises",
                passed=False,
                reason=f"Draft contains unauthorized-promise language matching /{pattern.pattern}/",
            )
    return GuardrailResult(
        check_name="no_unauthorized_promises", passed=True, reason="No unauthorized-promise language detected"
    )


_PII_PATTERNS = {
    "a credit-card-shaped number": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "a Social Security number": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}


def pii_scrub(draft: DraftResponse, context: RetrievalContext) -> GuardrailResult:
    """Fails if the draft appears to echo back sensitive personal/financial data."""
    for label, pattern in _PII_PATTERNS.items():
        if pattern.search(draft.text):
            return GuardrailResult(check_name="pii_scrub", passed=False, reason=f"Draft appears to contain {label}")
    return GuardrailResult(check_name="pii_scrub", passed=True, reason="No PII patterns detected")


_UNPROFESSIONAL_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [r"\bstupid\b", r"\bshut up\b", r"\bnot my problem\b", r"\bidiot\b", r"\bwhatever\b"]
]


def tone_check(draft: DraftResponse, context: RetrievalContext) -> GuardrailResult:
    """Fails if the draft is empty, shouty, or uses dismissive/unprofessional language."""
    text = draft.text.strip()
    if not text:
        return GuardrailResult(check_name="tone_check", passed=False, reason="Draft response is empty")

    for pattern in _UNPROFESSIONAL_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(
                check_name="tone_check",
                passed=False,
                reason=f"Draft contains unprofessional language matching /{pattern.pattern}/",
            )

    if len(text) > 20 and text.upper() == text and any(c.isalpha() for c in text):
        return GuardrailResult(check_name="tone_check", passed=False, reason="Draft is written in all caps")

    return GuardrailResult(check_name="tone_check", passed=True, reason="No tone issues detected")


def grounding_check(draft: DraftResponse, context: RetrievalContext) -> GuardrailResult:
    """Fails if any claim in the draft isn't backed by a chunk id that was actually retrieved.

    This is what makes draft.py's citation requirement (agent/prompts.py's
    DRAFT_RESPONSE_PROMPT) checkable rather than a claim we just trust the
    model to have followed.
    """
    text = draft.text.strip()
    if not draft.grounding:
        if not text:
            return GuardrailResult(check_name="grounding_check", passed=True, reason="Draft is empty; nothing to ground")
        return GuardrailResult(
            check_name="grounding_check", passed=False, reason="Draft has body text but no grounding entries"
        )

    valid_chunk_ids = {chunk.chunk_id for chunk in context.chunks}
    for claim in draft.grounding:
        if not claim.chunk_ids:
            return GuardrailResult(
                check_name="grounding_check",
                passed=False,
                reason=f"Claim {claim.claim!r} has no supporting chunk ids",
            )
        unknown = [cid for cid in claim.chunk_ids if cid not in valid_chunk_ids]
        if unknown:
            return GuardrailResult(
                check_name="grounding_check",
                passed=False,
                reason=f"Claim {claim.claim!r} cites chunk id(s) not in the retrieved context: {unknown}",
            )

    return GuardrailResult(
        check_name="grounding_check", passed=True, reason="Every claim is grounded in a retrieved chunk"
    )
