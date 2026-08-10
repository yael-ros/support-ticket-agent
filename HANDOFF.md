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
