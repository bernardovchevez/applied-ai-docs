"""Localhost and stage path configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

DOCS_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    base = DOCS_ROOT / ".env"
    if base.exists():
        load_dotenv(base, override=False)
    env_name = os.getenv("APP_ENV", "localhost")
    override = DOCS_ROOT / f".env.{env_name}"
    if override.exists():
        load_dotenv(override, override=True)


_load_env()

PLATFORM_ROOT = Path(
    os.getenv("PLATFORM_ROOT", DOCS_ROOT.parent / "applied-ai-platform")
).resolve()

LAKE_RAW_DIR = Path(
    os.getenv("LAKE_RAW_DIR", PLATFORM_ROOT / "data" / "lake" / "raw")
).resolve()
EVENTS_DIR = Path(
    os.getenv(
        "EVENTS_DIR",
        PLATFORM_ROOT / "data" / "lake" / "events" / "document_ingested",
    )
).resolve()

SEED_DIR = Path(
    os.getenv("SEED_DIR", DOCS_ROOT / "seed" / "harbor-line")
).resolve()
SEED_META = SEED_DIR / "sharepoint-meta.json"

DOCS_DB = Path(os.getenv("DOCS_DB", DOCS_ROOT / "data" / "catalog.sqlite")).resolve()
DOCS_BLOB_DIR = Path(os.getenv("DOCS_BLOB_DIR", DOCS_ROOT / "data" / "blobs")).resolve()
DOCS_PORT = int(os.getenv("DOCS_PORT", "8010"))

RUN_EMBED_WORKER = os.getenv("RUN_EMBED_WORKER", "").lower() in ("1", "true", "yes")
PLATFORM_PYTHON = os.getenv(
    "PLATFORM_PYTHON",
    str(PLATFORM_ROOT / ".venv" / "bin" / "python"),
)
