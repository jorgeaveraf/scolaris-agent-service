import json
import logging
import os
from typing import Dict, List

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def _int_env(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value
    except ValueError:
        logger.warning("Invalid integer for %s: %s", name, raw)
        return default


MAX_MESSAGES = _int_env("MEMORY_MAX_TURNS", 10) or 10
TTL_SECONDS = _int_env("MEMORY_TTL_SECONDS", None)
MAX_CONTENT_CHARS = _int_env("MEMORY_MAX_CONTENT_CHARS", 2000) or 2000


class ConversationMemory:
    """Redis-backed sliding window of recent chat messages."""

    def __init__(
        self,
        redis_url: str | None = None,
        max_messages: int | None = None,
        ttl_seconds: int | None = TTL_SECONDS,
    ):
        self.redis = redis.from_url(redis_url or REDIS_URL, decode_responses=True)
        self.max_messages = max_messages if max_messages is not None else MAX_MESSAGES
        self.ttl_seconds = ttl_seconds if ttl_seconds and ttl_seconds > 0 else None

    def _key(self, user_id: str) -> str:
        return f"memory:{user_id}"

    def load(self, user_id: str) -> List[Dict[str, str]]:
        key = self._key(user_id)
        try:
            if self.max_messages and self.max_messages > 0:
                raw_messages = self.redis.lrange(key, -self.max_messages, -1)
            else:
                raw_messages = self.redis.lrange(key, 0, -1)
        except redis.RedisError as exc:
            logger.warning("Redis memory load failed for user %s: %s", user_id, exc)
            return []

        history: List[Dict[str, str]] = []
        for item in raw_messages:
            try:
                decoded = json.loads(item)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict) and "role" in decoded and "content" in decoded:
                history.append(decoded)
        return history

    def append_messages(self, user_id: str, messages: List[Dict[str, str]]) -> None:
        if not messages:
            return
        key = self._key(user_id)

        serialized = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if not role or role not in {"user", "assistant"}:
                continue
            clipped = content if len(content) <= MAX_CONTENT_CHARS else f"{content[:MAX_CONTENT_CHARS]}..."
            serialized.append(json.dumps({"role": role, "content": clipped}, ensure_ascii=False))

        if not serialized:
            return

        try:
            pipe = self.redis.pipeline()
            for payload in serialized:
                pipe.rpush(key, payload)
            if self.max_messages and self.max_messages > 0:
                pipe.ltrim(key, -self.max_messages, -1)
            if self.ttl_seconds:
                pipe.expire(key, self.ttl_seconds)
            pipe.execute()
        except redis.RedisError as exc:
            logger.warning("Redis memory append failed for user %s: %s", user_id, exc)

    def clear_memory(self, user_id: str) -> None:
        try:
            self.redis.delete(self._key(user_id))
        except redis.RedisError as exc:
            logger.warning("Redis memory clear failed for user %s: %s", user_id, exc)


memory_store = ConversationMemory()
