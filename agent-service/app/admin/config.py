from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


@dataclass(frozen=True)
class AdminSettings:
    admin_token: str | None
    rbac_disabled: bool
    jwt_secret: str | None
    jwt_public_key: str | None
    jwt_algorithm: str
    jwt_issuer: str | None
    jwt_audience: str | None
    max_upload_bytes: int
    allowed_exts: set[str]
    allowed_mime_types: set[str]
    upload_dir: Path
    upload_async_enabled: bool
    upload_queue_name: str
    upload_max_pages: int | None
    upload_max_paragraphs: int | None
    upload_av_policy: str
    redis_url: str


DEFAULT_ALLOWED_EXTS = ".pdf,.docx,.txt,.md,.html"
DEFAULT_ALLOWED_MIME_TYPES = (
    "application/pdf,"
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
    "text/plain,"
    "text/markdown,"
    "text/html"
)


@lru_cache(maxsize=1)
def get_admin_settings() -> AdminSettings:
    rbac_disabled = os.getenv("RBAC_DISABLED", "false").lower() == "true"

    token = os.getenv("ADMIN_TOKEN")
    if rbac_disabled and not token:
        raise RuntimeError(
            "ADMIN_TOKEN debe estar configurado cuando RBAC_DISABLED=true para permitir el modo compat."
        )

    jwt_secret = os.getenv("JWT_SECRET")
    jwt_public_key = os.getenv("JWT_PUBLIC_KEY")
    if not rbac_disabled and not (jwt_secret or jwt_public_key):
        raise RuntimeError(
            "Debe configurarse JWT_SECRET (HS256) o JWT_PUBLIC_KEY (RS256) cuando RBAC_DISABLED=false."
        )

    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_issuer = os.getenv("JWT_ISSUER")
    jwt_audience = os.getenv("JWT_AUDIENCE")

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

    allowed_mime_raw = os.getenv("ALLOWED_MIME_TYPES", DEFAULT_ALLOWED_MIME_TYPES)
    allowed_mime_types = {
        mime.strip().lower()
        for mime in allowed_mime_raw.split(",")
        if mime.strip()
    } or {"application/pdf", "text/plain"}

    upload_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    upload_async_enabled = os.getenv("UPLOAD_ASYNC_ENABLED", "true").lower() == "true"
    upload_queue_name = os.getenv("UPLOAD_QUEUE_NAME", "ingest:default")

    def _parse_int(name: str, default: str | None) -> int | None:
        raw = os.getenv(name, default) if default is not None else os.getenv(name)
        if raw is None or str(raw).strip() == "":
            return None
        try:
            value = int(raw)
            return value if value > 0 else None
        except ValueError:
            raise RuntimeError(f"{name} debe ser un entero positivo.") from None

    upload_max_pages = _parse_int("UPLOAD_MAX_PAGES", None)
    upload_max_paragraphs = _parse_int("UPLOAD_MAX_PARAGRAPHS", None)
    upload_av_policy = os.getenv("UPLOAD_AV_POLICY", "allow").lower()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    return AdminSettings(
        admin_token=token,
        rbac_disabled=rbac_disabled,
        jwt_secret=jwt_secret,
        jwt_public_key=jwt_public_key,
        jwt_algorithm=jwt_algorithm,
        jwt_issuer=jwt_issuer,
        jwt_audience=jwt_audience,
        max_upload_bytes=max_upload_bytes,
        allowed_exts=allowed_exts,
        allowed_mime_types=allowed_mime_types,
        upload_dir=upload_dir,
        upload_async_enabled=upload_async_enabled,
        upload_queue_name=upload_queue_name,
        upload_max_pages=upload_max_pages,
        upload_max_paragraphs=upload_max_paragraphs,
        upload_av_policy=upload_av_policy,
        redis_url=redis_url,
    )


__all__ = ["AdminSettings", "get_admin_settings"]
