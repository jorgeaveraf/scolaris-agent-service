"""Reject active files and instructions aimed at the assistant before indexing.

This is a conservative intake policy, not a claim that every possible prompt
injection can be recognized. Retrieved chunks receive the same check again.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile

from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader


MAX_EXTRACTED_CHARS = 2_000_000
MAX_PDF_PAGES = 100
MAX_DOCX_MEMBERS = 500
MAX_DOCX_UNCOMPRESSED_BYTES = 40 * 1024 * 1024
ACTIVE_HTML_TAGS = {"script", "iframe", "object", "embed", "form", "base"}


class UnsafeDocumentError(ValueError):
    """The document cannot safely enter the searchable corpus."""


_INSTRUCTION_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in (
    r"\b(?:ignore|disregard|override|forget)\b.{0,100}\b(?:previous|prior|earlier|system|developer|instructions?|rules?)\b",
    r"\b(?:reveal|print|show|disclose|expose|leak)\b.{0,100}\b(?:system prompt|developer instructions?|hidden prompt|api key|secrets?|tokens?)\b",
    r"\b(?:assistant|system|developer)\s*(?:override|instructions?)\s*:",
    r"\b(?:when|if)\s+(?:this|the)\s+(?:document|file|chunk)\s+is\s+retrieved\b",
    r"(?:\[im_start\]|<\|(?:system|developer|assistant)\|>|\b(?:system|developer)\s+message\s*:)",
))


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", text)


def contains_prompt_injection(text: str) -> bool:
    """Identify explicit instructions directed at the assistant in source text."""
    normalized = _normalize(text)
    return any(pattern.search(normalized) for pattern in _INSTRUCTION_PATTERNS)


def _check_text(text: str) -> None:
    if len(text) > MAX_EXTRACTED_CHARS:
        raise UnsafeDocumentError("Extracted document text exceeds the safety limit.")
    if contains_prompt_injection(text):
        raise UnsafeDocumentError("Document contains instructions aimed at the assistant.")


def _html_text(data: bytes) -> str:
    try:
        html = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsafeDocumentError("HTML must be valid UTF-8.") from exc
    soup = BeautifulSoup(html, "html.parser")
    if soup.find(ACTIVE_HTML_TAGS):
        raise UnsafeDocumentError("Active HTML content is not allowed.")
    if soup.find(lambda tag: any(
        key.lower().startswith("on") or str(value).strip().lower().startswith("javascript:")
        for key, value in tag.attrs.items()
    )):
        raise UnsafeDocumentError("Active HTML content is not allowed.")
    for tag in soup(["style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def _pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF-") or any(marker in data for marker in (b"/JavaScript", b"/OpenAction", b"/AA")):
        raise UnsafeDocumentError("PDF structure or active content is not allowed.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted or len(reader.pages) > MAX_PDF_PAGES:
            raise UnsafeDocumentError("Encrypted or oversized PDF is not allowed.")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except UnsafeDocumentError:
        raise
    except Exception as exc:
        raise UnsafeDocumentError("PDF could not be read safely.") from exc


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > MAX_DOCX_MEMBERS or sum(item.file_size for item in members) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise UnsafeDocumentError("DOCX exceeds the expanded-size safety limit.")
            if any("vbaproject" in item.filename.lower() for item in members):
                raise UnsafeDocumentError("DOCX with active content is not allowed.")
            if any(item.file_size > 1_000_000 and item.file_size > 200 * max(item.compress_size, 1) for item in members):
                raise UnsafeDocumentError("DOCX compression ratio exceeds the safety limit.")
        document = Document(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except UnsafeDocumentError:
        raise
    except Exception as exc:
        raise UnsafeDocumentError("DOCX could not be read safely.") from exc


def validate_document_content(data: bytes, suffix: str) -> None:
    """Validate file bytes before persistence and again before embedding."""
    suffix = suffix.lower()
    if suffix == ".pdf":
        text = _pdf_text(data)
    elif suffix == ".docx":
        text = _docx_text(data)
    elif suffix in {".html", ".htm"}:
        text = _html_text(data)
    elif suffix in {".txt", ".md"}:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsafeDocumentError("Text file must be valid UTF-8.") from exc
        if "\x00" in text:
            raise UnsafeDocumentError("Binary content is not allowed in text files.")
    else:
        raise UnsafeDocumentError("Unsupported document type.")
    _check_text(text)
