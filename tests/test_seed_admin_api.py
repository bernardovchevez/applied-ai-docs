"""Admin seed routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


def test_seed_from_library_route(docs_paths) -> None:
    init_db(docs_paths["db"])
    client = TestClient(app)
    resp = client.post("/admin/seed-from-library")
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1


def test_seed_from_synthetic_legacy_route(docs_paths) -> None:
    init_db(docs_paths["db"])
    client = TestClient(app)
    resp = client.post("/admin/seed-from-synthetic")
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1
