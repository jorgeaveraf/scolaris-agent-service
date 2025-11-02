from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


@dataclass(frozen=True)
class AdminSettings:
    admin_token: str
    max_upload_bytes: int
    allowed_exts: set[str]
    upload_dir: Path


DEFAULT_ALLOWED_EXTS = ".pdf,.docx,.txt,.md,.html"


@lru_cache(maxsize=1)
def get_admin_settings() -> AdminSettings:
    token = os.getenv("ADMIN_TOKEN")
    if not token:
        raise RuntimeError("ADMIN_TOKEN must estar configurado para habilitar /admin.")

    max_upload_mb = os.getenv("MAX_UPLOAD_MB", "20")
    try:
        max_upload_bytes = int(max_upload_mb) * 1024 * 1024
    except ValueError:
        raise RuntimeError("MAX_UPLOAD_MB debe ser un entero válido.") from None

    allowed_raw = os.getenv("ALLOWED_EXTS", DEFAULT_ALLOWED_EXTS)
    allowed_exts = {
        ext.lower().strip()
        for ext in allowed_raw.split(",")
        if ext.strip()
    }
    if not allowed_exts:
        allowed_exts = {".pdf", ".docx", ".txt", ".md", ".html"}

    upload_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    return AdminSettings(
        admin_token=token,
        max_upload_bytes=max_upload_bytes,
        allowed_exts=allowed_exts,
        upload_dir=upload_dir,
    )


__all__ = ["AdminSettings", "get_admin_settings"]
