"""Public, unauthenticated demo endpoint (PORTFOLIO_ADDITIONS.md, Addition 1).

Explicitly out of BUILD_PLAN.md's original scope — see
PORTFOLIO_ADDITIONS.md for why this exists and its full spec. Runs the
same run_agent() pipeline as api/main.py's authenticated `/tickets`, but
with no API key required, so a portfolio reviewer can try the system from
a browser with zero setup.

Because this is unauthenticated and public, every safety rule below is
mandatory, not configurable:

- Always forces LLM_PROVIDER=gemini (agent/llm_client.py's
  force_provider()), regardless of the app's configured default —
  guarantees this endpoint can only ever hit Gemini's free tier and never
  generate real cost, no matter what LLM_PROVIDER is set to for the
  authenticated /tickets endpoint. Context-local (not an env var
  mutation), so it can't race a concurrent /tickets request running on a
  different provider.
- A per-IP rate limit (DEMO_PER_IP_RATE_LIMIT) and a global daily cap
  (DEMO_DAILY_CAP) shared across every visitor, keyed by the current UTC
  calendar date so it resets exactly at UTC midnight — see
  _demo_daily_key's docstring for why a plain "50/day" limit wouldn't do
  that on its own.
- Same subject/body length caps as /tickets (TicketCreateRequest is
  reused as-is from api/models.py).
- Never calls EmailSender. An anonymous caller supplying an arbitrary
  customer_email and triggering a real send would make this endpoint an
  open mail relay the moment a real (non-Console) EmailSender is wired
  in — the field exists on the shared request model for parity with
  /tickets, but demo requests never reach _email_sender.send().

NOTE: like api/main.py, deliberately does NOT `from __future__ import
annotations` — create_demo_ticket is wrapped by @limiter.limit, which has
the same __globals__/postponed-annotations interaction bug documented in
main.py's module docstring.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from slowapi.util import get_remote_address

from support_agent.agent.graph import run_agent
from support_agent.agent.llm_client import force_provider
from support_agent.agent.providers.base import LLMCallError
from support_agent.api.models import RoutingResponse, TicketCreateRequest, TicketResponse
from support_agent.api.rate_limit import limiter
from support_agent.schemas import Ticket

DEMO_PER_IP_RATE_LIMIT = "5/minute"
DEMO_DAILY_CAP = "50/day"

DEMO_PER_IP_ERROR_MESSAGE = (
    "You're sending requests too quickly — please wait a minute and try again."
)
DEMO_DAILY_CAP_ERROR_MESSAGE = "Demo limit reached for today, please try again tomorrow."

_STATIC_DIR = Path(__file__).parent / "static"
_DEMO_HTML = (_STATIC_DIR / "demo.html").read_text(encoding="utf-8")

router = APIRouter()


def _demo_daily_key(request: Request) -> str:
    """One shared bucket for the whole day, resetting at UTC midnight.

    `limits`' own "50/day" window is a rolling 24h-from-first-hit window,
    not a calendar-day window (confirmed by reading limits.storage.memory
    .MemoryStorage.incr — it stamps a key's expiry from whenever the
    *first* hit lands, not from a fixed clock boundary). Folding today's
    UTC date into the *key* instead gets an exact midnight-UTC reset for
    free: once the date rolls over this returns a brand-new key, so
    counting starts at 0 regardless of the underlying window's own
    internal expiry timer.

    Must keep the parameter literally named `request` even though it's
    unused: slowapi decides whether to call a key_func with the current
    Request by checking for that exact parameter name in its signature
    (see Limiter.__evaluate_limits) — renaming it silently breaks this
    into a zero-arg call and crashes.
    """
    return f"demo-daily-{datetime.now(UTC):%Y-%m-%d}"


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo_page() -> HTMLResponse:
    return HTMLResponse(_DEMO_HTML)


@router.post("/demo/tickets", response_model=TicketResponse)
@limiter.limit(
    DEMO_PER_IP_RATE_LIMIT, key_func=get_remote_address, error_message=DEMO_PER_IP_ERROR_MESSAGE
)
@limiter.limit(DEMO_DAILY_CAP, key_func=_demo_daily_key, error_message=DEMO_DAILY_CAP_ERROR_MESSAGE)
def create_demo_ticket(request: Request, payload: TicketCreateRequest) -> TicketResponse:
    # payload.id is ignored: a public demo has no need for caller-supplied
    # ticket ids, and every demo ticket gets a demo- prefix so it's
    # unmistakable in logs/observability output.
    ticket = Ticket(
        id=f"demo-{uuid.uuid4()}",
        subject=payload.subject,
        body=payload.body,
        language=payload.language,
    )

    try:
        with force_provider("gemini"):
            state = run_agent(ticket)
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    assert state.classification is not None
    assert state.routing_decision is not None

    response_text: str | None = None
    if state.routing_decision.action == "auto_send":
        assert state.draft is not None
        response_text = state.draft.text
        # Deliberately no _email_sender.send() call — see module docstring.

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
