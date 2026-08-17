"""Typed data contracts shared across every module in this project.

Per CLAUDE.md: all structured data (tickets, classifications, retrieved
chunks, agent state) is defined here as Pydantic v2 models. No raw dicts
are passed between modules.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Category(str, Enum):
    """Ticket queue, normalized from the raw `queue` field.

    Members mirror the 10 distinct `queue` values present in the
    English-language subset of the `Tobi-Bueck/customer-support-tickets`
    dataset (see support_agent/data/load_tickets.py). The full dataset
    (including non-English rows) contains ~40 additional long-tail queue
    values (e.g. "Pets & Animals/Veterinary Care") that do not occur in
    English and are out of scope for v1.
    """

    TECHNICAL_SUPPORT = "technical_support"
    PRODUCT_SUPPORT = "product_support"
    CUSTOMER_SERVICE = "customer_service"
    IT_SUPPORT = "it_support"
    BILLING_AND_PAYMENTS = "billing_and_payments"
    RETURNS_AND_EXCHANGES = "returns_and_exchanges"
    SERVICE_OUTAGES_AND_MAINTENANCE = "service_outages_and_maintenance"
    SALES_AND_PRE_SALES = "sales_and_pre_sales"
    HUMAN_RESOURCES = "human_resources"
    GENERAL_INQUIRY = "general_inquiry"


class Urgency(str, Enum):
    """Ticket urgency, normalized from the raw `priority` field.

    The English-language subset only contains {low, medium, high} — no
    `critical` or `very_low` rows (those values exist only among the
    dataset's German-language rows). `CRITICAL` is still defined here for
    schema completeness and forward-compatibility with non-English data;
    no v1 gold-set row will carry it. `very_low` (when encountered) maps
    to `LOW`.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(BaseModel):
    """A single normalized support ticket.

    Assumes `body` is non-empty (rows with null/empty body are dropped at
    ingestion — see load_tickets.py). `subject` and `answer` may be empty/
    None; `answer`, when present, is the dataset's actual historical agent
    reply and is used only as an evaluation reference, never as training
    data to imitate verbatim.
    """

    id: str
    subject: str
    body: str
    answer: str | None = None
    category: Category
    urgency: Urgency
    language: str
    ticket_type: str | None = None
    raw_queue: str
    raw_priority: str


class HumanLabel(BaseModel):
    """Hand-corrected ground truth for a gold-set row.

    All fields are optional so a reviewer can correct only what's wrong
    (e.g. leave category as-is, fix urgency only).
    """

    category: Category | None = None
    urgency: Urgency | None = None
    notes: str | None = None


class GoldSetRow(BaseModel):
    """One row of the hand-reviewable evaluation gold set.

    `weak_category`/`weak_urgency` are the dataset's own labels, treated as
    weak supervision, not ground truth (see data/DATA_CARD.md). `human_label`
    is null until a developer hand-corrects it; eval scripts must refuse to
    score rows where `human_label` is null (see .claude/skills/eval-harness).
    """

    ticket_id: str
    subject: str
    body: str
    reference_answer: str | None = None
    weak_category: Category
    weak_urgency: Urgency
    human_label: HumanLabel | None = None


class KBDocument(BaseModel):
    """A single hand-authored troubleshooting article in the knowledge base.

    Authored originally for this project (see knowledge_base/documents.py);
    `source_note` records which taxonomy inspired the topic (if any) —
    never a claim that dataset text was copied, since it wasn't.
    """

    id: str
    title: str
    category: Category
    body: str
    source_note: str


class Chunk(BaseModel):
    """A chunk of a KBDocument, produced by knowledge_base/build_index.py."""

    id: str
    doc_id: str
    doc_title: str
    category: Category
    chunk_index: int
    text: str


class RetrievedChunk(BaseModel):
    """A chunk returned by knowledge_base/retriever.py, with its similarity score."""

    chunk_id: str
    doc_id: str
    doc_title: str
    category: Category
    text: str
    score: float


class TicketClassification(BaseModel):
    """Structured output of agent/nodes/classify.py's LLM call.

    `confidence` is the model's own self-reported confidence in [0, 1] —
    not independently calibrated. It feeds the confidence-threshold router
    in Phase 4 (agent/nodes/route.py), so a classification the model isn't
    sure about can be routed to human review instead of auto-sent.
    """

    category: Category
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)


class RetrievalContext(BaseModel):
    """Chunks retrieved for a ticket, plus the query that produced them (agent/nodes/retrieve.py).

    `chunks` may legitimately be empty (no good match in the KB) — that's
    a real outcome the rest of the graph must handle explicitly, per
    CLAUDE.md's "no silent failures" rule, not something to paper over.
    """

    query: str
    chunks: list[RetrievedChunk]


class ClaimGrounding(BaseModel):
    """One factual claim in a drafted response, mapped to the retrieved chunk id(s) backing it.

    `chunk_ids` is what guardrails.grounding_check verifies against the
    RetrievalContext actually given to the drafting node — a claim citing
    a chunk id that was never retrieved is exactly the failure mode this
    exists to catch.
    """

    claim: str
    chunk_ids: list[str]


class DraftResponse(BaseModel):
    """Structured output of agent/nodes/draft.py's LLM call.

    `grounding` must cover every factual claim in `text`. An empty
    `grounding` list is valid — it means the draft made no claims that
    need backing (e.g. the KB had nothing relevant, per
    agent/prompts.py's DRAFT_RESPONSE_PROMPT) — but guardrails.py's
    grounding_check treats a non-trivial `text` with empty `grounding` as
    a failure, since that shape usually means the model made claims it
    forgot to cite rather than genuinely made none.
    """

    text: str
    grounding: list[ClaimGrounding]


class GuardrailResult(BaseModel):
    """Result of one guardrail check (guardrails.py).

    `check_name` and `reason` are what make a rejection reviewable by a
    human rather than just a bare boolean — see
    .claude/skills/agent-conventions. Set by the guardrail function
    itself (not inferred from `__name__` by the caller), so the result is
    self-describing wherever it ends up (state, logs, a human review UI).
    """

    check_name: str
    passed: bool
    reason: str


class RoutingDecision(BaseModel):
    """Output of agent/nodes/route.py: whether a ticket auto-sends or goes to human review, and why.

    `reason` concatenates every contributing factor (low confidence,
    failed guardrails, empty retrieval), not just the first one found —
    a human_review ticket should show a reviewer everything that was
    wrong, not force them to fix one issue and hit the next on resubmit.
    """

    action: Literal["auto_send", "human_review"]
    reason: str


class AgentState(BaseModel):
    """Mutable state threaded through the LangGraph agent (agent/graph.py).

    Each node reads specific fields off state and writes specific fields
    back — see .claude/skills/agent-conventions. Fields default to None
    until the corresponding node has run, so a node (or a test) can always
    tell whether an upstream step completed rather than inferring it from
    incidental state.
    """

    ticket: Ticket
    classification: TicketClassification | None = None
    retrieval_context: RetrievalContext | None = None
    draft: DraftResponse | None = None
    guardrail_results: list[GuardrailResult] | None = None
    routing_decision: RoutingDecision | None = None
