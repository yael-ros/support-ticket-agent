"""Named prompt templates for every LLM call in this project.

Per CLAUDE.md: every LLM-facing prompt lives here as a named template with
a docstring explaining what it's for and what output schema it expects —
never as an inline string in a node or route handler.
"""

from __future__ import annotations

from pathlib import Path

from support_agent.schemas import RetrievedChunk

CLASSIFY_TICKET_PROMPT = """You are triaging an incoming customer support ticket for a SaaS product. \
Read the ticket and classify it.

Ticket subject: {subject}
Ticket body:
{body}

Classify this ticket along three dimensions:

- category: which support queue it belongs to.
  - technical_support: bugs, crashes, sync issues, data loss/corruption, performance problems in the product itself
  - product_support: how-to questions, feature usage, plan usage limits/quotas, exporting/importing data
  - customer_service: account profile changes, email changes, account deletion, filing a complaint, \
marketing/promotional strategy consulting (not the product's own how-to usage)
  - it_support: password resets, two-factor auth, SSO/login issues, API keys/integrations, browser \
compatibility, security incidents (unauthorized access, data breaches/leaks, suspicious activity)
  - billing_and_payments: payment methods, invoices/charges, failed payments, cancellation fees
  - returns_and_exchanges: order cancellation/changes, refunds, order/refund tracking, shipping address changes
  - service_outages_and_maintenance: checking service status, outages, scheduled maintenance windows
  - sales_and_pre_sales: comparing plans, placing a new order or upgrading, requesting a demo or trial extension
  - human_resources: job application status, employee referral program, timesheets/PTO
  - general_inquiry: general contact requests, newsletter/email preferences, product feedback or reviews

- urgency: how quickly this ticket needs a response.
  - low: general question, no real time pressure
  - medium: normal priority, should be handled within a business day or two
  - high: meaningful impact on the customer (broken workflow, blocked task), needs prompt attention
  - critical: severe impact (active outage, data loss, security incident), needs immediate attention

- confidence: your own confidence in this classification, from 0.0 to 1.0. Use a lower value when the \
ticket is ambiguous or could plausibly belong to more than one category.

Respond by calling the emit_result tool with your classification. Do not include any other commentary.
"""


def format_classify_prompt(subject: str, body: str) -> str:
    """Fill CLASSIFY_TICKET_PROMPT for a specific ticket.

    Expected output schema: support_agent.schemas.TicketClassification
    (category, urgency, confidence), enforced via tool-use in
    agent/llm_client.py — this function only produces the prompt text.
    """
    return CLASSIFY_TICKET_PROMPT.format(subject=subject or "(no subject)", body=body)


DRAFT_RESPONSE_PROMPT = """You are drafting a reply to a customer support ticket. Use ONLY the \
knowledge-base excerpts below as the factual basis for your response — do not rely on outside \
knowledge about the product, and do not invent steps, policies, or facts that aren't in the \
excerpts.

Ticket subject: {subject}
Ticket body:
{body}

Knowledge-base excerpts:
{chunks_block}

Write a helpful, professional reply to the customer. Then, for every factual claim in your reply \
(e.g. "restart the sync client," "this is a known issue in v2.3"), list the excerpt id(s) from \
above that support it in the `grounding` field. If a claim you want to make isn't backed by any \
excerpt, leave that claim out of the reply entirely — only write what the excerpts support.

If none of the excerpts above are actually relevant to this ticket, write a short reply saying a \
human agent will follow up, and leave `grounding` empty — do not stretch an unrelated excerpt to \
cover the ticket just to have something to cite.

Do not promise refunds, discounts, compensation, or any other concession — say a human agent will \
review requests like that instead.

Respond by calling the emit_result tool with your draft. Do not include any other commentary.
"""


def format_draft_prompt(subject: str, body: str, chunks: list[RetrievedChunk]) -> str:
    """Fill DRAFT_RESPONSE_PROMPT for a specific ticket and its retrieved KB chunks.

    Expected output schema: support_agent.schemas.DraftResponse (text,
    grounding), enforced via tool-use in agent/llm_client.py. Each chunk
    is labeled with its `chunk_id` in the prompt so the model can cite it
    verbatim in `grounding` — guardrails.grounding_check later checks
    those citations against the same chunk ids.
    """
    if chunks:
        chunks_block = "\n\n".join(f"[{chunk.chunk_id}] ({chunk.doc_title}): {chunk.text}" for chunk in chunks)
    else:
        chunks_block = "(no relevant excerpts were retrieved for this ticket)"
    return DRAFT_RESPONSE_PROMPT.format(
        subject=subject or "(no subject)", body=body, chunks_block=chunks_block
    )


# Read once at import time so the prompt embeds evaluation/rubric.md's
# actual text rather than a paraphrase — the documented rubric and what
# the judge model sees can never drift out of sync this way.
_RUBRIC_PATH = Path(__file__).parent.parent / "evaluation" / "rubric.md"
_RUBRIC_TEXT = _RUBRIC_PATH.read_text(encoding="utf-8")

JUDGE_RESPONSE_PROMPT = """You are a support team lead reviewing a drafted reply before it goes to \
the customer. Score it against the rubric below.

Ticket subject: {subject}
Ticket body:
{body}

Knowledge-base excerpts the draft was given:
{chunks_block}

Drafted reply:
{draft_text}

Rubric:
{rubric}

Score the drafted reply on helpfulness, correctness, and tone (1-5 each, per the rubric above), and \
give a one-sentence rationale for each score.

Respond by calling the emit_result tool with your scores. Do not include any other commentary.
"""


def format_judge_prompt(subject: str, body: str, chunks: list[RetrievedChunk], draft_text: str) -> str:
    """Fill JUDGE_RESPONSE_PROMPT for a ticket, its retrieved chunks, and a drafted reply.

    Expected output schema: support_agent.schemas.JudgeScore (helpfulness,
    correctness, tone, rationale), enforced via tool-use in
    agent/llm_client.py.
    """
    if chunks:
        chunks_block = "\n\n".join(f"[{chunk.chunk_id}] ({chunk.doc_title}): {chunk.text}" for chunk in chunks)
    else:
        chunks_block = "(no excerpts were retrieved for this ticket)"
    return JUDGE_RESPONSE_PROMPT.format(
        subject=subject or "(no subject)",
        body=body,
        chunks_block=chunks_block,
        draft_text=draft_text,
        rubric=_RUBRIC_TEXT,
    )
