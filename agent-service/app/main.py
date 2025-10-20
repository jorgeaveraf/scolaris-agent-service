# agent-service/app/main.py
import os, json, secrets
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from .init import init_db
from .agent.graph import app_graph, AgentState
from .agent.graph import graph as _graph  # opcional: si usas el stream paso a paso

app = FastAPI(title="Scolaris Agent API")

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
def start_session(response: Response):
    sid = secrets.token_urlsafe(16)
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

# --- Chat sin streaming ---
@app.post("/chat")
def chat(body: ChatIn):
    state: AgentState = {
        "question": body.question,
        "role": body.role,
        "context": [],
        "answer": None
    }
    result = app_graph.invoke(state)
    return JSONResponse({"answer": result["answer"], "citations": result["context"]})

# --- Chat con streaming (SSE) ---
@app.post("/chat/stream")
def chat_stream(body: ChatIn):
    def _gen():
        state: AgentState = {
            "question": body.question,
            "role": body.role,
            "context": [],
            "answer": None
        }
        # Paso 1: retrieve
        s1 = _graph.get_state({}).apply("retrieve", state)
        citations_json = json.dumps(s1["context"])
        yield f"event: citations\ndata: {citations_json}\n\n"

        # Paso 2: answer
        s2 = _graph.get_state({}).apply("answer", s1)
        final_json = json.dumps({"answer": s2["answer"]})
        yield f"event: final\ndata: {final_json}\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
