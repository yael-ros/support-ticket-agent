"""Phase 5's full-graph eval: runs every hand-reviewed gold-set ticket
through the whole agent graph (agent/graph.py) and produces
eval/results/full_report.md. The report format is fixed by
.claude/skills/eval-harness — keep them in sync if either changes.

Resilience: a single ticket failing (an LLM call exhausting its retries,
a provider quota, ...) does not abort the whole batch. Per CLAUDE.md's
"no silent failures" rule, failures are recorded and reported explicitly
(n_failed, plus each failure's ticket id and error) — not swallowed —
but a bad ticket also doesn't throw away every other ticket's
already-completed, costly LLM calls.

Cost note: this is the most expensive eval in the project — 3 live LLM
calls per ticket (classify, draft, judge), versus classification eval's
1, on top of whatever the graph's own retries cost. Coordinate on
quota/budget before pointing this at the full gold set.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from support_agent.agent.eval_classification import (
    GoldSetNotReadyError,
    effective_ground_truth,
    reviewed_rows,
)
from support_agent.agent.graph import run_agent
from support_agent.agent.nodes.route import CONFIDENCE_THRESHOLD
from support_agent.agent.providers.usage import clear_usage_log, get_usage_log
from support_agent.data.build_gold_set import load_gold_set
from support_agent.evaluation.llm_judge import judge_response
from support_agent.evaluation.metrics import compute_classification_metrics
from support_agent.knowledge_base.eval_retrieval import run_retrieval_eval
from support_agent.schemas import AgentState, Category, GoldSetRow, JudgeScore, Ticket, Urgency

REPORT_PATH = Path(__file__).parent.parent.parent / "eval" / "results" / "full_report.md"

# Illustrative-only per-1M-token rates — NOT verified against a live
# pricing source (see gemini_provider.py's docstring on why this project
# doesn't trust its own training data for provider-specific facts
# without checking them). Cost below is real token counts
# (agent/providers/usage.py) x this placeholder rate; treat the dollar
# figure in the report as order-of-magnitude, not a real budgeting
# number, until checked against the active provider's current pricing
# page.
ILLUSTRATIVE_RATE_PER_MILLION_INPUT_TOKENS = 0.10
ILLUSTRATIVE_RATE_PER_MILLION_OUTPUT_TOKENS = 0.40


def _row_to_ticket(row: GoldSetRow) -> Ticket:
    return Ticket(
        id=row.ticket_id,
        subject=row.subject,
        body=row.body,
        answer=row.reference_answer,
        category=row.weak_category,
        urgency=row.weak_urgency,
        language="en",
        raw_queue=row.weak_category.value,
        raw_priority=row.weak_urgency.value,
    )


@dataclass
class TicketRunResult:
    ticket_id: str
    state: AgentState
    judge_score: JudgeScore
    latency_seconds: float


def _run_one_ticket(row: GoldSetRow) -> TicketRunResult:
    ticket = _row_to_ticket(row)
    start = time.perf_counter()
    state = run_agent(ticket)
    judge_score = judge_response(ticket, state.draft, state.retrieval_context)
    elapsed = time.perf_counter() - start
    return TicketRunResult(ticket_id=row.ticket_id, state=state, judge_score=judge_score, latency_seconds=elapsed)


def run_full_eval(rows: list[GoldSetRow] | None = None) -> dict:
    rows = rows if rows is not None else reviewed_rows(load_gold_set())
    if not rows:
        raise GoldSetNotReadyError(
            "No hand-reviewed gold-set rows to evaluate against — see "
            ".claude/skills/eval-harness and agent/eval_classification.py."
        )

    clear_usage_log()
    ticket_results: list[TicketRunResult] = []
    failures: list[tuple[str, str]] = []

    for row in rows:
        try:
            ticket_results.append(_run_one_ticket(row))
        except Exception as exc:  # noqa: BLE001 - one bad ticket must not abort the batch; see module docstring
            failures.append((row.ticket_id, f"{type(exc).__name__}: {exc}"))

    return aggregate_results(rows, ticket_results, failures)


def aggregate_results(
    rows: list[GoldSetRow],
    ticket_results: list[TicketRunResult],
    failures: list[tuple[str, str]],
    usage_log: list | None = None,
) -> dict:
    """Turn a batch of already-completed TicketRunResults into the same dict run_full_eval() returns.

    Split out from run_full_eval() so a batch collected across multiple
    process runs (e.g. because a single run got interrupted partway
    through a large gold set — see scratchpad tooling used for that) can
    still be aggregated and reported the same way, without re-running any
    LLM calls or duplicating this math. `usage_log` defaults to the
    current process's live log (agent/providers/usage.py) — pass it
    explicitly when reconstructing usage recorded in a different process,
    since a fresh process's live log won't contain it.
    """
    usage_log = usage_log if usage_log is not None else get_usage_log()
    row_by_id = {row.ticket_id: row for row in rows}
    category_true, category_pred = [], []
    urgency_true, urgency_pred = [], []
    helpfulness_scores, correctness_scores, tone_scores = [], [], []
    latencies: list[float] = []
    auto_send_count = 0

    for result in ticket_results:
        row = row_by_id[result.ticket_id]
        gt_category, gt_urgency = effective_ground_truth(row)
        classification = result.state.classification

        category_true.append(gt_category.value)
        category_pred.append(classification.category.value)
        urgency_true.append(gt_urgency.value)
        urgency_pred.append(classification.urgency.value)

        helpfulness_scores.append(result.judge_score.helpfulness)
        correctness_scores.append(result.judge_score.correctness)
        tone_scores.append(result.judge_score.tone)

        latencies.append(result.latency_seconds)
        if result.state.routing_decision.action == "auto_send":
            auto_send_count += 1

    total_input_tokens = sum(u.input_tokens for u in usage_log)
    total_output_tokens = sum(u.output_tokens for u in usage_log)
    total_cost = (
        total_input_tokens / 1_000_000 * ILLUSTRATIVE_RATE_PER_MILLION_INPUT_TOKENS
        + total_output_tokens / 1_000_000 * ILLUSTRATIVE_RATE_PER_MILLION_OUTPUT_TOKENS
    )

    n_succeeded = len(ticket_results)
    return {
        "n_attempted": len(rows),
        "n_succeeded": n_succeeded,
        "n_failed": len(failures),
        "failures": failures,
        "category": compute_classification_metrics(category_true, category_pred, [c.value for c in Category]),
        "urgency": compute_classification_metrics(urgency_true, urgency_pred, [u.value for u in Urgency]),
        "retrieval": run_retrieval_eval(),
        "avg_helpfulness": sum(helpfulness_scores) / n_succeeded if n_succeeded else 0.0,
        "avg_correctness": sum(correctness_scores) / n_succeeded if n_succeeded else 0.0,
        "avg_tone": sum(tone_scores) / n_succeeded if n_succeeded else 0.0,
        "auto_send_rate": auto_send_count / n_succeeded if n_succeeded else 0.0,
        "avg_latency_seconds": sum(latencies) / n_succeeded if n_succeeded else 0.0,
        "est_cost_per_ticket": total_cost / n_succeeded if n_succeeded else 0.0,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
    }


def _git_short_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-git-sha"


def write_report(results: dict, path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    sha = _git_short_sha()

    entry = f"## Run: {timestamp} — {sha}\n\n"
    entry += (
        f"n = {results['n_succeeded']} succeeded "
        f"({results['n_failed']} failed, {results['n_attempted']} attempted)\n\n"
    )
    if results["failures"]:
        entry += "Failures:\n"
        for ticket_id, error in results["failures"]:
            entry += f"- {ticket_id}: {error}\n"
        entry += "\n"

    entry += (
        f"### Classification\n"
        f"- Category accuracy: {results['category']['accuracy']:.3f} (n={results['n_succeeded']})\n"
        f"- Category F1 (macro): {results['category']['macro_f1']:.3f}\n"
        f"- Urgency accuracy: {results['urgency']['accuracy']:.3f}\n"
        f"- Urgency F1 (macro): {results['urgency']['macro_f1']:.3f}\n\n"
        f"### Retrieval\n"
        f"- Precision@3: {results['retrieval']['precision_at_3']:.3f}\n"
        f"- Recall@5: {results['retrieval']['recall_at_5']:.3f}\n\n"
        f"### Generation (LLM-as-judge, rubric v1)\n"
        f"- Helpfulness: {results['avg_helpfulness']:.2f}/5 (avg)\n"
        f"- Correctness: {results['avg_correctness']:.2f}/5 (avg)\n"
        f"- Tone: {results['avg_tone']:.2f}/5 (avg)\n\n"
        f"### Operations\n"
        f"- Auto-send rate at threshold={CONFIDENCE_THRESHOLD}: {results['auto_send_rate']:.3f}\n"
        f"- Avg latency per ticket: {results['avg_latency_seconds']:.2f} s\n"
        f"- Est. cost per ticket: ${results['est_cost_per_ticket']:.5f} "
        f"(illustrative rate, not verified live pricing — see run_eval.py)\n"
        f"- Total tokens across run: {results['total_input_tokens']} in / {results['total_output_tokens']} out\n"
    )
    entry += "\n"

    with path.open("a", encoding="utf-8") as f:
        f.write(entry)

    print(f"[run_eval] Appended run to {path}")


if __name__ == "__main__":
    gold_rows = reviewed_rows(load_gold_set())
    if not gold_rows:
        print("[run_eval] BLOCKED: no hand-reviewed gold-set rows found.")
        raise SystemExit(1)

    print(f"[run_eval] Running the full graph on {len(gold_rows)} hand-reviewed tickets...")
    outcome = run_full_eval(gold_rows)

    print(f"[run_eval] {outcome['n_succeeded']}/{outcome['n_attempted']} tickets succeeded")
    for ticket_id, error in outcome["failures"]:
        print(f"[run_eval]   FAILED {ticket_id}: {error}")
    print(f"[run_eval] Category accuracy: {outcome['category']['accuracy']:.3f}")
    print(f"[run_eval] Urgency accuracy: {outcome['urgency']['accuracy']:.3f}")
    print(
        f"[run_eval] Retrieval precision@3={outcome['retrieval']['precision_at_3']:.3f} "
        f"recall@5={outcome['retrieval']['recall_at_5']:.3f}"
    )
    print(
        f"[run_eval] Generation helpfulness={outcome['avg_helpfulness']:.2f} "
        f"correctness={outcome['avg_correctness']:.2f} tone={outcome['avg_tone']:.2f}"
    )
    print(f"[run_eval] Auto-send rate: {outcome['auto_send_rate']:.3f}")
    print(
        f"[run_eval] Avg latency: {outcome['avg_latency_seconds']:.2f}s, "
        f"est cost/ticket: ${outcome['est_cost_per_ticket']:.5f}"
    )
    write_report(outcome)
