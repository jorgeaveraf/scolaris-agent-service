from __future__ import annotations

import logging
import os
import re
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, field_validator


logger = logging.getLogger("uvicorn.error")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

app = FastAPI(title="Agent Service Embeddings")


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
            "embedding.request service=embedding-service operation=http status=error "
            "request_id=%s latency_ms=%.2f error_type=%s",
            request_id, (time.perf_counter() - start) * 1000, exc.__class__.__name__,
        )
        response = JSONResponse(
            {"detail": "Internal server error", "request_id": request_id}, status_code=500,
        )
    response.headers["X-Request-ID"] = request_id
    return response

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
try:
    EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))
    EMBED_CONFIGURATION_VALID = EMBED_DIM > 0
except ValueError:
    EMBED_DIM = 0
    EMBED_CONFIGURATION_VALID = False

try:
    embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
except Exception:  # invalid/missing credentials must not break liveness
    embeddings = None


class EmbedRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("text must not be empty")
        return text


class EmbedResponse(BaseModel):
    embedding: list[float]
    model: str
    dimension: int


@app.get("/health")
def health(request: Request) -> dict[str, str]:
    logger.info(
        "embedding.health service=embedding-service operation=liveness status=ok request_id=%s",
        request.state.request_id,
    )
    return {"status": "ok", "service": "embedding-service"}


@app.get("/ready")
def ready(request: Request) -> JSONResponse:
    request_id = request.state.request_id
    configuration_ok = bool(
        os.getenv("OPENAI_API_KEY") and EMBED_MODEL and EMBED_CONFIGURATION_VALID
    )
    checks = {
        "configuration": "ok" if configuration_ok else "error",
        "embedding_client": "ok" if embeddings is not None else "error",
    }
    is_ready = all(value == "ok" for value in checks.values())
    logger.info(
        "embedding.readiness service=embedding-service operation=readiness status=%s "
        "request_id=%s latency_ms=0 dependency=configuration error_type=%s",
        "ready" if is_ready else "not_ready", request_id,
        "-" if is_ready else "ConfigurationError",
    )
    return JSONResponse(
        {
            "status": "ready" if is_ready else "not_ready",
            "service": "embedding-service",
            "checks": checks,
        },
        status_code=200 if is_ready else 503,
    )


@app.post("/embed", response_model=EmbedResponse)
def embed(body: EmbedRequest, request: Request) -> EmbedResponse:
    request_id = request.state.request_id
    start = time.perf_counter()
    try:
        vector = embeddings.embed_query(body.text)
    except Exception as exc:  # noqa: PIE786
        logger.exception(
            "embedding.embed_error service=embedding-service operation=embed status=error "
            "request_id=%s query_length=%s model=%s error_type=%s",
            request_id,
            len(body.text),
            EMBED_MODEL,
            exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding generation failed.",
        ) from exc

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "embedding.embed_success service=embedding-service operation=embed status=ok "
        "request_id=%s latency_ms=%.2f query_length=%s dimension=%s model=%s",
        request_id,
        duration_ms,
        len(body.text),
        len(vector),
        EMBED_MODEL,
    )
    return EmbedResponse(embedding=vector, model=EMBED_MODEL, dimension=len(vector))
