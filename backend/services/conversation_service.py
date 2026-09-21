from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.conversation import ConversationCreate, MessageCreate
from database.models.conversation import Conversation, Message
from database.repositories.conversation_repository import ConversationRepository


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = ConversationRepository(session)
        self.session = session

    async def create(self, request: ConversationCreate, user_id: UUID, organization_id: UUID) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            organization_id=organization_id,
            title=request.title.strip() if request.title else None,
        )
        await self.repository.create(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_owned(
        self, conversation_id: UUID, user_id: UUID, organization_id: UUID
    ) -> Conversation | None:
        return await self.repository.get_owned(conversation_id, user_id, organization_id)

    async def list_owned(
        self, user_id: UUID, organization_id: UUID, limit: int, offset: int
    ) -> list[Conversation]:
        return await self.repository.list_owned(user_id, organization_id, limit, offset)

    async def add_message(
        self,
        conversation_id: UUID,
        request: MessageCreate,
        user_id: UUID,
        organization_id: UUID,
    ) -> Message | None:
        conversation = await self.repository.get_owned(conversation_id, user_id, organization_id)
        if conversation is None:
            return None
        message = Message(
            conversation_id=conversation.id,
            sequence=await self.repository.next_message_sequence(conversation.id),
            role=request.role,
            content=request.content,
        )
        await self.repository.add_message(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_messages(
        self, conversation_id: UUID, user_id: UUID, organization_id: UUID
    ) -> list[Message] | None:
        conversation = await self.repository.get_owned(conversation_id, user_id, organization_id)
        if conversation is None:
            return None
        return await self.repository.list_messages(conversation.id)
