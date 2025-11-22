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


class LatencyStats(BaseModel):
    count: int
    avg_ms: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None
    max_ms: float | None = None


class HttpMetrics(BaseModel):
    endpoints: dict[str, LatencyStats]
    errors: dict[str, int]


class GraphMetrics(BaseModel):
    steps: dict[str, LatencyStats]


class TokenBreakdown(BaseModel):
    requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    avg_total_tokens: float | None = None


class TokenMetrics(BaseModel):
    by_endpoint: dict[str, TokenBreakdown]
    totals: TokenBreakdown | None = None


class IngestionDocuments(BaseModel):
    total: int
    ready: int
    processing: int
    error: int
    other: int


class IngestionQueueMetrics(BaseModel):
    name: str | None = None
    pending: int | None = None
    recent_enqueued: int
    recent_processed: int


class IngestionMetrics(BaseModel):
    documents: IngestionDocuments
    queue: IngestionQueueMetrics


class MemoryMetrics(BaseModel):
    active_sessions: int
    avg_turns: float | None = None


class MetricsOverview(BaseModel):
    window_seconds: int
    http: HttpMetrics
    graph: GraphMetrics
    tokens: TokenMetrics
    ingestion: IngestionMetrics
    memory: MemoryMetrics


__all__ = [
    "DocumentSummary",
    "DocumentDetail",
    "DocumentsListResponse",
    "ChunkItem",
    "ChunksListResponse",
    "RehydrateResponse",
    "LatencyStats",
    "HttpMetrics",
    "GraphMetrics",
    "TokenBreakdown",
    "TokenMetrics",
    "IngestionDocuments",
    "IngestionQueueMetrics",
    "IngestionMetrics",
    "MemoryMetrics",
    "MetricsOverview",
]
