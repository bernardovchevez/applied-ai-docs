"""Emit document_ingested events (Kafka stub contract)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENT_TYPE = "document_ingested"
EVENT_VERSION = "1.0"


def doc_key_from_rel_path(rel_path: str) -> str:
    return Path(rel_path).stem


def build_publish_row(
    *,
    rel_path: str,
    file_name: str,
    content_hash: str,
    byte_size: int,
    sharepoint_path: str | None,
    doc_type: str | None,
    department: str | None,
    confidentiality: str | None,
    series: str | None,
    rights_tier: str | None,
    tags: list,
    territory_status: dict,
    clearance_territories: list,
) -> dict[str, Any]:
    return {
        "rel_path": rel_path,
        "file_name": file_name,
        "content_hash": content_hash,
        "byte_size": byte_size,
        "sharepoint_path": sharepoint_path,
        "doc_type": doc_type,
        "department": department,
        "confidentiality": confidentiality,
        "series": series,
        "rights_tier": rights_tier,
        "tags": json.dumps(tags or [], ensure_ascii=False),
        "territory_status": json.dumps(territory_status or {}, ensure_ascii=False),
        "clearance_territories": clearance_territories or [],
        "source_system": "applied-ai-docs",
    }


def build_event(
    row: dict[str, Any],
    *,
    raw_dir: Path,
    operation: str = "upsert",
    correlation_id: str | None = None,
) -> dict[str, Any]:
    rel_path = row["rel_path"]
    meta = {
        "tags": json.loads(row.get("tags") or "[]"),
        "territory_status": json.loads(row.get("territory_status") or "{}"),
        "clearance_territories": row.get("clearance_territories") or [],
    }
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": EVENT_TYPE,
        "event_version": EVENT_VERSION,
        "occurred_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "operation": operation,
        "document": {
            "doc_key": doc_key_from_rel_path(rel_path),
            "file_name": row["file_name"],
            "rel_path": rel_path,
            "content_hash": row["content_hash"],
            "content_uri": str((raw_dir / rel_path).resolve()),
            "byte_size": row.get("byte_size"),
            "series": row.get("series"),
            "doc_type": row.get("doc_type"),
            "department": row.get("department"),
            "confidentiality": row.get("confidentiality"),
            "sharepoint_path": row.get("sharepoint_path"),
            "rights_tier": row.get("rights_tier"),
            "source_system": row.get("source_system", "applied-ai-docs"),
        },
        "metadata": meta,
        "trace": {
            "correlation_id": correlation_id or f"docs-{datetime.now(timezone.utc):%Y%m%d}",
            "producer": "applied-ai-docs",
        },
    }


def write_event(
    event: dict[str, Any],
    events_dir: Path,
) -> Path:
    events_dir.mkdir(parents=True, exist_ok=True)
    doc_key = event["document"]["doc_key"]
    path = events_dir / f"{doc_key}.json"
    path.write_text(json.dumps(event, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
