"""LangGraph node: retrieve knowledge-base chunks relevant to a classified ticket.

Per .claude/skills/agent-conventions, reads `state.ticket` and
`state.classification.category` and writes `state.retrieval_context`;
every other field on state is left untouched. Runs after classify.py in
the graph (agent/graph.py), so classification must already be set — this
node raises rather than silently retrieving unfiltered results if it
isn't, per CLAUDE.md's "no silent failures" rule.

Query: ticket subject + body concatenated. Category filtering
(knowledge_base/retriever.py's `category` param) narrows results to the
ticket's own queue, avoiding cross-category noise (e.g. a billing query
pulling in an IT_SUPPORT chunk).

RETRIEVE_K=5 matches the k used when retrieval was hand-evaluated
(knowledge_base/eval_retrieval.py — precision@3=0.333, recall@5=1.000,
n=40), so this node's real-world behavior is the one those reported
numbers describe. A RetrievalContext with zero chunks is a valid,
explicit outcome — not an error — and is handled downstream by
route.py, which routes empty-retrieval tickets to human review rather
than auto-sending a reply with no grounding available.
"""

from __future__ import annotations

from support_agent.knowledge_base.retriever import retrieve
from support_agent.schemas import AgentState, RetrievalContext

RETRIEVE_K = 5


def retrieve_context(state: AgentState) -> AgentState:
    if state.classification is None:
        raise ValueError("retrieve_context requires state.classification to be set first")

    query = f"{state.ticket.subject}\n{state.ticket.body}".strip()
    chunks = retrieve(query, k=RETRIEVE_K, category=state.classification.category)
    return state.model_copy(update={"retrieval_context": RetrievalContext(query=query, chunks=chunks)})
