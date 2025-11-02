from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import AdminSettings


logger = logging.getLogger("admin")


class AdminAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: AdminSettings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path or ""
        if not path.startswith("/admin"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(
                "admin.access missing_token method=%s path=%s",
                request.method,
                path,
            )
            return JSONResponse(
                {"detail": "Authorization header required"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer":
            logger.warning(
                "admin.access invalid_scheme method=%s path=%s",
                request.method,
                path,
            )
            return JSONResponse(
                {"detail": "Invalid authentication scheme"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if token != self.settings.admin_token:
            logger.warning(
                "admin.access invalid_token method=%s path=%s",
                request.method,
                path,
            )
            return JSONResponse(
                {"detail": "Invalid token"},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except HTTPException as exc:
            logger.warning(
                "admin.access error method=%s path=%s status=%s detail=%s",
                request.method,
                path,
                exc.status_code,
                exc.detail,
            )
            payload = exc.detail
            if not isinstance(payload, dict):
                payload = {"detail": payload}
            return JSONResponse(payload, status_code=exc.status_code)
        except Exception as exc:  # noqa: PIE786 - capturamos para añadir trace_id
            trace_id = uuid4().hex
            logger.exception(
                "admin.access exception method=%s path=%s trace_id=%s",
                request.method,
                path,
                trace_id,
            )
            return JSONResponse(
                {"detail": "Internal server error", "trace_id": trace_id},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "admin.access method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            path,
            response.status_code,
            duration,
        )
        return response


__all__ = ["AdminAuthMiddleware"]
