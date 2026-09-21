from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.conversation import Conversation, Message


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, conversation: Conversation) -> Conversation:
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def get_owned(
        self, conversation_id: UUID, user_id: UUID, organization_id: UUID
    ) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.organization_id == organization_id,
                Conversation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_owned(self, user_id: UUID, organization_id: UUID, limit: int, offset: int) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.organization_id == organization_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.updated_at.desc(), Conversation.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def next_message_sequence(self, conversation_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(Message.sequence), 0) + 1).where(
                Message.conversation_id == conversation_id
            )
        )
        return int(result.scalar_one())

    async def add_message(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_messages(self, conversation_id: UUID) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence, Message.created_at, Message.id)
        )
        return list(result.scalars().all())
