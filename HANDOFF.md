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
