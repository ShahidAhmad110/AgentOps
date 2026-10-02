from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import get_current_user
from backend.core.errors import APIError
from backend.schemas.document import (
    DocumentResponse,
    SearchRequest,
    SearchResponse,
    SourceResponse,
)
from backend.services.document_service import DocumentService
from database.connection.session import get_database_session
from database.models.user import User

router = APIRouter(prefix="/documents", tags=["documents"])


def organization_id_for(user: User) -> UUID:
    if user.organization_id is None:
        raise APIError("ORGANIZATION_REQUIRED", "An organization is required.", status_code=403)
    return user.organization_id


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> DocumentResponse:
    try:
        document = await DocumentService(session).ingest(
            file.filename or "upload",
            file.content_type or "application/octet-stream",
            await file.read(),
            user.id,
            organization_id_for(user),
        )
        return DocumentResponse.model_validate(document)
    except ValueError as exc:
        raise APIError("DOCUMENT_ERROR", str(exc), status_code=400) from exc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> list[DocumentResponse]:
    if not 1 <= limit <= 100 or offset < 0:
        raise APIError("VALIDATION_ERROR", "Invalid pagination values.", status_code=422)
    documents = await DocumentService(session).list(limit, offset, organization_id_for(user))
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> DocumentResponse:
    document = await DocumentService(session).get(document_id, organization_id_for(user))
    if document is None:
        raise APIError("DOCUMENT_NOT_FOUND", "Document was not found.", status_code=404)
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> Response:
    archived = await DocumentService(session).archive(document_id, organization_id_for(user))
    if not archived:
        raise APIError("DOCUMENT_NOT_FOUND", "Document was not found.", status_code=404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> SearchResponse:
    result = await DocumentService(session).search(request.query, request.limit, organization_id_for(user))
    return SearchResponse(
        context=result.context,
        limitation=result.limitation,
        sources=[
            SourceResponse(
                document_id=source.document_id,
                filename=source.filename,
                chunk_index=source.chunk_index,
                content=source.content,
                score=source.score,
            )
            for source in result.sources
        ],
    )
