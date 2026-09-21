from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.conversation import ConversationCreate, MessageCreate
from backend.services.conversation_service import ConversationService
from mcp.schemas.context import ToolContext
from mcp.tools.base import RegisteredTool


class CreateConversationInput(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class GetConversationInput(BaseModel):
    conversation_id: UUID


class ListConversationsInput(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    search: str | None = Field(default=None, max_length=255)


class AddMessageInput(BaseModel):
    conversation_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=100000)


class ListMessagesInput(BaseModel):
    conversation_id: UUID


class ConversationTools:
    def __init__(self, session: AsyncSession) -> None:
        self.service = ConversationService(session)

    def registered_tools(self) -> list[RegisteredTool[Any]]:
        return [
            RegisteredTool("create_conversation", "Create a conversation for the authenticated user.", CreateConversationInput, self.create_conversation),
            RegisteredTool("get_conversation", "Retrieve an authorized conversation and its messages.", GetConversationInput, self.get_conversation),
            RegisteredTool("search_conversations", "List authorized conversations, optionally filtered by title.", ListConversationsInput, self.search_conversations),
            RegisteredTool("add_message", "Add a message to an authorized conversation.", AddMessageInput, self.add_message),
            RegisteredTool("list_messages", "Retrieve messages from an authorized conversation.", ListMessagesInput, self.list_messages),
        ]

    @staticmethod
    def _organization_id(context: ToolContext) -> UUID:
        if context.organization_id is None:
            raise PermissionError("An organization is required to use conversation tools.")
        return context.organization_id

    async def create_conversation(self, arguments: CreateConversationInput, context: ToolContext) -> dict[str, Any]:
        conversation = await self.service.create(
            ConversationCreate(**arguments.model_dump()), context.user_id, self._organization_id(context)
        )
        return conversation_response(conversation)

    async def get_conversation(self, arguments: GetConversationInput, context: ToolContext) -> dict[str, Any]:
        organization_id = self._organization_id(context)
        conversation = await self.service.get_owned(arguments.conversation_id, context.user_id, organization_id)
        if conversation is None:
            raise LookupError("Conversation was not found.")
        messages = await self.service.list_messages(conversation.id, context.user_id, organization_id)
        return {**conversation_response(conversation), "messages": [message_response(message) for message in messages or []]}

    async def search_conversations(self, arguments: ListConversationsInput, context: ToolContext) -> dict[str, Any]:
        conversations = await self.service.list_owned(
            context.user_id, self._organization_id(context), arguments.limit, arguments.offset
        )
        if arguments.search:
            search = arguments.search.casefold()
            conversations = [item for item in conversations if search in (item.title or "").casefold()]
        return {"conversations": [conversation_response(item) for item in conversations]}

    async def add_message(self, arguments: AddMessageInput, context: ToolContext) -> dict[str, Any]:
        message = await self.service.add_message(
            arguments.conversation_id,
            MessageCreate(role=arguments.role, content=arguments.content),
            context.user_id,
            self._organization_id(context),
        )
        if message is None:
            raise LookupError("Conversation was not found.")
        return message_response(message)

    async def list_messages(self, arguments: ListMessagesInput, context: ToolContext) -> dict[str, Any]:
        messages = await self.service.list_messages(
            arguments.conversation_id, context.user_id, self._organization_id(context)
        )
        if messages is None:
            raise LookupError("Conversation was not found.")
        return {"messages": [message_response(message) for message in messages]}


def conversation_response(conversation: Any) -> dict[str, Any]:
    return {
        "id": str(conversation.id),
        "user_id": str(conversation.user_id),
        "organization_id": str(conversation.organization_id),
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


def message_response(message: Any) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sequence": message.sequence,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "updated_at": message.updated_at.isoformat(),
    }
