"""Keyword-based retrieval over the local support corpus."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CorpusDoc:
    doc_id: str
    title: str
    product_area: str
    body: str
    keywords: frozenset[str]

    def snippet(self, max_len: int = 400) -> str:
        t = f"{self.title}: {self.body}".strip()
        if len(t) <= max_len:
            return t
        return t[: max_len - 3].rstrip() + "..."


@dataclass
class RetrievalResult:
    docs: list[CorpusDoc]
    scores: list[float]
    max_score: float


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _load_json_corpus(path: Path) -> list[CorpusDoc]:
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    docs: list[CorpusDoc] = []
    for item in raw:
        kid = str(item.get("id", ""))
        title = str(item.get("title", ""))
        area = str(item.get("product_area", "general"))
        body = str(item.get("body", ""))
        kws = item.get("keywords") or []
        kw_set = frozenset(str(k).lower() for k in kws) | frozenset(_tokenize(title + " " + body))
        docs.append(
            CorpusDoc(
                doc_id=kid or title[:32],
                title=title,
                product_area=area,
                body=body,
                keywords=kw_set,
            )
        )
    return docs


class SupportRetriever:
    """Simple TF-style overlap scorer between ticket text and corpus entries."""

    def __init__(self, corpus_path: Path | str | None = None):
        base = Path(__file__).resolve().parent / "data" / "support_corpus.json"
        self._path = Path(corpus_path) if corpus_path else base
        self._docs: list[CorpusDoc] = []
        self.reload()

    def reload(self) -> None:
        if not self._path.is_file():
            logger.error("Corpus file missing: %s", self._path)
            self._docs = []
            return
        self._docs = _load_json_corpus(self._path)
        logger.info("Loaded %d corpus document(s)", len(self._docs))

    @property
    def docs(self) -> list[CorpusDoc]:
        return list(self._docs)

    def retrieve(self, query: str, product_area: str | None = None, top_k: int = 3) -> RetrievalResult:
        if not self._docs or not (query or "").strip():
            return RetrievalResult(docs=[], scores=[], max_score=0.0)

        q_tokens = set(_tokenize(query))
        if not q_tokens:
            return RetrievalResult(docs=[], scores=[], max_score=0.0)

        # Strong tokens that should dominate routing when present in the ticket.
        signal_tokens = {"csv", "export", "download", "report", "reports", "webhook", "429", "api",
                         "password", "login", "dashboard", "widget", "invoice", "billing", "2fa", "mfa"}

        export_intent = len({"csv", "export", "download"} & q_tokens)

        scored: list[tuple[float, CorpusDoc]] = []
        for d in self._docs:
            overlap = len(q_tokens & d.keywords)
            title_hits = sum(1 for t in _tokenize(d.title) if t in q_tokens)
            area_bonus = 1.5 if product_area and d.product_area == product_area else 0.0
            general_bonus = 0.5 if d.product_area == "general" else 0.0
            signal_hits = sum(1.25 for t in (q_tokens & signal_tokens) if t in d.keywords)
            score = overlap + 0.5 * title_hits + area_bonus + general_bonus + signal_hits
            if export_intent >= 1 and d.product_area == "billing" and not ({"csv", "export"} & d.keywords):
                score -= 2.0
            if score > 0:
                scored.append((score, d))

        scored.sort(key=lambda x: -x[0])
        top = scored[:top_k]
        docs = [d for _, d in top]
        scores = [s for s, _ in top]
        max_s = scores[0] if scores else 0.0
        return RetrievalResult(docs=docs, scores=scores, max_score=max_s)
