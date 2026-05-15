#!/bin/bash
# Docker container entrypoint.
# Starts OpenSearch (if installed), waits for it, then starts the gateway.

set -euo pipefail

OPENSEARCH_BIN="/usr/share/opensearch/bin/opensearch"
OPENSEARCH_TIMEOUT=120   # seconds to wait for OpenSearch before giving up
GATEWAY_WORKERS=${UVICORN_WORKERS:-2}

# ---------------------------------------------------------------------------
# OpenSearch (optional – gateway continues without it)
# ---------------------------------------------------------------------------
if [ -x "$OPENSEARCH_BIN" ]; then
    echo "[startup] Starting OpenSearch..."
    su - opensearch -c "$OPENSEARCH_BIN -d -p /tmp/opensearch.pid" || true

    echo "[startup] Waiting for OpenSearch (timeout ${OPENSEARCH_TIMEOUT}s)..."
    elapsed=0
    while ! curl -sf http://localhost:9200/_cluster/health > /dev/null 2>&1; do
        if [ "$elapsed" -ge "$OPENSEARCH_TIMEOUT" ]; then
            echo "[startup] WARNING: OpenSearch did not become ready within ${OPENSEARCH_TIMEOUT}s – continuing without it."
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done

    if curl -sf http://localhost:9200/_cluster/health > /dev/null 2>&1; then
        echo "[startup] OpenSearch is ready."
    fi
else
    echo "[startup] OpenSearch not found – skipping (logging will be disabled)."
fi

# ---------------------------------------------------------------------------
# ML Inference Gateway
# ---------------------------------------------------------------------------
echo "[startup] Starting ML Inference Gateway (workers=$GATEWAY_WORKERS)..."

# In production never use --reload; use multiple workers for throughput.
exec uvicorn main:app \
    --host "${GATEWAY_HOST:-0.0.0.0}" \
    --port "${GATEWAY_PORT:-8000}" \
    --workers "$GATEWAY_WORKERS" \
    --log-level info \
    --access-log
