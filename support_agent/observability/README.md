# Observability

## What's in place (v1)

Structured JSON logging (`structlog`), one line per event, to stdout:

- **`node_completed`** — emitted once per graph node per ticket
  (`classify`, `retrieve`, `draft`, `guardrail_check`, `route`). Fields:
  `ticket_id`, `node`, `latency_ms`, plus a node-specific summary:
  - `classify`: `category`, `urgency`, `confidence`
  - `retrieve`: `query`, `chunk_ids`, `scores`
  - `draft`: `text_length`, `grounded_claim_count`
  - `guardrail_check`: `checks` (list of `{check_name, passed, reason}`)
  - `route`: `action`, `reason`
- **`ticket_processed`** — emitted once per ticket, after the full graph
  runs. Fields: `ticket_id`, `total_latency_ms`, `routing_action`.

Deliberately **not logged**: raw ticket subject/body text or the drafted
reply's full text. Those are customer-facing content, not operational
metadata — only their already-typed, structured outputs (category,
chunk ids, guardrail verdicts, routing decision, text length) are logged.
See `support_agent/observability/logging.py`'s module docstring.

Wiring: `agent/graph.py`'s `build_graph()` wraps each node with
`logging.log_node()` at registration time; the node functions themselves
are untouched and stay independently unit-testable.

## Next steps for a real production deployment

This is a single-process, stdout-JSON setup — enough to demonstrate the
pattern, not a production observability stack. A real deployment would add:

- **Distributed tracing** (OpenTelemetry): a span per ticket with child
  spans per node, so a slow ticket can be traced across
  classify/retrieve/draft/guardrail latency in one view, and correlated
  with the LLM provider's own request IDs.
- **Log shipping + dashboards**: ship the JSON lines to a log aggregator
  (e.g. Loki, Datadog, CloudWatch Logs) instead of stdout, with
  dashboards for latency percentiles, auto-send rate, and guardrail
  failure rate over time.
- **Drift monitoring**: track the classification category/urgency
  distribution over time and alert on sudden shifts — a proxy signal for
  either a genuine change in incoming ticket mix or the classifier
  quietly degrading (e.g. after a prompt or model change).
- **Cost/usage dashboards**: `agent/providers/usage.py` already records
  per-call token usage in-process (used by `evaluation/run_eval.py`);
  a production deployment would persist and aggregate that instead of
  only using it for one-off eval runs.
- **Alerting**: page on sustained guardrail-failure spikes, LLM error
  rate, or p95 latency breaching a threshold — none of which exist yet
  beyond a human reading log lines.
