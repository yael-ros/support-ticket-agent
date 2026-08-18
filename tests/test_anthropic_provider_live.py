"""Opt-in live regression test for the $PARAMETER_NAME / nested-schema bug.

See anthropic_provider.py's module docstring for the full story: Claude
Sonnet 5, called via the old forced tool-use mechanism, wrapped its
output in a bogus `{"$PARAMETER_NAME": {...}}` key 100% reproducibly
whenever the schema contained an array-of-objects via $ref
(DraftResponse.grounding: list[ClaimGrounding]) — TicketClassification's
own $defs (plain enums, no array-of-objects) never triggered it, so the
bug was specifically about that array-of-objects shape, not $defs
presence in general. Switching to client.messages.parse(output_format=...)
fixed it, confirmed live against this exact model/schema combination.

This test is the only thing that would catch a regression on that exact
path (an SDK upgrade, a provider change, a schema change) — every other
test in this suite mocks the API response and would happily keep passing
even if this exact bug came back. It's opt-in, not part of the default
`pytest -q` run, specifically to avoid a live, billed API call running by
accident in CI or on every local test run — every other test in this
project mocks the API for the same reason; this is a deliberate,
narrowly-scoped exception, not a new default.

    RUN_LIVE_ANTHROPIC_TESTS=1 pytest tests/test_anthropic_provider_live.py

Requires a real ANTHROPIC_API_KEY with credit (via env var or a
gitignored .env — see anthropic_provider.py). Makes exactly one real,
billed Claude Sonnet 5 call, capped at a small max_tokens.
"""

from __future__ import annotations

import os

import pytest

from support_agent.agent.providers.anthropic_provider import AnthropicProvider
from support_agent.agent.providers.base import ModelTier
from support_agent.schemas import ClaimGrounding, DraftResponse

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_ANTHROPIC_TESTS") != "1",
    reason="opt-in live test — set RUN_LIVE_ANTHROPIC_TESTS=1 (and a real ANTHROPIC_API_KEY) to run it",
)


def test_call_structured_handles_array_of_objects_schema_live():
    """DraftResponse.grounding is exactly the array-of-objects-via-$ref
    shape that reproduced the $PARAMETER_NAME bug under forced tool-use."""
    provider = AnthropicProvider()
    result = provider.call_structured(
        prompt=(
            "Reply with a DraftResponse: text should be the single word 'hello', and "
            "grounding should contain exactly one entry with claim='test' and "
            "chunk_ids=['chunk-1']."
        ),
        response_model=DraftResponse,
        tier=ModelTier.STRONG,
        max_tokens=256,
    )

    assert isinstance(result, DraftResponse)
    assert isinstance(result.text, str) and result.text
    assert len(result.grounding) >= 1
    assert isinstance(result.grounding[0], ClaimGrounding)
