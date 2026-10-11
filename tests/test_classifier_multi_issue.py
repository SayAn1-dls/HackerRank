"""Regression tests for multi-issue detection in support_triage.classifier."""

from __future__ import annotations

from support_triage.classifier import classify_ticket
from support_triage.ingestion import Ticket


def test_single_issue_two_sentences_not_multi() -> None:
    """Ordinary multi-sentence tickets are a single issue, not multiple."""
    ticket = Ticket(
        ticket_id="1",
        company="Acme",
        subject="Login problem",
        description="I cannot log in. Please help me reset it.",
    )
    assert classify_ticket(ticket).multi_issue is False


def test_decimal_version_number_not_multi() -> None:
    """A decimal like '2.0' must not be treated as a numbered-list delimiter."""
    ticket = Ticket(
        ticket_id="4",
        company="Acme",
        subject="App broken",
        description="I am on version 2.0 and it is broken. Please help me fix it.",
    )
    assert classify_ticket(ticket).multi_issue is False


def test_explicit_delimiters_still_multi() -> None:
    """Genuinely multiple issues separated by explicit delimiters stay multi."""
    newline_ticket = Ticket(
        ticket_id="2",
        company="Acme",
        subject="Two problems",
        description="My dashboard will not load at all.\nThe export button is missing too.",
    )
    assert classify_ticket(newline_ticket).multi_issue is True

    semicolon_ticket = Ticket(
        ticket_id="3",
        company="Acme",
        subject="Two problems",
        description="The dashboard will not load at all; the export button is missing too.",
    )
    assert classify_ticket(semicolon_ticket).multi_issue is True
