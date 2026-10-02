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

    async def list_runs_scoped(
        self, user_id: UUID, organization_id: UUID, limit: int, offset: int
    ) -> list[AgentRun]:
        result = await self.session.execute(
            select(AgentRun)
            .where(AgentRun.user_id == user_id, AgentRun.organization_id == organization_id)
            .order_by(AgentRun.created_at.desc(), AgentRun.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_steps(self, run_ids: list[UUID]) -> list[AgentStep]:
        if not run_ids:
            return []
        result = await self.session.execute(
            select(AgentStep)
            .where(AgentStep.run_id.in_(run_ids))
            .order_by(AgentStep.run_id, AgentStep.sequence)
        )
        return list(result.scalars().all())

    async def list_tool_calls(self, run_ids: list[UUID]) -> list[ToolCall]:
        if not run_ids:
            return []
        result = await self.session.execute(
            select(ToolCall)
            .where(ToolCall.run_id.in_(run_ids))
            .order_by(ToolCall.run_id, ToolCall.created_at, ToolCall.id)
        )
        return list(result.scalars().all())

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
