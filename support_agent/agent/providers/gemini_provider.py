"""Google Gemini implementation of the LLMProvider protocol (see providers/base.py).

Uses the Gemini free tier (a Google AI Studio API key, not a billed Vertex
AI project) — this is why it's the default provider (see llm_client.py):
it lets the classification eval run without spending Anthropic credits.
Anthropic remains fully supported and is one LLM_PROVIDER env var away
(see anthropic_provider.py); nothing about that path changed.

ASSUMPTION (unverified against live docs — no web access when this was
written): the `google-genai` SDK accepts a Pydantic model class directly
as `response_schema` and derives Gemini's own OpenAPI-subset schema from
it internally. We deliberately do NOT pass response_model.model_json_schema()
ourselves, since Pydantic's raw JSON Schema output uses $defs/$ref for
nested enums (Category, Urgency) that Gemini's schema format may not
resolve — letting the SDK do its own conversion sidesteps that. If model
construction or the API call raises because response_schema rejects the
class, that assumption is what to revisit first.

We still validate the returned JSON ourselves via Pydantic (not the SDK's
own `response.parsed`) so a malformed reply raises the same LLMCallError
contract as every other provider, rather than depending on SDK-version-
specific auto-parsing behavior.

Retry policy mirrors anthropic_provider.py's in spirit (retry on 429/5xx,
don't retry schema-validation failures) but the wait strategy is
different: the free tier's per-minute quota is small enough (observed: 5
requests/minute for gemini-2.5-flash) that generic exponential backoff
frequently retries before the quota window has actually rolled over. A
429 response's body includes a `RetryInfo.retryDelay` telling us exactly
how long the server wants us to wait — `_wait_seconds` honors that when
present and only falls back to exponential backoff for errors that don't
carry one (5xx, or a 429 without RetryInfo).

Thinking disabled (thinking_config.thinking_budget=0) on every call:
observed live, some models in this family (e.g. gemini-3.5-flash) spend
hidden reasoning tokens by default even on trivial prompts (319 thinking
tokens to reply "Hello" to a one-word instruction). None of our
structured-output use cases (classify/draft/judge) want or need
chain-of-thought — it only adds cost, latency, and, since thinking
tokens can eat into max_output_tokens, truncation risk on top of the one
draft.py already had to fix once (see DRAFT_MAX_TOKENS's docstring).
"""

from __future__ import annotations

import os
import re
from typing import TypeVar

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from support_agent.agent.providers.base import LLMCallError, ModelTier
from support_agent.agent.providers.usage import record_usage

# Loads a repo-root .env file (gitignored) if present, without overriding
# any key already set in the real environment. A no-op if no .env file
# exists — safe to call unconditionally at import time.
load_dotenv()

MAX_RETRIES = 5
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Both tiers pin a dated, non-preview model id rather than a "-latest"
# alias. Originally FAST used "gemini-flash-lite-latest" and STRONG used
# "gemini-flash-latest" — aliases looked like the safer bet (a vendor-
# maintained forward-compat pointer), but observed live: the FAST alias
# silently repointed to a different underlying model (gemini-3.7-flash)
# between one session and the next, and that new model had its own
# fresh, already-exhausted 20/day free-tier quota, breaking a previously-
# working call with no code change on our side. A dated id can still get
# deprecated (see the gemini-2.5-flash-lite 404 below), but at least it
# fails loudly and predictably instead of silently drifting mid-session.
# Both ids below were verified live against this key (client.models.list()
# plus a real generate_content call) on 2026-08-18, not guessed.
#
# FAST: gemini-3.1-flash-lite. Cheap/fast tier, no thinking by default
# (see module docstring on why we disable it anyway).
#
# STRONG was originally "gemini-pro-latest" (Phase 3, before any node
# used it) as a documented placeholder; once Phase 4's draft.py actually
# exercised it, that resolved to "gemini-3.1-pro" with a live 429 at
# limit: 0 for the free tier (Pro family is billed-only on this key,
# confirmed via the error body). gemini-3.5-flash is a step up from FAST
# within the free-tier-eligible Flash family.
#
# NOTE: the dated "gemini-2.5-flash-lite" id 404s for this (new) account
# ("no longer available to new users") — dated ids from an older
# generation aren't guaranteed to stay available either. Revisit this
# pin if either id starts failing.
MODEL_BY_TIER = {
    ModelTier.FAST: "gemini-3.1-flash-lite",
    ModelTier.STRONG: "gemini-3.5-flash",
}

T = TypeVar("T", bound=BaseModel)


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, genai_errors.APIError) and getattr(exc, "code", None) in _RETRYABLE_STATUS_CODES


_RETRY_DELAY_PATTERN = re.compile(r"^([\d.]+)s$")


def _server_retry_delay_seconds(exc: BaseException) -> float | None:
    """Extract RetryInfo.retryDelay (e.g. "46s") from a Gemini APIError's body, if present."""
    details = getattr(exc, "details", None)
    if not isinstance(details, dict):
        return None
    error_body = details.get("error", details)
    for entry in error_body.get("details", []) if isinstance(error_body, dict) else []:
        if isinstance(entry, dict) and entry.get("@type", "").endswith("RetryInfo"):
            match = _RETRY_DELAY_PATTERN.match(entry.get("retryDelay", ""))
            if match:
                return float(match.group(1))
    return None


def _wait_seconds(retry_state) -> float:
    """A small buffer added to the server's own retryDelay when it names one; exponential backoff otherwise."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    server_delay = _server_retry_delay_seconds(exc) if exc else None
    if server_delay is not None:
        return server_delay + 1
    return wait_exponential(multiplier=1, min=2, max=60)(retry_state)


class GeminiProvider:
    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LLMCallError(
                "GEMINI_API_KEY is not set. Set it as an environment variable "
                "(or in a gitignored .env file) before making LLM calls."
            )
        self._client = genai.Client(api_key=api_key)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=_wait_seconds,
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _generate(self, **kwargs):
        return self._client.models.generate_content(**kwargs)

    def call_structured(
        self,
        *,
        prompt: str,
        response_model: type[T],
        tier: ModelTier,
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> T:
        config: dict = {
            "response_mime_type": "application/json",
            "response_schema": response_model,
            "max_output_tokens": max_tokens,
            "thinking_config": {"thinking_budget": 0},
        }
        if system:
            config["system_instruction"] = system

        try:
            response = self._generate(model=MODEL_BY_TIER[tier], contents=prompt, config=config)
        except genai_errors.APIError as exc:
            if _is_retryable(exc):
                raise LLMCallError(f"LLM call failed after {MAX_RETRIES} attempts: {exc}") from exc
            raise LLMCallError(f"LLM call failed: {exc}") from exc

        usage = response.usage_metadata
        if usage is not None:
            record_usage(
                provider="gemini",
                tier=tier,
                input_tokens=usage.prompt_token_count or 0,
                output_tokens=usage.candidates_token_count or 0,
            )

        if not response.text:
            raise LLMCallError(f"Model returned no text content. Response: {response!r}")

        try:
            return response_model.model_validate_json(response.text)
        except ValidationError as exc:
            raise LLMCallError(f"Model output failed schema validation: {exc}") from exc
