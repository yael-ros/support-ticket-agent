"""Unit tests for agent/providers/usage.py."""

from __future__ import annotations

from support_agent.agent.providers.base import ModelTier
from support_agent.agent.providers.usage import clear_usage_log, get_usage_log, record_usage


def test_record_and_get_usage_log():
    record_usage(provider="gemini", tier=ModelTier.FAST, input_tokens=10, output_tokens=5)
    record_usage(provider="anthropic", tier=ModelTier.STRONG, input_tokens=20, output_tokens=8)

    log = get_usage_log()
    assert len(log) == 2
    assert log[0].provider == "gemini"
    assert log[0].input_tokens == 10
    assert log[1].provider == "anthropic"
    assert log[1].tier is ModelTier.STRONG


def test_get_usage_log_returns_a_copy():
    record_usage(provider="gemini", tier=ModelTier.FAST, input_tokens=1, output_tokens=1)
    log = get_usage_log()
    log.append("mutate me")
    assert len(get_usage_log()) == 1


def test_clear_usage_log_empties_it():
    record_usage(provider="gemini", tier=ModelTier.FAST, input_tokens=1, output_tokens=1)
    clear_usage_log()
    assert get_usage_log() == []
