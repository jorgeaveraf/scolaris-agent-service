from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..observability.metrics import MetricsRegistry


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Mide latencia y estatus HTTP de cada solicitud y las registra en el métrico
    compartido. No altera la respuesta.
    """

    def __init__(self, app: Any, *, metrics: MetricsRegistry):
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        path = self._path_template(request)

        try:
            response = await call_next(request)
        except HTTPException as exc:
            duration = (time.perf_counter() - start) * 1000
            self.metrics.record_http_request(
                path=path,
                status_code=exc.status_code,
                duration_ms=duration,
            )
            raise
        except Exception:  # noqa: PIE786
            duration = (time.perf_counter() - start) * 1000
            self.metrics.record_http_request(
                path=path,
                status_code=500,
                duration_ms=duration,
            )
            raise

        duration = (time.perf_counter() - start) * 1000
        self.metrics.record_http_request(
            path=path,
            status_code=response.status_code,
            duration_ms=duration,
        )
        return response

    @staticmethod
    def _path_template(request: Request) -> str:
        route = request.scope.get("route")
        path = getattr(route, "path", None) or request.url.path
        return f"{request.method.upper()} {path}"


__all__ = ["MetricsMiddleware"]
