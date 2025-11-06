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
    UploadFile,
    status,
)

from .config import get_admin_settings
from .schemas import (
    ChunksListResponse,
    DocumentDetail,
    DocumentsListResponse,
    RehydrateResponse,
)
from .service import DocumentAdminService


router = APIRouter(tags=["admin"])


@lru_cache(maxsize=1)
def get_service() -> DocumentAdminService:
    settings = get_admin_settings()
    return DocumentAdminService(settings)


@router.post(
    "/docs",
    response_model=DocumentDetail,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    response: Response,
    file: UploadFile = File(...),
    area: str | None = Form(None),
    role: str | None = Form(None),
    vigencia: str | None = Form(None),
    service: DocumentAdminService = Depends(get_service),
) -> DocumentDetail:
    document, duplicate = await service.upload_document(
        file=file,
        area=area,
        role=role,
        vigencia=vigencia,
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


__all__ = ["router"]
