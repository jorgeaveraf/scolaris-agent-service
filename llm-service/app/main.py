from __future__ import annotations

import logging
import os
import re
import json
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_validator


logger = logging.getLogger("uvicorn.error")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

app = FastAPI(title="Agent Service LLM")


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
    except Exception as exc:  # noqa: PIE786
        logger.exception(
            "llm.request service=llm-service operation=http status=error request_id=%s "
            "latency_ms=%.2f error_type=%s",
            request_id, (time.perf_counter() - start) * 1000, exc.__class__.__name__,
        )
        response = JSONResponse(
            {"detail": "Internal server error", "request_id": request_id}, status_code=500,
        )
    response.headers["X-Request-ID"] = request.state.request_id
    return response


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
        raise RuntimeError(f"{name} must be a positive number.") from exc


MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
try:
    LLM_TIMEOUT_SECONDS = _float_env("LLM_TIMEOUT_SECONDS", 20.0)
    LLM_CONFIGURATION_VALID = True
except RuntimeError:
    # Keep liveness available; readiness reports the invalid configuration.
    LLM_TIMEOUT_SECONDS = 20.0
    LLM_CONFIGURATION_VALID = False

try:
    llm = ChatOpenAI(
        model=MODEL_NAME,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=2,
    )
except Exception:  # invalid/missing credentials must not break liveness
    llm = None


class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None
    temperature: float = Field(default=0, ge=0, le=2)
    metadata: dict[str, Any] | None = None

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if not prompt:
            raise ValueError("prompt must not be empty")
        return prompt


def _model_input(body: GenerateRequest):
    if body.system_prompt:
        return [SystemMessage(content=body.system_prompt), HumanMessage(content=body.prompt)]
    return body.prompt


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class GenerateResponse(BaseModel):
    text: str
    model: str
    usage: Usage


@app.get("/health")
def health(request: Request) -> dict[str, str]:
    logger.info(
        "llm.health service=llm-service operation=liveness status=ok request_id=%s",
        request.state.request_id,
    )
    return {"status": "ok", "service": "llm-service"}


@app.get("/ready")
def ready(request: Request) -> JSONResponse:
    request_id = request.state.request_id
    checks = {
        "configuration": "ok",
        "llm_client": "ok",
    }
    if not os.getenv("OPENAI_API_KEY") or not MODEL_NAME or not LLM_CONFIGURATION_VALID:
        checks["configuration"] = "error"
    if llm is None:
        checks["llm_client"] = "error"
    is_ready = all(value == "ok" for value in checks.values())
    logger.info(
        "llm.readiness service=llm-service operation=readiness status=%s "
        "request_id=%s latency_ms=0 dependency=configuration error_type=%s",
        "ready" if is_ready else "not_ready", request_id,
        "-" if is_ready else "ConfigurationError",
    )
    return JSONResponse(
        {
            "status": "ready" if is_ready else "not_ready",
            "service": "llm-service",
            "checks": checks,
        },
        status_code=200 if is_ready else 503,
    )


def _extract_usage(message) -> Usage:
    meta = getattr(message, "response_metadata", None) or {}
    usage = meta.get("token_usage") or meta.get("usage") or {}
    input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    total_tokens = usage.get("total_tokens") or (int(input_tokens) + int(output_tokens))
    return Usage(
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
        total_tokens=int(total_tokens),
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "") for item in content if isinstance(item, dict)
        )
    return ""


@app.post("/generate/stream")
async def generate_stream(body: GenerateRequest, request: Request) -> StreamingResponse:
    metadata = body.metadata or {}
    # The transport header is authoritative when payload metadata differs.
    request_id = (
        request.state.request_id
        if request.headers.get("X-Request-ID")
        else _request_id(str(metadata.get("request_id") or ""))
    )
    request.state.request_id = request_id
    operation = str(metadata.get("operation") or "")

    async def events():
        start = time.perf_counter()
        chunks = 0
        characters = 0
        usage = Usage()
        finish_reason = "stop"
        try:
            yield _sse("metadata", {
                "request_id": request_id,
                "model": MODEL_NAME,
                "serving_mode": "http_service",
            })
            streaming_llm = llm.bind(temperature=body.temperature)
            async for chunk in streaming_llm.astream(_model_input(body)):
                text = _chunk_text(chunk)
                if text:
                    chunks += 1
                    characters += len(text)
                    yield _sse("delta", {"text": text})
                chunk_usage = _extract_usage(chunk)
                if chunk_usage.total_tokens:
                    usage = chunk_usage
                response_metadata = getattr(chunk, "response_metadata", None) or {}
                finish_reason = response_metadata.get("finish_reason") or finish_reason

            yield _sse("usage", usage.model_dump())
            yield _sse("done", {"finish_reason": finish_reason})
            logger.info(
                "llm.stream_success request_id=%s operation=%s serving_mode=http_service "
                "model=%s stream_duration_ms=%.2f chunk_count=%s character_count=%s "
                "prompt_length=%s finish_reason=%s",
                request_id or "-", operation or "-", MODEL_NAME,
                (time.perf_counter() - start) * 1000, chunks, characters,
                len(body.prompt), finish_reason,
            )
        except Exception as exc:  # errors after response start stay in-band
            logger.exception(
                "llm.stream_error request_id=%s operation=%s serving_mode=http_service "
                "model=%s stream_duration_ms=%.2f chunk_count=%s prompt_length=%s "
                "upstream_error_type=%s",
                request_id or "-", operation or "-", MODEL_NAME,
                (time.perf_counter() - start) * 1000, chunks, len(body.prompt),
                exc.__class__.__name__,
            )
            yield _sse("error", {
                "code": "llm_stream_error",
                "message": "LLM generation failed.",
                "request_id": request_id,
            })

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/generate", response_model=GenerateResponse)
def generate(body: GenerateRequest, request: Request) -> GenerateResponse:
    metadata = body.metadata or {}
    request_id = (
        request.state.request_id
        if request.headers.get("X-Request-ID")
        else _request_id(str(metadata.get("request_id") or ""))
    )
    request.state.request_id = request_id
    operation = (body.metadata or {}).get("operation")
    start = time.perf_counter()

    try:
        message = llm.invoke(_model_input(body))
    except Exception as exc:  # noqa: PIE786
        logger.exception(
            "llm.generate_error request_id=%s operation=%s prompt_length=%s model=%s",
            request_id or "-",
            operation or "-",
            len(body.prompt),
            MODEL_NAME,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM generation failed.",
        ) from exc

    usage = _extract_usage(message)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "llm.generate_success request_id=%s operation=%s latency_ms=%.2f "
        "model=%s prompt_length=%s input_tokens=%s output_tokens=%s",
        request_id or "-",
        operation or "-",
        duration_ms,
        MODEL_NAME,
        len(body.prompt),
        usage.input_tokens,
        usage.output_tokens,
    )
    return GenerateResponse(text=message.content, model=MODEL_NAME, usage=usage)
