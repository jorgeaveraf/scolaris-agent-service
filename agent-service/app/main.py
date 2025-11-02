# agent-service/app/main.py
import logging
import os, json, secrets, re
from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from .init import init_db
from .admin import register_admin_module
from .agent.graph import app_graph, AgentState
from .agent.graph import graph as _graph  # opcional: si usas el stream paso a paso
from .agent.memory import memory_store

logger = logging.getLogger(__name__)

app = FastAPI(title="Scolaris Agent API")

register_admin_module(app)

# --- CORS (importante para el widget) ---
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,      # <- requerido si usas cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup ---
@app.on_event("startup")
def _startup():
    init_db()

# --- Health ---
@app.get("/health")
def health():
    return {"ok": True}

# --- Sesión: setea cookie 'sid' ---
@app.post("/session/start")
def start_session(response: Response, request: Request):
    sid = request.cookies.get("sid") or secrets.token_urlsafe(16)
    secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # en prod: true
    samesite = os.getenv("COOKIE_SAMESITE", "lax")
    domain = os.getenv("COOKIE_DOMAIN")  # en dev: None
    response.set_cookie(
        "sid", sid,
        httponly=True,
        secure=secure,
        samesite=samesite,
        domain=domain
    )
    return {"sid": sid}

# --- DTO ---
class ChatIn(BaseModel):
    question: str
    role: str | None = None
    user_id: str | None = None
    mem_opt_in: bool = False


def _resolve_user_id(request: Request) -> str:
    header_id = request.headers.get("X-User-Id")
    if header_id:
        return header_id
    cookie_id = request.cookies.get("sid")
    if cookie_id:
        return cookie_id
    return "anonymous"


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

# --- Chat sin streaming ---
@app.post("/chat")
def chat(body: ChatIn, request: Request):
    user_id = body.user_id or _resolve_user_id(request)
    mem_enabled = bool(body.mem_opt_in and user_id)
    history = memory_store.load(user_id) if mem_enabled else []

    state: AgentState = {
        "user_id": user_id,
        "question": body.question,
        "role": body.role,
        "context": [],
        "memory": history,
        "answer": None,
    }
    result = app_graph.invoke(state)

    clean_answer = strip_source_mentions(result.get("answer"))

    if mem_enabled:
        memory_store.append_messages(user_id, [
            {"role": "user", "content": body.question},
            {"role": "assistant", "content": clean_answer},
        ])

    return JSONResponse({
        "answer": clean_answer,
        "citations": []   # <- devolvemos vacío para el widget
    })

# --- Chat con streaming (SSE) ---
@app.post("/chat/stream")
def chat_stream(body: ChatIn, request: Request):
    user_id = body.user_id or _resolve_user_id(request)
    mem_enabled = bool(body.mem_opt_in and user_id)
    history = memory_store.load(user_id) if mem_enabled else []

    def _gen():
        state: AgentState = {
            "user_id": user_id,
            "question": body.question,
            "role": body.role,
            "context": [],
            "memory": history,
            "answer": None,
        }
        # Paso 1: retrieve
        s1 = _graph.get_state({}).apply("retrieve", state)
        citations_json = json.dumps(s1["context"])
        yield f"event: citations\ndata: {citations_json}\n\n"

        # Paso 2: answer
        s2 = _graph.get_state({}).apply("answer", s1)
        clean_answer = strip_source_mentions(s2.get("answer"))
        if mem_enabled:
            memory_store.append_messages(user_id, [
                {"role": "user", "content": body.question},
                {"role": "assistant", "content": clean_answer},
            ])
        final_json = json.dumps({"answer": clean_answer})
        yield f"event: final\ndata: {final_json}\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
