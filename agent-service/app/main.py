# agent-service/app/main.py
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import time
from urllib.parse import urlsplit
from typing import Any
from uuid import uuid4

import httpx
import psycopg
import redis
from langchain_core.messages import HumanMessage, SystemMessage
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ValidationError, field_validator

from .admin import register_admin_module
from .chat_history import save_chat_answer
from .agent.graph import (
    AgentState,
    LLM_SERVICE_TIMEOUT_SECONDS,
    answer_node,
    app_graph,
    build_answer_prompt,
    build_answer_system_prompt,
    grounded_followup_answer,
    extractive_answer_with_passages,
    revise_answer_for_citations,
    classify_request_policy,
    select_supporting_passages,
    llm as local_llm,
    retrieve_node,
)
from .agent.memory import memory_store
from .agent.continuity import missing_context_reply, refers_to_previous_turn, unsupported_followup_reply
from .agent.language import conversational_reply, no_source_message, response_language
from .agent.policy import disclaimer_for, refusal
from .init import init_db
from .middleware.rate_limit import enforce_rate_limit
from .middleware.metrics import MetricsMiddleware
from .observability.metrics import metrics
from .oidc import bootstrap_admins, current_actor, register_oidc

logger = logging.getLogger("uvicorn.error")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

app = FastAPI(title="Agent Service API")

register_admin_module(app)
register_oidc(app)

# --- Configuración general ---
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

CHAT_MAX_QUESTION_CHARS = int(os.getenv("CHAT_MAX_QUESTION_CHARS", "800"))
STRICT_VALIDATION = os.getenv("STRICT_VALIDATION", "true").lower() == "true"
RAW_ALLOWED_ROLES = [
    role.strip()
    for role in os.getenv("CHAT_ALLOWED_ROLES", "").split(",")
    if role.strip()
]
CHAT_ALLOWED_ROLES = RAW_ALLOWED_ROLES
CHAT_ALLOWED_ROLE_KEYS = {role.lower() for role in CHAT_ALLOWED_ROLES}
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")


