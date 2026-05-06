#!/usr/bin/env bash
# Upload a local collection snapshot to Qdrant Cloud (recover from uploaded file).
# Run on your machine: ./scripts/upload_qdrant_snapshot.sh
#
# Credentials: either set QDRANT_URL and QDRANT_API_KEY, or keep them in repo-root ./need
# (lines like "API KEy : ..." and "cluster endpoint : https://...").
#
# If you see "Could not resolve host" but the URL is correct (must include "sa-east-1-0"
# style slug from the Cloud UI — not "sa-east-1" alone), your Mac DNS may be broken or
# blocking Qdrant. This script falls back to resolving via dig @8.8.8.8 and curl --resolve.
# Override with PUBLIC_DNS_FOR_LOOKUP (default 8.8.8.8). Set SKIP_DNS_FALLBACK=1 to disable.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SNAPSHOT="${1:-${SNAPSHOT_PATH:-$REPO_ROOT/knowledge_base.snapshot}}"
NEED="${NEED_FILE:-$REPO_ROOT/need}"
COLLECTION="${QDRANT_COLLECTION:-knowledge_base}"

if [[ ! -f "$SNAPSHOT" ]]; then
  echo "Snapshot not found: $SNAPSHOT" >&2
  exit 1
fi

if [[ -n "${QDRANT_API_KEY:-}" && -n "${QDRANT_URL:-}" ]]; then
  BASE="${QDRANT_URL%/}"
else
  if [[ ! -f "$NEED" ]]; then
    echo "Set QDRANT_URL + QDRANT_API_KEY or provide $NEED" >&2
    exit 1
  fi
  QDRANT_API_KEY="$(grep -E '^API KEy' "$NEED" | sed -E 's/^API KEy[[:space:]]*:[[:space:]]*//' | tr -d '\r')"
  BASE="$(grep -i 'cluster endpoint' "$NEED" | sed -E 's/.*:[[:space:]]*//' | tr -d '\r' | tr -d ' ')"
  BASE="${BASE%/}"
fi

if [[ -z "${QDRANT_API_KEY:-}" || -z "$BASE" ]]; then
  echo "Could not resolve API key or cluster URL." >&2
  exit 1
fi

# Qdrant Cloud REST commonly uses :6333 on the HTTPS host
if [[ "$BASE" != *":6333" ]]; then
  BASE="${BASE}:6333"
fi

URL="${BASE}/collections/${COLLECTION}/snapshots/upload?priority=snapshot"

if [[ "$BASE" =~ ^https://([^/:]+)(:([0-9]+))?$ ]]; then
  QHOST="${BASH_REMATCH[1]}"
  QPORT="${BASH_REMATCH[3]:-6333}"
else
  echo "Could not parse host/port from BASE: $BASE" >&2
  exit 1
fi

CURL_RESOLVE=()
PUBLIC_DNS="${PUBLIC_DNS_FOR_LOOKUP:-8.8.8.8}"
if [[ "${SKIP_DNS_FALLBACK:-0}" != "1" ]] && command -v dig >/dev/null 2>&1; then
  FALLBACK_IP="$(dig +short "$QHOST" @"$PUBLIC_DNS" | awk '/^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/{print; exit}')"
  if [[ -n "$FALLBACK_IP" ]]; then
    CURL_RESOLVE=(--resolve "${QHOST}:${QPORT}:${FALLBACK_IP}")
    echo "Using DNS fallback (${PUBLIC_DNS} → ${FALLBACK_IP}) for ${QHOST}:${QPORT}"
  fi
fi

echo "Uploading $(basename "$SNAPSHOT") to ${BASE} collection=${COLLECTION} ..."

RESP="$(curl -sS --max-time 600 "${CURL_RESOLVE[@]}" -X POST "$URL" \
  -H "api-key: ${QDRANT_API_KEY}" \
  -F "snapshot=@${SNAPSHOT}")"

echo "$RESP"

if echo "$RESP" | grep -qi forbidden; then
  cat >&2 <<EOF

403 forbidden usually means one of:
  • Cluster → Configure → Client IP restrictions blocks your current public IP (add it or widen range).
  • API key is read-only or lacks write permission — create a new key with write access in Cloud.
  • Wrong cluster URL vs key (key from another cluster/account).

Sanity check: GET ${BASE}/collections with the same api-key header (needs read access).
EOF
fi

echo ""
