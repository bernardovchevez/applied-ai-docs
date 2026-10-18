"""Request/response models for document CRUD."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ItemCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=200)
    rel_path: str = Field(min_length=1, max_length=400)
    content: str = Field(min_length=1)
    sharepoint_path: str | None = None
    doc_type: str | None = None
    department: str | None = None
    confidentiality: str | None = "internal"
    series: str | None = "Harbor Line"
    rights_tier: str | None = None
    tags: list[str] = Field(default_factory=list)
    territory_status: dict = Field(default_factory=dict)
    clearance_territories: list = Field(default_factory=list)

    @field_validator("rel_path")
    @classmethod
    def validate_rel_path(cls, v: str) -> str:
        v = v.strip().replace("\\", "/")
        if ".." in v or v.startswith("/"):
            raise ValueError("rel_path must be a relative path without '..'")
        lower = v.lower()
        if not (lower.endswith(".md") or lower.endswith(".txt")):
            raise ValueError("rel_path must end with .md or .txt")
        return v

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        v = v.strip()
        if "/" in v or "\\" in v:
            raise ValueError("file_name must not contain path separators")
        return v


class ItemUpdate(BaseModel):
    file_name: str | None = None
    rel_path: str | None = None
    content: str | None = None
    sharepoint_path: str | None = None
    doc_type: str | None = None
    department: str | None = None
    confidentiality: str | None = None
    series: str | None = None
    rights_tier: str | None = None
    tags: list[str] | None = None
    territory_status: dict | None = None
    clearance_territories: list | None = None

    @field_validator("rel_path")
    @classmethod
    def validate_rel_path(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().replace("\\", "/")
        if ".." in v or v.startswith("/"):
            raise ValueError("rel_path must be a relative path without '..'")
        lower = v.lower()
        if not (lower.endswith(".md") or lower.endswith(".txt")):
            raise ValueError("rel_path must end with .md or .txt")
        return v
