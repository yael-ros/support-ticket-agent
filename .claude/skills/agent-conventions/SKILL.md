---
name: agent-conventions
description: Use this skill when adding or modifying a node in the LangGraph agent graph, changing agent state, adding a new guardrail, or touching agent/graph.py, agent/nodes/, agent/prompts.py, or guardrails.py. Ensures new nodes stay testable and consistent with the existing graph.
---

# Agent Graph Conventions

## Adding a new node

1. Define its contribution to `AgentState` in `schemas.py` first — a node
   should read specific typed fields off state and write specific typed
   fields back, never mutate state ad hoc.
2. Write the node as a standalone function `def node_name(state:
   AgentState) -> AgentState`, importable and testable without spinning up
   the full graph.
3. Add it to `agent/graph.py` with an explicit edge, not a conditional
   buried inside another node's logic.
4. Any LLM call the node makes goes through `agent/llm_client.py` and uses
   a named prompt from `agent/prompts.py` with a documented expected output
   schema.
5. Write at least one unit test with a fixed/mocked LLM response so the
   test doesn't depend on live API calls or a specific model's phrasing.

## Adding a new guardrail

- Guardrails live in `guardrails.py` as pure functions:
  `def check_name(draft: DraftResponse, context: RetrievalContext) ->
  GuardrailResult`. `GuardrailResult` includes `passed: bool` and `reason:
  str` — never just a boolean, since the reason is what makes a rejection
  reviewable by a human.
- Register new guardrails in the `GUARDRAIL_CHECKS` list in
  `guardrail_check.py` rather than hardcoding calls — this keeps the set of
  active checks visible in one place.
- Every guardrail needs a passing-case and failing-case unit test.

## What not to do

- Don't fold guardrail logic into the drafting prompt ("please don't
  promise refunds"). Prompted behavior is not a guardrail — it's a
  suggestion the model can ignore. Guardrails must be checkable after the
  fact in code.
- Don't add a node that both drafts and checks its own output in one LLM
  call — grounding and safety checks need to inspect the draft
  independently of the process that produced it.
