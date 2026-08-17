"""LangGraph node: route a ticket to auto-send or human review.

Per BUILD_PLAN.md Phase 4: combines classification confidence and
guardrail pass/fail into a single routing decision. CONFIDENCE_THRESHOLD
is a named constant (not a magic number) so the auto-send bar is visible
and changeable in one place.

Threshold choice: 0.75, per BUILD_PLAN.md's specified default. Worth
flagging: eval/results/classification_report.md's Phase 3 run found the
model's self-reported confidence does NOT reliably track correctness
(avg confidence 0.936 against ~65% category accuracy on the gold set) —
so this threshold is a known-imperfect, deliberately conservative
starting point, not a value tuned against outcome data. A future phase
could calibrate it against eval results instead of the model's raw
self-report; until then, the other two checks below (guardrails, empty
retrieval) matter more than this one for catching bad auto-sends.

A ticket is routed to human_review if ANY of:
- classification confidence is below CONFIDENCE_THRESHOLD,
- any guardrail check failed (agent/nodes/guardrail_check.py),
- retrieval returned zero chunks — an explicit state per CLAUDE.md's "no
  silent failures" rule, since auto-sending a reply built on no
  retrieved context at all is exactly what grounding_check and this
  check exist to catch.
Otherwise the ticket is routed to auto_send. Every contributing reason is
recorded (not just the first), so a human reviewing the ticket sees the
full picture.
"""

from __future__ import annotations

from support_agent.schemas import AgentState, RoutingDecision

CONFIDENCE_THRESHOLD = 0.75


def route_ticket(state: AgentState) -> AgentState:
    if state.classification is None or state.retrieval_context is None or state.guardrail_results is None:
        raise ValueError(
            "route_ticket requires state.classification, state.retrieval_context, and "
            "state.guardrail_results to be set first"
        )

    reasons: list[str] = []

    if state.classification.confidence < CONFIDENCE_THRESHOLD:
        reasons.append(
            f"classification confidence {state.classification.confidence:.2f} is below "
            f"threshold {CONFIDENCE_THRESHOLD}"
        )

    failed_checks = [r for r in state.guardrail_results if not r.passed]
    if failed_checks:
        failed_summary = "; ".join(f"{r.check_name} ({r.reason})" for r in failed_checks)
        reasons.append(f"guardrail check(s) failed: {failed_summary}")

    if not state.retrieval_context.chunks:
        reasons.append("retrieval returned zero chunks")

    if reasons:
        decision = RoutingDecision(action="human_review", reason="; ".join(reasons))
    else:
        decision = RoutingDecision(
            action="auto_send", reason="classification confidence and all guardrail checks passed"
        )

    return state.model_copy(update={"routing_decision": decision})
