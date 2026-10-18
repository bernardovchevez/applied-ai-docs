"""Health and catalog list API smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


def test_health_reports_paths(docs_paths) -> None:
    init_db(docs_paths["db"])
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["seed_exists"] is True
    assert body["platform_root_exists"] is True
    assert docs_paths["seed"].name in body["seed_dir"]


def test_list_items_empty_catalog(docs_paths) -> None:
    init_db(docs_paths["db"])
    client = TestClient(app)
    resp = client.get("/api/items")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["publish_pending"] == 0
