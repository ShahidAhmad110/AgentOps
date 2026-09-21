from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal["TODO", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=100000)
    assignee_id: UUID | None = None
    status: TaskStatus = "TODO"
    priority: str | None = Field(default=None, max_length=32)
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=100000)
    assignee_id: UUID | None = None
    status: TaskStatus | None = None
    priority: str | None = Field(default=None, max_length=32)
    due_date: datetime | None = None


class TaskCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100000)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    owner_id: UUID
    assignee_id: UUID | None
    title: str
    description: str | None
    status: str
    priority: str | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class TaskCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime


class TaskDetailResponse(TaskResponse):
    comments: list[TaskCommentResponse]
