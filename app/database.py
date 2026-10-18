"""SQLite catalog for SharePoint-style document items."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS libraries (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS items (
  item_id TEXT PRIMARY KEY,
  library_id TEXT NOT NULL,
  file_name TEXT NOT NULL,
  rel_path TEXT NOT NULL,
  sharepoint_path TEXT,
  doc_type TEXT,
  department TEXT,
  confidentiality TEXT,
  series TEXT,
  rights_tier TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  territory_status_json TEXT NOT NULL DEFAULT '{}',
  clearance_territories_json TEXT NOT NULL DEFAULT '[]',
  content_hash TEXT,
  published_content_hash TEXT,
  published_at TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (library_id) REFERENCES libraries(id)
);

CREATE INDEX IF NOT EXISTS idx_items_library ON items(library_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_items_rel_path ON items(rel_path);
"""


@dataclass
class ItemRecord:
    item_id: str
    library_id: str
    file_name: str
    rel_path: str
    sharepoint_path: str | None
    doc_type: str | None
    department: str | None
    confidentiality: str | None
    series: str | None
    rights_tier: str | None
    tags: list
    territory_status: dict
    clearance_territories: list
    content_hash: str | None
    published_content_hash: str | None
    published_at: str | None
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "library_id": self.library_id,
            "file_name": self.file_name,
            "rel_path": self.rel_path,
            "sharepoint_path": self.sharepoint_path,
            "doc_type": self.doc_type,
            "department": self.department,
            "confidentiality": self.confidentiality,
            "series": self.series,
            "rights_tier": self.rights_tier,
            "tags": self.tags,
            "territory_status": self.territory_status,
            "clearance_territories": self.clearance_territories,
            "content_hash": self.content_hash,
            "published_content_hash": self.published_content_hash,
            "published_at": self.published_at,
            "updated_at": self.updated_at,
            "publish_pending": self.content_hash != self.published_content_hash,
        }


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    ensure_default_library(db_path)


def ensure_default_library(db_path: Path) -> str:
    lib_id = "harbor-line-default"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM libraries WHERE slug = ?", ("harbor-line",)
        ).fetchone()
        if row:
            return row[0]
        conn.execute(
            "INSERT INTO libraries (id, name, slug) VALUES (?, ?, ?)",
            (lib_id, "Harbor Line Media Ops", "harbor-line"),
        )
        conn.commit()
    return lib_id


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _row_to_item(row: sqlite3.Row) -> ItemRecord:
    return ItemRecord(
        item_id=row["item_id"],
        library_id=row["library_id"],
        file_name=row["file_name"],
        rel_path=row["rel_path"],
        sharepoint_path=row["sharepoint_path"],
        doc_type=row["doc_type"],
        department=row["department"],
        confidentiality=row["confidentiality"],
        series=row["series"],
        rights_tier=row["rights_tier"],
        tags=json.loads(row["tags_json"] or "[]"),
        territory_status=json.loads(row["territory_status_json"] or "{}"),
        clearance_territories=json.loads(row["clearance_territories_json"] or "[]"),
        content_hash=row["content_hash"],
        published_content_hash=row["published_content_hash"],
        published_at=row["published_at"],
        updated_at=row["updated_at"],
    )


def list_items(db_path: Path, library_id: str | None = None) -> list[ItemRecord]:
    with connect(db_path) as conn:
        if library_id:
            rows = conn.execute(
                "SELECT * FROM items WHERE library_id = ? ORDER BY rel_path",
                (library_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM items ORDER BY rel_path").fetchall()
    return [_row_to_item(r) for r in rows]


def get_item(db_path: Path, item_id: str) -> ItemRecord | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
    return _row_to_item(row) if row else None


def upsert_item(
    db_path: Path,
    *,
    library_id: str,
    file_name: str,
    rel_path: str,
    content_hash: str,
    sharepoint_path: str | None = None,
    doc_type: str | None = None,
    department: str | None = None,
    confidentiality: str | None = None,
    series: str | None = None,
    rights_tier: str | None = None,
    tags: list | None = None,
    territory_status: dict | None = None,
    clearance_territories: list | None = None,
    item_id: str | None = None,
) -> ItemRecord:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    item_id = item_id or str(uuid.uuid4())
    tags_json = json.dumps(tags or [], ensure_ascii=False)
    territory_json = json.dumps(territory_status or {}, ensure_ascii=False)
    clearance_json = json.dumps(clearance_territories or [], ensure_ascii=False)

    with connect(db_path) as conn:
        existing = conn.execute(
            "SELECT item_id, published_content_hash FROM items WHERE rel_path = ?",
            (rel_path,),
        ).fetchone()
        if existing:
            item_id = existing["item_id"]
            published_hash = existing["published_content_hash"]
            conn.execute(
                """
                UPDATE items SET
                  file_name = ?, sharepoint_path = ?, doc_type = ?, department = ?,
                  confidentiality = ?, series = ?, rights_tier = ?,
                  tags_json = ?, territory_status_json = ?, clearance_territories_json = ?,
                  content_hash = ?, updated_at = ?
                WHERE item_id = ?
                """,
                (
                    file_name,
                    sharepoint_path,
                    doc_type,
                    department,
                    confidentiality,
                    series,
                    rights_tier,
                    tags_json,
                    territory_json,
                    clearance_json,
                    content_hash,
                    now,
                    item_id,
                ),
            )
        else:
            published_hash = None
            conn.execute(
                """
                INSERT INTO items (
                  item_id, library_id, file_name, rel_path, sharepoint_path,
                  doc_type, department, confidentiality, series, rights_tier,
                  tags_json, territory_status_json, clearance_territories_json,
                  content_hash, published_content_hash, published_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    library_id,
                    file_name,
                    rel_path,
                    sharepoint_path,
                    doc_type,
                    department,
                    confidentiality,
                    series,
                    rights_tier,
                    tags_json,
                    territory_json,
                    clearance_json,
                    content_hash,
                    published_hash,
                    None,
                    now,
                ),
            )
        conn.commit()
        row = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
    return _row_to_item(row)


def delete_item(db_path: Path, item_id: str) -> bool:
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0


def mark_published(db_path: Path, item_id: str, content_hash: str) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE items SET published_content_hash = ?, published_at = ?, updated_at = ?
            WHERE item_id = ?
            """,
            (content_hash, now, now, item_id),
        )
        conn.commit()
