"""FastAPI webhook layer (BUILD_PLAN.md Phase 6).

`POST /tickets` runs an incoming raw ticket through the full agent graph
and, if the router decides `auto_send`, delivers the drafted reply via
`EmailSender`. Per CLAUDE.md, this is the only place in the codebase that
acts on `AgentState.routing_decision` — `agent/graph.py` deliberately stops
at producing the decision (see its module docstring).

ASSUMPTION: a `human_review` ticket is not pushed anywhere further — no
CRM/queue integration exists in this project. The response simply surfaces
the routing decision and reason so a caller can act on it. BUILD_PLAN.md's
Phase 6 scope only names `EmailSender`, not a review-queue system.

Run locally: `uvicorn support_agent.api:app --reload` (see CLAUDE.md).
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from support_agent.agent.graph import run_agent
from support_agent.agent.providers.base import LLMCallError
from support_agent.api.email_sender import ConsoleEmailSender, EmailSender
from support_agent.schemas import Category, Ticket, Urgency

app = FastAPI(title="Support Ticket Agent")

# Dev/demo default. Swap for a real provider per email_sender.py's documented seam.
_email_sender: EmailSender = ConsoleEmailSender()

# The dataset/API payload carries no real customer email field; used only
# when a request omits customer_email, so the demo sender has something to print.
_DEMO_CUSTOMER_EMAIL = "customer@example.com"


class TicketCreateRequest(BaseModel):
    """Raw incoming ticket payload.

    Deliberately has no category/urgency — determining them is
    agent/nodes/classify.py's job, not the caller's.
    """

    id: str | None = None
    subject: str = ""
    body: str
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


@app.post("/tickets", response_model=TicketResponse)
def create_ticket(payload: TicketCreateRequest) -> TicketResponse:
    ticket = Ticket(
        id=payload.id or str(uuid.uuid4()),
        subject=payload.subject,
        body=payload.body,
        language=payload.language,
    )

    try:
        state = run_agent(ticket)
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    # Guaranteed non-None: route always runs last and always sets these
    # (see agent/nodes/route.py) — asserts document that invariant, not a
    # runtime possibility we're handling.
    assert state.classification is not None
    assert state.routing_decision is not None

    response_text: str | None = None
    if state.routing_decision.action == "auto_send":
        assert state.draft is not None
        response_text = state.draft.text
        _email_sender.send(
            to=payload.customer_email or _DEMO_CUSTOMER_EMAIL,
            subject=f"Re: {payload.subject or ticket.id}",
            body=response_text,
        )

    return TicketResponse(
        ticket_id=ticket.id,
        category=state.classification.category,
        urgency=state.classification.urgency,
        confidence=state.classification.confidence,
        routing=RoutingResponse(
            action=state.routing_decision.action, reason=state.routing_decision.reason
        ),
        response_text=response_text,
    )
