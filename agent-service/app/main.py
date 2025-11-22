# agent-service/app/main.py
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import hmac
import time
from typing import Any, Optional
from uuid import uuid4

import jwt
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ValidationError, field_validator

from .admin import register_admin_module
from .agent.graph import AgentState, app_graph
from .agent.memory import memory_store
from .init import init_db
from .middleware.rate_limit import enforce_rate_limit, enforce_login_rate_limit
from .middleware.metrics import MetricsMiddleware
from .observability.metrics import metrics

logger = logging.getLogger(__name__)

app = FastAPI(title="Scolaris Agent API")

register_admin_module(app)

# --- Configuración general ---
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

CHAT_MAX_QUESTION_CHARS = int(os.getenv("CHAT_MAX_QUESTION_CHARS", "800"))
STRICT_VALIDATION = os.getenv("STRICT_VALIDATION", "true").lower() == "true"
RAW_ALLOWED_ROLES = [
    role.strip()
    for role in os.getenv("CHAT_ALLOWED_ROLES", "consultor,ventas,soporte").split(",")
    if role.strip()
]
CHAT_ALLOWED_ROLES = RAW_ALLOWED_ROLES
CHAT_ALLOWED_ROLE_KEYS = {role.lower() for role in CHAT_ALLOWED_ROLES}
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")

def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un número positivo.") from exc


AGENT_TIMEOUT_SECONDS = _float_env("AGENT_TIMEOUT_SECONDS", 25.0)
AGENT_FAILOVER_MESSAGE = os.getenv("AGENT_FAILOVER_MESSAGE")
JWT_EXPIRES_SECONDS = int(os.getenv("JWT_EXPIRES_SECONDS", "86400"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_PRIVATE_KEY = os.getenv("JWT_PRIVATE_KEY")
JWT_ISSUER = os.getenv("JWT_ISSUER")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")

_PASSWORD_MATRIX: list[tuple[str, str]] = [
    ("admin", (os.getenv("AUTH_PASSWORD_ADMIN") or "").strip()),
    ("curator", (os.getenv("AUTH_PASSWORD_CURATOR") or "").strip()),
    ("viewer", (os.getenv("AUTH_PASSWORD_VIEWER") or "").strip()),
]
PASSWORD_CREDENTIALS = [(role, pwd) for role, pwd in _PASSWORD_MATRIX if pwd]


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware, metrics=metrics)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/session/start")
def start_session(response: Response, request: Request) -> dict[str, str]:
    sid = request.cookies.get("sid") or secrets.token_urlsafe(16)
    secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    samesite = os.getenv("COOKIE_SAMESITE", "lax")
    domain = os.getenv("COOKIE_DOMAIN")
    response.set_cookie(
        "sid",
        sid,
        httponly=True,
        secure=secure,
        samesite=samesite,
        domain=domain,
    )
    return {"sid": sid}


class ChatRequest(BaseModel):
    question: str
    role: str | None = None
    user_id: str | None = None
    mem_opt_in: bool = False

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("question must not be empty")
        if len(trimmed) > CHAT_MAX_QUESTION_CHARS:
            raise ValueError(
                f"question must not exceed {CHAT_MAX_QUESTION_CHARS} characters"
            )
        return trimmed

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        key = normalized.lower()
        if CHAT_ALLOWED_ROLES and key not in CHAT_ALLOWED_ROLE_KEYS:
            raise ValueError("role is not allowed")
        if CHAT_ALLOWED_ROLES:
            for allowed in CHAT_ALLOWED_ROLES:
                if allowed.lower() == key:
                    return allowed
        return normalized

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not USER_ID_PATTERN.match(trimmed):
            raise ValueError("user_id format is invalid")
        return trimmed


class AgentTimeoutError(RuntimeError):
    def __init__(self, trace_id: str):
        super().__init__("Agent timeout")
        self.trace_id = trace_id


class AgentExecutionError(RuntimeError):
    def __init__(self, trace_id: str):
        super().__init__("Agent execution error")
        self.trace_id = trace_id


class LoginRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("password must not be empty")
        return value


class LoginResponse(BaseModel):
    token: str
    role: str
    expires_in: int


def _select_role_for_password(password: str) -> Optional[str]:
    for role, configured_password in PASSWORD_CREDENTIALS:
        if hmac.compare_digest(password, configured_password):
            return role
    return None


def _issue_jwt(*, role: str) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": f"auth-{role}",
        "role": role,
        "iat": now,
        "exp": now + max(1, JWT_EXPIRES_SECONDS),
    }
    if JWT_ISSUER:
        payload["iss"] = JWT_ISSUER
    if JWT_AUDIENCE:
        payload["aud"] = JWT_AUDIENCE

    algorithm = JWT_ALGORITHM.upper()

    if algorithm.startswith("HS"):
        if not JWT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret not configured.",
            )
        return jwt.encode(payload, JWT_SECRET, algorithm=algorithm)

    if algorithm.startswith("RS"):
        private_key = JWT_PRIVATE_KEY or JWT_SECRET
        if not private_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT private key not configured.",
            )
        return jwt.encode(payload, private_key, algorithm=algorithm)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unsupported JWT algorithm: {algorithm}",
    )


class LoginRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("password must not be empty")
        return value


class LoginResponse(BaseModel):
    token: str
    role: str
    expires_in: int


