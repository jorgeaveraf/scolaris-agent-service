from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI, HTTPException, status
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, field_validator


logger = logging.getLogger(__name__)

app = FastAPI(title="Scolaris Embedding Service")

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))
embeddings = OpenAIEmbeddings(model=EMBED_MODEL)


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
def health() -> dict[str, bool | str | int]:
    return {"ok": True, "model": EMBED_MODEL, "dimension": EMBED_DIM}


@app.post("/embed", response_model=EmbedResponse)
def embed(body: EmbedRequest) -> EmbedResponse:
    start = time.perf_counter()
    try:
        vector = embeddings.embed_query(body.text)
    except Exception as exc:  # noqa: PIE786
        logger.exception(
            "embedding.embed_error query_length=%s model=%s",
            len(body.text),
            EMBED_MODEL,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding generation failed.",
        ) from exc

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "embedding.embed_success latency_ms=%.2f query_length=%s dimension=%s model=%s",
        duration_ms,
        len(body.text),
        len(vector),
        EMBED_MODEL,
    )
    return EmbedResponse(embedding=vector, model=EMBED_MODEL, dimension=len(vector))
