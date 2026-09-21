from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    organization_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    role: str = Field(pattern=r"^(user|assistant|system)$")
    content: str = Field(min_length=1, max_length=100000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    sequence: int
    role: str
    content: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]
