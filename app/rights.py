"""Rights tier derivation (aligned with applied-ai-platform/stores/corpus.py)."""

from __future__ import annotations


def derive_rights_tier(meta: dict) -> str | None:
    doc_type = meta.get("doc_type")
    if doc_type != "rights_clearance":
        return None
    tags = [t.lower() for t in meta.get("tags") or []]
    territory_status = meta.get("territory_status") or {}
    if isinstance(territory_status, dict):
        values = {str(v).lower() for v in territory_status.values()}
        if "excluded" in values:
            return "excluded"
    if "excluded" in tags:
        return "excluded"
    if "pending" in tags:
        return "pending"
    return "cleared"
