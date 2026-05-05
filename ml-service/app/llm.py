from __future__ import annotations

import json
import os
import re

from openai import OpenAI

_client: OpenAI | None = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            max_retries=0,
            timeout=45.0,
        )
    return _client

LLM_MODEL = os.getenv("LLM_MODEL", "mistralai/mistral-large-3-675b-instruct-2512")
LLM_TIMEOUT = 30


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _extract_json(raw: str) -> dict:
    # Strategy 1 — direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Strategy 2 — find first { and last } and parse between them
    try:
        start = raw.index('{')
        end = raw.rindex('}') + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        pass
    return {}


def build_prompt(
    text: str,
    evidence: list[dict],
    credibility_score: float,
    stale_warning: bool = False,
    domain_known: bool = True,
) -> tuple[str, list[str]]:

    evidence = evidence[:5]

    # Split article into numbered sentences
    sentences = _split_sentences(text)
    numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(sentences))

    # Format evidence documents
    evidence_text = ""
    for i, e in enumerate(evidence):
        evidence_text += f"""
Source {i + 1}: {e['source']} (credibility: {e['credibility']:.2f}) [{e['entry_type']}]
Title: {e['title']}
URL: {e['url']}
Published: {e['published'] or 'Unknown'}
Content: {e['text'][:150]}
Fact-check verdict: {e.get('verdict') or 'N/A'}
"""

    # Build stale warning if needed
    stale_note = "\n⚠️ WARNING: This article may be outdated. Factor this into your reasoning." if stale_warning else ""
    domain_note = "\n⚠️ NOTE: This article is from an unknown or unverified domain. Treat with high suspicion." if not domain_known else ""


    prompt = f"""You are an expert fact-checking assistant. Analyze the following news article claim and determine if it is real, fake, or uncertain based ONLY on the provided evidence.

ARTICLE TEXT:
{text[:500]}

NUMBERED SENTENCES:
{numbered}

SOURCE CREDIBILITY SCORE: {credibility_score:.2f} (0=unreliable, 1=highly credible){stale_note}{domain_note}

EVIDENCE FROM KNOWLEDGE BASE:
{evidence_text}

STRICT INSTRUCTIONS:
- Only use the provided evidence. Do NOT use outside knowledge.
- If evidence is insufficient to reach a verdict, return verdict: uncertain.
- Cite every claim by source name explicitly e.g. "According to Reuters..."
- Never invent URLs, dates, quotes, or statistics.
- If source credibility is below 0.4, treat the article with high suspicion.
- Return suspicious sentence indices as 0-based integers e.g. [0, 2, 5]

Return ONLY valid JSON matching this exact schema, no other text:
{{
  "verdict": "real" | "fake" | "uncertain",
  "confidence": 0.0 to 1.0,
  "reasoning": "step by step explanation citing sources by name",
  "flagged_sentence_indices": [0, 2, 5],
  "fact_checks": [
    {{"claim": "...", "verdict": "...", "source": "..."}}
  ],
  "related_articles": [
    {{"title": "...", "url": "...", "source": "..."}}
  ]
}}"""

    return prompt, sentences

def call_llm(prompt: str) -> dict:
    fallback = {
        "verdict": "uncertain",
        "confidence": 0.0,
        "reasoning": "Unable to generate reliable explanation due to a timeout or parsing error.",
        "flagged_sentence_indices": [],
        "fact_checks": [],
        "related_articles": [],
    }
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024,
            timeout=30.0,
        )
        raw = response.choices[0].message.content or ""
        raw = raw.strip()
        print(f"=== LLM RAW RESPONSE ===\n{raw}\n=== END ===")
        result = _extract_json(raw)
        if not result:
            print("WARNING: JSON parsing failed, using fallback")
            return fallback
        return result
    except Exception as e:
        print(f"=== LLM CALL FAILED: {type(e).__name__}: {e} ===")
        return fallback

    


def map_flagged_sentences(
    indices: list[int],
    sentences: list[str]
) -> list[str]:
    return [
        sentences[i]
        for i in indices
        if isinstance(i, int) and 0 <= i < len(sentences)
    ]


def run_llm_reasoning(
    text: str,
    evidence: list[dict],
    credibility_score: float,
    stale_warning: bool = False,
    domain_known: bool = True,
) -> dict:

    if not evidence:
        evidence = [{
            "text": "No relevant evidence retrieved.",
            "source": "system",
            "title": "No evidence",
            "url": "",
            "published": "",
            "credibility": 0.0,
            "entry_type": "none"
        }]
    prompt, sentences = build_prompt(
        text, evidence, credibility_score, stale_warning
    )
    result = call_llm(prompt)

    # Map sentence indices to actual text
    indices = result.get("flagged_sentence_indices", [])
    flagged_sentences = map_flagged_sentences(indices, sentences)

    return {
        "verdict": result.get("verdict", "uncertain"),
        "confidence": result.get("confidence", 0.0),
        "reasoning": result.get("reasoning", ""),
        "flagged_sentences": flagged_sentences,
        "fact_checks": result.get("fact_checks", []),
        "related_articles": result.get("related_articles", []),
    }

