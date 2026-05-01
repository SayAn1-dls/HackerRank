#!/usr/bin/env python3
"""CLI: triage support tickets from CSV using local corpus only."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

from support_triage.classifier import classify_ticket
from support_triage.decision_engine import decide
from support_triage.ingestion import load_tickets_csv
from support_triage.responder import build_response
from support_triage.retriever import SupportRetriever


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Triage support tickets from CSV; outputs structured CSV (corpus-grounded)."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("support_tickets.csv"),
        help="Input CSV path (default: support_tickets.csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("triage_output.csv"),
        help="Output CSV path (default: triage_output.csv)",
    )
    parser.add_argument(
        "-c",
        "--corpus",
        type=Path,
        default=None,
        help="Override path to support_corpus.json",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)
    log = logging.getLogger("main")

    try:
        tickets = load_tickets_csv(args.input)
    except FileNotFoundError as e:
        log.error("%s", e)
        return 2

    retriever = SupportRetriever(args.corpus)

    fieldnames = [
        "ticket_id",
        "status",
        "product_area",
        "response",
        "justification",
        "request_type",
        "confidence_score",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ticket in tickets:
            clf = classify_ticket(ticket)
            retr = retriever.retrieve(
                ticket.combined_text,
                product_area=clf.product_area if clf.product_area != "unknown" else None,
            )
            # If primary area retrieval is weak, try without area filter
            if retr.max_score < 1.5 and clf.product_area not in ("general", "unknown"):
                retr2 = retriever.retrieve(ticket.combined_text, product_area=None)
                if retr2.max_score > retr.max_score:
                    retr = retr2

            decision = decide(
                clf,
                retr,
                combined_text_len=len(ticket.combined_text.strip()),
            )
            bundle = build_response(clf, decision, retr)
            justification = decision.justification
            if bundle.justification_append:
                justification = f"{justification} {bundle.justification_append}".strip()

            writer.writerow(
                {
                    "ticket_id": ticket.ticket_id,
                    "status": decision.status,
                    "product_area": clf.product_area,
                    "response": bundle.response.strip(),
                    "justification": justification,
                    "request_type": clf.request_type.value,
                    "confidence_score": f"{decision.confidence:.3f}",
                }
            )

    log.info("Wrote %d row(s) to %s", len(tickets), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
