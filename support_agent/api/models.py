"""Pydantic request/response models shared by api/main.py and api/demo.py.

Split out from main.py specifically so api/demo.py (PORTFOLIO_ADDITIONS.md's
public demo endpoint) can reuse the exact same request shape and length
caps as the authenticated /tickets endpoint without importing from
main.py — main.py in turn mounts demo.py's router, so main.py -> demo.py ->
main.py would be a circular import if demo.py needed anything defined in
main.py itself.

Safe to use postponed annotations here (unlike main.py/demo.py): the
slowapi __globals__ bug only bites a module that itself defines a
function slowapi's @limiter.limit wraps — these are plain, fully-evaluated
class definitions by the time demo.py/main.py import them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from support_agent.schemas import Category, Urgency

# Ticket bodies feed directly into LLM prompts (classify + draft); bounding
# their length bounds worst-case cost/latency per request.
MAX_SUBJECT_LENGTH = 300
MAX_BODY_LENGTH = 5_000


class TicketCreateRequest(BaseModel):
    """Raw incoming ticket payload.

    Deliberately has no category/urgency — determining them is
    agent/nodes/classify.py's job, not the caller's. subject/body are
    length-capped (see MAX_SUBJECT_LENGTH/MAX_BODY_LENGTH) since both feed
    directly into LLM prompts downstream.
    """

    id: str | None = None
    subject: str = Field(default="", max_length=MAX_SUBJECT_LENGTH)
    body: str = Field(max_length=MAX_BODY_LENGTH)
    customer_email: str | None = None
    language: str = "en"


class RoutingResponse(BaseModel):
    action: str
    reason: str


class TicketResponse(BaseModel):
    ticket_id: str
    category: Category
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)
    routing: RoutingResponse
    response_text: str | None = None  # populated only when routing.action == "auto_send"
