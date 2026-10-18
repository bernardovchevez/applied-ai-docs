#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -f .env.localhost ]]; then
  cp .env.localhost.example .env.localhost
  echo "Created .env.localhost from example. Edit PLATFORM_ROOT if needed."
fi

export APP_ENV=localhost
set -a
# shellcheck disable=SC1091
source .env.localhost
set +a

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${DOCS_PORT:-8010}"
