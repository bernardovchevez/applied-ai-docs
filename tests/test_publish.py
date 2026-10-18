"""Publish pipeline: catalog blob → lake raw + document_ingested event."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.crud import create_item
from app.database import get_item, init_db
from app.main import app
from app.publish import delete_and_unindex, publish_item
from app.schemas import ItemCreate


def _create_demo_item(docs_paths) -> str:
    init_db(docs_paths["db"])
    detail = create_item(
        ItemCreate(
            file_name="demo-clearance.md",
            rel_path="rights/demo-clearance.md",
            content="# Demo\n\nEMEA clearance note.",
            department="rights",
            doc_type="memo",
        ),
        db_path=docs_paths["db"],
    )
    return detail["item_id"]


def test_publish_writes_lake_file_and_event(docs_paths) -> None:
    item_id = _create_demo_item(docs_paths)
    result = publish_item(docs_paths["db"], item_id, run_worker=False)

    lake_file = docs_paths["lake"] / "rights/demo-clearance.md"
    assert lake_file.exists()
    assert "EMEA" in lake_file.read_text(encoding="utf-8")
    assert result["doc_key"] == "demo-clearance"

    event_path = docs_paths["events"] / "demo-clearance.json"
    assert event_path.exists()
    event = json.loads(event_path.read_text(encoding="utf-8"))
    assert event["operation"] == "upsert"
    assert event["document"]["doc_key"] == "demo-clearance"
    assert event["document"]["content_hash"] == result["content_hash"]

    item = get_item(docs_paths["db"], item_id)
    assert item is not None
    assert item.content_hash == item.published_content_hash


def test_publish_api_endpoint(docs_paths) -> None:
    item_id = _create_demo_item(docs_paths)
    client = TestClient(app)
    resp = client.post(f"/api/items/{item_id}/publish?run_worker=false")
    assert resp.status_code == 200
    assert resp.json()["lake_path"].endswith("rights/demo-clearance.md")


def test_delete_emits_delete_event_and_removes_lake_file(docs_paths) -> None:
    item_id = _create_demo_item(docs_paths)
    publish_item(docs_paths["db"], item_id, run_worker=False)
    lake_file = docs_paths["lake"] / "rights/demo-clearance.md"
    assert lake_file.exists()

    result = delete_and_unindex(docs_paths["db"], item_id, run_worker=False)
    assert result["deleted_from_catalog"] is True
    assert not lake_file.exists()
    assert get_item(docs_paths["db"], item_id) is None

    event_path = docs_paths["events"] / "demo-clearance.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    assert event["operation"] == "delete"
