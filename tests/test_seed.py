"""Seed import from harbor-line pack."""

from __future__ import annotations

from app.database import init_db, list_items
from app.seed import seed_from_library


def test_seed_from_minimal_pack(docs_paths) -> None:
    db = docs_paths["db"]
    init_db(db)
    result = seed_from_library(db_path=db)
    assert result["imported"] == 1
    assert result["skipped"] == 0
    items = list_items(db)
    assert len(items) == 1
    assert items[0].file_name == "demo-clearance.md"
    assert items[0].rel_path == "rights/demo-clearance.md"
    assert (docs_paths["blobs"] / f"{items[0].item_id}.md").exists()
