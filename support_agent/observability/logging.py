"""Structured JSON logging for the agent graph (BUILD_PLAN.md Phase 7).

Per node, per ticket: `log_node()` wraps a node function (registered in
agent/graph.py) with timing and a structured `node_completed` event —
input/output summary, retrieved chunk ids, guardrail results, or routing
decision, depending on the node. `run_agent()` additionally logs one
`ticket_processed` event per ticket with total latency and the final
routing decision.

ASSUMPTION: summaries never include raw ticket/draft text — only the
already-typed, non-free-text fields each node produces (category,
urgency, confidence, chunk ids/scores, guardrail pass/fail + reason,
routing action/reason). Ticket bodies and drafted replies are
customer-facing content, not operational metadata; logging them verbatim
to stdout/a log aggregator would be a PII leak this project has no
opt-in for. See observability/README.md for what a production deployment
would add on top of this (tracing, dashboards, drift monitoring).

Wrapping happens entirely at graph-assembly time in graph.py — the node
functions themselves stay pure `AgentState -> AgentState`, unit-testable
in isolation without pulling in logging (see .claude/skills/agent-conventions).
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable

import structlog

from support_agent.schemas import AgentState


def configure_logging() -> None:
    """Configure structlog to render JSON lines to stdout.

    Safe to call more than once (structlog.configure() just replaces the
    prior config) — called unconditionally at import time below, the same
    pattern agent/providers/gemini_provider.py uses for load_dotenv().
    """
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


configure_logging()
logger = structlog.get_logger("support_agent.agent")


def _summarize_classification(state: AgentState) -> dict:
    c = state.classification
    if c is None:
        return {}
    return {"category": c.category.value, "urgency": c.urgency.value, "confidence": c.confidence}


def _summarize_retrieval(state: AgentState) -> dict:
    ctx = state.retrieval_context
    if ctx is None:
        return {}
    return {
        "query": ctx.query,
        "chunk_ids": [chunk.chunk_id for chunk in ctx.chunks],
        "scores": [chunk.score for chunk in ctx.chunks],
    }


def _summarize_draft(state: AgentState) -> dict:
    d = state.draft
    if d is None:
        return {}
    return {"text_length": len(d.text), "grounded_claim_count": len(d.grounding)}


def _summarize_guardrails(state: AgentState) -> dict:
    results = state.guardrail_results
    if results is None:
        return {}
    return {
        "checks": [
            {"check_name": r.check_name, "passed": r.passed, "reason": r.reason} for r in results
        ]
    }


def _summarize_routing(state: AgentState) -> dict:
    rd = state.routing_decision
    if rd is None:
        return {}
    return {"action": rd.action, "reason": rd.reason}


# Keyed by the node name each node is registered under in graph.py's
# build_graph() — not the underlying function's own name.
NODE_SUMMARIZERS: dict[str, Callable[[AgentState], dict]] = {
    "classify": _summarize_classification,
    "retrieve": _summarize_retrieval,
    "draft": _summarize_draft,
    "guardrail_check": _summarize_guardrails,
    "route": _summarize_routing,
}


def log_node(
    name: str, fn: Callable[[AgentState], AgentState]
) -> Callable[[AgentState], AgentState]:
    """Wrap a node function with a `node_completed` structured log event.

    `name` must be a key in NODE_SUMMARIZERS (i.e. the same string used to
    register the node in build_graph()) so the right summary is logged.
    """
    summarize = NODE_SUMMARIZERS[name]

    @functools.wraps(fn)
    def wrapped(state: AgentState) -> AgentState:
        start = time.perf_counter()
        result = fn(state)
        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "node_completed",
            ticket_id=state.ticket.id,
            node=name,
            latency_ms=round(latency_ms, 2),
            **summarize(result),
        )
        return result

    return wrapped


def log_ticket_processed(ticket_id: str, final_state: AgentState, total_latency_ms: float) -> None:
    """Log one summary event per completed ticket (called by graph.run_agent())."""
    routing = final_state.routing_decision
    logger.info(
        "ticket_processed",
        ticket_id=ticket_id,
        total_latency_ms=round(total_latency_ms, 2),
        routing_action=routing.action if routing else None,
    )
