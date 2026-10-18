"""Publish catalog items to platform lake raw + document_ingested events."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from app.config import (
    DOCS_BLOB_DIR,
    EVENTS_DIR,
    LAKE_RAW_DIR,
    PLATFORM_PYTHON,
    PLATFORM_ROOT,
    RUN_EMBED_WORKER,
)
from app.database import ItemRecord, get_item, mark_published
from app.events import build_event, build_publish_row, write_event


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def blob_path_for_item(item_id: str) -> Path:
    return DOCS_BLOB_DIR / f"{item_id}.md"


def read_item_content(item: ItemRecord) -> str:
    path = blob_path_for_item(item.item_id)
    if not path.exists():
        raise FileNotFoundError(f"Blob missing for item {item.item_id}: {path}")
    return path.read_text(encoding="utf-8")


def remove_sharepoint_meta_entries(lake_raw: Path, file_names: list[str]) -> None:
    if not file_names:
        return
    meta_path = lake_raw / "sharepoint-meta.json"
    if not meta_path.exists():
        return
    existing = json.loads(meta_path.read_text(encoding="utf-8"))
    drop = set(file_names)
    existing["documents"] = [
        d for d in existing.get("documents", []) if d.get("file_name") not in drop
    ]
    meta_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sync_sharepoint_meta(lake_raw: Path, items: list[ItemRecord]) -> None:
    """Merge catalog metadata into lake sharepoint-meta.json for embed_worker."""
    meta_path = lake_raw / "sharepoint-meta.json"
    existing: dict = {"library": "Harbor Media Operations", "documents": []}
    if meta_path.exists():
        existing = json.loads(meta_path.read_text(encoding="utf-8"))

    by_name = {d["file_name"]: d for d in existing.get("documents", []) if d.get("file_name")}
    for item in items:
        entry = {
            "file_name": item.file_name,
            "sharepoint_path": item.sharepoint_path,
            "department": item.department,
            "confidentiality": item.confidentiality,
            "series": item.series,
            "doc_type": item.doc_type,
            "tags": item.tags,
        }
        if item.territory_status:
            entry["territory_status"] = item.territory_status
        if item.clearance_territories:
            entry["clearance_territories"] = item.clearance_territories
        by_name[item.file_name] = entry

    existing["documents"] = sorted(by_name.values(), key=lambda d: d["file_name"])
    meta_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def publish_item(
    db_path: Path,
    item_id: str,
    *,
    run_worker: bool | None = None,
) -> dict:
    item = get_item(db_path, item_id)
    if not item:
        raise ValueError(f"Unknown item_id: {item_id}")

    text = read_item_content(item)
    chash = content_hash(text)
    dest = LAKE_RAW_DIR / item.rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")

    sync_sharepoint_meta(LAKE_RAW_DIR, [item])

    row = build_publish_row(
        rel_path=item.rel_path,
        file_name=item.file_name,
        content_hash=chash,
        byte_size=len(text.encode("utf-8")),
        sharepoint_path=item.sharepoint_path,
        doc_type=item.doc_type,
        department=item.department,
        confidentiality=item.confidentiality,
        series=item.series,
        rights_tier=item.rights_tier,
        tags=item.tags,
        territory_status=item.territory_status,
        clearance_territories=item.clearance_territories,
    )
    event = build_event(row, raw_dir=LAKE_RAW_DIR, correlation_id=f"publish-{item_id[:8]}")
    event_path = write_event(event, EVENTS_DIR)

    mark_published(db_path, item_id, chash)

    worker_result = None
    should_run = RUN_EMBED_WORKER if run_worker is None else run_worker
    if should_run:
        worker_result = run_embed_worker(event_path)

    return {
        "item_id": item_id,
        "rel_path": item.rel_path,
        "content_hash": chash,
        "lake_path": str(dest),
        "event_path": str(event_path),
        "doc_key": event["document"]["doc_key"],
        "embed_worker": worker_result,
    }


def run_embed_worker(event_path: Path) -> dict:
    script = PLATFORM_ROOT / "platform" / "pipelines" / "embed_worker.py"
    python = Path(PLATFORM_PYTHON)
    if not script.exists():
        return {"status": "skipped", "reason": f"missing script: {script}"}
    if not python.exists():
        return {"status": "skipped", "reason": f"missing python: {python}"}

    proc = subprocess.run(
        [str(python), str(script), "--event", str(event_path)],
        cwd=str(PLATFORM_ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "status": "ok" if proc.returncode == 0 else "error",
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:] if proc.stdout else "",
        "stderr": proc.stderr[-2000:] if proc.stderr else "",
    }


def delete_and_unindex(
    db_path: Path,
    item_id: str,
    *,
    run_worker: bool | None = None,
) -> dict:
    from app.database import delete_item

    item = get_item(db_path, item_id)
    if not item:
        raise ValueError(f"Unknown item_id: {item_id}")

    event_path = None
    worker_result = None
    lake_path = LAKE_RAW_DIR / item.rel_path

    if item.published_content_hash or lake_path.exists():
        row = build_publish_row(
            rel_path=item.rel_path,
            file_name=item.file_name,
            content_hash=item.published_content_hash or item.content_hash or "",
            byte_size=0,
            sharepoint_path=item.sharepoint_path,
            doc_type=item.doc_type,
            department=item.department,
            confidentiality=item.confidentiality,
            series=item.series,
            rights_tier=item.rights_tier,
            tags=item.tags,
            territory_status=item.territory_status,
            clearance_territories=item.clearance_territories,
        )
        event = build_event(
            row,
            raw_dir=LAKE_RAW_DIR,
            operation="delete",
            correlation_id=f"delete-{item_id[:8]}",
        )
        event_path = write_event(event, EVENTS_DIR)
        should_run = RUN_EMBED_WORKER if run_worker is None else run_worker
        if should_run:
            worker_result = run_embed_worker(event_path)

    if lake_path.exists():
        lake_path.unlink()
    remove_sharepoint_meta_entries(LAKE_RAW_DIR, [item.file_name])
    blob = blob_path_for_item(item_id)
    if blob.exists():
        blob.unlink()
    delete_item(db_path, item_id)

    return {
        "item_id": item_id,
        "rel_path": item.rel_path,
        "deleted_from_catalog": True,
        "event_path": str(event_path) if event_path else None,
        "doc_key": Path(item.rel_path).stem,
        "embed_worker": worker_result,
    }


def publish_all_pending(db_path: Path, *, run_worker: bool = False) -> list[dict]:
    from app.database import list_items

    results: list[dict] = []
    for item in list_items(db_path):
        if item.content_hash == item.published_content_hash and item.published_content_hash:
            continue
        results.append(publish_item(db_path, item.item_id, run_worker=run_worker))
    return results
