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

Security (see README's Security section for the full picture): every
request must carry a valid `X-API-Key` header (checked against
`SUPPORT_AGENT_API_KEY`), and is rate-limited per key. This is a
single-shared-key model appropriate for a portfolio demo, not multi-tenant
auth — see README for what's explicitly out of scope.

Run locally: `SUPPORT_AGENT_API_KEY=<key> uvicorn support_agent.api:app --reload`.

NOTE: deliberately does NOT `from __future__ import annotations` (unlike
every other module in this project). slowapi's `@limiter.limit` decorator
wraps this module's route functions in a new function object defined in
slowapi's own module, which doesn't inherit this module's `__globals__`.
With postponed evaluation on, annotations become strings FastAPI can't
resolve through that wrapper, and it silently misreads `payload` as a
required query param instead of the request body (confirmed by removing
the import and watching a 422 on every valid request turn into a 200).
Real, non-optional type annotations avoid the string-resolution step
entirely, so this file's `X | None` syntax works as plain runtime type
objects (Python 3.11+, no future import needed).
"""

import os
import secrets
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from support_agent.agent.graph import run_agent
from support_agent.agent.providers.base import LLMCallError
from support_agent.api.email_sender import ConsoleEmailSender, EmailSender
from support_agent.schemas import Category, Ticket, Urgency

API_KEY_ENV_VAR = "SUPPORT_AGENT_API_KEY"
API_KEY_HEADER = "X-API-Key"

# Reasonable default for a portfolio demo, not a tuned production value.
RATE_LIMIT = "20/minute"

# Ticket bodies feed directly into LLM prompts (classify + draft); bounding
# their length bounds worst-case cost/latency per request.
MAX_SUBJECT_LENGTH = 300
MAX_BODY_LENGTH = 5_000


def _rate_limit_key(request: Request) -> str:
    """Bucket rate limits per caller API key, not per IP.

    Falls back to a shared 'anonymous' bucket for keyless requests — those
    are rejected by verify_api_key regardless, so the bucket choice only
    matters for logging/debugging, not for security.
    """
    return request.headers.get(API_KEY_HEADER, "anonymous")


limiter = Limiter(key_func=_rate_limit_key)
app = FastAPI(title="Support Ticket Agent")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Dev/demo default. Swap for a real provider per email_sender.py's documented seam.
_email_sender: EmailSender = ConsoleEmailSender()

# The dataset/API payload carries no real customer email field; used only
# when a request omits customer_email, so the demo sender has something to print.
_DEMO_CUSTOMER_EMAIL = "customer@example.com"


def verify_api_key(x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER)) -> None:
    """FastAPI dependency: require X-API-Key to match SUPPORT_AGENT_API_KEY.

    Reads the expected key from the environment on every call (mirrors
    llm_client._get_provider's pattern of re-reading its env var each call)
    rather than caching it at import time, so tests can set/change it via
    monkeypatch. Uses secrets.compare_digest for a constant-time comparison
    — a plain `==` would leak timing information about how many leading
    characters matched. If the server has no key configured, every request
    is denied (fails closed) rather than silently allowing access.
    """
    expected = os.environ.get(API_KEY_ENV_VAR, "")
    if not expected or not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


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


@app.post("/tickets", response_model=TicketResponse)
@limiter.limit(RATE_LIMIT)
def create_ticket(
    request: Request,
    payload: TicketCreateRequest,
    _authorized: None = Depends(verify_api_key),
) -> TicketResponse:
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
