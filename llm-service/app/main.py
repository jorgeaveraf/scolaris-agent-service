from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import FastAPI, HTTPException, status
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator


logger = logging.getLogger(__name__)

app = FastAPI(title="Scolaris LLM Service")


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
LLM_TIMEOUT_SECONDS = _float_env("LLM_TIMEOUT_SECONDS", 20.0)

llm = ChatOpenAI(
    model=MODEL_NAME,
    timeout=LLM_TIMEOUT_SECONDS,
    max_retries=2,
)


class GenerateRequest(BaseModel):
    prompt: str
    temperature: float = Field(default=0, ge=0, le=2)
    metadata: dict[str, Any] | None = None

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if not prompt:
            raise ValueError("prompt must not be empty")
        return prompt


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class GenerateResponse(BaseModel):
    text: str
    model: str
    usage: Usage


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "llm-service", "model": MODEL_NAME}


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


@app.post("/generate", response_model=GenerateResponse)
def generate(body: GenerateRequest) -> GenerateResponse:
    request_id = (body.metadata or {}).get("request_id")
    operation = (body.metadata or {}).get("operation")
    start = time.perf_counter()

    try:
        message = llm.invoke(body.prompt)
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
