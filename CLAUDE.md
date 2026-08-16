# CLAUDE.md

Instructions for Claude Code working in this repository. Keep this file under
200 lines — if it grows, move detail into `.claude/rules/` or a skill instead.

## What this project is

A RAG-powered customer support ticket agent, built as a portfolio piece meant
to read as production-grade, not a notebook demo. Full spec: `BUILD_PLAN.md`.
Read that file before starting any phase — it has the dataset schema, the
architecture, and the definition of done for each component.

## Non-negotiable standards

- **Type everything.** All function signatures typed; all structured data
  (tickets, classifications, retrieved chunks, agent state) defined as
  Pydantic v2 models in `schemas.py`, never raw dicts passed between modules.
- **No bare LLM calls, and no node depends on a concrete provider.** Every
  LLM call goes through `agent/llm_client.py`'s `call_structured()`, which
  wraps retries (tenacity, exponential backoff), timeouts, and
  structured-output parsing. Never call a provider SDK directly from a node
  or route handler. Nodes ask for a `ModelTier` (`FAST`/`STRONG`), never a
  model name — `llm_client.py` resolves the active provider (env var
  `LLM_PROVIDER`, default `gemini`) and delegates to its implementation in
  `agent/providers/*_provider.py`. Both Anthropic and Gemini are fully
  supported; switching is a one-line env var change, not a code change. See
  `agent/providers/base.py` for the `LLMProvider` protocol.
- **Every LLM-facing prompt lives in `agent/prompts.py`** as a named template
  with a docstring explaining what it's for and what output schema it expects.
  No inline prompt strings in logic files.
- **Guardrails are testable functions, not prompt instructions.** A guardrail
  that only exists as "please don't do X" in a prompt is not a guardrail.
  Each check in `guardrails.py` must be a pure function with unit tests.
- **No silent failures.** Retrieval returning zero chunks, classification
  confidence below threshold, and guardrail rejections must all be explicit
  states in the agent graph, not exceptions swallowed by a try/except.
- **Every module that touches the dataset or KB gets a docstring stating its
  assumptions** (e.g. "assumes `queue` field is non-null; tickets missing it
  are routed to `general` at ingestion").

## Architecture (see BUILD_PLAN.md for full detail)

Ingest → classify (category + urgency) → retrieve (KB vector search) → draft
+ guardrail check → confidence router → auto-send or human review queue →
CRM/email update. Built as an explicit LangGraph state machine in
`agent/graph.py` — do not collapse this into a single mega-prompt "agent does
everything" call. Each node should be independently testable.

## Commands

- Install: `uv sync` (or `pip install -e ".[dev]"` if uv isn't available)
- Run tests: `pytest -q`
- Run the API locally: `uvicorn support_agent.api:app --reload`
- Build/refresh the KB index: `python -m support_agent.knowledge_base.build`
- Run the eval suite: `python -m support_agent.evaluation.run_eval`
- Lint/format: `ruff check . && ruff format .`

## Working style for this repo

- Work through `BUILD_PLAN.md` phase by phase. Don't jump ahead to the API
  layer before the classification + retrieval eval numbers exist — the eval
  harness is the thing that makes this portfolio-credible, not the FastAPI
  wrapper.
- After each phase, run the relevant tests and the eval script before moving
  on, and report the actual numbers (don't just say "tests pass").
- When a design decision isn't specified in BUILD_PLAN.md, state the
  assumption you're making in a code comment and proceed — don't stop and
  ask unless it changes the external API contract.
- Prefer explicit code over clever abstraction. This repo will be read by
  people evaluating engineering judgment, not by future-you extending it for
  years — clarity beats DRY-at-all-costs here.

## Do not

- Do not fabricate evaluation numbers or gold-set examples. If the gold eval
  set doesn't exist yet, say so and propose creating it — never invent
  plausible-looking metrics.
- Do not add a heavyweight agent framework beyond LangGraph without asking.
- Do not commit real API keys, `.env`, or the raw Hugging Face dataset cache
  — all are gitignored; verify before every commit.
- **NEVER add `Co-authored-by` or any other co-author metadata to git
  commits.** All commits in this repo must be strictly under the user's own
  identity — no assistant attribution in the message body, trailers, author,
  or committer fields.
