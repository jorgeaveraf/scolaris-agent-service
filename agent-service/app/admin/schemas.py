from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    id: UUID
    filename: str
    status: str
    size_bytes: int = Field(..., ge=0)
    area: str | None = None
    role: str | None = None
    vigencia: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    content_type: str | None = None
    checksum: str
    doc_id: str | None = None
    chunks_count: int | None = None
    last_ingested_at: datetime | None = None
    error_msg: str | None = None


class DocumentsListResponse(BaseModel):
    total: int
    items: list[DocumentSummary]


class ChunkItem(BaseModel):
    chunk_id: int
    chunk_no: int
    text_preview: str
    tokens: int
    metadata: dict[str, Any] | None = None


class ChunksListResponse(BaseModel):
    total: int
    items: list[ChunkItem]


class RehydrateResponse(BaseModel):
    id: UUID
    status: str


__all__ = [
    "DocumentSummary",
    "DocumentDetail",
    "DocumentsListResponse",
    "ChunkItem",
    "ChunksListResponse",
    "RehydrateResponse",
]
