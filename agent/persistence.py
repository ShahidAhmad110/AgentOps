from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.agent_execution import AgentRun, AgentStep, ToolCall
from database.repositories.agent_execution_repository import AgentExecutionRepository


class ExecutionRecorder(Protocol):
    async def start_run(self, state: Mapping[str, Any]) -> UUID: ...

    async def record_step(self, run_id: UUID, step: Mapping[str, Any]) -> None: ...

    async def record_tool_call(self, run_id: UUID, tool_call: Mapping[str, Any]) -> None: ...

    async def finish_run(self, run_id: UUID, state: Mapping[str, Any]) -> None: ...


class DatabaseExecutionRecorder:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AgentExecutionRepository(session)

    async def start_run(self, state: Mapping[str, Any]) -> UUID:
        run = AgentRun(
            user_id=state["user_id"],
            organization_id=state["organization_id"],
            conversation_id=state.get("conversation_id"),
            request=state["request"],
            status="RUNNING",
        )
        await self.repository.create_run(run)
        await self.repository.commit()
        return run.id

    async def record_step(self, run_id: UUID, step: Mapping[str, Any]) -> None:
        await self.repository.create_step(
            AgentStep(
                run_id=run_id,
                sequence=int(step["sequence"]),
                node_name=str(step["node_name"]),
                status=str(step["status"]),
                error_message=step.get("error"),
            )
        )
        await self.repository.commit()

    async def record_tool_call(self, run_id: UUID, tool_call: Mapping[str, Any]) -> None:
        await self.repository.create_tool_call(
            ToolCall(
                run_id=run_id,
                tool_name=str(tool_call["tool_name"]),
                arguments=dict(tool_call.get("arguments", {})),
                success=bool(tool_call.get("success", False)),
                result=tool_call.get("result"),
                error_message=tool_call.get("error"),
            )
        )
        await self.repository.commit()

    async def finish_run(self, run_id: UUID, state: Mapping[str, Any]) -> None:
        run = await self.repository.get_run(run_id)
        if run is None:
            return
        run.status = str(state.get("status", "FAILED")).upper()
        run.final_response = state.get("final_response")
        errors = state.get("errors", [])
        run.error_message = "; ".join(str(error) for error in errors) or None
        run.completed_at = datetime.now(timezone.utc)
        await self.repository.commit()
