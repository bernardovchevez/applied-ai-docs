"""Create, read, update catalog items and blob content."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import DOCS_BLOB_DIR, DOCS_DB
from app.database import (
    ItemRecord,
    connect,
    ensure_default_library,
    get_item,
    upsert_item,
)
from app.publish import blob_path_for_item, content_hash
from app.schemas import ItemCreate, ItemUpdate


def read_content(item_id: str) -> str:
    path = blob_path_for_item(item_id)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_content(item_id: str, text: str) -> None:
    DOCS_BLOB_DIR.mkdir(parents=True, exist_ok=True)
    blob_path_for_item(item_id).write_text(text, encoding="utf-8")


def item_to_detail(item: ItemRecord, *, include_content: bool = True) -> dict:
    data = item.to_dict()
    if include_content:
        data["content"] = read_content(item.item_id)
    return data


def create_item(payload: ItemCreate, db_path: Path | None = None) -> dict:
    db_path = db_path or DOCS_DB
    library_id = ensure_default_library(db_path)

    with connect(db_path) as conn:
        clash = conn.execute(
            "SELECT item_id FROM items WHERE rel_path = ?", (payload.rel_path,)
        ).fetchone()
        if clash:
            raise ValueError(f"rel_path already exists: {payload.rel_path}")

    chash = content_hash(payload.content)
    item = upsert_item(
        db_path,
        library_id=library_id,
        file_name=payload.file_name,
        rel_path=payload.rel_path,
        content_hash=chash,
        sharepoint_path=payload.sharepoint_path,
        doc_type=payload.doc_type,
        department=payload.department,
        confidentiality=payload.confidentiality,
        series=payload.series,
        rights_tier=payload.rights_tier,
        tags=payload.tags,
        territory_status=payload.territory_status,
        clearance_territories=payload.clearance_territories,
    )
    write_content(item.item_id, payload.content)
    return item_to_detail(item)


def update_item(item_id: str, payload: ItemUpdate, db_path: Path | None = None) -> dict:
    db_path = db_path or DOCS_DB
    item = get_item(db_path, item_id)
    if not item:
        raise LookupError(f"Unknown item_id: {item_id}")

    new_rel = payload.rel_path if payload.rel_path is not None else item.rel_path
    new_name = payload.file_name if payload.file_name is not None else item.file_name

    if new_rel != item.rel_path:
        with connect(db_path) as conn:
            clash = conn.execute(
                "SELECT item_id FROM items WHERE rel_path = ? AND item_id != ?",
                (new_rel, item_id),
            ).fetchone()
            if clash:
                raise ValueError(f"rel_path already in use: {new_rel}")

    if payload.content is not None:
        write_content(item_id, payload.content)
        chash = content_hash(payload.content)
    else:
        chash = item.content_hash or content_hash(read_content(item_id))

    tags = payload.tags if payload.tags is not None else item.tags
    territory = (
        payload.territory_status
        if payload.territory_status is not None
        else item.territory_status
    )
    clearance = (
        payload.clearance_territories
        if payload.clearance_territories is not None
        else item.clearance_territories
    )

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    tags_json = json.dumps(tags, ensure_ascii=False)
    territory_json = json.dumps(territory, ensure_ascii=False)
    clearance_json = json.dumps(clearance, ensure_ascii=False)

    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE items SET
              file_name = ?, rel_path = ?, sharepoint_path = ?, doc_type = ?,
              department = ?, confidentiality = ?, series = ?, rights_tier = ?,
              tags_json = ?, territory_status_json = ?, clearance_territories_json = ?,
              content_hash = ?, updated_at = ?
            WHERE item_id = ?
            """,
            (
                new_name,
                new_rel,
                payload.sharepoint_path
                if payload.sharepoint_path is not None
                else item.sharepoint_path,
                payload.doc_type if payload.doc_type is not None else item.doc_type,
                payload.department if payload.department is not None else item.department,
                payload.confidentiality
                if payload.confidentiality is not None
                else item.confidentiality,
                payload.series if payload.series is not None else item.series,
                payload.rights_tier
                if payload.rights_tier is not None
                else item.rights_tier,
                tags_json,
                territory_json,
                clearance_json,
                chash,
                now,
                item_id,
            ),
        )
        conn.commit()

    updated = get_item(db_path, item_id)
    assert updated
    return item_to_detail(updated)
