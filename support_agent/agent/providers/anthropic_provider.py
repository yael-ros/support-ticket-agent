"""Anthropic implementation of the LLMProvider protocol (see providers/base.py).

Structured output goes through `client.messages.parse(output_format=...)`,
Anthropic's purpose-built structured-output helper — not forced tool-use,
and not a hand-rolled `output_config.format` call either. Two real bugs
were found and fixed live getting here, in order:

1. This project originally forced a single tool call instead (the target
   model's JSON schema as the tool's input_schema), which worked for
   classify.py's flat TicketClassification schema but broke 100%
   reproducibly on draft.py's DraftResponse: Claude Sonnet 5 wrapped its
   output in a bogus extra `{"$PARAMETER_NAME": {...}}` key whenever the
   tool's input_schema contained a $defs/$ref (DraftResponse nests
   ClaimGrounding).
2. Switching to a hand-built `output_config.format` call (passing
   `response_model.model_json_schema()` directly) fixed that, but then
   400'd on TicketClassification: `confidence: float = Field(ge=0, le=1)`
   emits JSON Schema `minimum`/`maximum` keywords, which Anthropic's
   structured-output schema validator rejects outright — no
   `additionalProperties` massaging fixes this, it's a genuinely
   unsupported schema construct server-side.

`client.messages.parse(output_format=response_model)` is the officially
documented fix for both: it derives the request schema from the Pydantic
class itself (never sends $ref-adjacent tool-use framing) and strips
constraints the API doesn't support (minimum/maximum/minLength/etc.)
before sending, validating them client-side instead — undifferentiated
schema-translation work we'd otherwise have to reimplement and keep in
sync with the API's evolving limitations ourselves.

3. `.parse()`'s `response.parsed_output` is `None` when the model
   returned well-formed JSON that doesn't match the schema, but raises a
   raw `pydantic.ValidationError` (not caught anywhere by default) when
   the response text isn't even valid JSON — e.g. truncated mid-string
   because `max_tokens` was too small for the model's actual output
   (observed live on evaluation/llm_judge.py's judge call before its own
   max_tokens was raised). We catch `ValidationError` explicitly below so
   that failure mode still surfaces as `LLMCallError`, per this
   provider's documented contract, instead of an uncaught pydantic
   exception breaking out of the LLMProvider abstraction.
4. Claude Sonnet 5 defaults to adaptive thinking ON when `thinking` is
   omitted (unlike Opus 4.8 and earlier, where omitting it meant no
   thinking) — confirmed live: a full 40-ticket Phase 5 run had 3/40
   failures, all draft/judge calls on Sonnet 5 truncating mid-JSON, one
   with a `ThinkingBlock` visible in the raw response. `max_tokens` caps
   thinking + response text combined, so hidden reasoning tokens were
   silently eating the budget meant for the structured JSON output. None
   of classify/draft/judge need visible chain-of-thought, so
   `thinking={"type": "disabled"}` is passed on every call (verified live
   against both Haiku 4.5 and Sonnet 5 that this is accepted, not just
   assumed) — this also cuts cost and latency, same rationale as
   gemini_provider.py's `thinking_budget=0`.

SDK version note: `output_format`/`output_config` requires anthropic
SDK >= ~0.122 (pyproject.toml pins this) — confirmed live that 0.72.1
doesn't expose the parameter at all (TypeError at the client, before any
request is sent).

Retry policy: transient errors (connection issues, timeouts, rate limits,
5xx server errors) are retried up to MAX_RETRIES times with exponential
backoff. Schema-validation failures are NOT retried — a malformed response
means something is wrong with the prompt or model behavior, not a network
hiccup, and blindly retrying could mask a systematic problem instead of
surfacing it.
"""

from __future__ import annotations

import os
from typing import TypeVar

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from support_agent.agent.providers.base import LLMCallError, ModelTier
from support_agent.agent.providers.usage import record_usage

# Loads a repo-root .env file (gitignored) if present, without overriding
# any key already set in the real environment. A no-op if no .env file
# exists — safe to call unconditionally at import time.
load_dotenv()

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 3

# FAST mirrors the model classify.py has used since Phase 3. STRONG is a
# placeholder for Phase 4's draft-generation node — not exercised yet.
MODEL_BY_TIER = {
    ModelTier.FAST: "claude-haiku-4-5-20251001",
    ModelTier.STRONG: "claude-sonnet-5",
}

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class AnthropicProvider:
    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMCallError(
                "ANTHROPIC_API_KEY is not set. Set it as an environment variable "
                "(or in a gitignored .env file) before making LLM calls."
            )
        self._client = anthropic.Anthropic(api_key=api_key, timeout=DEFAULT_TIMEOUT_SECONDS)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        reraise=True,
    )
    def _call_with_retry(self, **kwargs):
        return self._client.messages.parse(**kwargs)

    def call_structured(
        self,
        *,
        prompt: str,
        response_model: type[T],
        tier: ModelTier,
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> T:
        kwargs: dict = {
            "model": MODEL_BY_TIER[tier],
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "output_format": response_model,
            "thinking": {"type": "disabled"},
        }
        if system:
            kwargs["system"] = system

        try:
            response = self._call_with_retry(**kwargs)
        except _RETRYABLE_ERRORS as exc:
            raise LLMCallError(f"LLM call failed after {MAX_RETRIES} attempts: {exc}") from exc
        except anthropic.APIError as exc:
            raise LLMCallError(f"LLM call failed: {exc}") from exc
        except ValidationError as exc:
            raise LLMCallError(f"Model output failed schema validation: {exc}") from exc

        record_usage(
            provider="anthropic",
            tier=tier,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        parsed = response.parsed_output
        if parsed is None:
            raise LLMCallError(
                f"Model did not return a parseable {response_model.__name__}. "
                f"stop_reason={response.stop_reason!r}, content={response.content!r}"
            )
        return parsed
