"""Anthropic implementation of the LLMProvider protocol (see providers/base.py).

Structured output is obtained via Claude's tool-use mechanism: the target
Pydantic model's JSON schema becomes a single forced tool call, so the
model's reply is JSON matching that schema rather than free-form prose we'd
have to parse hopefully. This is more reliable than asking the model to
"please respond in JSON" in the prompt text.

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
    def _call_with_retry(self, **kwargs) -> anthropic.types.Message:
        return self._client.messages.create(**kwargs)

    def call_structured(
        self,
        *,
        prompt: str,
        response_model: type[T],
        tier: ModelTier,
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> T:
        tool_schema = {
            "name": "emit_result",
            "description": f"Emit the result as {response_model.__name__}.",
            "input_schema": response_model.model_json_schema(),
        }

        kwargs: dict = {
            "model": MODEL_BY_TIER[tier],
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [tool_schema],
            "tool_choice": {"type": "tool", "name": "emit_result"},
        }
        if system:
            kwargs["system"] = system

        try:
            response = self._call_with_retry(**kwargs)
        except _RETRYABLE_ERRORS as exc:
            raise LLMCallError(f"LLM call failed after {MAX_RETRIES} attempts: {exc}") from exc
        except anthropic.APIError as exc:
            raise LLMCallError(f"LLM call failed: {exc}") from exc

        tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
        if not tool_use_blocks:
            raise LLMCallError(
                f"Model did not return a tool_use block. Response content: {response.content!r}"
            )

        try:
            return response_model.model_validate(tool_use_blocks[0].input)
        except ValidationError as exc:
            raise LLMCallError(f"Model output failed schema validation: {exc}") from exc
