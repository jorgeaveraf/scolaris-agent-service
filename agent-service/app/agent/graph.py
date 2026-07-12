from typing import TypedDict, List, Dict, Optional
import logging
import os
import re
import time
from uuid import uuid4

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, StateGraph

from ..observability.metrics import metrics
from ..retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    user_id: str | None
    question: str
    role: str | None
    context: List[Dict]
    memory: List[Dict]
    answer: str | None
    tokens: Optional[Dict[str, int]]


# --- Configuración ---
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


LLM_TIMEOUT_SECONDS = _float_env("LLM_TIMEOUT_SECONDS", 20.0)
LLM_SERVICE_TIMEOUT_SECONDS = _float_env("LLM_SERVICE_TIMEOUT_SECONDS", LLM_TIMEOUT_SECONDS)
LLM_SERVICE_URL = (os.getenv("LLM_SERVICE_URL") or "").strip()
EMBED_TIMEOUT_SECONDS = _float_env("EMBED_TIMEOUT_SECONDS", 10.0)
EMBEDDING_SERVICE_TIMEOUT_SECONDS = _float_env(
    "EMBEDDING_SERVICE_TIMEOUT_SECONDS",
    min(EMBED_TIMEOUT_SECONDS, 5.0),
)
EMBEDDING_SERVICE_URL = (os.getenv("EMBEDDING_SERVICE_URL") or "").strip()


# --- Inicialización ---
llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
    timeout=LLM_TIMEOUT_SECONDS,
    max_retries=2,
)
emb = OpenAIEmbeddings(
    model=os.getenv("EMBED_MODEL", "text-embedding-3-small"),
    request_timeout=EMBED_TIMEOUT_SECONDS,
)
vs = VectorStore(os.getenv("DATABASE_URL", "postgresql://scol:scolpwd@localhost:5432/scolaris"))


def _local_embed_query(text: str) -> list[float]:
    return emb.embed_query(text)


