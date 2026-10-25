from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    Response,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from .config import get_admin_settings
from .schemas import (
    ChunksListResponse,
    DocumentDetail,
    DocumentsListResponse,
    MetricsOverview,
    DashboardSummary,
    RehydrateResponse,
)
from .service import DocumentAdminService
from .dashboard import dashboard_summary as build_dashboard_summary
from ..chat_history import list_chat_history, list_chat_users
from ..observability.snapshot import build_metrics_overview
from ..oidc import require_actor


router = APIRouter(tags=["admin"])


@router.get("/chat-history")
def chat_history(
    q: str | None = Query(default=None, max_length=200, description="Search email, question, answer, and source metadata"),
    actor_email: str | None = Query(default=None, max_length=320, description="Only show one signed-in user's conversation"),
    newest_first: bool = Query(default=False, description="Return the latest page first"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return list_chat_history(limit=limit, offset=offset, q=q, actor_email=actor_email, newest_first=newest_first)


@router.get("/chat-history/users")
def chat_history_users(
    q: str | None = Query(default=None, max_length=200, description="Search email, question, answer, and source metadata"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return list_chat_users(limit=limit, offset=offset, q=q)


@lru_cache(maxsize=1)
def get_service() -> DocumentAdminService:
    settings = get_admin_settings()
    return DocumentAdminService(settings)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(service: DocumentAdminService = Depends(get_service)) -> DashboardSummary:
    return DashboardSummary.model_validate(build_dashboard_summary(service))


@router.post(
    "/docs",
    response_model=DocumentDetail,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    area: str | None = Form(None),
    role: str | None = Form(None),
    vigencia: str | None = Form(None),
    source_url: str | None = Form(None),
    service: DocumentAdminService = Depends(get_service),
) -> DocumentDetail:
    actor = require_actor(request)
    document, duplicate = await service.upload_document(
        file=file,
        area=area,
        role=role,
        vigencia=vigencia,
        source_url=source_url,
        uploaded_by_email=actor.email,
        uploaded_by_name=actor.display_name,
    )
    response.status_code = (
        status.HTTP_200_OK if duplicate else status.HTTP_202_ACCEPTED
    )
    return document


@router.get("/docs", response_model=DocumentsListResponse)
def list_documents(
    q: str | None = Query(default=None, description="Búsqueda por nombre de archivo"),
    status_filter: str | None = Query(default=None, alias="status"),
    area: str | None = Query(default=None),
    role: str | None = Query(default=None),
    vigencia: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: DocumentAdminService = Depends(get_service),
) -> DocumentsListResponse:
    return service.list_documents(
        q=q,
        status_filter=status_filter,
        area=area,
        role=role,
        vigencia=vigencia,
        limit=limit,
        offset=offset,
    )


@router.get("/docs/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: UUID,
    service: DocumentAdminService = Depends(get_service),
) -> DocumentDetail:
    return service.get_document(document_id)


@router.get(
    "/docs/{document_id}/file",
    summary="Download the original uploaded document",
    description="Returns the original file for an authorized console user. The browser preview fetches this endpoint with the same session as document details.",
)
def get_document_file(
    document_id: UUID,
    service: DocumentAdminService = Depends(get_service),
) -> FileResponse:
    path, filename, media_type = service.get_original_file(document_id)
    headers = {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if media_type.startswith("text/html"):
        headers["Content-Security-Policy"] = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:"
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="attachment",
        headers=headers,
    )


@router.get("/docs/{document_id}/chunks", response_model=ChunksListResponse)
def list_chunks(
    document_id: UUID,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: DocumentAdminService = Depends(get_service),
) -> ChunksListResponse:
    return service.get_chunks(document_id, limit=limit, offset=offset)


@router.post(
    "/docs/{document_id}/rehydrate",
    response_model=RehydrateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def rehydrate_document(
    document_id: UUID,
    background: BackgroundTasks,
    service: DocumentAdminService = Depends(get_service),
) -> RehydrateResponse:
    detail = service.schedule_rehydrate(document_id, background=background)
    return RehydrateResponse(id=detail.id, status=detail.status)


@router.delete("/docs/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    service: DocumentAdminService = Depends(get_service),
) -> Response:
    service.delete_document(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/metrics/overview", response_model=MetricsOverview)
def metrics_overview(
    service: DocumentAdminService = Depends(get_service),
) -> MetricsOverview:
    return build_metrics_overview(service)


__all__ = ["router"]
