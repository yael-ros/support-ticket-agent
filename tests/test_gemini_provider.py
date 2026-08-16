"""Unit tests for providers/gemini_provider.py — no live API calls.

call_structured()-level tests patch GeminiProvider._generate directly,
bypassing the real Gemini client entirely. The retry tests instead swap in
a fake client so tenacity's real retry/backoff logic runs against it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from support_agent.agent.providers.base import LLMCallError, ModelTier
from support_agent.agent.providers.gemini_provider import (
    GeminiProvider,
    _server_retry_delay_seconds,
)


class _DummySchema(BaseModel):
    value: str


def _make_provider() -> GeminiProvider:
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        return GeminiProvider()


def _fake_response(text: str):
    return SimpleNamespace(text=text)


def test_call_structured_happy_path():
    provider = _make_provider()
    fake_response = _fake_response('{"value": "hello"}')
    with patch.object(GeminiProvider, "_generate", return_value=fake_response):
        result = provider.call_structured(
            prompt="test prompt", response_model=_DummySchema, tier=ModelTier.FAST
        )

    assert isinstance(result, _DummySchema)
    assert result.value == "hello"


def test_call_structured_empty_text_raises():
    provider = _make_provider()
    fake_response = _fake_response("")
    with (
        patch.object(GeminiProvider, "_generate", return_value=fake_response),
        pytest.raises(LLMCallError, match="no text content"),
    ):
        provider.call_structured(prompt="test prompt", response_model=_DummySchema, tier=ModelTier.FAST)


def test_call_structured_schema_validation_failure_raises():
    provider = _make_provider()
    fake_response = _fake_response('{"wrong_field": 123}')
    with (
        patch.object(GeminiProvider, "_generate", return_value=fake_response),
        pytest.raises(LLMCallError, match="failed schema validation"),
    ):
        provider.call_structured(prompt="test prompt", response_model=_DummySchema, tier=ModelTier.FAST)


def test_missing_api_key_raises_on_construction():
    with (
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(LLMCallError, match="GEMINI_API_KEY"),
    ):
        GeminiProvider()


def test_generate_retries_transient_errors_then_succeeds():
    provider = _make_provider()
    fake_success = _fake_response('{"value": "ok"}')

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [
        genai_errors.APIError(code=503, response_json={"message": "unavailable"}),
        genai_errors.APIError(code=429, response_json={"message": "rate limited"}),
        fake_success,
    ]
    provider._client = fake_client

    result = provider._generate(model="fake-model", contents="hi", config={})

    assert result is fake_success
    assert fake_client.models.generate_content.call_count == 3


def test_server_retry_delay_seconds_parses_retry_info():
    exc = genai_errors.ClientError(
        429,
        {
            "error": {
                "code": 429,
                "message": "quota exceeded",
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": []},
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "46s"},
                ],
            }
        },
    )
    assert _server_retry_delay_seconds(exc) == 46.0


def test_server_retry_delay_seconds_returns_none_without_retry_info():
    exc = genai_errors.APIError(code=503, response_json={"error": {"message": "unavailable"}})
    assert _server_retry_delay_seconds(exc) is None


def test_generate_waits_for_server_specified_retry_delay(monkeypatch):
    provider = _make_provider()
    fake_success = _fake_response('{"value": "ok"}')
    rate_limited = genai_errors.ClientError(
        429,
        {
            "error": {
                "code": 429,
                "status": "RESOURCE_EXHAUSTED",
                "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "2.5s"}],
            }
        },
    )

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [rate_limited, fake_success]
    provider._client = fake_client

    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    result = provider._generate(model="fake-model", contents="hi", config={})

    assert result is fake_success
    assert sleeps == [3.5]  # server's 2.5s + our 1s buffer


def test_generate_does_not_retry_non_retryable_error():
    provider = _make_provider()
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = genai_errors.APIError(
        code=400, response_json={"message": "bad request"}
    )
    provider._client = fake_client

    with pytest.raises(genai_errors.APIError):
        provider._generate(model="fake-model", contents="hi", config={})

    assert fake_client.models.generate_content.call_count == 1