def _service_embed_query(text: str) -> list[float]:
    response = httpx.post(
        EMBEDDING_SERVICE_URL,
        json={"text": text},
        timeout=EMBEDDING_SERVICE_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    embedding = payload.get("embedding")
    if not isinstance(embedding, list):
        raise RuntimeError("embedding-service returned an invalid embedding payload.")
    return embedding


def _embed_query(text: str) -> tuple[list[float], str]:
    if not EMBEDDING_SERVICE_URL:
        return _local_embed_query(text), "local_fallback"

    try:
        return _service_embed_query(text), "embedding_service"
    except Exception as exc:  # noqa: PIE786 - fallback keeps serving available
        logger.warning(
            "agent.embedding fallback=local reason=%s service_url_configured=%s",
            exc.__class__.__name__,
            bool(EMBEDDING_SERVICE_URL),
        )
        return _local_embed_query(text), "local_fallback_after_error"


def _extract_usage_from_payload(payload: dict) -> dict[str, int] | None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None

    prompt_tokens = usage.get("prompt_tokens")
    if prompt_tokens is None:
        prompt_tokens = usage.get("input_tokens")

    completion_tokens = usage.get("completion_tokens")
    if completion_tokens is None:
        completion_tokens = usage.get("output_tokens")

    total_tokens = usage.get("total_tokens")
    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        return None

    prompt = int(prompt_tokens or 0)
    completion = int(completion_tokens or 0)
    total = int(total_tokens or (prompt + completion))
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


def _invoke_llm_local(prompt: str):
    out = llm.invoke(prompt)
    usage = _extract_token_usage(out)
    return out.content, usage, os.getenv("MODEL_NAME", "gpt-4o-mini"), "local_fallback"


def _invoke_llm_service(prompt: str, request_id: str):
    request_start = time.perf_counter()
    try:
        response = httpx.post(
            LLM_SERVICE_URL,
            json={
                "prompt": prompt,
                "temperature": 0,
                "metadata": {
                    "request_id": request_id,
                    "operation": "rag_answer",
                },
            },
            timeout=LLM_SERVICE_TIMEOUT_SECONDS,
        )
    finally:
        request_ms = (time.perf_counter() - request_start) * 1000
        metrics.record_graph_step(step="llm_request", duration_ms=request_ms)

    response.raise_for_status()
    payload = response.json()
    text = payload.get("text")
    model = payload.get("model") or os.getenv("MODEL_NAME", "gpt-4o-mini")
    if not isinstance(text, str):
        raise RuntimeError("llm-service returned an invalid text payload.")
    usage = _extract_usage_from_payload(payload)
    return text, usage, model, "http_service", request_ms


def _invoke_llm(prompt: str, request_id: str):
    if not LLM_SERVICE_URL:
        text, usage, model, mode = _invoke_llm_local(prompt)
        return text, usage, model, mode

    try:
        text, usage, model, mode, _ = _invoke_llm_service(prompt, request_id)
        return text, usage, model, mode
    except httpx.TimeoutException as exc:
        reason = "timeout"
        error = exc
    except httpx.ConnectError as exc:
        reason = "connection_error"
        error = exc
    except httpx.HTTPStatusError as exc:
        reason = f"http_status_{exc.response.status_code}"
        error = exc
    except (ValueError, RuntimeError) as exc:
        reason = "invalid_response"
        error = exc
    except Exception as exc:  # noqa: PIE786 - fallback keeps serving available
        reason = exc.__class__.__name__
        error = exc

    logger.warning(
        "agent.llm fallback=local reason=%s request_id=%s service_url_configured=%s",
        reason,
        request_id,
        bool(LLM_SERVICE_URL),
    )

    try:
        text, usage, model, _ = _invoke_llm_local(prompt)
        return text, usage, model, "local_fallback_after_error"
    except Exception as fallback_exc:  # noqa: PIE786
        logger.exception(
            "agent.llm fallback_failed request_id=%s original_reason=%s fallback_reason=%s",
            request_id,
            reason,
            fallback_exc.__class__.__name__,
        )
        raise RuntimeError("LLM generation failed in service and local fallback.") from error


# --- Recupera contexto (RAG) ---
def retrieve_node(state: AgentState):
    total_start = time.perf_counter()
    q = state["question"]
    query_length = len(q)

    embedding_start = time.perf_counter()
    q_emb, embedding_source = _embed_query(q)
    embedding_ms = (time.perf_counter() - embedding_start) * 1000
    metrics.record_graph_step(step="embedding_query", duration_ms=embedding_ms)
    logger.info(
        "agent.embedding step=embedding_query latency_ms=%.2f query_length=%s source=%s",
        embedding_ms,
        query_length,
        embedding_source,
    )

    role = state.get("role")
    filters = {"role": role} if role else None

    search_start = time.perf_counter()
    results = vs.search(q_emb, k=5, filters=filters, qtext=q)
    search_ms = (time.perf_counter() - search_start) * 1000
    metrics.record_graph_step(step="vector_search", duration_ms=search_ms)

    total_ms = (time.perf_counter() - total_start) * 1000
    metrics.record_graph_step(step="retrieval_total", duration_ms=total_ms)

    logger.info(
        "agent.retrieve step=retrieval_total latency_ms=%.2f embedding_ms=%.2f "
        "vector_search_ms=%.2f docs_count=%s query_length=%s",
        total_ms,
        embedding_ms,
        search_ms,
        len(results),
        query_length,
    )

    state["context"] = results
    return state


# --- Genera respuesta comercial (sin citas) ---
def answer_node(state: AgentState):
    # --- Limpiamos el texto del contexto ---
    cleaned_chunks = []
    for c in state["context"]:
        text = c["content"]
        # elimina patrones tipo [Fuente 1], (Fuente 2), etc.
        text = re.sub(r"\[Fuente\s*\d+\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\(Fuente\s*\d+\)", "", text, flags=re.IGNORECASE)
        text = text.replace("Fuente:", "").strip()
        cleaned_chunks.append(text)

    ctx = "\n\n".join(cleaned_chunks)

    history = state.get("memory", [])
    history_lines = []
    for message in history:
        role = message.get("role")
        speaker = "Usuario" if role == "user" else "Asistente"
        history_lines.append(f"{speaker}: {message.get('content', '').strip()}")
    history_block = "\n".join([line for line in history_lines if line])

    history_prompt = ""
    if history_block:
        history_prompt = f"Historial reciente:\n{history_block}\n\n"

    prompt = (
        "Eres un asesor comercial experto de *Scolaris*, un sistema para la gestión escolar. "
        "Respondes de forma clara, amable y persuasiva, con el tono de un consultor de ventas profesional. "
        "Tu objetivo es ayudar a un posible cliente a comprender los beneficios de Scolaris sin usar tecnicismos.\n\n"

        "**Estilo y reglas de respuesta:**\n"
        "- Mantén las respuestas **compactas y directas** (máximo 3–5 líneas) a menos que el cliente pida más detalles.\n"
        "- Si el usuario solicita “más información” o “detalles”, entonces puedes **expandir** con ejemplos o módulos.\n"
        "- Usa un tono positivo, confiado y enfocado en **beneficios reales** (ahorro de tiempo, facilidad, organización, etc.).\n"
        "- No cites fuentes, referencias ni puntajes técnicos.\n"
        "- Evita frases genéricas como “Scolaris es el mejor” y enfócate en **por qué** resulta útil para el cliente.\n\n"

        f"{history_prompt}"

        f"**Pregunta del cliente:**\n{state['question']}\n\n"

        f"**Información de soporte (solo para tu contexto, no la menciones directamente):**\n{ctx}\n\n"
    )

    request_id = uuid4().hex
    start = time.perf_counter()
    answer, usage, model, serving_mode = _invoke_llm(prompt, request_id)
    duration_ms = (time.perf_counter() - start) * 1000
    metrics.record_graph_step(step="llm_total", duration_ms=duration_ms)
    metrics.record_graph_step(step="llm", duration_ms=duration_ms)

    prompt_tokens = usage.get("prompt_tokens", 0) if usage else 0
    completion_tokens = usage.get("completion_tokens", 0) if usage else 0
    logger.info(
        "agent.llm step=llm_total serving_mode=%s latency_ms=%.2f model=%s "
        "prompt_length=%s input_tokens=%s output_tokens=%s request_id=%s",
        serving_mode,
        duration_ms,
        model,
        len(prompt),
        prompt_tokens,
        completion_tokens,
        request_id,
    )

    if usage:
        state["tokens"] = usage
        metrics.record_token_usage(
            endpoint="chat",
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    state["answer"] = answer
    return state


def _extract_token_usage(message) -> dict[str, int] | None:
    meta = getattr(message, "response_metadata", None) or {}
    usage = meta.get("token_usage") or meta.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
    total_tokens = usage.get("total_tokens")

    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        return None

    prompt = int(prompt_tokens or 0)
    completion = int(completion_tokens or 0)
    total = int(total_tokens or (prompt + completion))
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


# --- Grafo ---
def _timed(name: str, fn):
    def wrapper(state: AgentState):
        start = time.perf_counter()
        result = fn(state)
        duration_ms = (time.perf_counter() - start) * 1000
        metrics.record_graph_step(step=name, duration_ms=duration_ms)
        return result

    return wrapper


graph = StateGraph(AgentState)
graph.add_node("retrieve", _timed("retrieve", retrieve_node))
graph.add_node("generate_answer", _timed("generate_answer", answer_node))
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "generate_answer")
graph.add_edge("generate_answer", END)
app_graph = graph.compile()
