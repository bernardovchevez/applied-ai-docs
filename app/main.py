"""FastAPI entrypoint for applied-ai-docs."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import (
    DOCS_DB,
    DOCS_PORT,
    DOCS_ROOT,
    EVENTS_DIR,
    LAKE_RAW_DIR,
    PLATFORM_ROOT,
    SYNTHETIC_DIR,
)
from app.crud import create_item, item_to_detail, update_item
from app.database import get_item, init_db, list_items
from app.publish import delete_and_unindex, publish_all_pending, publish_item
from app.schemas import ItemCreate, ItemUpdate
from app.seed import seed_from_synthetic

app = FastAPI(
    title="Applied AI Docs",
    description="SharePoint-style document catalog with publish to applied-ai-platform lake",
    version="0.1.0",
)

STATIC_DIR = DOCS_ROOT / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def _startup() -> None:
    init_db(DOCS_DB)


@app.get("/")
def home() -> FileResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, "static/index.html missing")
    return FileResponse(index)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "platform_root": str(PLATFORM_ROOT),
        "platform_root_exists": PLATFORM_ROOT.is_dir(),
        "synthetic_dir": str(SYNTHETIC_DIR),
        "synthetic_exists": SYNTHETIC_DIR.is_dir(),
        "lake_raw_dir": str(LAKE_RAW_DIR),
        "events_dir": str(EVENTS_DIR),
        "catalog_db": str(DOCS_DB),
    }


@app.post("/admin/seed-from-synthetic")
def admin_seed() -> dict:
    try:
        return seed_from_synthetic()
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/items")
def api_list_items() -> dict:
    items = [i.to_dict() for i in list_items(DOCS_DB)]
    pending = sum(1 for i in items if i.get("publish_pending"))
    return {"count": len(items), "publish_pending": pending, "items": items}


@app.get("/api/items/{item_id}")
def api_get_item(item_id: str, include_content: bool = True) -> dict:
    item = get_item(DOCS_DB, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return item_to_detail(item, include_content=include_content)


@app.post("/api/items")
def api_create_item(body: ItemCreate) -> dict:
    try:
        return create_item(body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.put("/api/items/{item_id}")
def api_update_item(item_id: str, body: ItemUpdate) -> dict:
    try:
        return update_item(item_id, body)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/items/{item_id}/publish")
def api_publish_item(item_id: str, run_worker: bool = False) -> dict:
    try:
        return publish_item(DOCS_DB, item_id, run_worker=run_worker)
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/admin/publish-all-pending")
def api_publish_all(run_worker: bool = False) -> dict:
    results = publish_all_pending(DOCS_DB, run_worker=run_worker)
    return {"published": len(results), "results": results}


@app.delete("/api/items/{item_id}")
def api_delete_item(item_id: str, run_worker: bool = False) -> dict:
    try:
        return delete_and_unindex(DOCS_DB, item_id, run_worker=run_worker)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=DOCS_PORT, reload=False)


if __name__ == "__main__":
    main()
