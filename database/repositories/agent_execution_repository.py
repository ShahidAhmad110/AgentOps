from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.agent_execution import AgentRun, AgentStep, ToolCall


class AgentExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: AgentRun) -> AgentRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_run(self, run_id: UUID) -> AgentRun | None:
        result = await self.session.execute(select(AgentRun).where(AgentRun.id == run_id))
        return result.scalar_one_or_none()

    async def create_step(self, step: AgentStep) -> AgentStep:
        self.session.add(step)
        await self.session.flush()
        return step

    async def create_tool_call(self, tool_call: ToolCall) -> ToolCall:
        self.session.add(tool_call)
        await self.session.flush()
        return tool_call

    async def commit(self) -> None:
        await self.session.commit()
