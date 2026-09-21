from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.task import Task, TaskComment


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_scoped(self, task_id: UUID, organization_id: UUID) -> Task | None:
        result = await self.session.execute(
            select(Task).where(
                Task.id == task_id,
                Task.organization_id == organization_id,
                Task.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_scoped(
        self,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None,
        assignee_id: UUID | None,
        search: str | None,
    ) -> list[Task]:
        statement = select(Task).where(
            Task.organization_id == organization_id,
            Task.deleted_at.is_(None),
        )
        if status is not None:
            statement = statement.where(Task.status == status)
        if assignee_id is not None:
            statement = statement.where(Task.assignee_id == assignee_id)
        if search:
            statement = statement.where(Task.title.ilike(f"%{search}%"))
        statement = statement.order_by(Task.updated_at.desc(), Task.id).limit(limit).offset(offset)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def add_comment(self, comment: TaskComment) -> TaskComment:
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_comments(self, task_id: UUID) -> list[TaskComment]:
        result = await self.session.execute(
            select(TaskComment)
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at, TaskComment.id)
        )
        return list(result.scalars().all())

    async def soft_delete(self, task: Task) -> None:
        task.deleted_at = datetime.now(timezone.utc)
