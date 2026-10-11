"""Regression tests for multi-issue detection in the classifier."""

from __future__ import annotations

from support_triage.classifier import _split_issues, classify_ticket
from support_triage.ingestion import Ticket


def _ticket(description: str, subject: str = "API error") -> Ticket:
    return Ticket(ticket_id="2", company=None, subject=subject, description=description)


def test_version_decimal_does_not_split_into_multiple_issues() -> None:
    ticket = _ticket("We are on version 3.5 and get a 500 error on the endpoint.")
    assert classify_ticket(ticket).multi_issue is False


def test_version_string_does_not_split_into_multiple_issues() -> None:
    ticket = _ticket("We are on v2.0 and the dashboard widget is broken.")
    assert classify_ticket(ticket).multi_issue is False


def test_decimal_version_with_trailing_space_does_not_split() -> None:
    ticket = _ticket("We are on version 2.0 and the dashboard widget is broken.")
    assert classify_ticket(ticket).multi_issue is False


def test_version_decimal_does_not_split_into_chunks() -> None:
    text = "We are on version 3.5 and get a 500 error on the endpoint."
    assert _split_issues(text) == [text]


def test_version_string_does_not_split_into_chunks() -> None:
    text = "We are on v2.0 and the dashboard widget is broken."
    assert _split_issues(text) == [text]


def test_genuine_inline_numbered_list_is_multi_issue() -> None:
    ticket = _ticket("1. login fails 2. logout fails")
    assert classify_ticket(ticket).multi_issue is True


def test_zero_whitespace_inline_numbered_list_is_multi_issue() -> None:
    ticket = _ticket("1.login fails 2.logout fails")
    assert classify_ticket(ticket).multi_issue is True


def test_comma_separated_inline_numbered_list_is_multi_issue() -> None:
    ticket = _ticket("1. login fails, 2. logout fails")
    assert classify_ticket(ticket).multi_issue is True
