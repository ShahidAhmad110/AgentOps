from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import get_current_user
from backend.core.errors import APIError
from backend.schemas.task import (
    TaskCommentCreate,
    TaskCommentResponse,
    TaskCreate,
    TaskDetailResponse,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)
from backend.services.task_service import TaskService, TaskValidationError
from database.connection.session import get_database_session
from database.models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


def organization_id_for(user: User) -> UUID:
    if user.organization_id is None:
        raise APIError("ORGANIZATION_REQUIRED", "An organization is required.", status_code=403)
    return user.organization_id


def handle_task_validation(error: TaskValidationError) -> APIError:
    return APIError("TASK_VALIDATION_ERROR", str(error), status_code=422)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> TaskResponse:
    try:
        task = await TaskService(session).create(request, user.id, organization_id_for(user))
    except TaskValidationError as exc:
        raise handle_task_validation(exc) from exc
    return TaskResponse.model_validate(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    assignee_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> list[TaskResponse]:
    tasks = await TaskService(session).list(
        organization_id_for(user), limit, offset, task_status, assignee_id, search
    )
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> TaskDetailResponse:
    service = TaskService(session)
    task = await service.get(task_id, organization_id_for(user))
    if task is None:
        raise APIError("TASK_NOT_FOUND", "The task was not found.", status_code=404)
    comments = await service.list_comments(task.id, user.organization_id)
    return TaskDetailResponse(
        **TaskResponse.model_validate(task).model_dump(),
        comments=[TaskCommentResponse.model_validate(comment) for comment in comments or []],
    )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    request: TaskUpdate,
    task_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> TaskResponse:
    try:
        task = await TaskService(session).update(task_id, request, organization_id_for(user))
    except TaskValidationError as exc:
        raise handle_task_validation(exc) from exc
    if task is None:
        raise APIError("TASK_NOT_FOUND", "The task was not found.", status_code=404)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_task(
    task_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> Response:
    archived = await TaskService(session).archive(task_id, organization_id_for(user))
    if not archived:
        raise APIError("TASK_NOT_FOUND", "The task was not found.", status_code=404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_task_comment(
    request: TaskCommentCreate,
    task_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> TaskCommentResponse:
    comment = await TaskService(session).add_comment(
        task_id, request, user.id, organization_id_for(user)
    )
    if comment is None:
        raise APIError("TASK_NOT_FOUND", "The task was not found.", status_code=404)
    return TaskCommentResponse.model_validate(comment)


@router.get("/{task_id}/comments", response_model=list[TaskCommentResponse])
async def list_task_comments(
    task_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> list[TaskCommentResponse]:
    comments = await TaskService(session).list_comments(task_id, organization_id_for(user))
    if comments is None:
        raise APIError("TASK_NOT_FOUND", "The task was not found.", status_code=404)
    return [TaskCommentResponse.model_validate(comment) for comment in comments]
