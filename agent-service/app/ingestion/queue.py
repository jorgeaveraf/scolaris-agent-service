from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import redis

logger = logging.getLogger("admin.queue")


@dataclass(frozen=True)
class IngestionJob:
    document_id: str
    action: str = "ingest"


class IngestionQueue:
    def __init__(self, *, name: str, redis_url: str):
        self.name = name
        self.redis = redis.from_url(redis_url, decode_responses=True)

    def enqueue(self, job: IngestionJob) -> None:
        payload = json.dumps(job.__dict__)
        try:
            self.redis.rpush(self.name, payload)
            logger.info("admin.queue.enqueued queue=%s job=%s", self.name, payload)
        except redis.RedisError as exc:  # pragma: no cover - depende de Redis
            logger.exception("admin.queue.enqueue_failed queue=%s error=%s", self.name, exc)
            raise

    def dequeue(self, timeout: int = 5) -> Optional[IngestionJob]:
        try:
            item = self.redis.blpop(self.name, timeout=timeout)
        except redis.RedisError as exc:  # pragma: no cover - depende de Redis
            logger.exception("admin.queue.dequeue_failed queue=%s error=%s", self.name, exc)
            return None
        if not item:
            return None
        _, payload = item
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("admin.queue.invalid_payload payload=%s", payload)
            return None

        document_id = data.get("document_id")
        action = data.get("action", "ingest")
        if not document_id:
            logger.warning("admin.queue.missing_document payload=%s", payload)
            return None
        return IngestionJob(document_id=document_id, action=action)


__all__ = ["IngestionQueue", "IngestionJob"]
