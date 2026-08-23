# Portfolio Additions

Work in this file is explicitly **out of BUILD_PLAN.md's original scope**.
BUILD_PLAN.md defines the system as designed (webhook/API-driven, no UI).
Everything here is added afterward, specifically to make the finished system
demonstrable to a non-technical portfolio reviewer — it should never be
confused with, or silently folded into, the original phase numbering.

## Addition 1: Public demo UI

### Why

The authenticated `/tickets` endpoint (Phase 6) is correct but inaccessible
to anyone without an API key and a terminal. A portfolio reviewer needs to
be able to click a link and see the system work in under a minute, with
zero setup.

### What to build

1. **A new, unauthenticated endpoint `POST /demo/tickets`** running the same
   `run_agent()` pipeline as `/tickets`, without requiring `X-API-Key`.

2. **Mandatory safety rules for this endpoint** — all required, none
   optional:
   - Always forces `LLM_PROVIDER=gemini` internally, regardless of the
     app's configured default. This is a hard rule, not a config
     suggestion: it guarantees this public endpoint can never generate
     real cost, only hit Gemini's free quota.
   - Per-IP rate limit: 5 requests/minute.
   - A global daily cap across all visitors: 50 requests/day total,
     resetting at midnight UTC. Once exceeded, respond with a friendly
     "demo limit reached for today, please try again tomorrow" message,
     not a generic error.
   - Ticket subject/body length caps at least as strict as `/tickets`.

3. **A single static HTML page**, vanilla JS, no framework or build step.
   - Form fields: subject, body, optional customer email.
   - On submit, calls `/demo/tickets` and clearly displays: category,
     urgency, confidence, routing decision (auto-send vs. human review)
     and why, and the drafted response text if auto-sent.
   - Clean, intentional styling — not a bare unstyled form — but stay
     simple: one file, no external dependencies.
   - A short, honest note that this is a portfolio demo instance on
     free-tier infrastructure: responses may take a few seconds, and the
     daily demo limit may occasionally be reached.
   - 2-3 "try an example" buttons that pre-fill the form with realistic
     sample tickets — at least one likely to auto-send, one likely to
     route to human review — so a visitor can see both outcomes without
     composing their own test case. This is the main way the guardrail
     and routing logic actually becomes visible to someone just clicking
     around.

4. **Served from the same FastAPI app** (e.g. mounted at `/demo`), so it
   deploys as part of the single Render service — no separate frontend
   hosting.

5. **Tests**: auth-exempt behavior, per-IP rate limiting, global daily cap
   and its reset/message behavior, forced-Gemini behavior regardless of
   the app's default provider config, and routing/guardrail correctness
   equivalent to the authenticated endpoint.

6. **Documentation**: add a Security section entry (in HANDOFF.md/README)
   explaining this second, intentionally more open, tightly bounded
   endpoint — why each safeguard exists, and that even a rate-limit bypass
   via IP rotation has no real-cost exposure and is capped by the daily
   limit.

### Definition of done

Working locally, verified two ways: a real classification through the demo
form, and the rate-limit/daily-cap messages actually triggering — not just
the happy path.
