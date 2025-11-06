from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import AdminSettings


logger = logging.getLogger("admin")


@dataclass(slots=True, frozen=True)
class AdminActor:
    actor_id: str
    role: str
    token_type: str


ALLOWED_ROLES = {"admin", "curator", "viewer"}


class AdminAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: AdminSettings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path or ""
        if not path.startswith("/admin"):
            return await call_next(request)

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
                    {"detail": "Authorization header required"},
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
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )

        if self.settings.rbac_disabled:
            if token == self.settings.admin_token:
                return AdminActor(actor_id="compat-admin", role="admin", token_type="compat")
            # Intentamos tratarlo como JWT emitido por /auth/login
            try:
                payload = self._decode_jwt(token)
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid token",
                )
        else:
            payload = self._decode_jwt(token)

        subject = str(payload.get("sub") or payload.get("subject") or "").strip()
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject",
            )

        role = payload.get("role")
        if isinstance(role, list):
            role = role[0] if role else None
        role = str(role or "").lower().strip()

        if role not in ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token role not authorized",
            )

        return AdminActor(actor_id=subject, role=role, token_type="jwt")

    def _decode_jwt(self, token: str) -> dict[str, Any]:
        options = {"require": ["sub", "role"], "verify_signature": True}
        issuer = self.settings.jwt_issuer
        audience = self.settings.jwt_audience

        decode_kwargs: dict[str, Any] = {
            "algorithms": [self.settings.jwt_algorithm],
            "options": options,
        }
        if issuer:
            decode_kwargs["issuer"] = issuer
        if audience:
            decode_kwargs["audience"] = audience

        key: str | bytes | None = None
        if self.settings.jwt_public_key:
            key = self.settings.jwt_public_key
        elif self.settings.jwt_secret:
            key = self.settings.jwt_secret

        if not key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT configuration error",
            )

        try:
            return jwt.decode(token, key, **decode_kwargs)
        except InvalidTokenError as exc:  # pragma: no cover - depende de librería externa
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc

    def _is_authorized(self, role: str, request: Request) -> bool:
        method = request.method.upper()
        path = request.url.path

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
