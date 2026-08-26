# How to hand this to Claude Code

1. Create a new empty directory (e.g. `support-ticket-agent/`) and put
   `CLAUDE.md`, `BUILD_PLAN.md`, and the `.claude/skills/` folder from this
   package at its root, exactly as structured here.
2. `git init` and make an initial commit of just these planning files —
   gives you a clean diff history of "spec" vs. "generated code."
3. Start Claude Code in that directory (`claude` in the terminal, or open it
   in Claude Code Desktop / VS Code extension).
4. First prompt, verbatim:
   > Read CLAUDE.md and BUILD_PLAN.md. Set up the project structure and
   > implement Phase 1 (data pipeline). Stop after Phase 1 and show me the
   > row counts and DATA_CARD.md before continuing.
5. Review Phase 1's output before saying "continue to Phase 2." Doing this
   phase-by-phase, with a stop-and-check between each one, is what keeps
   Claude Code from silently drifting from the spec on a multi-hour build —
   and it mirrors how you'd actually manage a junior engineer's PRs, which
   is worth mentioning in your portfolio writeup.
6. Once all phases are done, ask Claude Code to run `/init` — it will
   likely propose trimming CLAUDE.md down further as the codebase now
   speaks for itself on things like directory layout.

## Optional: MCP

Not required to build this. If you want it:
- A **GitHub MCP server** lets Claude Code open commits/PRs as it works
  through phases instead of just editing local files — nice if you want a
  clean commit-per-phase history automatically.
- Skip a Gmail/email MCP server for the actual send step — that belongs in
  the app's own `EmailSender` implementation (see BUILD_PLAN.md Phase 6),
  not wired through your personal Claude Code session. Use an MCP email
  connector only if you want to manually test what a sent message looks
  like during development.

## Deploy (Render)

The deployed app needs the KB vector index (`support_agent/knowledge_base
/chroma/`) to exist, but that directory is **gitignored** — it's a
generated artifact, not source (see `build_index.py`'s docstring: it
deletes and recreates the Chroma collection from scratch on every run,
specifically so stale chunks never linger). The actual source of truth,
`support_agent/knowledge_base/documents.py` (the 40 hand-authored KB
articles), *is* committed — confirmed via `git ls-files` /
`git check-ignore`, not assumed. This means the index must be built fresh
as part of every deploy, not shipped as a committed file.

**Build Command** (set this in Render's dashboard under the service's
Settings → Build & Deploy, or see `render.yaml` below):

```
pip install -e . && python -m support_agent.knowledge_base.build_index
```

**Start Command** (unchanged):

```
uvicorn support_agent.api:app --host 0.0.0.0 --port $PORT
```

**`GEMINI_API_KEY` is now required at *build* time, not just runtime.**
`build_index.py` calls `embed_texts()` to embed all 42 KB chunks, which
now calls Gemini's hosted embedding API (see `knowledge_base/embeddings.py`
— this is the same change that fixed the free-tier memory crash below).
If the key isn't available during the build step, the build fails
immediately with a clear `GEMINI_API_KEY is not set` error (see
`embeddings.py`'s `_get_client()`) rather than a vague SDK error or a
silently-empty index. Render's standard behavior for a native (non-Docker)
Python web service is to run the build step in the same environment as
runtime, so dashboard-configured environment variables should already be
available at build time — **this is Render's documented standard
behavior, not something verified against this specific account's service
configuration**, since there's no Render CLI/API access available to
check it directly. If the build fails on a missing key, that's the first
thing to check in the service's Environment settings.

`render.yaml` in the repo root declares this Blueprint-style, with
`GEMINI_API_KEY`/`ANTHROPIC_API_KEY`/`SUPPORT_AGENT_API_KEY` marked
`sync: false` (Render prompts for the value in its dashboard rather than
reading it from the committed file). **This file only takes effect if the
Render service is actually deployed/synced from it** — either by creating
a new service via "New Blueprint," or by enabling Blueprint sync on an
existing one. A service originally created by hand through the dashboard
keeps using whatever's typed into its own Build/Start Command fields
regardless of what's in this file; update those fields directly with the
commands above in that case.

## Ops: the Render free-tier memory crash (2026-08-24)

The Render deployment crashed with "Out of memory (used over 512Mi)".
Investigated with a real RSS-measurement script (not assumed) walking the
app's actual import chain step by step:

- **`sentence-transformers` (→ `torch`) was the dominant cost**: ~261MB of
  process RSS just to import, plus another ~40MB the moment the local
  embedding model's weights actually loaded on first `retrieve()` call.
  Confirmed from Render's own build log that `torch` had resolved to the
  **full CUDA-enabled wheel** on Render's Linux container (nvidia-cudnn,
  nvidia-cufft, nvidia-cusolver, nvidia-nccl, etc. all pulled in as
  dependencies) rather than a CPU-only build — nothing in `pyproject.toml`
  told pip/uv to prefer the CPU wheel index, so it silently took the
  larger default. Startup alone (before any request) measured at 456MB —
  89% of the 512Mi ceiling with zero traffic.
