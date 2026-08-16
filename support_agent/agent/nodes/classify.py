"""LangGraph node: classify a ticket into category, urgency, and confidence.

Per .claude/skills/agent-conventions, this is a standalone function of
`AgentState -> AgentState`, testable without spinning up the full graph
(agent/graph.py, Phase 4). It reads `state.ticket` and writes
`state.classification`; every other field on state is left untouched.

Model tier: FAST. Classification is a well-defined, low-ambiguity
structured task (pick one of 10 categories, one of 4 urgency levels) — a
fast/cheap model is sufficient, and keeping per-ticket cost low matters
since classification runs on every incoming ticket. Draft generation
(Phase 4) is open-ended writing and will use the STRONG tier instead. This
node doesn't know or care which concrete model/provider FAST resolves to
— see agent/llm_client.py and agent/providers/.
"""

from __future__ import annotations

from support_agent.agent.llm_client import ModelTier, call_structured
from support_agent.agent.prompts import format_classify_prompt
from support_agent.schemas import AgentState, TicketClassification


def classify_ticket(state: AgentState) -> AgentState:
    prompt = format_classify_prompt(state.ticket.subject, state.ticket.body)
    classification = call_structured(
        prompt=prompt,
        response_model=TicketClassification,
        tier=ModelTier.FAST,
    )
    return state.model_copy(update={"classification": classification})
