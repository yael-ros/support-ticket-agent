"""LangGraph node: run every registered guardrail against a drafted response.

Per .claude/skills/agent-conventions: guardrails themselves are pure
functions in agent/guardrails.py; this node's only job is to run the
registered GUARDRAIL_CHECKS set and record every result — not just the
first failure — so a ticket routed to human review shows a reviewer
everything that was checked, not just whichever check happened to fail
first. Reads `state.draft` and `state.retrieval_context`, writes
`state.guardrail_results`.

New guardrails are added to GUARDRAIL_CHECKS here, not called ad hoc
elsewhere — this keeps the active check set visible in one place.
"""

from __future__ import annotations

from collections.abc import Callable

from support_agent.agent.guardrails import (
    grounding_check,
    no_unauthorized_promises,
    pii_scrub,
    tone_check,
)
from support_agent.schemas import AgentState, DraftResponse, GuardrailResult, RetrievalContext

GUARDRAIL_CHECKS: list[Callable[[DraftResponse, RetrievalContext], GuardrailResult]] = [
    no_unauthorized_promises,
    pii_scrub,
    tone_check,
    grounding_check,
]


def guardrail_check(state: AgentState) -> AgentState:
    if state.draft is None or state.retrieval_context is None:
        raise ValueError(
            "guardrail_check requires state.draft and state.retrieval_context to be set first"
        )

    results = [check(state.draft, state.retrieval_context) for check in GUARDRAIL_CHECKS]
    return state.model_copy(update={"guardrail_results": results})
