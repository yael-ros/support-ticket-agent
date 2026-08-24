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

force_provider() lets a caller (api/demo.py's unauthenticated demo
endpoint — see PORTFOLIO_ADDITIONS.md) pin the provider for one call
tree without touching the LLM_PROVIDER env var, which is process-wide and
therefore unsafe to mutate per-request under concurrent traffic (one
demo request flipping it would affect every other in-flight request,
including authenticated /tickets calls on a different provider). It uses
a contextvars.ContextVar, which FastAPI/Starlette correctly propagate
into the thread pool a sync endpoint runs in and correctly isolate
between concurrent requests (confirmed empirically before relying on
this — see task history).

Provider SDKs are imported lazily, inside _load_anthropic_provider() /
_load_gemini_provider(), not at module top level. Measured directly
(see HANDOFF.md's Ops section): the anthropic SDK costs ~15MB of process
RSS to import, google-genai ~76MB — importing both unconditionally at
process startup, when a given deployment only ever uses one, was pure
waste on a memory-constrained free-tier host. Whichever provider
LLM_PROVIDER actually resolves to now only pays that cost on its first
real call, and the other provider's SDK is never imported at all.
"""

from __future__ import annotations

import contextlib
import contextvars
import os
from collections.abc import Callable, Iterator
from typing import TypeVar

from pydantic import BaseModel

from support_agent.agent.providers.base import LLMCallError, LLMProvider, ModelTier

__all__ = ["LLMCallError", "ModelTier", "call_structured", "force_provider"]

T = TypeVar("T", bound=BaseModel)

DEFAULT_PROVIDER = "gemini"


def _load_anthropic_provider() -> LLMProvider:
    from support_agent.agent.providers.anthropic_provider import AnthropicProvider

    return AnthropicProvider()


def _load_gemini_provider() -> LLMProvider:
    from support_agent.agent.providers.gemini_provider import GeminiProvider

    return GeminiProvider()


_PROVIDER_FACTORIES: dict[str, Callable[[], LLMProvider]] = {
    "anthropic": _load_anthropic_provider,
    "gemini": _load_gemini_provider,
}

_provider_instances: dict[str, LLMProvider] = {}

_provider_override: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_provider_override", default=None
)


@contextlib.contextmanager
def force_provider(name: str) -> Iterator[None]:
    """Force _get_provider() to resolve to `name` for calls made within this context."""
    token = _provider_override.set(name)
    try:
        yield
    finally:
        _provider_override.reset(token)


def _get_provider() -> LLMProvider:
    """Resolve the active provider to a (cached, lazily-constructed) instance.

    Checks force_provider()'s context override first, then re-reads the
    LLM_PROVIDER env var on every call rather than caching the *name*, so
    tests (and callers) can switch providers within a process by setting
    the env var — each distinct provider name still only gets constructed
    once (construction is what requires the provider's API key).
    """
    name = (_provider_override.get() or os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER)).lower()
    if name not in _PROVIDER_FACTORIES:
        raise LLMCallError(
            f"Unknown LLM_PROVIDER={name!r}; choose one of {sorted(_PROVIDER_FACTORIES)}"
        )
    if name not in _provider_instances:
        _provider_instances[name] = _PROVIDER_FACTORIES[name]()
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
