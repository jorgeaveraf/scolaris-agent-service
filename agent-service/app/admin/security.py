from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..oidc import current_actor


logger = logging.getLogger("admin")


@dataclass(slots=True, frozen=True)
class AdminActor:
    actor_id: str
    role: str


ALLOWED_ROLES = {"admin", "curator", "viewer"}


class AdminAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path or ""
        if not path.startswith("/admin"):
            return await call_next(request)

        if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            allowed = {value.strip() for value in os.getenv("ALLOWED_ORIGINS", "").split(",") if value.strip()}
            origin = request.headers.get("Origin", "")
            if origin not in allowed:
                return JSONResponse({"detail": "Invalid request origin"}, status_code=403)

        start = time.perf_counter()
        actor: Optional[AdminActor] = None
        decision = "deny"
        status_code = status.HTTP_401_UNAUTHORIZED
        reason = ""

        try:
            actor = self._authenticate(request)
            if not actor:
                reason = "missing_actor"
                return JSONResponse(
                    {"detail": "Sign in required"},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            request.state.actor = actor  # type: ignore[attr-defined]

            if not self._is_authorized(actor.role, request):
                reason = "forbidden"
                status_code = status.HTTP_403_FORBIDDEN
                return JSONResponse(
                    {"detail": "Insufficient permissions"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            decision = "allow"
            response = await call_next(request)
            status_code = response.status_code
            return response
        except HTTPException as exc:
            status_code = exc.status_code
            reason = "handled_error"
            payload = exc.detail
            if not isinstance(payload, dict):
                payload = {"detail": payload}
            return JSONResponse(payload, status_code=exc.status_code)
        except Exception as exc:  # noqa: PIE786
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            trace_id = uuid4().hex
            reason = f"exception:{trace_id}"
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
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            actor_id = getattr(actor, "actor_id", None)
            role = getattr(actor, "role", None)
            logger.info(
                "admin.access decision=%s reason=%s actor_id=%s role=%s method=%s path=%s status=%s duration_ms=%.2f",
                decision,
                reason or decision,
                actor_id or "-",
                role or "-",
                request.method,
                path,
                status_code,
                duration_ms,
            )

    def _authenticate(self, request: Request) -> Optional[AdminActor]:
        identity = current_actor(request)
        if identity and identity.role in ALLOWED_ROLES:
            return AdminActor(actor_id=identity.email, role=identity.role)
        return None

    def _is_authorized(self, role: str, request: Request) -> bool:
        method = request.method.upper()
        path = request.url.path

        if path.startswith("/admin/chat-history"):
            return role == "admin" and (
                method in {"GET", "HEAD", "OPTIONS"}
                or (method == "PATCH" and path.endswith("/evaluation"))
            )

        if role == "admin":
            return True

        if method in {"GET", "HEAD", "OPTIONS"}:
            return True  # viewer+ tienen acceso de sólo lectura

        if role == "viewer":
            return False

        # curator
        if method == "POST":
            if path == "/admin/docs":
                return True
            if path.endswith("/rehydrate"):
                return True
        if method == "DELETE" and path.startswith("/admin/docs/"):
            return True

        # cualquier otra ruta sensible requiere admin
        return False


__all__ = ["AdminAuthMiddleware", "AdminActor"]
