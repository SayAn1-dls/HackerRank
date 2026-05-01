"""Decide replied vs escalated using classification, risk, and retrieval."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from support_triage.classifier import Classification, RequestType, RiskCategory
from support_triage.retriever import RetrievalResult

logger = logging.getLogger(__name__)

# Minimum retrieval strength to allow a customer-facing reply grounded in corpus.
MIN_REPLY_SCORE = 2.0
# Stricter threshold when multiple issues are detected.
MIN_REPLY_SCORE_MULTI = 3.0


@dataclass(frozen=True)
class Decision:
    status: str  # "replied" | "escalated"
    justification: str
    confidence: float


def decide(
    classification: Classification,
    retrieval: RetrievalResult,
    combined_text_len: int,
) -> Decision:
    """Return reply vs escalate with justification and confidence in [0,1]."""

    if classification.request_type == RequestType.INVALID:
        return Decision(
            status="escalated",
            justification="Ticket appears invalid, empty, or out of scope; human review required.",
            confidence=0.85,
        )

    sensitive = classification.risk_categories & {
        RiskCategory.FRAUD,
        RiskCategory.BILLING,
        RiskCategory.ACCOUNT_ACCESS,
        RiskCategory.SECURITY,
    }
    if sensitive:
        labels = ", ".join(sorted(s.value for s in sensitive))
        return Decision(
            status="escalated",
            justification=f"Sensitive topic detected ({labels}); policy requires specialist review.",
            confidence=0.9,
        )

    if classification.multi_issue:
        thresh = MIN_REPLY_SCORE_MULTI
        multi_note = " Multiple distinct issues detected;"
    else:
        thresh = MIN_REPLY_SCORE
        multi_note = ""

    # Multiple issues: prefer a human unless retrieval strongly covers all threads.
    if classification.multi_issue and retrieval.max_score < 8.0:
        return Decision(
            status="escalated",
            justification=(
                "Multiple distinct issues in one ticket; single automated reply may miss required "
                f"steps (retrieval score {retrieval.max_score:.2f}; threshold 8.0)."
            ),
            confidence=0.82,
        )

    if retrieval.max_score < thresh:
        return Decision(
            status="escalated",
            justification=(
                f"{multi_note.strip()} Insufficient grounding in the internal support corpus "
                f"(retrieval score {retrieval.max_score:.2f} below threshold {thresh:.1f})."
            ).strip(),
            confidence=0.75,
        )

    if combined_text_len < 15:
        return Decision(
            status="escalated",
            justification="Request is too vague to answer safely from the corpus alone.",
            confidence=0.7,
        )

    conf = _confidence_from_signals(classification, retrieval, thresh)
    return Decision(
        status="replied",
        justification=(
            f"Corpus match sufficient (score {retrieval.max_score:.2f}); "
            f"no mandatory escalation triggers; response limited to retrieved passages."
        ),
        confidence=conf,
    )


def _confidence_from_signals(
    classification: Classification,
    retrieval: RetrievalResult,
    threshold: float,
) -> float:
    base = 0.55
    if retrieval.max_score >= threshold + 2:
        base += 0.15
    elif retrieval.max_score >= threshold + 1:
        base += 0.08
    if not classification.company_inferred:
        base += 0.05
    if classification.risk_level == "low":
        base += 0.1
    elif classification.risk_level == "medium":
        base += 0.02
    if classification.multi_issue:
        base -= 0.12
    return max(0.35, min(0.95, round(base, 3)))
