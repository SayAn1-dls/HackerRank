"""Build safe, corpus-grounded responses (no external knowledge)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from support_triage.classifier import Classification
from support_triage.decision_engine import Decision
from support_triage.retriever import CorpusDoc, RetrievalResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResponseBundle:
    response: str
    justification_append: str


def build_response(
    classification: Classification,
    decision: Decision,
    retrieval: RetrievalResult,
) -> ResponseBundle:
    """Produce customer-facing text; escalations get a holding message only."""

    if decision.status == "escalated":
        body = (
            "Thank you for contacting support. Your request has been forwarded to a specialist "
            "who will review the details and follow up with you. If you have reference numbers "
            "or screenshots, please keep them available for the next message."
        )
        return ResponseBundle(response=body, justification_append="")

    # replied — only use retrieved doc text
    if not retrieval.docs:
        logger.warning("Decision was 'replied' but retrieval is empty; caller should escalate.")
        hold = (
            "We are reviewing your message and will respond with specific steps shortly."
        )
        return ResponseBundle(
            response=hold,
            justification_append=" Fallback: empty retrieval despite reply decision.",
        )

    intro = "Thank you for reaching out. Based on our internal help resources, here is what applies:"
    bullets = _format_bullets(retrieval.docs[:3])
    closing = (
        "If this does not fully resolve your situation, reply with any error messages or "
        "timestamps you see, and we can continue from there."
    )
    text = f"{intro}\n\n{bullets}\n\n{closing}"
    return ResponseBundle(response=text, justification_append="")


def _format_bullets(docs: list[CorpusDoc]) -> str:
    lines: list[str] = []
    for i, d in enumerate(docs, start=1):
        safe = d.snippet(320)
        lines.append(f"{i}. {safe}")
    return "\n".join(lines)
