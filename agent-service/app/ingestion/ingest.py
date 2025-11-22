import hashlib
import math
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

ENV_ALLOWED_EXTS = os.getenv("ALLOWED_EXTS", ".pdf,.docx,.txt,.md,.html")
SUPPORTED_EXTENSIONS = {
    ext.lower().strip()
    for ext in ENV_ALLOWED_EXTS.split(",")
    if ext.strip()
} or {".pdf", ".txt"}
TEXTUAL_EXTENSIONS = {".txt", ".md"}


def _estimate_tokens(text: str) -> int:
    # Simple heuristic: average 4 characters per token
    return max(1, math.ceil(len(text) / 4))


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
    metadata: dict[str, str] | None = None,
):
    if not chunks:
        return 0
    metadata = {k: v for k, v in (metadata or {}).items() if v is not None}
    embeddings = emb.embed_documents(chunks)
    rows = [{
        "doc_id": doc_id,
        "title": title,
        "source": source,
        "chunks": [
            {
                "content": c,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "tokens": _estimate_tokens(c),
                },
                "embedding": e,
            }
            for i, (c, e) in enumerate(zip(chunks, embeddings))
        ],
    }]
    vs.upsert_chunks(rows)
    return len(chunks)

def ingest_text_file(
    path: str | pathlib.Path,
    doc_id: str,
    title: str,
    role: str | None = None,
    source: str | None = None,
    metadata: dict[str, str] | None = None,
):
    path_obj = pathlib.Path(path)
    txt = path_obj.read_text(encoding="utf-8", errors="ignore")
    chunks = splitter.split_text(txt)
    chunk_metadata = {
        "role": role,
        "filename": path_obj.name,
        **({} if metadata is None else metadata),
    }
    return _ingest_chunks(
        chunks,
        doc_id=doc_id,
        title=title,
        source=source or str(path_obj),
        metadata=chunk_metadata,
    )

def ingest_pdf_file(
    path: str | pathlib.Path,
    doc_id: str,
    title: str,
    role: str | None = None,
    source: str | None = None,
    metadata: dict[str, str] | None = None,
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
    chunk_metadata = {
        "role": role,
        "filename": path_obj.name,
        **({} if metadata is None else metadata),
    }
    return _ingest_chunks(
        chunks,
        doc_id=doc_id,
        title=title,
        source=source or str(path_obj),
        metadata=chunk_metadata,
    )


def _load_docx_text(path: pathlib.Path) -> str:
    from docx import Document

    document = Document(str(path))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _load_html_text(path: pathlib.Path) -> str:
    from bs4 import BeautifulSoup

    html_raw = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html_raw, "html.parser")
    text = soup.get_text(separator="\n")
    return text.strip()


def ingest_uploaded_file(
    path: str | pathlib.Path,
    *,
    area: str | None = None,
    role: str | None = None,
    vigencia: str | None = None,
    title: str | None = None,
) -> tuple[str, int]:
    path_obj = pathlib.Path(path)
    suffix = path_obj.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Extensión no soportada: {suffix}")

    doc_id = _build_doc_id(path_obj)
    source = _source_key(path_obj)
    title = title or _title_from_path(path_obj)
    base_metadata = {
        "role": role,
        "area": area,
        "vigencia": vigencia,
        "filename": path_obj.name,
    }

    if suffix == ".pdf":
        chunk_count = ingest_pdf_file(
            path_obj,
            doc_id=doc_id,
            title=title,
            role=role,
            source=source,
            metadata={"area": area, "vigencia": vigencia},
        )
    elif suffix in TEXTUAL_EXTENSIONS:
        chunk_count = ingest_text_file(
            path_obj,
            doc_id=doc_id,
            title=title,
            role=role,
            source=source,
            metadata={"area": area, "vigencia": vigencia},
        )
    elif suffix == ".docx":
        text = _load_docx_text(path_obj)
        chunks = splitter.split_text(text)
        chunk_count = _ingest_chunks(
            chunks,
            doc_id=doc_id,
            title=title,
            source=source,
            metadata=base_metadata,
        )
    elif suffix in {".html", ".htm"}:
        text = _load_html_text(path_obj)
        chunks = splitter.split_text(text)
        chunk_count = _ingest_chunks(
            chunks,
            doc_id=doc_id,
            title=title,
            source=source,
            metadata=base_metadata,
        )
    else:
        raise ValueError(f"Extensión no soportada: {suffix}")

    return doc_id, chunk_count


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
        ingest_uploaded_file(
            path,
            role=role,
            area=None,
            vigencia=None,
            title=title,
        )
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