def _enabled(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() == "true"


def _source_records(context: list[dict[str, Any]], *, include_snippet: bool = False) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for chunk in context:
        metadata = chunk.get("metadata") or {}
        title = str(chunk.get("title") or metadata.get("filename") or "Documento").strip()
        source = str(chunk.get("source") or "")
        url = source if source.startswith(("https://", "http://")) else ""
        passage = str(chunk.get("evidence_quote") or "").strip()
        key = (title, url, passage)
        if key in seen:
            continue
        seen.add(key)
        record = {"title": title, **({"url": url} if url else {})}
        if passage or include_snippet:
            record["snippet"] = passage or " ".join(str(chunk.get("content") or "").split())[:240]
        citations.append(record)
    return citations


def _public_citations(context: list[dict[str, Any]]) -> list[dict[str, str]]:
    return _source_records(context, include_snippet=True) if _enabled("CHAT_SHOW_CITATIONS") else []


async def _record_chat_answer(request: Request, question: str, answer: str, context: list[dict[str, Any]]) -> None:
    actor = current_actor(request)
    await asyncio.to_thread(
        save_chat_answer,
        actor_email=actor.email if actor else None,
        question=question,
        answer=answer,
        sources=_source_records(context),
    )


async def _policy_decision(question: str, request_id: str) -> str:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(classify_request_policy, question, request_id),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.exception("chat.policy_check_failed request_id=%s", request_id)
        raise HTTPException(status_code=503, detail="Policy check unavailable") from exc


async def _supported_passages(result: AgentState, answer: str) -> list[dict[str, Any]]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(select_supporting_passages, result, answer),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("chat.passage_selection_failed request_id=%s", result.get("request_id"))
        return []


def _covers_named_publishers(result: AgentState, passages: list[dict[str, Any]]) -> bool:
    publishers = {"irs": "irs.gov", "sec": "investor.gov", "sightbridge": "sightbridge.com"}
    required = [host for label, host in publishers.items()
                if re.search(rf"\b{label}\b", result["question"], re.I)]
    if len(required) < 2:
        return True
    return all(any((urlsplit(str(passage.get("source") or "")).hostname or "").removeprefix("www.") == host
                   for passage in passages)
               for host in required)


async def _answer_with_citations(result: AgentState, answer: str) -> tuple[str, list[dict[str, Any]]]:
    passages = await _supported_passages(result, answer)
    if passages and _covers_named_publishers(result, passages):
        return answer, passages
    try:
        revised = await asyncio.wait_for(
            asyncio.to_thread(revise_answer_for_citations, result, answer),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("chat.citation_revision_failed request_id=%s", result.get("request_id"))
        return answer, []
    if not revised:
        return answer, []
    revised = strip_source_mentions(revised)
    passages = await _supported_passages(result, revised)
    return (revised, passages) if passages and _covers_named_publishers(result, passages) else (answer, [])


async def _extractive_fallback(result: AgentState) -> tuple[str, list[dict[str, Any]]] | None:
    for attempt in range(2):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(extractive_answer_with_passages, result),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            if response:
                return response
        except Exception:
            logger.exception("chat.extractive_fallback_failed request_id=%s attempt=%d", result.get("request_id"), attempt + 1)
    return None


@app.get("/chat/config")
def chat_config() -> dict[str, bool | int]:
    return {
        "login_required": _enabled("CHAT_LOGIN_REQUIRED"),
        "show_citations": _enabled("CHAT_SHOW_CITATIONS"),
        "require_sources": _enabled("ANSWER_REQUIRE_SOURCES"),
        "max_question_chars": CHAT_MAX_QUESTION_CHARS,
    }

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
LLM_SERVICE_STREAM_URL = (os.getenv("LLM_SERVICE_STREAM_URL") or "").strip()
EMBEDDING_SERVICE_URL = (os.getenv("EMBEDDING_SERVICE_URL") or "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+psycopg", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
READINESS_TIMEOUT_SECONDS = _float_env("READINESS_TIMEOUT_SECONDS", 2.0)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware, metrics=metrics)


def _request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if candidate and len(candidate) <= 128 and re.fullmatch(r"[A-Za-z0-9._:-]+", candidate):
        return candidate
    return uuid4().hex


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    request_id = _request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # keep the ID on otherwise-unhandled errors
        logger.exception(
            "api.request service=api operation=http status=error request_id=%s "
            "latency_ms=%.2f error_type=%s",
            request_id, (time.perf_counter() - start) * 1000, exc.__class__.__name__,
        )
        response = JSONResponse(
            {"detail": "Internal server error", "request_id": request_id},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "api.request service=api operation=http status=%s request_id=%s latency_ms=%.2f",
        response.status_code, request_id, (time.perf_counter() - start) * 1000,
    )
    return response


@app.on_event("startup")
def _startup() -> None:
    init_db()
    bootstrap_admins()


@app.get("/health")
def health(request: Request) -> dict[str, str]:
    logger.info(
        "api.health service=api operation=liveness status=ok request_id=%s",
        request.state.request_id,
    )
    return {"status": "ok", "service": "api"}


def _postgres_ready() -> None:
    if not DATABASE_URL:
        raise RuntimeError("database_not_configured")
    with psycopg.connect(DATABASE_URL, connect_timeout=max(1, int(READINESS_TIMEOUT_SECONDS))) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")


def _redis_ready() -> None:
    client = redis.from_url(
        REDIS_URL,
        socket_connect_timeout=READINESS_TIMEOUT_SECONDS,
        socket_timeout=READINESS_TIMEOUT_SECONDS,
    )
    client.ping()


def _ready_url(service_url: str, endpoint: str) -> str:
    if not service_url:
        return ""
    return str(httpx.URL(service_url).copy_with(path=endpoint, query=None))


@app.get("/ready")
async def ready(request: Request) -> JSONResponse:
    request_id = request.state.request_id
    dependencies = {
        "postgres": "unavailable",
        "redis": "degraded",
        "embedding_service": "unavailable",
        "llm_service": "unavailable",
    }

    async def local_check(name: str, fn, degraded: bool = False) -> None:
        start = time.perf_counter()
        try:
            await asyncio.wait_for(asyncio.to_thread(fn), timeout=READINESS_TIMEOUT_SECONDS)
            dependencies[name] = "ok"
            check_status = "ok"
            error_type = "-"
        except Exception as exc:  # noqa: PIE786
            dependencies[name] = "degraded" if degraded else "unavailable"
            check_status = dependencies[name]
            error_type = exc.__class__.__name__
        logger.info(
            "api.readiness service=api operation=readiness status=%s request_id=%s "
            "dependency=%s latency_ms=%.2f error_type=%s",
            check_status, request_id, name,
            (time.perf_counter() - start) * 1000, error_type,
        )

    async def http_check(name: str, url: str) -> None:
        start = time.perf_counter()
        error_type = "-"
        try:
            if not url:
                raise RuntimeError("service_not_configured")
            async with httpx.AsyncClient(timeout=READINESS_TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers={"X-Request-ID": request_id})
                response.raise_for_status()
            dependencies[name] = "ok"
        except Exception as exc:  # noqa: PIE786
            dependencies[name] = "unavailable"
            error_type = exc.__class__.__name__
        logger.info(
            "api.readiness service=api operation=readiness status=%s request_id=%s "
            "dependency=%s latency_ms=%.2f error_type=%s",
            dependencies[name], request_id, name,
            (time.perf_counter() - start) * 1000, error_type,
        )

    await asyncio.gather(
        local_check("postgres", _postgres_ready),
        local_check("redis", _redis_ready, degraded=True),
        http_check("embedding_service", _ready_url(EMBEDDING_SERVICE_URL, "/ready")),
        http_check("llm_service", _ready_url(LLM_SERVICE_STREAM_URL, "/ready")),
    )
    critical_ready = all(
        dependencies[name] == "ok"
        for name in ("postgres", "embedding_service", "llm_service")
    )
    payload = {
        "status": "ready" if critical_ready else "not_ready",
        "service": "api",
        "dependencies": dependencies,
    }
    return JSONResponse(payload, status_code=200 if critical_ready else 503)


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
    language: str | None = None
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

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        if value is not None and value not in {"es", "en"}:
            raise ValueError("language must be es or en")
        return value

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
    actor = current_actor(request)
    if actor:
        # The signed-in identity, not a browser-provided ID, owns conversation memory.
        return f"actor:{actor.google_sub}"

    if body.user_id:
        return f"browser:{body.user_id}"

    header_id = request.headers.get("X-User-Id")
    if header_id and USER_ID_PATTERN.match(header_id.strip()):
        return f"browser:{header_id.strip()}"

    cookie_id = request.cookies.get("sid")
    if cookie_id and USER_ID_PATTERN.match(cookie_id):
        return f"browser:{cookie_id}"

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
        r"\[[^\]]*(?:source|fragment|excerpt|passage)[^\]]*\]",
        r"\(\s*(?:sources?|fragments?|framents?|excerpts?|passages?)\s+[\d,\sandy&]+\)",
        r"fuentes?\s*:[^\n]*",
        r"fuente\s*\d+",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\[\s*\]", "", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
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
    language: str | None,
    role: str | None,
    history: list[dict[str, Any]],
    request_id: str,
) -> AgentState:
    return {
        "request_id": request_id,
        "user_id": user_id,
        "question": question,
        "language": language,
        "role": role,
        "context": [],
        "memory": history,
        "answer": None,
    }


@app.post("/chat")
async def chat(request: Request) -> Response:
    if _enabled("CHAT_LOGIN_REQUIRED") and not current_actor(request):
        raise HTTPException(status_code=401, detail="Sign in required")
    body = await _parse_chat_request(request)
    user_id = _resolve_user_id(body, request)
    identity = _rate_limit_identity(user_id, request)
    client_ip = request.client.host if request.client else None
    enforce_rate_limit(request_ip=client_ip, identity=identity)

    mem_enabled = bool(body.mem_opt_in and user_id != "anonymous")
    policy_decision = await _policy_decision(body.question, request.state.request_id)
    if policy_decision != "ALLOW":
        answer = refusal(policy_decision, response_language(body.question, body.language))
        await _record_chat_answer(request, body.question, answer, [])
        _append_memory(user_id, body.question, answer, mem_enabled)
        return JSONResponse({"answer": answer, "citations": []}, status_code=status.HTTP_200_OK)
    social_answer = conversational_reply(body.question, body.language)
    if social_answer is not None:
        await _record_chat_answer(request, body.question, social_answer, [])
        _append_memory(user_id, body.question, social_answer, mem_enabled)
        return JSONResponse({"answer": social_answer, "citations": []}, status_code=status.HTTP_200_OK)

    history = memory_store.load(user_id) if mem_enabled else []
    if not history and refers_to_previous_turn(body.question):
        answer = missing_context_reply(body.question, body.language, memory_enabled=mem_enabled)
        await _record_chat_answer(request, body.question, answer, [])
        _append_memory(user_id, body.question, answer, mem_enabled)
        return JSONResponse({"answer": answer, "citations": []}, status_code=status.HTTP_200_OK)
    state = _build_state(
        user_id=user_id,
        question=body.question,
        language=body.language,
        role=body.role,
        history=history,
        request_id=request.state.request_id,
    )

    try:
        result = await _invoke_agent(state)
    except AgentTimeoutError as exc:
        return _agent_error_response("Agent timeout", exc.trace_id)
    except AgentExecutionError as exc:
        return _agent_error_response("Agent execution error", exc.trace_id)

    clean_answer = strip_source_mentions(result.get("answer"))
    cited_context = result.get("context", [])
    followup = bool(history and refers_to_previous_turn(body.question))
    if result.get("context") and (_enabled("ANSWER_REQUIRE_SOURCES") or followup):
        try:
            clean_answer, supported = await asyncio.wait_for(
                asyncio.to_thread(grounded_followup_answer, result, clean_answer, followup=followup),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            if not supported:
                cited_context = []
        except Exception:  # noqa: PIE786 - never publish an unchecked follow-up
            logger.exception("agent.followup_verification_error request_id=%s", request.state.request_id)
            clean_answer = (
                unsupported_followup_reply(body.question, body.language)
                if followup else no_source_message(response_language(body.question, body.language))
            )
            cited_context = []
    clean_answer = strip_source_mentions(clean_answer)
    if cited_context:
        clean_answer, cited_context = await _answer_with_citations(result, clean_answer)
    if result.get("context") and not cited_context:
        fallback = await _extractive_fallback(result)
        if fallback:
            clean_answer, cited_context = fallback
        else:
            clean_answer = (
                unsupported_followup_reply(body.question, body.language)
                if followup else no_source_message(response_language(body.question, body.language))
            )
    await _record_chat_answer(request, body.question, clean_answer, cited_context)
    _append_memory(user_id, body.question, clean_answer, mem_enabled)

    return JSONResponse(
        {"answer": clean_answer, "citations": _public_citations(cited_context),
         "disclaimer": disclaimer_for(body.question, body.language) if cited_context else ""},
        status_code=status.HTTP_200_OK,
    )


@app.post("/chat/stream")
async def chat_stream(request: Request) -> Response:
    if _enabled("CHAT_LOGIN_REQUIRED") and not current_actor(request):
        raise HTTPException(status_code=401, detail="Sign in required")
    body = await _parse_chat_request(request)
    user_id = _resolve_user_id(body, request)
    identity = _rate_limit_identity(user_id, request)
    client_ip = request.client.host if request.client else None
    enforce_rate_limit(request_ip=client_ip, identity=identity)

    mem_enabled = bool(body.mem_opt_in and user_id != "anonymous")
    policy_decision = await _policy_decision(body.question, request.state.request_id)
    if policy_decision != "ALLOW":
        answer = refusal(policy_decision, response_language(body.question, body.language))
        await _record_chat_answer(request, body.question, answer, [])
        _append_memory(user_id, body.question, answer, mem_enabled)

        async def policy_stream():
            yield f"event: citations\ndata: []\n\n"
            yield f"event: delta\ndata: {json.dumps({'text': answer}, ensure_ascii=False)}\n\n"
            yield f"event: final\ndata: {json.dumps({'answer': answer}, ensure_ascii=False)}\n\n"

        return StreamingResponse(policy_stream(), media_type="text/event-stream")
    social_answer = conversational_reply(body.question, body.language)
    if social_answer is not None:
        await _record_chat_answer(request, body.question, social_answer, [])
        _append_memory(user_id, body.question, social_answer, mem_enabled)

        async def social_stream():
            yield f"event: citations\ndata: []\n\n"
            yield f"event: delta\ndata: {json.dumps({'text': social_answer}, ensure_ascii=False)}\n\n"
            yield f"event: final\ndata: {json.dumps({'answer': social_answer}, ensure_ascii=False)}\n\n"

        return StreamingResponse(social_stream(), media_type="text/event-stream")

    history = memory_store.load(user_id) if mem_enabled else []
    if not history and refers_to_previous_turn(body.question):
        answer = missing_context_reply(body.question, body.language, memory_enabled=mem_enabled)
        await _record_chat_answer(request, body.question, answer, [])
        _append_memory(user_id, body.question, answer, mem_enabled)

        async def clarification_stream():
            yield f"event: citations\ndata: []\n\n"
            yield f"event: delta\ndata: {json.dumps({'text': answer}, ensure_ascii=False)}\n\n"
            yield f"event: final\ndata: {json.dumps({'answer': answer}, ensure_ascii=False)}\n\n"

        return StreamingResponse(clarification_stream(), media_type="text/event-stream")
    state = _build_state(
        user_id=user_id,
        question=body.question,
        language=body.language,
        role=body.role,
        history=history,
        request_id=request.state.request_id,
    )

    try:
        # Retrieval is intentionally outside TTFT: the metric starts immediately
        # before opening the generation stream.
        result = await asyncio.wait_for(
            asyncio.to_thread(retrieve_node, state),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return _agent_error_response("Agent timeout", uuid4().hex)
    except Exception:  # noqa: PIE786
        trace_id = uuid4().hex
        logger.exception("agent.stream_retrieval_error trace_id=%s", trace_id)
        return _agent_error_response("Agent execution error", trace_id)

    def sse(event: str, data: Any) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    if _enabled("ANSWER_REQUIRE_SOURCES") and not result.get("context"):
        answer = (
            unsupported_followup_reply(body.question, body.language)
            if history and refers_to_previous_turn(body.question)
            else no_source_message(response_language(body.question, body.language))
        )
        await _record_chat_answer(request, body.question, answer, [])
        _append_memory(user_id, body.question, answer, mem_enabled)

        async def no_source_stream():
            yield sse("citations", [])
            yield sse("delta", {"text": answer})
            yield sse("final", {"answer": answer})

        return StreamingResponse(no_source_stream(), media_type="text/event-stream")

    followup = bool(history and refers_to_previous_turn(body.question))
    if _enabled("ANSWER_REQUIRE_SOURCES") or followup:
        try:
            answered = await asyncio.wait_for(
                asyncio.to_thread(answer_node, result),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            answer, supported = await asyncio.wait_for(
                asyncio.to_thread(
                    grounded_followup_answer, answered, strip_source_mentions(answered.get("answer")),
                    followup=followup,
                ),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
        except Exception:  # noqa: PIE786 - no unverified partial response is streamed
            logger.exception("agent.followup_answer_error request_id=%s", request.state.request_id)
            return _agent_error_response("Agent execution error", uuid4().hex)
        answer = strip_source_mentions(answer)
        cited_context = result.get("context", []) if supported else []
        logger.info("chat.grounding request_id=%s supported=%s retrieved=%d", request.state.request_id, supported, len(result.get("context", [])))
        if cited_context:
            answer, cited_context = await _answer_with_citations(result, answer)
            logger.info("chat.passages request_id=%s selected=%d", request.state.request_id, len(cited_context))
        if result.get("context") and not cited_context:
            fallback = await _extractive_fallback(result)
            if fallback:
                answer, cited_context = fallback
            else:
                answer = (
                    unsupported_followup_reply(body.question, body.language)
                    if followup else no_source_message(response_language(body.question, body.language))
                )
        await _record_chat_answer(request, body.question, answer, cited_context)
        _append_memory(user_id, body.question, answer, mem_enabled)

        async def grounded_stream():
            yield sse("citations", _public_citations(cited_context))
            if cited_context:
                yield sse("disclaimer", {"text": disclaimer_for(body.question, body.language)})
            yield sse("delta", {"text": answer})
            yield sse("final", {"answer": answer})

        return StreamingResponse(grounded_stream(), media_type="text/event-stream")

    prompt = build_answer_prompt(result)
    system_prompt = build_answer_system_prompt(result)
    request_id = request.state.request_id

    async def stream() -> Any:
        generation_start = time.perf_counter()
        first_token_ms: float | None = None
        chunks = 0
        characters = 0
        answer_parts: list[str] = []
        finish_reason = "stop"
        serving_mode = "http_service"
        model = os.getenv("MODEL_NAME", "gpt-4o-mini")
        upstream_error_type = "-"
        client_disconnected = False
        completed = False
        usage: dict[str, int] | None = None

        # Citations describe retrieval, so they are available before generation.
        yield sse("citations", [])

        async def accept_delta(text: str):
            nonlocal first_token_ms, chunks, characters
            if not text:
                return None
            if first_token_ms is None:
                first_token_ms = (time.perf_counter() - generation_start) * 1000
                metrics.record_graph_step(step="time_to_first_token_ms", duration_ms=first_token_ms)
            chunks += 1
            characters += len(text)
            answer_parts.append(text)
            return sse("delta", {"text": text})

        try:
            if not LLM_SERVICE_STREAM_URL:
                raise httpx.ConnectError("LLM_SERVICE_STREAM_URL is not configured")

            timeout = httpx.Timeout(LLM_SERVICE_TIMEOUT_SECONDS)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    LLM_SERVICE_STREAM_URL,
                    json={
                        "prompt": prompt,
                        "system_prompt": system_prompt,
                        "temperature": 0,
                        "metadata": {"request_id": request_id, "operation": "rag_answer"},
                    },
                    headers={"X-Request-ID": request_id},
                ) as upstream:
                    upstream.raise_for_status()
                    event_name = "message"
                    data_lines: list[str] = []
                    async for line in upstream.aiter_lines():
                        if await request.is_disconnected():
                            client_disconnected = True
                            break
                        if line.startswith("event:"):
                            event_name = line[6:].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line[5:].strip())
                        elif not line:
                            if not data_lines:
                                event_name = "message"
                                continue
                            payload = json.loads("\n".join(data_lines))
                            data_lines = []
                            if event_name == "metadata":
                                model = payload.get("model") or model
                                serving_mode = payload.get("serving_mode") or serving_mode
                                yield sse(event_name, payload)
                            elif event_name == "delta":
                                outgoing = await accept_delta(payload.get("text", ""))
                                if outgoing:
                                    yield outgoing
                            elif event_name == "usage":
                                usage = payload
                                yield sse(event_name, payload)
                            elif event_name == "done":
                                finish_reason = payload.get("finish_reason") or finish_reason
                                completed = True
                                yield sse(event_name, payload)
                            elif event_name == "error":
                                upstream_error_type = payload.get("code", "upstream_stream_error")
                                yield sse("error", payload)
                                return
                            event_name = "message"

            if client_disconnected:
                return
        except asyncio.CancelledError:
            # Starlette cancels the response task when the downstream socket closes.
            client_disconnected = True
            raise
        except Exception as exc:  # safe fallback only before a text delta
            upstream_error_type = exc.__class__.__name__
            if chunks:
                yield sse("error", {
                    "code": "upstream_stream_interrupted",
                    "message": "LLM stream interrupted.",
                })
                return

            serving_mode = "local_fallback_after_error"
            logger.warning(
                "agent.llm_stream fallback=local request_id=%s upstream_error_type=%s",
                request_id, upstream_error_type,
            )
            try:
                yield sse("metadata", {
                    "request_id": request_id, "model": model, "serving_mode": serving_mode,
                })
                async for chunk in local_llm.astream([SystemMessage(content=system_prompt), HumanMessage(content=prompt)]):
                    if await request.is_disconnected():
                        client_disconnected = True
                        return
                    content = chunk.content if isinstance(chunk.content, str) else ""
                    outgoing = await accept_delta(content)
                    if outgoing:
                        yield outgoing
                completed = True
                yield sse("usage", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
                yield sse("done", {"finish_reason": finish_reason})
            except Exception as fallback_exc:  # noqa: PIE786
                upstream_error_type = fallback_exc.__class__.__name__
                logger.exception("agent.llm_stream fallback_failed request_id=%s", request_id)
                yield sse("error", {
                    "code": "llm_stream_error", "message": "LLM generation failed.",
                })
                return
        finally:
            duration_ms = (time.perf_counter() - generation_start) * 1000
            metrics.record_graph_step(step="llm_stream_request", duration_ms=duration_ms)
            metrics.record_graph_step(step="llm_stream_total", duration_ms=duration_ms)
            metrics.record_graph_step(step="stream_duration_ms", duration_ms=duration_ms)
            metrics.record_graph_step(step="streamed_chunk_count", duration_ms=float(chunks))
            metrics.record_graph_step(step="streamed_character_count", duration_ms=float(characters))
            metrics.record_graph_step(step="llm", duration_ms=duration_ms)
            metrics.record_graph_step(step="generate_answer", duration_ms=duration_ms)
            if usage:
                metrics.record_token_usage(
                    endpoint="chat/stream",
                    prompt_tokens=int(usage.get("input_tokens", 0)),
                    completion_tokens=int(usage.get("output_tokens", 0)),
                )
            logger.info(
                "agent.llm_stream request_id=%s serving_mode=%s model=%s "
                "time_to_first_token_ms=%s stream_duration_ms=%.2f chunk_count=%s "
                "character_count=%s prompt_length=%s finish_reason=%s "
                "client_disconnected=%s upstream_error_type=%s",
                request_id, serving_mode, model,
                f"{first_token_ms:.2f}" if first_token_ms is not None else "-",
                duration_ms, chunks, characters, len(prompt), finish_reason,
                client_disconnected, upstream_error_type,
            )

        if completed:
            clean_answer = strip_source_mentions("".join(answer_parts))
            cited_context = result.get("context", [])
            if cited_context:
                cited_context = await _supported_passages(result, clean_answer)
                if not cited_context:
                    clean_answer = no_source_message(response_language(body.question, body.language))
            if cited_context:
                yield sse("citations", _public_citations(cited_context))
                yield sse("disclaimer", {"text": disclaimer_for(body.question, body.language)})
            try:
                await _record_chat_answer(request, body.question, clean_answer, cited_context)
            except Exception:
                logger.exception("chat.history_write_failed request_id=%s", request_id)
                yield sse("error", {"code": "history_unavailable", "message": "Answer could not be recorded."})
                return
            _append_memory(user_id, body.question, clean_answer, mem_enabled)
            # Retained for compatibility with the existing widget contract.
            yield sse("final", {"answer": clean_answer})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["app"]
