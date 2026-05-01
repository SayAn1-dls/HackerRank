"""Load and normalize support ticket CSV rows."""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


@dataclass
class Ticket:
    """Normalized ticket for downstream processing."""

    ticket_id: str
    company: str | None
    subject: str
    description: str
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def combined_text(self) -> str:
        parts = [self.subject, self.description]
        return " ".join(p.strip() for p in parts if p and p.strip())


def _clean_cell(value: str | None) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    s = _CONTROL_RE.sub("", s)
    s = _WHITESPACE_RE.sub(" ", s)
    return s


def _normalize_header(h: str) -> str:
    return _WHITESPACE_RE.sub("_", h.strip().lower().replace(" ", "_"))


def _pick(row: dict[str, str], *keys: str) -> str:
    norm = {_normalize_header(k): v for k, v in row.items()}
    for k in keys:
        nk = _normalize_header(k)
        if nk in norm and norm[nk]:
            return _clean_cell(norm[nk])
    return ""


def load_tickets_csv(path: Path | str) -> list[Ticket]:
    """Read tickets from CSV. Accepts flexible column names."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    tickets: list[Ticket] = []
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            logger.warning("CSV has no header row")
            return []

        for i, row in enumerate(reader):
            if not row:
                continue
            tid = _pick(row, "ticket_id", "id", "ticket", "case_id", "case")
            if not tid:
                tid = f"row_{i + 2}"

            company_raw = _pick(row, "company", "organization", "org", "customer_company")
            company = company_raw if company_raw else None

            subject = _pick(row, "subject", "title", "summary")
            description = _pick(
                row,
                "description",
                "body",
                "message",
                "details",
                "issue",
                "content",
            )

            if not subject and not description:
                logger.debug("Skipping empty row %s", i + 2)
                continue

            tickets.append(
                Ticket(
                    ticket_id=tid,
                    company=company,
                    subject=subject,
                    description=description,
                    raw={k: v for k, v in row.items() if v is not None},
                )
            )

    logger.info("Loaded %d ticket(s) from %s", len(tickets), path)
    return tickets


def tickets_to_dict_rows(tickets: list[Ticket]) -> Iterator[dict[str, Any]]:
    for t in tickets:
        yield {
            "ticket_id": t.ticket_id,
            "company": t.company or "",
            "subject": t.subject,
            "description": t.description,
        }
