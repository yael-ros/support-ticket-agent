"""The single entry point for every LLM call in this project.

Per CLAUDE.md: "No bare LLM calls. Every call goes through
agent/llm_client.py [...]. Never call a provider SDK directly from a node
or route handler." Nodes call call_structured() with a ModelTier, never a
concrete model name or provider — this module resolves which provider is
active (LLM_PROVIDER env var) and delegates to it. See providers/base.py
for the LLMProvider protocol and providers/*_provider.py for the concrete
implementations (Anthropic, Gemini).

Provider selection: LLM_PROVIDER=gemini|anthropic, defaulting to "gemini"
so the eval suite runs against Gemini's free tier out of the box. Anthropic
remains fully supported — set LLM_PROVIDER=anthropic (and have
ANTHROPIC_API_KEY set) to switch back with no code change.
"""

from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

from support_agent.agent.providers.anthropic_provider import AnthropicProvider
from support_agent.agent.providers.base import LLMCallError, LLMProvider, ModelTier
from support_agent.agent.providers.gemini_provider import GeminiProvider

__all__ = ["LLMCallError", "ModelTier", "call_structured"]

T = TypeVar("T", bound=BaseModel)

DEFAULT_PROVIDER = "gemini"

_PROVIDER_CLASSES: dict[str, type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}

_provider_instances: dict[str, LLMProvider] = {}


def _get_provider() -> LLMProvider:
    """Resolve LLM_PROVIDER to a (cached, lazily-constructed) provider instance.

    Re-reads the env var on every call rather than caching the *name*, so
    tests (and callers) can switch providers within a process by setting
    the env var — each distinct provider name still only gets constructed
    once (construction is what requires the provider's API key).
    """
    name = os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER).lower()
    if name not in _PROVIDER_CLASSES:
        raise LLMCallError(
            f"Unknown LLM_PROVIDER={name!r}; choose one of {sorted(_PROVIDER_CLASSES)}"
        )
    if name not in _provider_instances:
        _provider_instances[name] = _PROVIDER_CLASSES[name]()
    return _provider_instances[name]


def call_structured(
    *,
    prompt: str,
    response_model: type[T],
    tier: ModelTier = ModelTier.FAST,
    max_tokens: int = 1024,
    system: str | None = None,
) -> T:
    """Call the active provider, forcing a reply that validates as `response_model`.

    Raises LLMCallError if the call fails after retries, if the provider's
    reply doesn't contain the expected structured content, or if that
    content fails Pydantic validation against `response_model`.
    """
    return _get_provider().call_structured(
        prompt=prompt,
        response_model=response_model,
        tier=tier,
        max_tokens=max_tokens,
        system=system,
    )
