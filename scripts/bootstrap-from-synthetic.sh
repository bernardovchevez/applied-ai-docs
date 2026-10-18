#!/usr/bin/env bash
# One-time dev bootstrap: import synthetic seed into docs catalog (does not publish).
set -euo pipefail
PORT="${DOCS_PORT:-8010}"
curl -sf -X POST "http://127.0.0.1:${PORT}/admin/seed-from-synthetic" | python3 -m json.tool
echo "Seed complete. Publish from http://127.0.0.1:${PORT}/ then run embed_worker on the platform."
