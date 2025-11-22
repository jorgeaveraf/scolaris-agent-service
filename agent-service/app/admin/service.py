from __future__ import annotations

import hashlib
import io
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple
from uuid import UUID, uuid4

import redis
from fastapi import BackgroundTasks, HTTPException, UploadFile, status

from ..ingestion.ingest import ingest_uploaded_file, vs as vector_store
from ..ingestion.queue import IngestionJob, IngestionQueue
from ..observability.metrics import metrics
from . import repository
from .config import AdminSettings
from .schemas import (
    ChunkItem,
    ChunksListResponse,
    DocumentDetail,
    DocumentSummary,
    DocumentsListResponse,
)


logger = logging.getLogger("admin")


class DocumentAdminService:
    def __init__(self, settings: AdminSettings):
        self.settings = settings
        self.queue: Optional[IngestionQueue] = (
            IngestionQueue(
                name=settings.upload_queue_name,
                redis_url=settings.redis_url,
            )
            if settings.upload_async_enabled
            else None
        )

    def get_ingestion_stats(self) -> dict[str, Any]:
        counts = repository.count_documents_by_status()
        ready = counts.get("ready", 0)
        processing = counts.get("processing", 0)
        error = counts.get("error", 0)
        unknown = sum(value for key, value in counts.items() if key not in {"ready", "processing", "error"})
        total = ready + processing + error + unknown

        queue_depth: int | None = None
        if self.queue:
            try:
                queue_depth = int(self.queue.redis.llen(self.queue.name))
            except redis.RedisError:  # pragma: no cover - depende de Redis
                queue_depth = None

        return {
            "total": total,
            "ready": ready,
            "processing": processing,
            "error": error,
            "other": unknown,
            "queue_depth": queue_depth,
        }

    async def upload_document(
        self,
        *,
        file: UploadFile,
        area: str | None,
        role: str | None,
        vigencia: str | None,
    ) -> Tuple[DocumentDetail, bool]:
        area = self._clean_string(area)
        role = self._clean_string(role)
        vigencia = self._clean_string(vigencia)
        filename = (file.filename or "document").strip()
        suffix = Path(filename).suffix.lower()
        self._ensure_allowed_extension(suffix)

        data = await file.read()
        size_bytes = len(data)
        self._validate_size(size_bytes)
        content_type = (file.content_type or "").lower() or None
        self._validate_upload_constraints(
            suffix=suffix,
            content_type=content_type,
            size_bytes=size_bytes,
            data=data,
        )

        checksum = hashlib.sha256(data).hexdigest()
        self._apply_security_policy(
            filename=filename,
            checksum=checksum,
            content_type=content_type,
        )

        existing = repository.get_document_by_checksum(checksum)
        if existing and existing["status"] == "ready":
            logger.info(
                "admin.upload.duplicate document_id=%s checksum=%s",
                existing["id"],
                checksum,
            )
            return self._to_detail(existing), True

        destination = self._save_file(checksum, suffix, data)

        if existing:
            document_id = existing["id"]
            repository.update_upload_metadata(
                document_id,
                filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
                checksum=checksum,
                area=area,
                role=role,
                vigencia=vigencia,
                upload_path=str(destination),
            )
        else:
            document_id = uuid4()
            repository.create_document(
                document_id=document_id,
                filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
                checksum=checksum,
                status="processing",
                area=area,
                role=role,
                vigencia=vigencia,
                upload_path=str(destination),
            )

        record = repository.update_status(
            document_id,
            status="processing",
            error_msg=None,
        )

        logger.info(
            "admin.upload enqueued document_id=%s filename=%s size_bytes=%s checksum=%s async=%s",
            document_id,
            filename,
            size_bytes,
            checksum,
            self.settings.upload_async_enabled,
        )

        if self.settings.upload_async_enabled:
            self._enqueue_ingestion(document_id=document_id, action="ingest")
            return self._to_detail(record), False

        doc_detail = self._run_ingestion(
            document_id=document_id,
            path=destination,
            filename=filename,
            area=area,
            role=role,
            vigencia=vigencia,
        )
        return doc_detail, False

    def list_documents(
        self,
        *,
        q: str | None,
        status_filter: str | None,
        area: str | None,
        role: str | None,
        vigencia: str | None,
        limit: int,
        offset: int,
    ) -> DocumentsListResponse:
        total, items = repository.list_documents(
            filters={
                "q": q,
                "status": status_filter,
                "area": area,
                "role": role,
                "vigencia": vigencia,
            },
            limit=limit,
            offset=offset,
        )
        summaries = [self._to_summary(row) for row in items]
        return DocumentsListResponse(total=total, items=summaries)

    def get_document(self, document_id: UUID) -> DocumentDetail:
        record = repository.get_document(document_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
        return self._to_detail(record)

    def get_chunks(
        self,
        document_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> ChunksListResponse:
        record = repository.get_document(document_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
        doc_ref = record.get("doc_id")
        if not doc_ref:
            return ChunksListResponse(total=0, items=[])

        total, rows = repository.get_chunks_for_doc(
            doc_ref,
            limit=limit,
            offset=offset,
        )
        items = [self._map_chunk(row) for row in rows]
        return ChunksListResponse(total=total, items=items)

    def schedule_rehydrate(self, document_id: UUID, *, background: BackgroundTasks) -> DocumentDetail:
        _ = background  # background tasks se manejan via cola
        record = repository.get_document(document_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
        if record["status"] == "processing":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El documento ya está en procesamiento.")

        upload_path = record.get("upload_path")
        if not upload_path or not Path(upload_path).exists():
            repository.update_status(
                document_id,
                status="error",
                error_msg="El archivo original no está disponible.",
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El archivo original no está disponible para reingesta.",
            )

        updated = repository.update_status(document_id, status="processing", error_msg=None)

        if self.settings.upload_async_enabled:
            self._enqueue_ingestion(document_id=document_id, action="rehydrate")
            refreshed = repository.get_document(document_id)
            logger.info("admin.ingest.rehydrate_queued document_id=%s", document_id)
            return self._to_detail(refreshed or updated)

        path_obj = Path(upload_path)
        detail = self._run_ingestion(
            document_id=document_id,
            path=path_obj,
            filename=record["filename"],
            area=record.get("area"),
            role=record.get("role"),
            vigencia=record.get("vigencia"),
        )
        logger.info("admin.ingest.rehydrate_sync document_id=%s", document_id)
        return detail

    def delete_document(self, document_id: UUID) -> None:
        record = repository.get_document(document_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
        if record["status"] == "processing":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El documento está en procesamiento.")

        doc_ref = record.get("doc_id")
        if doc_ref:
            self._purge_document_vectors(doc_ref)

        repository.delete_document(document_id)

        upload_path = record.get("upload_path")
        if upload_path:
            path_obj = Path(upload_path)
            try:
                path_obj.unlink()
            except FileNotFoundError:
                logger.warning(
                    "admin.delete.missing_file document_id=%s path=%s",
                    document_id,
                    path_obj,
                )

        logger.info("admin.delete document_id=%s doc_ref=%s", document_id, doc_ref)

    def _save_file(self, checksum: str, suffix: str, data: bytes) -> Path:
        destination = self.settings.upload_dir / f"{checksum}{suffix}"
        destination.write_bytes(data)
        return destination

    def _run_ingestion(
        self,
        *,
        document_id: UUID,
        path: Path,
        filename: str,
        area: str | None,
        role: str | None,
        vigencia: str | None,
    ) -> DocumentDetail:
        existing = repository.get_document(document_id) or {}
        old_doc_id = existing.get("doc_id")
        if old_doc_id:
            self._purge_document_vectors(old_doc_id)

        logger.info(
            "admin.ingest.started document_id=%s path=%s",
            document_id,
            path,
        )
        start = time.perf_counter()
        try:
            doc_ref, chunks = ingest_uploaded_file(
                path,
                area=area,
                role=role,
                vigencia=vigencia,
                title=filename,
            )
        except Exception as exc:  # noqa: PIE786 - re-emitimos como HTTPException con log
            trace_id = uuid4().hex
            logger.exception(
                "admin.ingest.error document_id=%s path=%s trace_id=%s",
                document_id,
                path,
                trace_id,
            )
            repository.update_status(
                document_id,
                status="error",
                error_msg=str(exc),
            )
            metrics.record_ingestion_event(
                queue=self.settings.upload_queue_name or "ingestion",
                kind="processed",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "detail": "Error al procesar el documento.",
                    "trace_id": trace_id,
                },
            ) from exc

        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "admin.ingest.finished document_id=%s doc_ref=%s chunks=%s duration_ms=%.2f",
            document_id,
            doc_ref,
            chunks,
            duration,
        )

        updated = repository.update_status(
            document_id,
            status="ready",
            error_msg=None,
            doc_id=doc_ref,
            chunks_count=chunks,
            last_ingested_at=datetime.now(timezone.utc),
        )
        metrics.record_ingestion_event(
            queue=self.settings.upload_queue_name or "ingestion",
            kind="processed",
        )
        return self._to_detail(updated)

    def _purge_document_vectors(self, doc_ref: str) -> None:
        try:
            vector_store.delete_document(doc_ref)
        except Exception:
            logger.exception("admin.vector.purge_failed doc_ref=%s", doc_ref)

    @staticmethod
    def _to_detail(row: dict) -> DocumentDetail:
        return DocumentDetail(
            id=row["id"],
            filename=row["filename"],
            status=row["status"],
            size_bytes=row["size_bytes"],
            area=row.get("area"),
            role=row.get("role"),
            vigencia=row.get("vigencia"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            content_type=row.get("content_type"),
            checksum=row["checksum"],
            doc_id=row.get("doc_id"),
            chunks_count=row.get("chunks_count") or 0,
            last_ingested_at=row.get("last_ingested_at"),
            error_msg=row.get("error_msg"),
        )

    @staticmethod
    def _to_summary(row: dict) -> DocumentSummary:
        return DocumentSummary(
            id=row["id"],
            filename=row["filename"],
            status=row["status"],
            size_bytes=row["size_bytes"],
            area=row.get("area"),
            role=row.get("role"),
            vigencia=row.get("vigencia"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _map_chunk(row: dict) -> ChunkItem:
        metadata = row.get("metadata") or {}
        content: str = row["content"]
        preview = (content[:297] + "...") if len(content) > 300 else content
        tokens = metadata.get("tokens")
        if tokens is None:
            tokens = max(1, len(content) // 4)
        return ChunkItem(
            chunk_id=row["id"],
            chunk_no=row["chunk_no"],
            text_preview=preview,
            tokens=int(tokens),
            metadata=metadata,
        )

    def process_ingestion_job(self, document_id: UUID, *, action: str = "ingest") -> None:
        record = repository.get_document(document_id)
        if not record:
            logger.error("admin.queue.missing_document document_id=%s", document_id)
            return

        upload_path = record.get("upload_path")
        if not upload_path:
            repository.update_status(
                document_id,
                status="error",
                error_msg="Archivo original no encontrado.",
            )
            return

        path_obj = Path(upload_path)
        if not path_obj.exists():
            repository.update_status(
                document_id,
                status="error",
                error_msg="Archivo original no encontrado.",
            )
            return

        logger.info(
            "admin.queue.process_start document_id=%s action=%s",
            document_id,
            action,
        )
        try:
            self._run_ingestion(
                document_id=document_id,
                path=path_obj,
                filename=record["filename"],
                area=record.get("area"),
                role=record.get("role"),
                vigencia=record.get("vigencia"),
            )
        except HTTPException:
            return

    def _enqueue_ingestion(self, *, document_id: UUID, action: str) -> None:
        if not self.queue:
            raise RuntimeError("Ingestion queue no está disponible en modo síncrono.")
        job = IngestionJob(document_id=str(document_id), action=action)
        try:
            self.queue.enqueue(job)
            metrics.record_ingestion_event(queue=self.queue.name, kind="enqueued")
        except Exception as exc:
            repository.update_status(
                document_id,
                status="error",
                error_msg="No pudimos programar la ingesta.",
            )
            logger.exception("admin.queue.enqueue_failed document_id=%s", document_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No pudimos programar la ingesta. Intenta nuevamente.",
            ) from exc

    def _ensure_allowed_extension(self, suffix: str) -> None:
        if not suffix:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El archivo debe tener una extensión.",
            )
        if suffix not in self.settings.allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Extensión no permitida: {suffix}",
            )

    def _validate_size(self, size_bytes: int) -> None:
        if size_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El archivo está vacío.",
            )
        if size_bytes > self.settings.max_upload_bytes:
            max_mb = self.settings.max_upload_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El archivo supera el máximo permitido de {max_mb} MB.",
            )

    def _validate_upload_constraints(
        self,
        *,
        suffix: str,
        content_type: str | None,
        size_bytes: int,
        data: bytes,
    ) -> None:
        if content_type:
            mime = content_type.lower()
            if (
                mime != "application/octet-stream"
                and self.settings.allowed_mime_types
                and mime not in self.settings.allowed_mime_types
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Tipo MIME no permitido: {content_type}",
                )

        if suffix == ".pdf" and self.settings.upload_max_pages:
            pages = self._count_pdf_pages(data)
            if pages > self.settings.upload_max_pages:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"El PDF excede el máximo de {self.settings.upload_max_pages} páginas."
                    ),
                )

        if suffix == ".docx" and self.settings.upload_max_paragraphs:
            paragraphs = self._count_docx_paragraphs(data)
            if paragraphs > self.settings.upload_max_paragraphs:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "El documento contiene más párrafos "
                        f"que el máximo permitido de {self.settings.upload_max_paragraphs}."
                    ),
                )

    def _apply_security_policy(
        self,
        *,
        filename: str,
        checksum: str,
        content_type: str | None,
    ) -> None:
        policy = self.settings.upload_av_policy
        if policy == "deny_all":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Carga bloqueada por la política de seguridad vigente.",
            )
        if policy == "monitor":
            logger.warning(
                "admin.upload.monitor filename=%s checksum=%s content_type=%s",
                filename,
                checksum,
                content_type,
            )

    @staticmethod
    def _clean_string(value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @staticmethod
    def _count_pdf_pages(data: bytes) -> int:
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            return len(reader.pages)
        except Exception as exc:  # pragma: no cover - depende de librería externa
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No pudimos leer el PDF para validar sus páginas.",
            ) from exc

    @staticmethod
    def _count_docx_paragraphs(data: bytes) -> int:
        from docx import Document

        try:
            document = Document(io.BytesIO(data))
            return len(document.paragraphs)
        except Exception as exc:  # pragma: no cover - depende de librería externa
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No pudimos analizar el DOCX para validar su contenido.",
            ) from exc


__all__ = ["DocumentAdminService"]
