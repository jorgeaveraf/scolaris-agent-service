from __future__ import annotations

import logging
from uuid import UUID

from ..admin.config import get_admin_settings
from ..admin.service import DocumentAdminService

logger = logging.getLogger("admin.worker")


def run_worker(poll_timeout: int = 10) -> None:
    settings = get_admin_settings()
    if not settings.upload_async_enabled:
        logger.warning("upload_async_enabled=false; worker no-op.")
        return

    service = DocumentAdminService(settings)
    if not service.queue:
        logger.error("Ingestion queue not configured; aborting worker.")
        return

    logger.info(
        "admin.worker.started queue=%s timeout=%s",
        settings.upload_queue_name,
        poll_timeout,
    )

    queue = service.queue
    while True:
        job = queue.dequeue(timeout=poll_timeout)
        if not job:
            continue
        try:
            document_id = UUID(job.document_id)
        except ValueError:
            logger.warning("admin.worker.invalid_job document_id=%s", job.document_id)
            continue

        logger.info(
            "admin.worker.processing document_id=%s action=%s",
            job.document_id,
            job.action,
        )
        service.process_ingestion_job(document_id=document_id, action=job.action)


if __name__ == "__main__":
    run_worker()
