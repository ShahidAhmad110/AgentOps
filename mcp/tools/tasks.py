from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.task import TaskCreate, TaskUpdate
from backend.services.task_service import TaskService
from mcp.schemas.context import ToolContext
from mcp.tools.base import RegisteredTool

TaskStatus = Literal["TODO", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"]


class CreateTaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=100000)
    assignee_id: UUID | None = None
    status: TaskStatus = "TODO"
    priority: str | None = Field(default=None, max_length=32)
    due_date: datetime | None = None


class GetTaskInput(BaseModel):
    task_id: UUID


class UpdateTaskInput(BaseModel):
    task_id: UUID
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=100000)
    assignee_id: UUID | None = None
    status: TaskStatus | None = None
    priority: str | None = Field(default=None, max_length=32)
    due_date: datetime | None = None


class ListTasksInput(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    status: TaskStatus | None = None
    assignee_id: UUID | None = None
    search: str | None = Field(default=None, max_length=255)


class TaskTools:
    def __init__(self, session: AsyncSession) -> None:
        self.service = TaskService(session)

    def registered_tools(self) -> list[RegisteredTool[Any]]:
        return [
            RegisteredTool("create_task", "Create a task in the authenticated organization.", CreateTaskInput, self.create_task),
            RegisteredTool("get_task", "Retrieve a task from the authenticated organization.", GetTaskInput, self.get_task),
            RegisteredTool("update_task", "Update a task in the authenticated organization.", UpdateTaskInput, self.update_task),
            RegisteredTool("list_tasks", "List and filter tasks in the authenticated organization.", ListTasksInput, self.list_tasks),
        ]

    @staticmethod
    def _organization_id(context: ToolContext) -> UUID:
        if context.organization_id is None:
            raise PermissionError("An organization is required to use task tools.")
        return context.organization_id

    async def create_task(self, arguments: CreateTaskInput, context: ToolContext) -> dict[str, Any]:
        task = await self.service.create(
            TaskCreate(**arguments.model_dump()), context.user_id, self._organization_id(context)
        )
        return task_response(task)

    async def get_task(self, arguments: GetTaskInput, context: ToolContext) -> dict[str, Any]:
        task = await self.service.get(arguments.task_id, self._organization_id(context))
        if task is None:
            raise LookupError("Task was not found.")
        return task_response(task)

    async def update_task(self, arguments: UpdateTaskInput, context: ToolContext) -> dict[str, Any]:
        update_data = arguments.model_dump(exclude={"task_id"}, exclude_unset=True)
        task = await self.service.update(
            arguments.task_id,
            TaskUpdate(**update_data),
            self._organization_id(context),
        )
        if task is None:
            raise LookupError("Task was not found.")
        return task_response(task)

    async def list_tasks(self, arguments: ListTasksInput, context: ToolContext) -> dict[str, Any]:
        tasks = await self.service.list(
            self._organization_id(context),
            arguments.limit,
            arguments.offset,
            arguments.status,
            arguments.assignee_id,
            arguments.search,
        )
        return {"tasks": [task_response(task) for task in tasks]}


def task_response(task: Any) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "organization_id": str(task.organization_id),
        "owner_id": str(task.owner_id),
        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "deleted_at": task.deleted_at.isoformat() if task.deleted_at else None,
    }