@app.post("/auth/login", response_model=LoginResponse)
async def auth_login(request: Request, body: LoginRequest) -> LoginResponse:
    client_ip = request.client.host if request.client else None
    enforce_login_rate_limit(request_ip=client_ip)

    if not PASSWORD_CREDENTIALS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password login not configured.",
        )

    trace_id = uuid4().hex
    role = _select_role_for_password(body.password.strip())
    if not role:
        logger.warning(
            "auth.login failure ip=%s trace_id=%s",
            client_ip or "-",
            trace_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    token = _issue_jwt(role=role)
    logger.info(
        "auth.login success role=%s ip=%s trace_id=%s",
        role,
        client_ip or "-",
        trace_id,
    )
    return LoginResponse(token=token, role=role, expires_in=JWT_EXPIRES_SECONDS)


def _extract_validation_message(error: ValidationError) -> str:
    details = error.errors()
    if not details:
        return "Invalid payload"
    first = details[0]
    loc = ".".join(str(entry) for entry in first.get("loc", []))
    message = first.get("msg", "Invalid payload")
    return f"{loc}: {message}" if loc else message


async def _parse_chat_request(request: Request) -> ChatRequest:
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required",
        )
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    try:
        return ChatRequest.model_validate(payload, strict=STRICT_VALIDATION)
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_extract_validation_message(err),
        ) from err


def _resolve_user_id(body: ChatRequest, request: Request) -> str:
    if body.user_id:
        return body.user_id

    header_id = request.headers.get("X-User-Id")
    if header_id and USER_ID_PATTERN.match(header_id.strip()):
        return header_id.strip()

    cookie_id = request.cookies.get("sid")
    if cookie_id and USER_ID_PATTERN.match(cookie_id):
        return cookie_id

    return "anonymous"


def _rate_limit_identity(user_id: str, request: Request) -> str | None:
    if user_id and user_id != "anonymous":
        return user_id
    cookie_id = request.cookies.get("sid")
    if cookie_id and USER_ID_PATTERN.match(cookie_id):
        return cookie_id
    return None


def strip_source_mentions(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text
    patterns = [
        r"\[[^\]]*fuente[^\]]*\]",
        r"\([^\)]*fuente[^\)]*\)",
        r"fuentes?\s*:[^\n]*",
        r"fuente\s*\d+",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\[\s*\]", "", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


async def _invoke_agent(state: AgentState) -> AgentState:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(app_graph.invoke, state),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        trace_id = uuid4().hex
        logger.warning("agent.timeout trace_id=%s", trace_id)
        raise AgentTimeoutError(trace_id) from exc
    except Exception as exc:  # noqa: PIE786
        trace_id = uuid4().hex
        logger.exception("agent.execution_error trace_id=%s", trace_id)
        raise AgentExecutionError(trace_id) from exc


def _agent_error_response(message: str, trace_id: str) -> JSONResponse:
    if AGENT_FAILOVER_MESSAGE:
        logger.info(
            "agent.failover trace_id=%s message=%s",
            trace_id,
            message,
        )
        return JSONResponse(
            {"answer": AGENT_FAILOVER_MESSAGE, "trace_id": trace_id},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        {"detail": message, "trace_id": trace_id},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _append_memory(user_id: str, question: str, answer: str, enabled: bool) -> None:
    if not enabled:
        return
    memory_store.append_messages(
        user_id,
        [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
    )


def _build_state(
    *,
    user_id: str,
    question: str,
    role: str | None,
    history: list[dict[str, Any]],
) -> AgentState:
    return {
        "user_id": user_id,
        "question": question,
        "role": role,
        "context": [],
        "memory": history,
        "answer": None,
    }


@app.post("/chat")
async def chat(request: Request) -> Response:
    body = await _parse_chat_request(request)
    user_id = _resolve_user_id(body, request)
    identity = _rate_limit_identity(user_id, request)
    client_ip = request.client.host if request.client else None
    enforce_rate_limit(request_ip=client_ip, identity=identity)

    mem_enabled = bool(body.mem_opt_in and user_id != "anonymous")
    history = memory_store.load(user_id) if mem_enabled else []
    state = _build_state(
        user_id=user_id,
        question=body.question,
        role=body.role,
        history=history,
    )

    try:
        result = await _invoke_agent(state)
    except AgentTimeoutError as exc:
        return _agent_error_response("Agent timeout", exc.trace_id)
    except AgentExecutionError as exc:
        return _agent_error_response("Agent execution error", exc.trace_id)

    clean_answer = strip_source_mentions(result.get("answer"))
    _append_memory(user_id, body.question, clean_answer, mem_enabled)

    return JSONResponse(
        {"answer": clean_answer, "citations": []},
        status_code=status.HTTP_200_OK,
    )


@app.post("/chat/stream")
async def chat_stream(request: Request) -> Response:
    body = await _parse_chat_request(request)
    user_id = _resolve_user_id(body, request)
    identity = _rate_limit_identity(user_id, request)
    client_ip = request.client.host if request.client else None
    enforce_rate_limit(request_ip=client_ip, identity=identity)

    mem_enabled = bool(body.mem_opt_in and user_id != "anonymous")
    history = memory_store.load(user_id) if mem_enabled else []
    state = _build_state(
        user_id=user_id,
        question=body.question,
        role=body.role,
        history=history,
    )

    try:
        result = await _invoke_agent(state)
    except AgentTimeoutError as exc:
        return _agent_error_response("Agent timeout", exc.trace_id)
    except AgentExecutionError as exc:
        return _agent_error_response("Agent execution error", exc.trace_id)

    clean_answer = strip_source_mentions(result.get("answer"))
    citations = result.get("context", [])
    _append_memory(user_id, body.question, clean_answer, mem_enabled)

    async def stream() -> Any:
        yield f"event: citations\ndata: {json.dumps(citations, ensure_ascii=False)}\n\n"
        payload = json.dumps({"answer": clean_answer}, ensure_ascii=False)
        yield f"event: final\ndata: {payload}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["app"]
