"""Unit tests for api/email_sender.py's ConsoleEmailSender."""

from __future__ import annotations

from support_agent.api.email_sender import ConsoleEmailSender


def test_console_email_sender_prints_the_message(capsys):
    ConsoleEmailSender().send(to="a@example.com", subject="Re: help", body="Try restarting.")

    captured = capsys.readouterr()
    assert "a@example.com" in captured.out
    assert "Re: help" in captured.out
    assert "Try restarting." in captured.out
