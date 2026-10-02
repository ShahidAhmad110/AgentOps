from __future__ import annotations

from typing import Any, Literal, TypedDict
from uuid import UUID


Intent = Literal["knowledge", "operational", "general"]
AgentStatus = Literal["pending", "running", "completed", "failed"]


class AgentState(TypedDict, total=False):
    request: str
    user_id: UUID
    organization_id: UUID
    conversation_id: UUID | None
    conversation_context: list[dict[str, Any]]
    intent: Intent
    selected_tool: str | None
    tool_arguments: dict[str, Any]
    tool_result: dict[str, Any] | None
    retrieved_sources: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    errors: list[str]
    status: AgentStatus
    final_response: str | None
    run_id: UUID | None
    route: str | None
