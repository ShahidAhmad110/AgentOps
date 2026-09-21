from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import get_current_user
from backend.core.errors import APIError
from backend.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from backend.services.conversation_service import ConversationService
from database.connection.session import get_database_session
from database.models.user import User

router = APIRouter(prefix="/conversations", tags=["conversations"])


def organization_id_for(user: User) -> UUID:
    if user.organization_id is None:
        raise APIError("ORGANIZATION_REQUIRED", "An organization is required.", status_code=403)
    return user.organization_id


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> ConversationResponse:
    conversation = await ConversationService(session).create(
        request, user.id, organization_id_for(user)
    )
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> list[ConversationResponse]:
    conversations = await ConversationService(session).list_owned(
        user.id, organization_id_for(user), limit, offset
    )
    return [ConversationResponse.model_validate(item) for item in conversations]


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> ConversationDetailResponse:
    service = ConversationService(session)
    conversation = await service.get_owned(conversation_id, user.id, organization_id_for(user))
    if conversation is None:
        raise APIError("CONVERSATION_NOT_FOUND", "The conversation was not found.", status_code=404)
    messages = await service.list_messages(conversation.id, user.id, user.organization_id)
    return ConversationDetailResponse(
        **ConversationResponse.model_validate(conversation).model_dump(),
        messages=[MessageResponse.model_validate(message) for message in messages or []],
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    request: MessageCreate,
    conversation_id: UUID = Path(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> MessageResponse:
    message = await ConversationService(session).add_message(
        conversation_id, request, user.id, organization_id_for(user)
    )
    if message is None:
        raise APIError("CONVERSATION_NOT_FOUND", "The conversation was not found.", status_code=404)
    return MessageResponse.model_validate(message)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> list[MessageResponse]:
    messages = await ConversationService(session).list_messages(
        conversation_id, user.id, organization_id_for(user)
    )
    if messages is None:
        raise APIError("CONVERSATION_NOT_FOUND", "The conversation was not found.", status_code=404)
    return [MessageResponse.model_validate(message) for message in messages]
