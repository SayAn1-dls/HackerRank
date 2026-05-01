"""Classify request type, product area, risk, and multi-issue hints."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from support_triage.ingestion import Ticket

logger = logging.getLogger(__name__)


class RequestType(str, Enum):
    PRODUCT_ISSUE = "product_issue"
    FEATURE_REQUEST = "feature_request"
    BUG = "bug"
    INVALID = "invalid"


class RiskCategory(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FRAUD = "fraud"
    BILLING = "billing"
    ACCOUNT_ACCESS = "account_access"
    SECURITY = "security"


@dataclass(frozen=True)
class Classification:
    request_type: RequestType
    product_area: str
    risk_categories: frozenset[RiskCategory]
    risk_level: str
    multi_issue: bool
    company_inferred: bool


_FRAUD_PAT: Final = re.compile(
    r"\b(fraud|scam|stolen\s*card|unauthorized\s*charge|chargeback|"
    r"identity\s*theft|phish|phishing|someone\s*else\s*(used|paid))\b",
    re.I,
)
_BILLING_PAT: Final = re.compile(
    r"\b(billing|invoice|refund|charged\s*twice|double\s*bill|wrong\s*amount|"
    r"subscription|cancel\s*subscription|payment\s*failed|overcharged|dispute)\b",
    re.I,
)
_ACCOUNT_ACCESS_PAT: Final = re.compile(
    r"\b(locked\s*out|cannot\s*log\s*in|can'?t\s*log\s*in|password\s*reset|"
    r"forgot\s*(my\s*)?password|reset\s*(email|link)|"
    r"account\s*(locked|disabled|suspended|hacked|compromised)|"
    r"lost\s*access|2fa|mfa|two[\s-]?factor)\b",
    re.I,
)
_SECURITY_PAT: Final = re.compile(
    r"\b(vulnerability|cve|exploit|breach|data\s*leak|pen\s*test|"
    r"security\s*issue|malware|rce|xss)\b",
    re.I,
)

_BUG_PAT: Final = re.compile(
    r"\b(crash|error\s*message|stack\s*trace|503|500|bug|broken|not\s*working|"
    r"hangs|freeze|regression|defect)\b",
    re.I,
)
_FEATURE_PAT: Final = re.compile(
    r"\b(feature\s*request|please\s*add|would\s*be\s*(nice|great)\s+if|"
    r"if\s+you\s+(could|can)\s+add|roadmap|enhancement|"
    r"wish\s*list|suggest)\b",
    re.I,
)
_INVALID_PAT: Final = re.compile(
    r"\b(unsubscribe|spam|wrong\s*number|test\s*ticket|asdf|lorem\s*ipsum)\b",
    re.I,
)

_AREA_KEYWORDS: Final[dict[str, tuple[str, ...]]] = {
    "billing": ("bill", "invoice", "payment", "charge", "refund", "subscription", "plan", "pricing"),
    "authentication": ("login", "password", "sign in", "signin", "2fa", "mfa", "sso", "oauth"),
    "api": ("api", "endpoint", "webhook", "rate limit", "sdk", "integration"),
    "dashboard": ("dashboard", "ui", "console", "portal", "settings page"),
    "data_export": ("export", "csv download", "report", "backup data"),
    "general": ("hello", "question", "how to", "help", "documentation"),
}


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1}


def _split_issues(text: str) -> list[str]:
    """Heuristic: multiple issues if several strong separators or numbered lists."""
    parts = re.split(r"\n+|(?:\s*;\s+)|(?:\s*\.(?:\s+|$)){2,}", text)
    chunks = [p.strip() for p in parts if p and len(p.strip()) > 10]
    if len(chunks) >= 2:
        return chunks
    # Inline numbered lists: "1) foo 2) bar" on one line
    numbered_inline = [p.strip() for p in re.split(r"\b\d+[\.)]\s*", text) if p.strip()]
    if len(numbered_inline) >= 2:
        return [n for n in numbered_inline if len(n) > 8]
    numbered = re.findall(r"(?:^|\n)\s*\d+[\.)]\s*([^\n]+)", text, re.M)
    if len(numbered) >= 2:
        return [n.strip() for n in numbered if len(n.strip()) > 8]
    return [text]


def classify_ticket(ticket: Ticket) -> Classification:
    text = ticket.combined_text
    if not text or len(text.strip()) < 3:
        return Classification(
            request_type=RequestType.INVALID,
            product_area="unknown",
            risk_categories=frozenset(),
            risk_level="low",
            multi_issue=False,
            company_inferred=ticket.company is None,
        )

    multi = len(_split_issues(text)) > 1
    risks: set[RiskCategory] = set()

    if _FRAUD_PAT.search(text):
        risks.add(RiskCategory.FRAUD)
    if _BILLING_PAT.search(text):
        risks.add(RiskCategory.BILLING)
    if _ACCOUNT_ACCESS_PAT.search(text):
        risks.add(RiskCategory.ACCOUNT_ACCESS)
    if _SECURITY_PAT.search(text):
        risks.add(RiskCategory.SECURITY)

    sensitive = risks & {
        RiskCategory.FRAUD,
        RiskCategory.BILLING,
        RiskCategory.ACCOUNT_ACCESS,
        RiskCategory.SECURITY,
    }
    if sensitive:
        risk_level = "high"
    elif _BUG_PAT.search(text) or "error" in text.lower():
        risk_level = "medium"
    else:
        risk_level = "low"

    # Request type
    if _INVALID_PAT.search(text) and len(text) < 80:
        req = RequestType.INVALID
    elif _FEATURE_PAT.search(text) and not _BUG_PAT.search(text):
        req = RequestType.FEATURE_REQUEST
    elif _BUG_PAT.search(text):
        req = RequestType.BUG
    else:
        req = RequestType.PRODUCT_ISSUE

    product_area = _infer_product_area(text, ticket.company)
    company_inferred = ticket.company is None

    return Classification(
        request_type=req,
        product_area=product_area,
        risk_categories=frozenset(risks),
        risk_level=risk_level,
        multi_issue=multi,
        company_inferred=company_inferred,
    )


def _infer_product_area(text: str, company: str | None) -> str:
    low = text.lower()
    company_hint = (company or "").lower()

    scores: dict[str, int] = {k: 0 for k in _AREA_KEYWORDS}
    for area, kws in _AREA_KEYWORDS.items():
        for kw in kws:
            if kw in low:
                scores[area] += 2
            if company_hint and kw in company_hint:
                scores[area] += 1

    tokens = _tokenize(low)
    if "api" in tokens or "webhook" in tokens:
        scores["api"] += 3
    if "login" in tokens or "password" in tokens:
        scores["authentication"] += 2

    best = max(scores.items(), key=lambda x: x[1])
    if best[1] == 0:
        if "billing" in low or "invoice" in low:
            return "billing"
        return "general"
    return best[0]
