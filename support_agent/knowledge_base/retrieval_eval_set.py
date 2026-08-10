"""Hand-written retrieval eval set: (query, expected_doc_id) pairs.

Every query below was written by hand, phrased the way a user or agent
would naturally ask — not copied from any KBDocument title or body — to
make this a genuine test of semantic retrieval rather than keyword
matching. One query per KBDocument, covering the full 40-document KB (the
BUILD_PLAN.md definition of done asks for at least 20).

Each entry is `(query, expected_doc_id)`. `expected_doc_id` must match a
real `KBDocument.id` in documents.py — this is checked by a unit test
(tests/test_retrieval_eval_set.py) so a typo here fails loudly instead of
silently under-scoring the eval.
"""

from __future__ import annotations

RETRIEVAL_EVAL_SET: list[tuple[str, str]] = [
    ("The app keeps crashing every time I open it", "ts-01-app-crashes-freezes"),
    ("What does error E204 mean?", "ts-02-error-codes"),
    ("My changes on my phone aren't showing up on my laptop", "ts-03-sync-issues"),
    ("The app has gotten really slow lately", "ts-04-slow-performance"),
    ("I accidentally deleted an important document and need it back", "ts-05-data-loss-recovery"),
    ("How do I get my data out as a CSV file?", "ps-01-export-import-data"),
    ("Why can't I do bulk editing on my phone?", "ps-02-feature-parity"),
    ("How much storage am I allowed on my plan?", "ps-03-usage-limits"),
    ("Is there a way to search commands with the keyboard?", "ps-04-keyboard-shortcuts"),
    ("How do I change my display name?", "cs-01-update-profile"),
    ("I need to change the email linked to my account", "cs-02-change-email"),
    ("I want to permanently close my account", "cs-03-delete-account"),
    ("I'm unhappy with how I was treated, how do I complain?", "cs-04-file-complaint"),
    ("I forgot my password and can't log in", "it-01-password-reset"),
    ("How do I turn on two-factor authentication?", "it-02-two-factor-setup"),
    ("I keep getting redirected in a loop when trying to log in with SSO", "it-03-login-issues"),
    ("How do I generate an API token for a Zapier integration?", "it-04-api-integration"),
    ("Which browsers does the app support?", "it-05-browser-compatibility"),
    ("My credit card expired, how do I add a new one?", "bp-01-update-payment-method"),
    ("There's a charge on my invoice I don't recognize", "bp-02-understand-invoice"),
    ("My card payment keeps getting declined", "bp-03-failed-payment"),
    ("Do I get charged a fee if I cancel my annual plan early?", "bp-04-cancellation-fees"),
    ("Can I pay with PayPal?", "bp-05-accepted-payment-methods"),
    ("I want to cancel an order I just placed", "re-01-cancel-order"),
    ("Can I change the size of an item I already ordered?", "re-02-change-order"),
    ("Where's my refund, it's been a week", "re-03-track-order-refund"),
    ("What's your return policy for unused items?", "re-04-refund-policy"),
    ("I need to update my shipping address on an order", "re-05-shipping-address"),
    ("Is there an outage right now?", "so-01-check-status"),
    ("When is the next maintenance window scheduled?", "so-02-scheduled-maintenance"),
    ("The service seems down, what should I do?", "so-03-during-outage"),
    ("What's the difference between the Team and Business plans?", "sp-01-plan-comparison"),
    ("How do I upgrade to a paid subscription?", "sp-02-place-new-order"),
    ("Can I get a longer free trial?", "sp-03-request-demo-trial"),
    ("Has my job application been reviewed yet?", "hr-01-application-status"),
    ("How does the employee referral bonus work?", "hr-02-referral-program"),
    ("How do I request time off?", "hr-03-timesheet-pto"),
    ("I'd like to talk to a real support person", "gi-01-contact-support"),
    ("How do I stop getting the monthly newsletter?", "gi-02-newsletter-preferences"),
    ("Where can I suggest a new feature?", "gi-03-leave-feedback"),
]