- A secondary, smaller finding: `agent/llm_client.py` imported **both**
  the `anthropic` and `google-genai` SDKs unconditionally at module load
  (~15.5MB and ~76.4MB respectively), regardless of which one
  `LLM_PROVIDER` actually selected.

**Fix**: replaced the local `sentence-transformers` model with Gemini's
hosted embedding API (`knowledge_base/embeddings.py` — see its module
docstring for the model choice and the new `GEMINI_API_KEY` coupling this
introduces), and made `llm_client.py`'s provider SDK imports lazy (only
the configured provider's SDK is ever imported, not both). See
`pyproject.toml`'s dependencies-block comment for the CPU-only-torch
pinning mechanism to use if a torch-backed dependency is ever
reintroduced — not applied as live config right now since torch isn't a
dependency at all anymore, which is strictly better than pinning it.

**Result** (measured the same way, real script, real end-to-end
`run_agent()` call — classify + retrieve + draft + guardrail + route, not
just import): **236MB**, down from 496MB for *less* work (the old
measurement stopped at `retrieve()`, before a real classify/draft cycle).
`anthropic` is no longer imported at all when `LLM_PROVIDER=gemini`
(confirmed via `sys.modules`); `google-genai` is still always imported
regardless of `LLM_PROVIDER`, since embeddings now unconditionally depend
on it — worth knowing if you ever look at `sys.modules` and expect it
absent under `LLM_PROVIDER=anthropic`. Retrieval quality is unchanged
post-swap: precision@3=0.333, recall@5=1.000 (n=40), identical to the
pre-swap baseline — see `eval/results/retrieval_report.md`'s
2026-08-24 entry.

## Security

What's in place on `POST /tickets` (`support_agent/api/main.py`) as of the
Phase 6 security hardening pass:

- **API key auth.** Every request must carry a `X-API-Key` header matching
  the `SUPPORT_AGENT_API_KEY` env var, checked with
  `secrets.compare_digest` (constant-time, avoids leaking a timing signal
  on partial matches). Missing or wrong key → `401`. If the server itself
  has no key configured, every request is denied rather than silently
  allowed through (fails closed).
- **Rate limiting.** 20 requests/minute per API key (`slowapi`,
  in-memory storage — see `RATE_LIMIT` in `api/main.py`), independent per
  key. Exceeding it → `429`.
- **Request size bounds.** `subject` is capped at 300 characters, `body`
  at 5,000 (`MAX_SUBJECT_LENGTH`/`MAX_BODY_LENGTH`) — both feed straight
  into LLM prompts, so this bounds worst-case cost and latency per
  request. Over the limit → `422`.
