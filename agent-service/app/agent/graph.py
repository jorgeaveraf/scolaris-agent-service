from typing import TypedDict, List, Dict
import os
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ..retrieval.vector_store import VectorStore

class AgentState(TypedDict):
    question: str
    role: str | None
    context: List[Dict]
    answer: str | None

llm = ChatOpenAI(model=os.getenv("MODEL_NAME", "gpt-4o-mini"))
emb = OpenAIEmbeddings(model=os.getenv("EMBED_MODEL", "text-embedding-3-small"))
vs = VectorStore(os.getenv("DATABASE_URL", "postgresql://scol:scolpwd@localhost:5432/scolaris"))

def retrieve_node(state: AgentState):
    q = state["question"]
    q_emb = emb.embed_query(q)
    role = state.get("role")
    filters = {"role": role} if role else None
    results = vs.search(q_emb, k=5, filters=filters, qtext=q)
    state["context"] = results
    return state


def answer_node(state: AgentState):
    ctx = "\n\n".join([f"[Fuente {i+1} score={c['score']:.2f}]\n{c['content']}" for i, c in enumerate(state["context"])])
    prompt = (
        "Responde SOLO con información que esté EXACTAMENTE en las fuentes. "
        "Cita entre [ ] el número de fuente usada. Si no aparece explícito, responde 'No hay evidencia suficiente'.\n\n"
        f"Pregunta: {state['question']}\n\nFuentes:\n{ctx}"
    )
    out = llm.invoke(prompt)
    state["answer"] = out.content
    return state

graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve_node)
graph.add_node("answer", answer_node)
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "answer")
graph.add_edge("answer", END)
app_graph = graph.compile()
