from __future__ import annotations

from datetime import datetime
from typing import Any

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_conn import get_qdrant_client
from app.credibility import get_credibility_score
from app.llm import run_llm_reasoning
import re

MIN_SIMILARITY = 0.35

COLLECTION_NAME = "knowledge_base"
TOP_K = 15


_embed_model: SentenceTransformer | None = None
_qdrant: QdrantClient | None = None


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = get_qdrant_client()
    return _qdrant

def _split_sentences(text: str) -> list[str]:
    # Simple sentence splitter (good enough for now)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

# def construct_query(text: str, headline: str | None = None) -> str:
#     # Step 1 — paragraphs
#     paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
#     first_para = paragraphs[0] if paragraphs else text

#     # Step 2 — split sentences
#     all_sentences = _split_sentences(text)
#     first_para_sentences = set(_split_sentences(first_para))

#     # Step 3 — exclude first paragraph sentences
#     remaining_sentences = [
#         s for s in all_sentences if s not in first_para_sentences
#     ]

#     # Step 4 — pick top 2 longest sentences
#     longest_sentences = sorted(
#         remaining_sentences,
#         key=lambda s: len(s),
#         reverse=True
#     )[:2]

#     # Step 5 — build query parts
#     parts = []

#     if headline:
#         parts.append(headline.strip())

#     parts.append(first_para)

#     parts.extend(longest_sentences)

#     # Step 6 — combine and trim
#     combined = " ".join(parts)
#     return combined[:600]  # slightly increased from 500

def construct_query(text: str, headline: str | None = None) -> str:
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    first_para = paragraphs[0] if paragraphs else text

    # Take only first ~250 chars of context
    context = first_para[:250]

    # Build structured query
    if headline:
        query = f"Claim: {headline}. Context: {context}"
    else:
        query = f"Claim: {context}"

    return query


def embed_text(text: str) -> list[float]:
    return _get_embed_model().encode(text).tolist()


def search_qdrant(vector: list[float], top_k: int = TOP_K) -> list[Any]:
    return _get_qdrant().search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        limit=top_k,
        with_payload=True,
    )

def _parse_date(date_str: str | None) -> datetime:
    if not date_str:
        return datetime(2000, 1, 1)
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
    ):
        try:
            return datetime.strptime(date_str[:25].strip(), fmt).replace(tzinfo=None)
        except ValueError:
            continue
    return datetime(2000, 1, 1)


def _composite_score(result: Any) -> float:
    similarity = result.score
    credibility = get_credibility_score(result.payload.get("url", ""))
    days_old = (datetime.utcnow() - _parse_date(result.payload.get("published"))).days
    recency = max(0.0, 1.0 - (days_old / 730))

    credibility_factor = 0.5 + 0.5 * credibility
    recency_factor = 0.5 + 0.5 * recency

    return similarity * credibility_factor * recency_factor


def _is_fact_check(result: Any) -> bool:
    return result.payload.get("source", "") == "Google Fact Check"

def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())

def _is_similar(a: str, b: str) -> bool:
    a = _normalize_text(a)
    b = _normalize_text(b)

    # Simple overlap check
    if not a or not b:
        return False

    # If one is mostly contained in the other → duplicate
    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    return shorter in longer


def _is_evidence_weak(evidence: list[dict]) -> bool:
    if not evidence:
        return True

    # Check top evidence strength
    top = evidence[0]

    # If similarity too low → weak
    if top["similarity"] < 0.4:
        return True

    # If all evidence has very low credibility
    avg_cred = sum(e["credibility"] for e in evidence) / len(evidence)
    if avg_cred < 0.3:
        return True

    return False

def process_evidence(results: list[Any]) -> list[dict]:
    # Step 1 — deduplicate by URL
    unique = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    seen_texts: list[str] = []

    for r in results:
        url = r.payload.get("url", "")
        title = r.payload.get("title", "")
        text = r.payload.get("text", "")

        # Skip duplicate URL
        if url and url in seen_urls:
            continue

        # Skip similar titles
        if any(_is_similar(title, t) for t in seen_titles):
            continue

        # Skip similar text (first 150 chars for speed)
        text_snippet = text[:150]
        if any(_is_similar(text_snippet, t) for t in seen_texts):
            continue

        # Keep this result
        unique.append(r)

        if url:
            seen_urls.add(url)
        if title:
            seen_titles.append(title)
        if text_snippet:
            seen_texts.append(text_snippet)

    # Step 2 — score each result
    for r in unique:
        r._composite = _composite_score(r)

    # Step 3 — sort by composite score descending
    ranked = sorted(unique, key=lambda r: r._composite, reverse=True)

    # Step 4 — diversity enforcement
    final: list[Any] = []

    fact_added = False
    news_added = False
    official_added = False

    for r in ranked:
        entry_type = _get_entry_type(r)

        if entry_type == "fact-check" and not fact_added:
            final.append(r)
            fact_added = True

        elif entry_type == "news" and not news_added:
            final.append(r)
            news_added = True

        elif entry_type == "official" and not official_added:
            final.append(r)
            official_added = True

        if fact_added and news_added and official_added:
            break
    # Step 5 — fill remaining slots up to 5
    for r in ranked:
        if len(final) >= 5:
            break
        if r not in final:
            final.append(r)

    # Step 6 — convert to plain dicts
    return [
        {
            "text": r.payload.get("text", ""),
            "source": r.payload.get("source", "Unknown"),
            "url": r.payload.get("url", ""),
            "title": r.payload.get("title", ""),
            "published": r.payload.get("published", ""),
            "verdict": r.payload.get("verdict"),
            "publisher": r.payload.get("publisher"),
            "is_fact_check": _is_fact_check(r),
            "entry_type": _get_entry_type(r),
            "credibility": get_credibility_score(r.payload.get("url", "")),
            "similarity": round(r.score, 4),
            "composite_score": round(r._composite, 4),
        }
        for r in final
    ]




def _is_retrieval_weak(results: list[Any]) -> bool:
    if not results:
        return True

    top_score = results[0].score

    # If best match is too weak → retrieval is useless
    return top_score < MIN_SIMILARITY

def _get_entry_type(result: Any) -> str:
    return result.payload.get("entry_type", "unknown")


def run_rag_pipeline(text: str, headline: str | None = None , credibility_score: float = 0.5,
    stale_warning: bool = False,domain_known: bool = True,) -> dict:
    query = construct_query(text, headline)
    vector = embed_text(query)
    raw_results = search_qdrant(vector)

    print("\n=== RAW RETRIEVAL RESULTS ===")
    for r in raw_results[:5]:
        print({
            "score": round(r.score, 4),
            "title": r.payload.get("title"),
            "source": r.payload.get("source"),
            "type": r.payload.get("entry_type")
        })
    print("=== END ===\n")

    if _is_retrieval_weak(raw_results):
        return {
            "verdict": "uncertain",
            "reasoning": "Insufficient relevant evidence retrieved.",
            "flagged_sentences": [],
            "fact_checks": [],
            "related_articles": [],
        }


    evidence = process_evidence(raw_results)

    if _is_evidence_weak(evidence):
        return {
        "verdict": "uncertain",
        "reasoning": "Retrieved evidence is weak or not reliable.",
        "flagged_sentences": [],
        "fact_checks": [],
        "related_articles": [],
         }



    return run_llm_reasoning(
    text=text,
    evidence=evidence,
    credibility_score=credibility_score,
    stale_warning=stale_warning,
)