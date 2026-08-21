"""Re-exports `app` so `uvicorn support_agent.api:app --reload` (per CLAUDE.md) works."""

from support_agent.api.main import app

__all__ = ["app"]
