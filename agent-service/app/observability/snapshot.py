from __future__ import annotations

import logging
import math
from typing import Dict

import redis

from ..admin.schemas import (
    GraphMetrics,
    HttpMetrics,
    IngestionDocuments,
    IngestionMetrics,
    IngestionQueueMetrics,
    LatencyStats,
    MemoryMetrics,
    MetricsOverview,
    TokenBreakdown,
    TokenMetrics,
)
from ..admin.service import DocumentAdminService
from ..agent.memory import memory_store
from .metrics import metrics

logger = logging.getLogger("metrics")


def _latency_from_snapshot(data: dict | None) -> LatencyStats:
    data = data or {}
    return LatencyStats(
        count=int(data.get("count", 0) or 0),
        avg_ms=data.get("avg_ms"),
        p50_ms=data.get("p50_ms"),
        p95_ms=data.get("p95_ms"),
        max_ms=data.get("max_ms"),
    )


def _token_breakdown(payload: dict | None) -> TokenBreakdown:
    payload = payload or {}
    return TokenBreakdown(
        requests=int(payload.get("requests", 0) or 0),
        prompt_tokens=int(payload.get("prompt_tokens", 0) or 0),
        completion_tokens=int(payload.get("completion_tokens", 0) or 0),
        total_tokens=int(payload.get("total_tokens", 0) or 0),
        avg_total_tokens=payload.get("avg_total_tokens"),
    )


def _memory_stats() -> MemoryMetrics:
    try:
        keys = []
        total_messages = 0
        # limitamos el escaneo para evitar bloquear Redis en instalaciones grandes
        for idx, key in enumerate(memory_store.redis.scan_iter("memory:*", count=200)):  # type: ignore[attr-defined]
            keys.append(key)
            try:
                total_messages += int(memory_store.redis.llen(key))  # type: ignore[attr-defined]
            except redis.RedisError:
                continue
            if idx >= 500:
                break

        active = len(keys)
        if active == 0:
            return MemoryMetrics(active_sessions=0, avg_turns=None)

        # cada turno son 2 mensajes (user/assistant) en promedio
        avg_turns = total_messages / max(active, 1) / 2
        return MemoryMetrics(
            active_sessions=active,
            avg_turns=round(avg_turns, 2) if not math.isnan(avg_turns) else None,
        )
    except redis.RedisError as exc:  # pragma: no cover - depende de Redis
        logger.warning("metrics.memory.redis_error error=%s", exc)
        return MemoryMetrics(active_sessions=0, avg_turns=None)


def build_metrics_overview(admin_service: DocumentAdminService) -> MetricsOverview:
    http_snapshot = metrics.http_snapshot()
    graph_snapshot = metrics.graph_snapshot()
    token_snapshot = metrics.token_snapshot()
    ingestion_snapshot = metrics.ingestion_snapshot()
    doc_stats = admin_service.get_ingestion_stats()

    endpoint_latencies: Dict[str, LatencyStats] = {
        path: _latency_from_snapshot(data)
        for path, data in http_snapshot.get("endpoints", {}).items()
    }
    graph_latencies: Dict[str, LatencyStats] = {
        name: _latency_from_snapshot(data)
        for name, data in graph_snapshot.get("steps", {}).items()
    }

    tokens_by_endpoint = {
        endpoint: _token_breakdown(data)
        for endpoint, data in token_snapshot.get("by_endpoint", {}).items()
    }
    tokens_totals_raw = token_snapshot.get("totals")
    token_metrics = TokenMetrics(
        by_endpoint=tokens_by_endpoint,
        totals=_token_breakdown(tokens_totals_raw) if tokens_totals_raw else None,
    )

    queue_name = admin_service.settings.upload_queue_name
    queue_stats = ingestion_snapshot.get("queues", {}).get(queue_name or "ingestion", {})

    ingestion_metrics = IngestionMetrics(
        documents=IngestionDocuments(
            total=int(doc_stats.get("total", 0) or 0),
            ready=int(doc_stats.get("ready", 0) or 0),
            processing=int(doc_stats.get("processing", 0) or 0),
            error=int(doc_stats.get("error", 0) or 0),
            other=int(doc_stats.get("other", 0) or 0),
        ),
        queue=IngestionQueueMetrics(
            name=queue_name,
            pending=doc_stats.get("queue_depth"),
            recent_enqueued=int(queue_stats.get("enqueued", 0) or 0),
            recent_processed=int(queue_stats.get("processed", 0) or 0),
        ),
    )

    return MetricsOverview(
        window_seconds=metrics.window_seconds,
        http=HttpMetrics(
            endpoints=endpoint_latencies,
            errors=http_snapshot.get("errors", {}),
        ),
        graph=GraphMetrics(steps=graph_latencies),
        tokens=token_metrics,
        ingestion=ingestion_metrics,
        memory=_memory_stats(),
    )


__all__ = ["build_metrics_overview"]
