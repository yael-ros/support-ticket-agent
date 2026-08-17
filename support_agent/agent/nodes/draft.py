"""LangGraph node: draft a reply to a classified, retrieval-augmented ticket.

Per .claude/skills/agent-conventions, reads `state.ticket` and
`state.retrieval_context` and writes `state.draft`; every other field on
state is left untouched. Runs after retrieve.py in the graph
(agent/graph.py), so retrieval_context must already be set.

Model tier: STRONG. Drafting a customer-facing reply is open-ended
generation, unlike classification's fixed label set — worth the
stronger (and more expensive) tier. This node doesn't know or care which
concrete model/provider STRONG resolves to — see agent/llm_client.py and
agent/providers/.
"""

from __future__ import annotations

from support_agent.agent.llm_client import ModelTier, call_structured
from support_agent.agent.prompts import format_draft_prompt
from support_agent.schemas import AgentState, DraftResponse

# call_structured's default max_tokens (1024) is sized for classify.py's
# tiny {category, urgency, confidence} object. A draft has to fit both an
# open-ended customer-facing reply AND a structured grounding breakdown
# in the same JSON payload — observed live, 1024 truncates mid-object on
# a real ticket (Pydantic raised "EOF while parsing an object" on the cut
# JSON). 2048 was not similarly derived from a failure — it's a
# conservative-looking round-number headroom bump, worth revisiting with
# real token-count data once eval/results/full_report.md's Phase 5 cost
# numbers exist.
DRAFT_MAX_TOKENS = 2048


def draft_response(state: AgentState) -> AgentState:
    if state.retrieval_context is None:
        raise ValueError("draft_response requires state.retrieval_context to be set first")

    prompt = format_draft_prompt(
        state.ticket.subject, state.ticket.body, state.retrieval_context.chunks
    )
    draft = call_structured(
        prompt=prompt, response_model=DraftResponse, tier=ModelTier.STRONG, max_tokens=DRAFT_MAX_TOKENS
    )
    return state.model_copy(update={"draft": draft})
