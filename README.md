# applied-ai-docs

SharePoint-style **document catalog** for the Applied AI Platform. **Source of truth for document bodies and library metadata**; [applied-ai-platform](https://github.com/bernardovchevez/applied-ai-platform) owns pgvector, RAG, and agents **after Publish**.

Publishes to `data/lake/raw/` and emits `document_ingested` events for `embed_worker.py`. See platform [document-corpus-sources.md](https://github.com/bernardovchevez/applied-ai-platform/blob/main/docs/document-corpus-sources.md).

```
applied-ai-platform/   ← RAG, BFF, pgvector, embed worker
applied-ai-docs/       ← this repo (catalog + publish)
applied-ai-web/        ← chat UI
applied-ai-slack/      ← Slack ops UI
```

## Local setup

### 1. Prerequisites

- `applied-ai-platform` cloned as a sibling directory (default `../applied-ai-platform`)
- Python 3.11+
- Platform Postgres + pgvector when you run the embed worker (see platform README)

### 2. Configure

```bash
cd applied-ai-docs
cp .env.localhost.example .env.localhost
# Confirm PLATFORM_ROOT points at your platform checkout
```

### 3. Install and run

```bash
chmod +x run.sh
./run.sh
```

Open [http://127.0.0.1:8010/](http://127.0.0.1:8010/)

### 4. Confirm locally (UI)

1. Click **Seed from synthetic** (imports `data/synthetic/` into the catalog), or **New document** to create one.
2. **Open** a row to view/edit markdown and metadata; **Save changes**, then **Publish to AI index** (or use **Publish all pending** on the list).
3. On the platform repo, index changes:

```bash
cd ../applied-ai-platform
python platform/pipelines/embed_worker.py
# Or process one event:
# python platform/pipelines/embed_worker.py --event data/lake/events/document_ingested/music-clearance-emea.json
```

4. With BFF + Slack/web running, ask a question that cites the published files.

### 5. Smoke script (API)

With `./run.sh` in another terminal:

```bash
chmod +x scripts/smoke_local.sh
./scripts/smoke_local.sh
```

## API (MVP)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Paths and platform/synthetic presence |
| POST | `/admin/seed-from-synthetic` | Import synthetic corpus into catalog |
| GET | `/api/items` | List catalog items |
| GET | `/api/items/{item_id}` | Item metadata + markdown body |
| POST | `/api/items` | Create document (catalog + blob) |
| PUT | `/api/items/{item_id}` | Update metadata and/or body (marks publish pending) |
| POST | `/api/items/{item_id}/publish` | Publish one item to lake + event |
| POST | `/api/admin/publish-all-pending` | Publish all changed items |
| DELETE | `/api/items/{item_id}` | Remove catalog item, lake file, and emit index delete event |

Optional query: `?run_worker=true` on publish routes if `RUN_EMBED_WORKER=true` and platform venv Python is configured.

## Environment

| Variable | Default |
|----------|---------|
| `PLATFORM_ROOT` | `../applied-ai-platform` |
| `LAKE_RAW_DIR` | `{PLATFORM_ROOT}/data/lake/raw` |
| `EVENTS_DIR` | `{PLATFORM_ROOT}/data/lake/events/document_ingested` |
| `DOCS_PORT` | `8010` |
| `DOCS_DB` | `data/catalog.sqlite` |

Do not commit `.env.localhost` or `data/catalog.sqlite`.
