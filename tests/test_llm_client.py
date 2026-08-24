"""Unit tests for llm_client.py's provider-selection dispatcher.

These test routing only (LLM_PROVIDER -> provider instance -> delegated
call), not any concrete provider's internals — see test_anthropic_provider.py
and test_gemini_provider.py for those.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from support_agent.agent import llm_client
from support_agent.agent.llm_client import LLMCallError, ModelTier, call_structured, force_provider


class _DummySchema(BaseModel):
    value: str


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    llm_client._provider_instances.clear()
    yield
    llm_client._provider_instances.clear()


def test_call_structured_delegates_to_configured_provider():
    fake_provider = MagicMock()
    fake_provider.call_structured.return_value = _DummySchema(value="hi")
    fake_provider_cls = MagicMock(return_value=fake_provider)

    with (
        patch.dict("os.environ", {"LLM_PROVIDER": "gemini"}),
        patch.object(llm_client, "_PROVIDER_FACTORIES", {"gemini": fake_provider_cls}),
    ):
        result = call_structured(prompt="p", response_model=_DummySchema, tier=ModelTier.FAST)

    assert result.value == "hi"
    fake_provider.call_structured.assert_called_once_with(
        prompt="p", response_model=_DummySchema, tier=ModelTier.FAST, max_tokens=1024, system=None
    )


def test_defaults_to_gemini_when_env_var_unset():
    fake_provider_cls = MagicMock()
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.object(llm_client, "_PROVIDER_FACTORIES", {"gemini": fake_provider_cls}),
    ):
        llm_client._get_provider()

    fake_provider_cls.assert_called_once()


def test_unknown_provider_raises():
    with (
        patch.dict("os.environ", {"LLM_PROVIDER": "not-a-real-provider"}),
        pytest.raises(LLMCallError, match="Unknown LLM_PROVIDER"),
    ):
        llm_client._get_provider()


def test_provider_instance_is_cached_across_calls():
    fake_provider_cls = MagicMock()
    with (
        patch.dict("os.environ", {"LLM_PROVIDER": "gemini"}),
        patch.object(llm_client, "_PROVIDER_FACTORIES", {"gemini": fake_provider_cls}),
    ):
        first = llm_client._get_provider()
        second = llm_client._get_provider()

    assert first is second
    fake_provider_cls.assert_called_once()


def test_force_provider_overrides_the_env_var_within_its_context():
    fake_gemini_cls = MagicMock()
    fake_anthropic_cls = MagicMock()
    with (
        patch.dict("os.environ", {"LLM_PROVIDER": "anthropic"}),
        patch.object(
            llm_client,
            "_PROVIDER_FACTORIES",
            {"gemini": fake_gemini_cls, "anthropic": fake_anthropic_cls},
        ),
    ):
        with force_provider("gemini"):
            llm_client._get_provider()
        fake_gemini_cls.assert_called_once()
        fake_anthropic_cls.assert_not_called()

        # outside the context, the env var is respected again
        llm_client._get_provider()
        fake_anthropic_cls.assert_called_once()


def test_force_provider_resets_after_the_context_exits():
    fake_gemini_cls = MagicMock()
    fake_anthropic_cls = MagicMock()
    with (
        patch.dict("os.environ", {"LLM_PROVIDER": "anthropic"}),
        patch.object(
            llm_client,
            "_PROVIDER_FACTORIES",
            {"gemini": fake_gemini_cls, "anthropic": fake_anthropic_cls},
        ),
    ):
        with force_provider("gemini"):
            pass
        llm_client._get_provider()

    fake_anthropic_cls.assert_called_once()
    fake_gemini_cls.assert_not_called()


def test_force_provider_resets_even_if_the_call_raises():
    with patch.dict("os.environ", {"LLM_PROVIDER": "anthropic"}):
        with pytest.raises(RuntimeError), force_provider("gemini"):
            raise RuntimeError("boom")

        assert llm_client._provider_override.get() is None
