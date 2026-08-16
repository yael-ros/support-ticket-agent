"""Shared interface every LLM provider implements, plus the tier concept
that lets a node ask for a capability level without naming a model or a
vendor.

Per CLAUDE.md, no node or route handler calls a provider directly — every
call goes through agent/llm_client.py's call_structured(), which resolves
the configured provider (see LLM_PROVIDER in llm_client.py) and delegates
to it. A node only ever sees this Protocol, never a concrete provider
class, so swapping providers (or adding a new one) never touches node code.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModelTier(str, Enum):
    """A capability/cost tier, resolved to a concrete model by each provider.

    FAST: cheap, low-latency, for well-defined structured tasks (e.g.
    ticket classification in agent/nodes/classify.py) that run on every
    incoming ticket.
    STRONG: higher-capability, for open-ended generation (e.g. Phase 4
    draft-reply generation). Defined now for forward-compatibility; not
    exercised by any node as of Phase 3.
    """

    FAST = "fast"
    STRONG = "strong"


class LLMCallError(Exception):
    """Raised when a structured LLM call fails after retries, or returns output that fails schema validation."""


class LLMProvider(Protocol):
    """What every provider in agent/providers/*_provider.py must implement."""

    def call_structured(
        self,
        *,
        prompt: str,
        response_model: type[T],
        tier: ModelTier,
        max_tokens: int,
        system: str | None,
    ) -> T:
        """Call the provider's model for `tier`, forcing a reply that validates as `response_model`.

        Must raise LLMCallError if the call fails after retries, if the
        provider's reply doesn't contain the expected structured content,
        or if that content fails Pydantic validation against
        `response_model`.
        """
        ...
