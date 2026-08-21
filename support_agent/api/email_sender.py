"""Abstraction for delivering a drafted response to a customer.

Per BUILD_PLAN.md's Phase 6 spec: an abstract `EmailSender` interface with
a `ConsoleEmailSender` for dev/demo use, and a documented seam for a real
provider. No provider SDK (Resend/SendGrid/Gmail API/etc.) is imported here
or anywhere in `agent/` — api/main.py constructs one concrete sender (via
config/env) and passes it in, so swapping providers never touches agent or
route-handling logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmailSender(ABC):
    """Delivers a response to a customer. Implementations own their own transport."""

    @abstractmethod
    def send(self, *, to: str, subject: str, body: str) -> None:
        """Send `body` to `to` with `subject`. Must raise on delivery failure, never fail silently."""
        ...


class ConsoleEmailSender(EmailSender):
    """Dev/demo sender: prints the email instead of delivering it.

    This is what api/main.py wires up by default so the API is runnable
    end-to-end with no email provider account or credentials.
    """

    def send(self, *, to: str, subject: str, body: str) -> None:
        print(
            f"----- ConsoleEmailSender -----\nTo: {to}\nSubject: {subject}\n\n{body}\n-------------------------------"
        )


# Production seam: implement e.g. ResendEmailSender / SendGridEmailSender /
# GmailEmailSender as another EmailSender subclass, each wrapping that
# provider's own SDK/HTTP client entirely within its own `send()` method.
# api/main.py would then choose which concrete sender to construct (e.g.
# from an EMAIL_PROVIDER env var) at startup — the rest of the app only
# ever depends on the EmailSender interface above.
