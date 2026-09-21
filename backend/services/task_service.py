from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.task import TaskCommentCreate, TaskCreate, TaskUpdate
from database.models.task import Task, TaskComment
from database.repositories.task_repository import TaskRepository
from database.repositories.user_repository import UserRepository


class TaskValidationError(ValueError):
    pass


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = TaskRepository(session)
        self.users = UserRepository(session)

    async def create(self, request: TaskCreate, owner_id: UUID, organization_id: UUID) -> Task:
        await self._validate_assignee(request.assignee_id, organization_id)
        task = Task(
            organization_id=organization_id,
            owner_id=owner_id,
            assignee_id=request.assignee_id,
            title=request.title.strip(),
            description=request.description,
            status=request.status,
            priority=request.priority,
            due_date=request.due_date,
        )
        await self.repository.create(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get(self, task_id: UUID, organization_id: UUID) -> Task | None:
        return await self.repository.get_scoped(task_id, organization_id)

    async def list(
        self,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None,
        assignee_id: UUID | None,
        search: str | None,
    ) -> list[Task]:
        return await self.repository.list_scoped(
            organization_id, limit, offset, status, assignee_id, search
        )

    async def update(self, task_id: UUID, request: TaskUpdate, organization_id: UUID) -> Task | None:
        task = await self.repository.get_scoped(task_id, organization_id)
        if task is None:
            return None
        if "assignee_id" in request.model_fields_set:
            await self._validate_assignee(request.assignee_id, organization_id)
            task.assignee_id = request.assignee_id
        if "title" in request.model_fields_set:
            task.title = request.title.strip() if request.title else task.title
        if "description" in request.model_fields_set:
            task.description = request.description
        if "status" in request.model_fields_set and request.status is not None:
            task.status = request.status
        if "priority" in request.model_fields_set:
            task.priority = request.priority
        if "due_date" in request.model_fields_set:
            task.due_date = request.due_date
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def archive(self, task_id: UUID, organization_id: UUID) -> bool:
        task = await self.repository.get_scoped(task_id, organization_id)
        if task is None:
            return False
        await self.repository.soft_delete(task)
        await self.session.commit()
        return True

    async def add_comment(
        self,
        task_id: UUID,
        request: TaskCommentCreate,
        author_id: UUID,
        organization_id: UUID,
    ) -> TaskComment | None:
        task = await self.repository.get_scoped(task_id, organization_id)
        if task is None:
            return None
        comment = TaskComment(task_id=task.id, author_id=author_id, content=request.content)
        await self.repository.add_comment(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def list_comments(self, task_id: UUID, organization_id: UUID) -> list[TaskComment] | None:
        task = await self.repository.get_scoped(task_id, organization_id)
        if task is None:
            return None
        return await self.repository.list_comments(task.id)

    async def _validate_assignee(self, assignee_id: UUID | None, organization_id: UUID) -> None:
        if assignee_id is None:
            return
        assignee = await self.users.get_by_id(assignee_id)
        if assignee is None or not assignee.is_active or assignee.organization_id != organization_id:
            raise TaskValidationError("The assignee must be an active user in the organization.")
