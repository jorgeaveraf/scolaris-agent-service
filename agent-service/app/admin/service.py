from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile, status

from ..ingestion.ingest import ingest_uploaded_file, vs as vector_store
from .config import AdminSettings
from . import repository
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

    async def upload_document(
        self,
        *,
        file: UploadFile,
        area: str | None,
        role: str | None,
        vigencia: str | None,
    ) -> Tuple[DocumentDetail, bool]:
        area = area.strip() if area else None
        role = role.strip() if role else None
        vigencia = vigencia.strip() if vigencia else None
        filename = (file.filename or "document").strip()
        suffix = Path(filename).suffix.lower()
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

        data = await file.read()
        size_bytes = len(data)
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

        checksum = hashlib.sha256(data).hexdigest()
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
                content_type=file.content_type,
                size_bytes=size_bytes,
                checksum=checksum,
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
        else:
            document_id = uuid4()
            record = repository.create_document(
                document_id=document_id,
                filename=filename,
                content_type=file.content_type,
                size_bytes=size_bytes,
                checksum=checksum,
                status="processing",
                area=area,
                role=role,
                vigencia=vigencia,
                upload_path=str(destination),
            )

        logger.info(
            "admin.upload document_id=%s filename=%s size_bytes=%s checksum=%s",
            document_id,
            filename,
            size_bytes,
            checksum,
        )

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
        background.add_task(
            self._rehydrate_task,
            document_id=document_id,
        )
        logger.info("admin.ingest.rehydrate document_id=%s", document_id)
        return self._to_detail(updated)

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
        return self._to_detail(updated)

    def _rehydrate_task(self, document_id: UUID) -> None:
        record = repository.get_document(document_id)
        if not record:
            logger.error("admin.rehydrate missing document_id=%s", document_id)
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
            # error ya fue registrado y estado actualizado
            return

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


__all__ = ["DocumentAdminService"]
