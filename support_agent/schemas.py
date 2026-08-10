"""Typed data contracts shared across every module in this project.

Per CLAUDE.md: all structured data (tickets, classifications, retrieved
chunks, agent state) is defined here as Pydantic v2 models. No raw dicts
are passed between modules.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


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