- **Dependency scanning.** Run `pip-audit` before deploying — in a clean
  venv scoped to this project's own dependencies (`pip install -e ".[dev]"`
  there, then `pip-audit`), not the ambient dev environment, which
  otherwise pulls in unrelated tools' vulnerabilities and drowns out
  anything actionable. See `eval/results/` conventions for how this
  project treats "run it and report the real output" vs. hand-written
  claims — the same rule applies here.

  Last scan (2026-08-21, scoped venv): 2 packages flagged.
  - `chromadb` 1.5.9 — `PYSEC-2026-311`, a pre-auth code-injection
    vulnerability in Chroma's `/api/v2/.../collections` HTTP endpoint when
    a collection is created with `trust_remote_code=True`. **Not
    exploitable here**: this project only uses `chromadb.PersistentClient`
    (an embedded, in-process client — see `knowledge_base/build_index.py`,
    `knowledge_base/retriever.py`), never runs Chroma as its own server
    process, and never sets `trust_remote_code` anywhere. No fixed version
    was available from PyPI at scan time; re-run the audit periodically
    and pin an upgrade once one ships.
  - `pip` 23.2.1 (venv-bundled installer, not a declared project
    dependency) — several VCS/tar/wheel-extraction CVEs, all in pip's own
    install-time code path, not the running API. Keep the deploy
    pipeline's pip current; doesn't affect the deployed app's runtime
    surface.

  No findings in `fastapi`, `slowapi`, `uvicorn`, `anthropic`,
  `google-genai`, `langgraph`, or `pydantic` — the dependencies that
  actually sit in the running API's request path.

### `GET /demo` and `POST /demo/tickets` (portfolio addition, not BUILD_PLAN scope)

`support_agent/api/demo.py` mounts a second, **unauthenticated** surface —
see `PORTFOLIO_ADDITIONS.md` for why it exists (a portfolio reviewer can't
be expected to have an API key and a terminal). Because it's public, its
safety rules are stricter than `/tickets`'s, not looser:

- **Forced free-tier provider.** Every demo request runs under
  `agent/llm_client.py`'s `force_provider("gemini")`, a `contextvars`-based
  override — not an env var mutation — so it can't be flipped by, or itself
  flip, a concurrent authenticated `/tickets` request running on a
  different provider. This is a hard rule in code, not a config default:
  the demo endpoint cannot generate real (Anthropic) cost no matter how
  `LLM_PROVIDER` is set for the rest of the app.
- **Per-IP rate limit**: 5 requests/minute (`DEMO_PER_IP_RATE_LIMIT`).
- **Global daily cap**: 50 requests/day, shared across every visitor
  (`DEMO_DAILY_CAP`), resetting exactly at UTC midnight — the limit is
  keyed by the current UTC calendar date (`_demo_daily_key`) rather than
  relying on `slowapi`/`limits`' built-in "day" window, which is actually
  a rolling 24h-from-first-hit window, not a calendar-day one.
- **Same length caps as `/tickets`** — reuses the identical
  `TicketCreateRequest` model (`api/models.py`), so nothing here is looser
  than the authenticated endpoint.
- **Never sends email.** The form accepts an optional `customer_email` for
  parity with `/tickets`, but `create_demo_ticket` never calls
  `EmailSender.send()`. With `ConsoleEmailSender` this is moot today, but
  it matters the moment a real provider is wired in per `email_sender.py`'s
  documented seam — an anonymous, unauthenticated endpoint that emails an
  arbitrary caller-supplied address on request is an open mail relay
  waiting to happen.
- **Bypassing the per-IP limit via IP rotation has no real-cost exposure.**
  Even a determined visitor rotating IPs to dodge the 5/minute limit is
  still bounded by the global 50/day cap (which counts every attempt,
  successful or not, regardless of which IP made it — see `demo.py`'s
  module docstring) and by the forced free-tier provider. Worst case is
  exhausting Gemini's own free daily quota early, not an open-ended bill.

Explicitly **out of scope for v1** (this is a single-operator portfolio
demo, not a production multi-user service):

- No multi-tenancy — one shared API key for every caller, not per-user or
  per-tenant keys with scoped permissions.
- No OAuth/JWT/session auth — a static shared secret is enough to
  demonstrate the pattern; a real deployment serving multiple customers
  would need real identity and authorization.
- No brute-force protection on the key itself — the rate limiter throttles
  a *valid* key's usage; it doesn't specially detect or slow repeated
  guesses at an invalid one.
- In-memory rate-limit storage — counts reset on restart and aren't shared
  across multiple server processes/hosts. A real multi-instance deployment
  would need a shared backend (e.g. Redis, via `slowapi`'s `storage_uri`).
- No TLS termination in the app itself — assumed to run behind a reverse
  proxy/load balancer that terminates HTTPS.
- No secrets-manager integration or key rotation — `SUPPORT_AGENT_API_KEY`
  and the LLM provider keys are plain environment variables (`.env` in
  dev), rotated manually if at all.
