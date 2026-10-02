from datetime import datetime
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


class AgentStepResponse(BaseModel):
    sequence: int
    node_name: str
    status: str
    error_message: str | None


class AgentToolCallResponse(BaseModel):
    tool_name: str
    success: bool
    result: dict[str, Any] | None
    error_message: str | None
    created_at: datetime


class AgentRunResponse(BaseModel):
    run_id: UUID
    conversation_id: UUID | None
    request: str
    status: str
    response: str | None
    errors: list[str]
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    nodes: list[AgentStepResponse]
    tool_calls: list[AgentToolCallResponse]
    retrieved_sources: list[dict[str, Any]]
