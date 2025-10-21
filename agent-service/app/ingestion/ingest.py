import hashlib
import os
import pathlib
import re
import unicodedata
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from ..retrieval.vector_store import VectorStore
from pypdf import PdfReader

DATA_DIR = pathlib.Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

emb = OpenAIEmbeddings(model=os.getenv("EMBED_MODEL", "text-embedding-3-small"))
vs = VectorStore(os.getenv("DATABASE_URL", "postgresql://scol:scolpwd@localhost:5432/scolaris"))

splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=120)

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_value.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lower).strip("-")
    return slug or "document"


def _build_doc_id(path: pathlib.Path) -> str:
    digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
    return f"{_slugify(path.stem)}:{digest}"


def _source_key(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(DATA_DIR))
    except ValueError:
        return path.name


def _title_from_path(path: pathlib.Path) -> str:
    candidate = re.sub(r"[_-]+", " ", path.stem).strip()
    return candidate.title() if candidate else path.stem


def _ingest_chunks(
    chunks: list[str],
    doc_id: str,
    title: str,
    source: str,
    role: str | None = None,
):
    if not chunks:
        return
    embeddings = emb.embed_documents(chunks)
    rows = [{
        "doc_id": doc_id,
        "title": title,
        "source": source,
        "chunks": [
            {"content": c, "metadata": {"role": role}, "embedding": e}
            for c, e in zip(chunks, embeddings)
        ],
    }]
    vs.upsert_chunks(rows)

def ingest_text_file(
    path: str | pathlib.Path,
    doc_id: str,
    title: str,
    role: str | None = None,
    source: str | None = None,
):
    path_obj = pathlib.Path(path)
    txt = path_obj.read_text(encoding="utf-8", errors="ignore")
    chunks = splitter.split_text(txt)
    _ingest_chunks(chunks, doc_id=doc_id, title=title, source=source or str(path_obj), role=role)

def ingest_pdf_file(
    path: str | pathlib.Path,
    doc_id: str,
    title: str,
    role: str | None = None,
    source: str | None = None,
):
    path_obj = pathlib.Path(path)
    reader = PdfReader(str(path_obj))
    pages = []
    for page in reader.pages:
        content = page.extract_text()
        if content:
            pages.append(content)
    if not pages:
        raise ValueError("El PDF no contiene texto extraíble.")
    combined = "\n\n".join(pages)
    chunks = splitter.split_text(combined)
    _ingest_chunks(chunks, doc_id=doc_id, title=title, source=source or str(path_obj), role=role)


def ingest_path(path: pathlib.Path, role: str | None = None) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return "unsupported"

    doc_id = _build_doc_id(path)
    if vs.document_exists(doc_id):
        print(f"Saltando {path.name}: ya existe (doc_id={doc_id}).")
        return "skipped"

    title = _title_from_path(path)
    source = _source_key(path)

    try:
        if suffix == ".txt":
            ingest_text_file(path, doc_id=doc_id, title=title, role=role, source=source)
        elif suffix == ".pdf":
            ingest_pdf_file(path, doc_id=doc_id, title=title, role=role, source=source)
        print(f"Ingestado {path.name} -> doc_id={doc_id}")
        return "ingested"
    except Exception as exc:
        print(f"Error al procesar {path.name}: {exc}")
        return "error"


def process_directory(role: str | None = None):
    counts = {"ingested": 0, "skipped": 0, "error": 0}
    for path in sorted(DATA_DIR.glob("**/*")):
        if not path.is_file():
            continue
        status = ingest_path(path, role=role)
        if status in counts:
            counts[status] += 1
    return counts

if __name__ == "__main__":
    stats = process_directory()
    total = sum(stats.values())
    if stats["ingested"]:
        print(f"Ingesta completa: {stats['ingested']} nuevos, {stats['skipped']} omitidos.")
    elif stats["skipped"]:
        print(f"Sin documentos nuevos. {stats['skipped']} ya estaban cargados.")
    elif total == 0:
        print("No se encontraron documentos .txt o .pdf en", DATA_DIR)
    if stats["error"]:
        print(f"{stats['error']} archivos fallaron; revisa los mensajes anteriores.")
