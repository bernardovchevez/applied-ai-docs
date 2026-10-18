# Localhost setup (clean path)

## Repos (siblings)

```text
cursor_workspace/
├── applied-ai-platform/
├── applied-ai-docs/      ← seed + catalog + publish
├── applied-ai-web/
└── applied-ai-slack/
```

## First-time bootstrap

### 1. Platform (Postgres + BFF)

```bash
cd applied-ai-platform
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Start Postgres per platform README / docker compose
cd platform/bff && ./run.sh --env localhost
```

Verify: `curl http://localhost:8000/health`

### 2. Document catalog

```bash
cd applied-ai-docs
cp .env.localhost.example .env.localhost
./run.sh
```

Open http://127.0.0.1:8010/

1. **Import seed library** (loads `seed/harbor-line/` into the catalog)
2. **Publish all pending** (optional: check **Run embed worker after publish**)
3. If you did not run the worker from the UI:

```bash
cd ../applied-ai-platform
python platform/pipelines/embed_worker.py
```

### 3. Slack (optional)

```bash
cd applied-ai-slack
npm run build && npm run start:localhost
```

## Day-to-day

- **Add / edit docs:** applied-ai-docs UI only → Save → Publish (+ worker)
- **Do not** edit `applied-ai-platform/data/lake/raw/` by hand unless debugging ingest
- **Seed files** live in `applied-ai-docs/seed/harbor-line/` (not in the platform repo)

## Dev fallback (no docs UI)

Copy seed from the docs repo into the lake and batch-ingest (rare; flag name is legacy):

```bash
cd applied-ai-platform
python platform/pipelines/ingest_batch.py --seed-from-synthetic --emit-events
python platform/pipelines/embed_worker.py
```

Requires sibling checkout: `applied-ai-docs/seed/harbor-line/` (see `DOCS_SEED_DIR` in platform `shared/config.py`).
