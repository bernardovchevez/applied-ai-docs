#!/usr/bin/env bash
# Quick smoke test (docs API must be running on DOCS_PORT).
set -euo pipefail
PORT="${DOCS_PORT:-8010}"
BASE="http://127.0.0.1:${PORT}"

echo "== health =="
curl -sf "${BASE}/health" | python3 -m json.tool

echo "== seed =="
curl -sf -X POST "${BASE}/admin/seed-from-library" | python3 -m json.tool

echo "== items (first publish pending count) =="
curl -sf "${BASE}/api/items" | python3 -m json.tool | head -40

echo "Smoke OK. Open ${BASE}/ in a browser, then publish and run embed_worker on the platform."
