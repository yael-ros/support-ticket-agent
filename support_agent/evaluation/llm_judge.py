"""LLM-as-judge: score a drafted response against evaluation/rubric.md.

Per CLAUDE.md's "no bare LLM calls" rule, this goes through
agent/llm_client.py's call_structured() like every other LLM call in the
project — an eval script is not an exception. Model tier: STRONG, same
tier used for drafting — judging quality is not a simpler task than
producing the draft in the first place.

This is eval-only: judge_response() is never called from agent/graph.py
or any node. It exists purely to produce the "Generation" section of
eval/results/full_report.md (evaluation/run_eval.py).
"""

from __future__ import annotations

from support_agent.agent.llm_client import ModelTier, call_structured
from support_agent.agent.prompts import format_judge_prompt
from support_agent.schemas import DraftResponse, JudgeScore, RetrievalContext, Ticket

# Same failure mode draft.py already hit and fixed: 512 truncated
# mid-JSON on a live Anthropic call (Claude Sonnet 5's rationale text is
# more verbose than the small default assumed). Same fix — headroom, not
# a precisely-derived number.
JUDGE_MAX_TOKENS = 1024


def judge_response(ticket: Ticket, draft: DraftResponse, retrieval_context: RetrievalContext) -> JudgeScore:
    prompt = format_judge_prompt(ticket.subject, ticket.body, retrieval_context.chunks, draft.text)
    return call_structured(
        prompt=prompt, response_model=JudgeScore, tier=ModelTier.STRONG, max_tokens=JUDGE_MAX_TOKENS
    )
