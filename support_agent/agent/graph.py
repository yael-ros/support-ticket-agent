"""The agent's LangGraph state machine.

Per CLAUDE.md: an explicit graph, not a single mega-prompt — each node is
independently testable (agent/nodes/*.py) and this file's only job is
wiring them together: classify -> retrieve -> draft -> guardrail_check ->
route.

ASSUMPTION: this graph stops at `route`. It produces a RoutingDecision
(state.routing_decision) but doesn't act on it — BUILD_PLAN.md's Phase 4
sequence also names `auto_send | human_review -> update_ticket`, but
those are side effects (actually sending a reply, updating a CRM) that
depend on the EmailSender abstraction BUILD_PLAN.md scopes to Phase 6,
which doesn't exist yet. Phase 4's job is producing the decision;
Phase 6's API layer is what will act on state.routing_decision once a
real send/update mechanism exists.

`StateGraph(AgentState)` accepts the Pydantic model directly (confirmed
against the installed langgraph version — see task history). Each node
function takes and returns a full AgentState (via `state.model_copy`),
which langgraph merges correctly; `compiled.invoke()` returns a plain
dict, not an AgentState, so run_agent() re-validates it back into one.

Observability (BUILD_PLAN.md Phase 7): every node is wrapped with
observability/logging.py's log_node() at registration time below, not
inside the node functions themselves — nodes stay pure and independently
testable (see .claude/skills/agent-conventions), logging is purely a
graph-assembly concern. run_agent() additionally logs one summary event
per ticket (total latency, final routing decision).
"""

from __future__ import annotations

import time

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from support_agent.agent.nodes.classify import classify_ticket
from support_agent.agent.nodes.draft import draft_response
from support_agent.agent.nodes.guardrail_check import guardrail_check
from support_agent.agent.nodes.retrieve import retrieve_context
from support_agent.agent.nodes.route import route_ticket
from support_agent.observability.logging import log_node, log_ticket_processed
from support_agent.schemas import AgentState, Ticket


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("classify", log_node("classify", classify_ticket))
    graph.add_node("retrieve", log_node("retrieve", retrieve_context))
    graph.add_node("draft", log_node("draft", draft_response))
    graph.add_node("guardrail_check", log_node("guardrail_check", guardrail_check))
    graph.add_node("route", log_node("route", route_ticket))

    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "draft")
    graph.add_edge("draft", "guardrail_check")
    graph.add_edge("guardrail_check", "route")
    graph.add_edge("route", END)

    return graph.compile()


def run_agent(ticket: Ticket) -> AgentState:
    """Run the full graph for one ticket, returning the final AgentState."""
    compiled = build_graph()
    start = time.perf_counter()
    result = compiled.invoke(AgentState(ticket=ticket))
    final_state = AgentState.model_validate(result)
    log_ticket_processed(ticket.id, final_state, (time.perf_counter() - start) * 1000)
    return final_state
