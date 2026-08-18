"""Unit tests for providers/anthropic_provider.py — no live API calls.

call_structured()-level tests patch AnthropicProvider._call_with_retry
directly, bypassing the real Anthropic client entirely. The retry test
instead swaps in a fake client so tenacity's real retry/backoff logic
runs against it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from anthropic import APIConnectionError
from pydantic import BaseModel, ValidationError

from support_agent.agent.providers.anthropic_provider import AnthropicProvider
from support_agent.agent.providers.base import LLMCallError, ModelTier
from support_agent.agent.providers.usage import get_usage_log


class _DummySchema(BaseModel):
    value: str


def _fake_parsed_message(parsed_output, input_tokens: int = 10, output_tokens: int = 5, stop_reason="end_turn"):
    return SimpleNamespace(
        parsed_output=parsed_output,
        stop_reason=stop_reason,
        content=[],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _make_provider() -> AnthropicProvider:
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        return AnthropicProvider()


def test_call_structured_happy_path():
    provider = _make_provider()
    fake_response = _fake_parsed_message(_DummySchema(value="hello"), input_tokens=42, output_tokens=7)
    with patch.object(AnthropicProvider, "_call_with_retry", return_value=fake_response) as mock_call:
        result = provider.call_structured(
            prompt="test prompt", response_model=_DummySchema, tier=ModelTier.FAST
        )

    assert isinstance(result, _DummySchema)
    assert result.value == "hello"

    _, kwargs = mock_call.call_args
    assert kwargs["output_format"] is _DummySchema

    usage_log = get_usage_log()
    assert len(usage_log) == 1
    assert usage_log[0].provider == "anthropic"
    assert usage_log[0].tier is ModelTier.FAST
    assert usage_log[0].input_tokens == 42
    assert usage_log[0].output_tokens == 7


def test_call_structured_unparseable_output_raises():
    provider = _make_provider()
    fake_response = _fake_parsed_message(None, stop_reason="refusal")
    with (
        patch.object(AnthropicProvider, "_call_with_retry", return_value=fake_response),
        pytest.raises(LLMCallError, match="did not return a parseable"),
    ):
        provider.call_structured(prompt="test prompt", response_model=_DummySchema, tier=ModelTier.FAST)


def test_call_structured_wraps_validation_error_from_unparseable_json():
    # .parse() raises a bare pydantic.ValidationError (not LLMCallError)
    # when the response text isn't valid JSON at all — e.g. truncated
    # mid-string because max_tokens was too small. Reproduced live.
    provider = _make_provider()
    try:
        _DummySchema.model_validate_json("not valid json")
    except ValidationError as exc:
        validation_error = exc

    with (
        patch.object(AnthropicProvider, "_call_with_retry", side_effect=validation_error),
        pytest.raises(LLMCallError, match="failed schema validation"),
    ):
        provider.call_structured(prompt="test prompt", response_model=_DummySchema, tier=ModelTier.FAST)


def test_missing_api_key_raises_on_construction():
    with (
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(LLMCallError, match="ANTHROPIC_API_KEY"),
    ):
        AnthropicProvider()


def test_call_with_retry_retries_transient_errors_then_succeeds():
    provider = _make_provider()
    dummy_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    fake_success = _fake_parsed_message(_DummySchema(value="ok"))

    fake_client = MagicMock()
    fake_client.messages.parse.side_effect = [
        APIConnectionError(request=dummy_request),
        APIConnectionError(request=dummy_request),
        fake_success,
    ]
    provider._client = fake_client

    result = provider._call_with_retry(model="fake-model", max_tokens=10, messages=[])

    assert result is fake_success
    assert fake_client.messages.parse.call_count == 3
