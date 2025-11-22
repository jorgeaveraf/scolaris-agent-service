from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque, Dict, Iterable, List, Optional


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


def _percentile(values: List[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * percentile / 100
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


def _now() -> float:
    return time.time()


@dataclass
class HttpEvent:
    ts: float
    path: str
    status: int


@dataclass
class TokenEvent:
    ts: float
    endpoint: str
    prompt_tokens: int
    completion_tokens: int


@dataclass
class IngestionEvent:
    ts: float
    queue: str
    kind: str  # "enqueued" | "processed"


class RollingSeries:
    """
    Mantiene una lista acotada de muestras recientes para calcular percentiles.
    """

    def __init__(self, *, window_seconds: int, max_samples: int):
        self.window_seconds = window_seconds
        self.max_samples = max_samples
        self.samples: Deque[tuple[float, float]] = deque()

    def add(self, value: float, ts: Optional[float] = None) -> None:
        ts = ts or _now()
        self.samples.append((ts, value))
        self._prune(ts)
        if len(self.samples) > self.max_samples:
            # descartamos los más antiguos para no crecer sin límite
            overflow = len(self.samples) - self.max_samples
            for _ in range(overflow):
                self.samples.popleft()

    def _prune(self, now: Optional[float] = None) -> None:
        now = now or _now()
        cutoff = now - self.window_seconds
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()

    def snapshot(self, now: Optional[float] = None) -> dict:
        now = now or _now()
        self._prune(now)
        values = [value for _, value in self.samples]
        count = len(values)
        if not values:
            return {"count": 0, "avg_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None}
        avg = sum(values) / count
        return {
            "count": count,
            "avg_ms": round(avg, 2),
            "p50_ms": round(_percentile(values, 50) or 0, 2),
            "p95_ms": round(_percentile(values, 95) or 0, 2),
            "max_ms": round(max(values), 2),
        }


class MetricsRegistry:
    """
    Registro en memoria para métricas de uso reciente.
    Los cálculos se mantienen en una ventana temporal acotada.
    """

    def __init__(self) -> None:
        self.window_seconds = _int_env("METRICS_WINDOW_SECONDS", 3600)
        max_samples = _int_env("METRICS_MAX_SAMPLES", 2000)
        self.max_events = _int_env("METRICS_MAX_EVENTS", 5000)

        self.http_latencies: Dict[str, RollingSeries] = defaultdict(
            lambda: RollingSeries(window_seconds=self.window_seconds, max_samples=max_samples)
        )
        self.graph_latencies: Dict[str, RollingSeries] = defaultdict(
            lambda: RollingSeries(window_seconds=self.window_seconds, max_samples=max_samples)
        )
        self.http_events: Deque[HttpEvent] = deque()
        self.token_events: Deque[TokenEvent] = deque()
        self.ingestion_events: Deque[IngestionEvent] = deque()
        self._lock = Lock()

    # --- Recorders ---
    def record_http_request(
        self,
        *,
        path: str,
        status_code: int,
        duration_ms: float,
        ts: Optional[float] = None,
    ) -> None:
        ts = ts or _now()
        with self._lock:
            self.http_latencies[path].add(duration_ms, ts)
            self.http_events.append(HttpEvent(ts=ts, path=path, status=status_code))
            self._prune_events(self.http_events, ts)

    def record_graph_step(self, *, step: str, duration_ms: float, ts: Optional[float] = None) -> None:
        ts = ts or _now()
        with self._lock:
            self.graph_latencies[step].add(duration_ms, ts)

    def record_token_usage(
        self,
        *,
        endpoint: str,
        prompt_tokens: int,
        completion_tokens: int,
        ts: Optional[float] = None,
    ) -> None:
        ts = ts or _now()
        with self._lock:
            self.token_events.append(
                TokenEvent(
                    ts=ts,
                    endpoint=endpoint,
                    prompt_tokens=max(0, prompt_tokens),
                    completion_tokens=max(0, completion_tokens),
                )
            )
            self._prune_events(self.token_events, ts)

    def record_ingestion_event(self, *, queue: str, kind: str, ts: Optional[float] = None) -> None:
        ts = ts or _now()
        with self._lock:
            self.ingestion_events.append(IngestionEvent(ts=ts, queue=queue, kind=kind))
            self._prune_events(self.ingestion_events, ts)

    # --- Snapshots ---
    def http_snapshot(self) -> dict:
        now = _now()
        with self._lock:
            per_path = {path: series.snapshot(now) for path, series in self.http_latencies.items()}
            counts = self._status_counts(self.http_events, now)
        return {"endpoints": per_path, "errors": counts}

    def graph_snapshot(self) -> dict:
        now = _now()
        with self._lock:
            per_step = {step: series.snapshot(now) for step, series in self.graph_latencies.items()}
        return {"steps": per_step}

    def token_snapshot(self) -> dict:
        now = _now()
        with self._lock:
            events = list(self._recent_events(self.token_events, now))
        if not events:
            return {"by_endpoint": {}, "totals": None}

        by_endpoint: Dict[str, dict] = {}
        for event in events:
            bucket = by_endpoint.setdefault(
                event.endpoint,
                {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            )
            bucket["requests"] += 1
            bucket["prompt_tokens"] += event.prompt_tokens
            bucket["completion_tokens"] += event.completion_tokens
            bucket["total_tokens"] += event.prompt_tokens + event.completion_tokens

        totals = {
            "requests": sum(item["requests"] for item in by_endpoint.values()),
            "prompt_tokens": sum(item["prompt_tokens"] for item in by_endpoint.values()),
            "completion_tokens": sum(item["completion_tokens"] for item in by_endpoint.values()),
        }
        totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
        totals["avg_total_tokens"] = (
            round(totals["total_tokens"] / totals["requests"], 2) if totals["requests"] else None
        )

        for data in by_endpoint.values():
            data["avg_total_tokens"] = (
                round(data["total_tokens"] / data["requests"], 2) if data["requests"] else None
            )

        return {"by_endpoint": by_endpoint, "totals": totals}

    def ingestion_snapshot(self) -> dict:
        now = _now()
        with self._lock:
            events = list(self._recent_events(self.ingestion_events, now))
        summary: Dict[str, dict] = {}
        for event in events:
            bucket = summary.setdefault(event.queue, {"enqueued": 0, "processed": 0})
            if event.kind == "enqueued":
                bucket["enqueued"] += 1
            elif event.kind == "processed":
                bucket["processed"] += 1
        return {"queues": summary}

    # --- Internals ---
    def _prune_events(self, dq: Deque, now: Optional[float] = None) -> None:
        now = now or _now()
        cutoff = now - self.window_seconds
        while dq and getattr(dq[0], "ts", 0) < cutoff:
            dq.popleft()
        # limite de seguridad por tamaño
        overflow = len(dq) - self.max_events
        if overflow > 0:
            for _ in range(overflow):
                dq.popleft()

    def _recent_events(self, dq: Deque, now: float) -> Iterable:
        cutoff = now - self.window_seconds
        for event in dq:
            if getattr(event, "ts", 0) >= cutoff:
                yield event

    def _status_counts(self, events: Deque[HttpEvent], now: float) -> dict:
        counts = {"400": 0, "401": 0, "403": 0, "429": 0, "500": 0, "503": 0, "other": 0}
        for event in self._recent_events(events, now):
            code = event.status
            key = str(code)
            if key in counts:
                counts[key] += 1
            elif 500 <= code < 600:
                counts["500"] += 1
            elif 400 <= code < 500:
                counts["other"] += 1
        return counts


metrics = MetricsRegistry()

__all__ = ["metrics", "MetricsRegistry"]
