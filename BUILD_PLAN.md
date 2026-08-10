# Build Plan: Support Ticket RAG Agent

## Goal

An end-to-end system that ingests a customer support ticket, classifies it
(category + urgency), retrieves relevant troubleshooting knowledge, drafts a
response, checks that response against guardrails, and routes it to either
auto-send or a human review queue — with an evaluation harness that produces
real, reportable numbers.

## Data sources

1. **Ticket stream (primary):** Hugging Face `Tobi-Bueck/customer-support-tickets`.
   Real support emails with `subject`, `body`, `answer` (the actual agent
   response — use this as a reference for evaluation, not as training data
   to imitate verbatim), `priority` (low / medium / critical), `queue`
   (category), and `language`. Filter to English-language rows for v1.
2. **Knowledge base seed content:** Hugging Face
   `bitext/Bitext-customer-support-llm-chatbot-training-dataset`. Use the
   intent/category structure to derive ~30-50 troubleshooting articles
   (write these yourself, in your own words — do not copy dataset text
   verbatim into KB docs; treat the dataset as a taxonomy reference).
3. Both are loaded via the `datasets` library. Cache locally under
   `data/cache/` (gitignored).

## Phase 1 — Data pipeline (`data/`)

- `load_tickets.py`: load the ticket dataset, filter to English, normalize
  `priority` and `queue` into the `Urgency` and `Category` enums in
  `schemas.py`.
- `build_gold_set.py`: sample 200 tickets stratified by category and
  urgency, write to `data/gold_set.jsonl` for manual review. Leave a
  `human_label` field null — this file is meant to be hand-corrected by
  the developer (me) before it's used in eval. Document this clearly in
  the script's docstring and in a printed message when it runs.
- Definition of done: running the script produces a reproducible train/eval
  split with documented row counts, and a checked-in `data/DATA_CARD.md`
  describing provenance, filtering, and known limitations (e.g. dataset is
  email-based, not chat-based; no urgency ground truth beyond the dataset's
  own field, which itself should be treated as weak supervision, not truth).

## Phase 2 — Knowledge base (`knowledge_base/`)

- `documents.py`: the ~30-50 troubleshooting articles as structured
  documents (id, title, category, body, source_note).
- `build_index.py`: chunk (semantic, ~200-400 tokens/chunk with overlap),
  embed (use a local sentence-transformers model to keep this runnable
  without API cost — `all-MiniLM-L6-v2` is fine for a portfolio project;
  note in a comment how you'd swap in a hosted embedding model for
  production scale), store in Chroma (local, file-backed — no external
  service required to run this project).
- `retriever.py`: `retrieve(query: str, k: int) -> list[RetrievedChunk]`,
  returns chunks with similarity scores and source document ids.
- Definition of done: a small retrieval eval set of (query, expected_doc_id)
  pairs — write at least 20 by hand — with precision@3 and recall@5 reported.

## Phase 3 — Classification (`agent/nodes/classify.py`)

- Structured-output LLM call producing `TicketClassification(category,
  urgency, confidence)`. Prompt template lives in `agent/prompts.py`.
- Evaluate against the hand-corrected gold set from Phase 1: report accuracy
  and per-class F1 for both category and urgency, in a generated
  `eval/results/classification_report.md`.

## Phase 4 — Agent graph (`agent/graph.py`)

LangGraph state machine, nodes in `agent/nodes/`:
`classify → retrieve → draft → guardrail_check → route → (auto_send |
human_review) → update_ticket`.

- `draft.py`: LLM call that must cite which retrieved chunk(s) informed each
  claim in the response (structured output with a `grounding` field mapping
  claims to chunk ids) — this is what makes the hallucination guardrail
  checkable rather than vibes-based.
- `guardrails.py`: pure functions — `no_unauthorized_promises`,
  `pii_scrub`, `tone_check`, `grounding_check` (verifies the draft's
  `grounding` field actually references retrieved chunk ids). Each has
  unit tests with at least one clear pass and one clear fail example.
- `route.py`: confidence threshold (configurable, default 0.75) combining
  classification confidence and guardrail pass/fail into an auto-send vs.
  human-review decision. Document the threshold choice and make it a named
  constant, not a magic number.

## Phase 5 — Evaluation (`evaluation/`)

- `run_eval.py`: runs the full graph over the gold set and produces
  `eval/results/full_report.md` containing: classification accuracy/F1,
  retrieval precision/recall, generation quality (LLM-as-judge against a
  written rubric — rubric lives in `evaluation/rubric.md`, scored 1-5 on
  helpfulness/correctness/tone), auto-send rate at the default threshold,
  and average latency + estimated cost per ticket.
- This report is the actual portfolio deliverable — treat its clarity as
  seriously as the code.

## Phase 6 — API layer (`api/main.py`)

- FastAPI app, single `POST /tickets` webhook endpoint accepting a raw
  ticket payload, running it through the graph, returning the routing
  decision and (if auto-sent) the response.
- `EmailSender` as an abstract interface with a `ConsoleEmailSender` (prints,
  used in dev/demo) and a documented stub for a real provider (Resend/
  SendGrid/Gmail API) — do not hardcode a specific provider's SDK into the
  agent logic.

## Phase 7 — Observability (`observability/`)

- Structured JSON logging (structlog) per ticket: every node's input/output
  summary, retrieved chunk ids, guardrail results, routing decision, latency.
- Not full OpenTelemetry tracing for v1 — note in `observability/README.md`
  what you'd add for a real production deployment (tracing, dashboards,
  drift monitoring on classification distribution over time) as a
  "next steps" section. Being explicit about what's out of scope is part of
  the professional presentation.

## Out of scope for v1 (state this explicitly in the final README)

- Multi-language support beyond English
- Fine-tuning any model
- A production email provider integration (stubbed, not implemented)
- Auth/multi-tenancy on the API
