 # SOLO BUILD PLAN  
## Fake News Detection System  
### An Explainable & Evidence-Based AI Backend  

**Arya Majumder · 10-Week Solo Execution Plan**  
**HITK — Department of Computer Science and Business Systems**

---

## Overview

This document outlines the complete solo execution plan for the **Fake News Detection System** — a distributed AI backend built by Arya Majumder.

The project is structured into **four phases over 10 weeks**, combining:
- A **Python ML pipeline**
- A **production-grade Go API gateway**

### Key Architectural Decision

The Python ML service *(DistilBERT + RAG + LLM)* is wrapped inside a **Go API gateway**.

This transforms the project from:
> ❌ Just an ML experiment  
> ✅ Into a backend engineering system

This positioning makes it highly relevant for:
- Backend engineering roles  
- AI infrastructure roles  
- Forward deployment engineering  

---

## System Architecture

- **Client → Go API Gateway**
- Gateway handles:
  - Authentication (JWT)
  - Rate limiting (Redis)
  - Routing logic
- Requests forwarded to:
  - Python ML Service (DistilBERT classifier)
  - Vector DB (Qdrant)
  - LLM for explanation

---

## Ground Rules

- ❌ No LangChain / LangGraph  
- ✅ Build everything manually (Go + Python)
- ❌ No deep ML theory required  
- ✅ Understand RAG conceptually
- 📊 Instrument with Prometheus from **Week 7**
- 🐳 Docker Compose runs full stack by **Week 9**
- ⚡ Load testing with **k6**
- 🌍 Deploy on **Fly.io / Railway** in Week 10

---

## Phase 1 (Weeks 1–3): Core ML Service

Build the **Python microservice**.

### Deliverables
- DistilBERT-based fake news classifier
- Vector database (Qdrant) populated
- REST API endpoints:
  - `/predict`
  - `/embed`
  - `/search`

### Outcome
A fully functional ML backend that the Go gateway can call.

---

## Phase 2 (Weeks 4–5): RAG Pipeline

Implement **Retrieval-Augmented Generation (RAG)**.

### Flow


Input Claim
↓
Classifier (confidence check)
↓
If low confidence:
→ Vector Search (Qdrant)
→ Retrieve evidence
→ LLM generates explanation



### Outcome
- Evidence-backed responses
- Transparent decision-making

---

## Phase 3 (Weeks 6–8): Go API Gateway (MOST IMPORTANT)

This phase defines your **resume strength**.

### Features to Build

- JWT Authentication
- Redis Rate Limiting
- Circuit Breaker (timeout handling)
- Request Routing:
  - Fast path → classifier
  - Slow path → RAG pipeline
- Async Job Queue:
  - Go worker pool
  - Retry with exponential backoff
- Webhook callback system

### Outcome
Transforms project into a **production backend system**

---

## Phase 4 (Weeks 9–10): Deployment & Observability

### Deliverables

- Docker Compose (full stack)
- Metrics:
  - Prometheus
  - Grafana dashboards
  - OpenTelemetry tracing
- Load testing with k6
- Deployment:
  - Fly.io or Railway
- Public live URL

---

## Resume Positioning

### Core Strategy

Lead with:
> ✅ Go backend engineering  
Support with:
> ➕ ML pipeline  

---

## Suggested Resume Bullet Points

- Built a **Go API gateway** with JWT auth, Redis rate limiting, and fallback logic routing requests to a distributed Python ML pipeline  
- Implemented **end-to-end RAG pipeline** — DistilBERT classifier triggers vector search (Qdrant) + LLM explanation when confidence < 85%  
- Instrumented system with **Prometheus + OpenTelemetry**, achieving **200 req/s throughput** with p95 latency < 500ms under load (k6 tested)  
- Designed **async job queue** with Go worker pool and Redis backend, including retry logic and webhook callbacks  
- Deployed full stack (**Go + Python + Qdrant + Redis + Grafana**) using Docker Compose on Fly.io with live URL  

---

## Interview Talking Points

### Why Go for the gateway?
Go’s concurrency model (**goroutines + channels**) allows handling many concurrent requests efficiently, especially when calling slower Python services.

---

### Why RAG instead of a larger model?
- Provides **real, verifiable sources**
- Improves **transparency**
- Avoids reliance on outdated model weights

---

### Handling slow Python service?
- Circuit breaker pattern
- 3-second timeout
- Fallback responses
- Async job queue for delayed processing

---

### Future Improvements

- Replace DistilBERT with a more advanced model
- Add real-time streaming analysis (e.g., social media APIs)
- Implement feedback loop for improving vector DB

---

## Final Outcome

A **production-grade AI backend system** that demonstrates:

- Backend engineering (Go)
- Distributed systems design
- AI integration (RAG + LLM)
- Observability & performance engineering

---


