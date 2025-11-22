from typing import TypedDict, List, Dict, Optional
import os
import re
import time

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, StateGraph

from ..observability.metrics import metrics
from ..retrieval.vector_store import VectorStore


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
EMBED_TIMEOUT_SECONDS = _float_env("EMBED_TIMEOUT_SECONDS", 10.0)


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


# --- Recupera contexto (RAG) ---
def retrieve_node(state: AgentState):
    q = state["question"]
    q_emb = emb.embed_query(q)
    role = state.get("role")
    filters = {"role": role} if role else None
    results = vs.search(q_emb, k=5, filters=filters, qtext=q)
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

    start = time.perf_counter()
    out = llm.invoke(prompt)
    duration_ms = (time.perf_counter() - start) * 1000
    metrics.record_graph_step(step="llm", duration_ms=duration_ms)

    usage = _extract_token_usage(out)
    if usage:
        state["tokens"] = usage
        metrics.record_token_usage(
            endpoint="chat",
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    state["answer"] = out.content
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
