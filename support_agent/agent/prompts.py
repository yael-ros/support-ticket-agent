"""Named prompt templates for every LLM call in this project.

Per CLAUDE.md: every LLM-facing prompt lives here as a named template with
a docstring explaining what it's for and what output schema it expects —
never as an inline string in a node or route handler.
"""

from __future__ import annotations

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
