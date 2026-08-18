"""In-memory token-usage log, populated by each provider after a real API call.

Exists so evaluation/run_eval.py (and, later, Phase 7's observability
logging) can report real per-ticket cost without changing
call_structured()'s return type — every existing call site
(classify.py, draft.py, evaluation/llm_judge.py, ...) keeps getting back
just the parsed response_model instance. Each provider records usage
itself, right after it has the raw API response with real usage
metadata, before returning the parsed model up the call stack — see
anthropic_provider.py and gemini_provider.py.

Module-level state, not per-provider-instance: a single eval run may use
one provider instance across many calls (agent/llm_client.py caches
provider instances), and the log needs to span the whole batch, not just
one provider's lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass

from support_agent.agent.providers.base import ModelTier


@dataclass(frozen=True)
class CallUsage:
    provider: str
    tier: ModelTier
    input_tokens: int
    output_tokens: int


_usage_log: list[CallUsage] = []


def record_usage(*, provider: str, tier: ModelTier, input_tokens: int, output_tokens: int) -> None:
    _usage_log.append(
        CallUsage(provider=provider, tier=tier, input_tokens=input_tokens, output_tokens=output_tokens)
    )


def get_usage_log() -> list[CallUsage]:
    return list(_usage_log)


def clear_usage_log() -> None:
    _usage_log.clear()
