"""Shared pytest fixtures, applied automatically to every test in the suite."""

from __future__ import annotations

import pytest

from support_agent.agent.providers.usage import clear_usage_log


@pytest.fixture(autouse=True)
def _clear_usage_log():
    """agent/providers/usage.py's log is module-level, process-wide state
    (see its docstring) — without this, usage recorded during one test
    would leak into another test's assertions."""
    clear_usage_log()
    yield
    clear_usage_log()
