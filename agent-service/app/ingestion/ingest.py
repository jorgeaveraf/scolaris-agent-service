import os, json, pathlib
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from ..retrieval.vector_store import VectorStore

DATA_DIR = pathlib.Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

emb = OpenAIEmbeddings(model=os.getenv("EMBED_MODEL", "text-embedding-3-small"))
vs = VectorStore(os.getenv("DATABASE_URL", "postgresql://scol:scolpwd@localhost:5432/scolaris"))

splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=120)

def ingest_text_file(path: str, doc_id: str, title: str, role: str | None = None):
    txt = open(path, "r", encoding="utf-8").read()
    chunks = splitter.split_text(txt)
    rows = []
    ecs = emb.embed_documents(chunks)
    rows.append({
        "doc_id": doc_id,
        "title": title,
        "source": path,
        "chunks": [
            {"content": c, "metadata": {"role": role}, "embedding": e}
            for c, e in zip(chunks, ecs)
        ],
    })
    vs.upsert_chunks(rows)

if __name__ == "__main__":
    sample = DATA_DIR / "reglamento_general.txt"
    if sample.exists():
        ingest_text_file(str(sample), doc_id="reglamento_general:v1", title="Reglamento General", role=None)
        print("Ingesta completa")
    else:
        print("Coloca documentos .txt en", DATA_DIR, "y ejecuta este script.")
