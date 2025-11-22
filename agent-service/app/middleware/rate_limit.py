from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import redis
from fastapi import HTTPException, status


logger = logging.getLogger("chat.rate_limit")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value >= 0 else default
    except ValueError:
        raise RuntimeError(f"{name} debe ser un entero.") from None


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class RateLimitConfig:
    enabled: bool
    ip_limit: int
    identity_limit: int
    window_seconds: int
    redis_url: str


def _load_config() -> RateLimitConfig:
    enabled = _bool_env("RATE_LIMIT_ENABLED", True)
    ip_limit = _int_env("CHAT_IP_LIMIT", 30)
    identity_limit = _int_env("CHAT_ID_LIMIT", 15)
    window = _int_env("CHAT_RATE_WINDOW_SECONDS", 300)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return RateLimitConfig(
        enabled=enabled,
        ip_limit=ip_limit,
        identity_limit=identity_limit,
        window_seconds=window if window > 0 else 300,
        redis_url=redis_url,
    )


class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._redis = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.config.redis_url, decode_responses=True)
        return self._redis

    def enforce(self, *, ip: Optional[str], identity: Optional[str]) -> None:
        if not self.config.enabled:
            return

        events: list[tuple[str, int]] = []

        if ip and self.config.ip_limit > 0:
            events.append((f"rl:ip:{ip}", self.config.ip_limit))
        if identity and self.config.identity_limit > 0:
            events.append((f"rl:id:{identity}", self.config.identity_limit))

        ttl_hint = None
        for key, limit in events:
            ttl_hint = self._increment(key, limit)
            if ttl_hint is not None and ttl_hint < 0:
                ttl_hint = None

        if ttl_hint is not None and ttl_hint < 1:
            ttl_hint = 1

    def _increment(self, key: str, limit: int) -> Optional[int]:
        try:
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.config.window_seconds, nx=True)
            count, _ = pipe.execute()
            ttl = self.redis.ttl(key)
        except redis.RedisError as exc:  # pragma: no cover - depende de Redis
            logger.warning("rate_limit.redis_error key=%s error=%s", key, exc)
            return None

        if count > limit:
            retry_after = ttl if ttl and ttl > 0 else self.config.window_seconds
            logger.warning("rate_limit.exceeded key=%s limit=%s ttl=%s", key, limit, ttl)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "detail": "Rate limit exceeded",
                    "retry_after_seconds": retry_after,
                },
            )
        return ttl


_CONFIG = _load_config()
limiter = RateLimiter(_CONFIG)

_LOGIN_LIMIT = _int_env("AUTH_LOGIN_RATE_LIMIT", 5)
_LOGIN_WINDOW = _int_env("AUTH_LOGIN_RATE_WINDOW_SECONDS", 300)
_LOGIN_LIMITER = RateLimiter(
    RateLimitConfig(
        enabled=_LOGIN_LIMIT > 0,
        ip_limit=_LOGIN_LIMIT,
        identity_limit=0,
        window_seconds=_LOGIN_WINDOW if _LOGIN_WINDOW > 0 else 300,
        redis_url=_CONFIG.redis_url,
    )
)


def enforce_rate_limit(*, request_ip: Optional[str], identity: Optional[str]) -> None:
    limiter.enforce(ip=request_ip, identity=identity)


def enforce_login_rate_limit(*, request_ip: Optional[str]) -> None:
    _LOGIN_LIMITER.enforce(ip=request_ip, identity=None)


__all__ = ["enforce_rate_limit", "enforce_login_rate_limit"]
