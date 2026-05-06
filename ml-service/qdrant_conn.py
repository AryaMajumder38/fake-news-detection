"""Build QdrantClient from env: Cloud (QDRANT_URL) or local Compose (QDRANT_HOST)."""

from __future__ import annotations

import os

from qdrant_client import QdrantClient


def get_qdrant_client() -> QdrantClient:
    url = (os.getenv("QDRANT_URL") or "").strip()
    if url:
        api_key = (os.getenv("QDRANT_API_KEY") or "").strip()
        kwargs: dict = {"url": url}
        if api_key:
            kwargs["api_key"] = api_key
        return QdrantClient(**kwargs)
    host = os.getenv("QDRANT_HOST", "qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    local_key = (os.getenv("QDRANT_LOCAL_API_KEY") or "").strip()
    if local_key:
        return QdrantClient(host=host, port=port, api_key=local_key)
    return QdrantClient(host=host, port=port)
