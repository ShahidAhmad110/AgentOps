from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    request: str = Field(min_length=1, max_length=100000)
    conversation_id: UUID | None = None


class AgentResponse(BaseModel):
    run_id: UUID | None
    status: str
    response: str | None
    errors: list[str]
    retrieved_sources: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
