"""Import Harbor Line synthetic corpus into the docs catalog."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from app.config import DOCS_BLOB_DIR, DOCS_DB, SEED_DIR, SEED_META
from app.database import ensure_default_library, init_db, upsert_item
from app.rights import derive_rights_tier


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_meta_by_file() -> dict[str, dict]:
    if not SEED_META.exists():
        return {}
    data = json.loads(SEED_META.read_text(encoding="utf-8"))
    return {row["file_name"]: row for row in data.get("documents", []) if row.get("file_name")}


def seed_from_library(*, db_path: Path | None = None) -> dict:
    db_path = db_path or DOCS_DB
    init_db(db_path)
    library_id = ensure_default_library(db_path)

    if not SEED_DIR.exists():
        raise FileNotFoundError(
            f"Seed corpus not found at {SEED_DIR}. Clone applied-ai-docs with seed/harbor-line/."
        )

    meta_by_file = load_meta_by_file()
    DOCS_BLOB_DIR.mkdir(parents=True, exist_ok=True)

    imported = 0
    skipped = 0
    for src in sorted(SEED_DIR.rglob("*")):
        if not src.is_file():
            continue
        if src.suffix.lower() not in {".md", ".txt"}:
            continue
        if src.name == "sharepoint-meta.json":
            continue

        rel_path = str(src.relative_to(SEED_DIR))
        sp = meta_by_file.get(src.name, {})
        doc_type = sp.get("doc_type") or (
            src.parent.name if src.parent != SEED_DIR else "general"
        )
        text = src.read_text(encoding="utf-8")
        chash = _content_hash(text)

        item = upsert_item(
            db_path,
            library_id=library_id,
            file_name=src.name,
            rel_path=rel_path,
            content_hash=chash,
            sharepoint_path=sp.get("sharepoint_path"),
            doc_type=doc_type,
            department=sp.get("department"),
            confidentiality=sp.get("confidentiality"),
            series=sp.get("series"),
            rights_tier=derive_rights_tier(sp),
            tags=sp.get("tags") or [],
            territory_status=sp.get("territory_status") or {},
            clearance_territories=sp.get("clearance_territories") or [],
        )
        blob = DOCS_BLOB_DIR / f"{item.item_id}.md"
        shutil.copy2(src, blob)
        imported += 1

    return {
        "library_id": library_id,
        "imported": imported,
        "skipped": skipped,
        "seed_dir": str(SEED_DIR),
        "catalog_db": str(db_path),
    }


# Back-compat alias (deprecated route name).
seed_from_synthetic = seed_from_library
