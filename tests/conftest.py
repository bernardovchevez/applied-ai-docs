"""Isolated catalog, lake, and events paths for pytest."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MINIMAL_SEED = FIXTURES / "minimal_seed"


@pytest.fixture
def docs_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point app modules at temp dirs (config is imported at load time)."""
    db = tmp_path / "catalog.sqlite"
    lake = tmp_path / "lake" / "raw"
    events = tmp_path / "events" / "document_ingested"
    blobs = tmp_path / "blobs"
    platform = tmp_path / "applied-ai-platform"
    platform.mkdir(parents=True)
    seed = MINIMAL_SEED

    paths = {
        "db": db,
        "lake": lake,
        "events": events,
        "blobs": blobs,
        "platform": platform,
        "seed": seed,
    }

    seed_meta = seed / "sharepoint-meta.json"

    for mod in (
        "app.config",
        "app.main",
        "app.publish",
        "app.crud",
        "app.seed",
    ):
        monkeypatch.setattr(f"{mod}.DOCS_DB", db, raising=False)
        monkeypatch.setattr(f"{mod}.DOCS_BLOB_DIR", blobs, raising=False)
        monkeypatch.setattr(f"{mod}.LAKE_RAW_DIR", lake, raising=False)
        monkeypatch.setattr(f"{mod}.EVENTS_DIR", events, raising=False)
        monkeypatch.setattr(f"{mod}.PLATFORM_ROOT", platform, raising=False)
        monkeypatch.setattr(f"{mod}.SEED_DIR", seed, raising=False)
        monkeypatch.setattr(f"{mod}.SEED_META", seed_meta, raising=False)

    return paths
