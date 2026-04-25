from __future__ import annotations


"""Fake News ML microservice — Phase 1 stubs; wire DistilBERT + Qdrant later."""

"""Fake News ML microservice."""



import hashlib
import math
from contextlib import asynccontextmanager
from typing import Any

import torch
from fastapi import FastAPI
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from app.credibility import get_credibility_score

MODEL_PATH = "/app/model/roberta-fakedetect"

tokenizer: AutoTokenizer | None = None
classifier: AutoModelForSequenceClassification | None = None



@asynccontextmanager
async def lifespan(app: FastAPI):
    global tokenizer, classifier
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    classifier = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    classifier.eval()
    print("Model loaded successfully")
    yield


app = FastAPI(title="Fake News ML Service", version="0.1.0", lifespan=lifespan)


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="News text or claim to classify.")
    source_url: str  


class PredictResponse(BaseModel):
    verdict: str = Field(..., description='One of: "fake", "real","uncertain".')
    confidence: float = Field(..., ge=0.0, le=1.0)
    #statement: str 
    #reasoning: str | None = None  # add this
    #sources: list[str] = []       # add this 
    credibility_score: float  # add this  
    

class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1)


class EmbedResponse(BaseModel):
    embedding: list[float]
    model: str = "stub-deterministic-hash"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)


class SearchHit(BaseModel):
    id: str
    score: float
    text: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    backend: str = "stub-in-memory"


def _stub_confidence_from_text(text: str) -> float:
    """Deterministic pseudo-confidence in (0,1) for stable demos."""
    h = hashlib.sha256(text.encode()).digest()
    x = int.from_bytes(h[:8], "big") / float(2**64)
    return 0.5 + 0.49 * math.sin(x * 9999)


def _stub_verdict_from_text(text: str) -> str:
    h = hashlib.sha256(text.encode()).digest()
    return "fake" if h[0] & 1 else "real"


def _stub_embedding(text: str, dim: int = 64) -> list[float]:
    """Deterministic low-dim embedding for API contract tests (not semantic)."""
    h = hashlib.sha256(text.encode()).digest()
    out: list[float] = []
    for i in range(dim):
        b = h[i % len(h)]
        out.append((b / 255.0) * 2.0 - 1.0)
    return out


_STUB_DOCS: list[dict[str, Any]] = [
    {
        "id": "doc-1",
        "text": "Official sources confirmed the event occurred on Tuesday.",
    },
    {
        "id": "doc-2",
        "text": "Anonymous insiders say scientists are hiding the truth.",
    },
]


def _stub_search_hits(query: str, top_k: int) -> list[SearchHit]:
    q_emb = _stub_embedding(query, dim=32)
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in _STUB_DOCS:
        d_emb = _stub_embedding(doc["text"], dim=32)
        score = sum(a * b for a, b in zip(q_emb, d_emb)) / max(len(q_emb), 1)
        scored.append((float(score), doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    hits = []
    for score, doc in scored[:top_k]:
        hits.append(SearchHit(id=doc["id"], score=score, text=doc["text"]))
    return hits


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    inputs= tokenizer(body.text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        outputs = classifier(**inputs)

    probs = torch.softmax(outputs.logits, dim=1)[0]
    pred = torch.argmax(probs).item()
    confidence = probs[pred].item()
    credibility_score = get_credibility_score(body.source_url)
    

    verdict = "fake" if pred == 1 else "real"
    if confidence < 0.85:
        verdict = "uncertain"
    
    return PredictResponse(
        verdict=verdict,
        confidence=round(confidence, 4),
        #statement=body.text , # add this
        credibility_score=credibility_score
    )


@app.post("/embed", response_model=EmbedResponse)
def embed(body: EmbedRequest) -> EmbedResponse:
    return EmbedResponse(embedding=_stub_embedding(body.text))


@app.post("/search", response_model=SearchResponse)
def search(body: SearchRequest) -> SearchResponse:
    hits = _stub_search_hits(body.query, body.top_k)
    return SearchResponse(hits=hits)
