from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import get_current_user, require_roles
from backend.core.errors import APIError
from backend.schemas.auth import (
    OrganizationResponse,
    UserResponse,
    UserStatusUpdateRequest,
    UserWithOrganizationResponse,
)
from backend.services.user_service import UserService
from database.connection.session import get_database_session
from database.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserWithOrganizationResponse)
async def get_my_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> UserWithOrganizationResponse:
    organization = await UserService(session).get_organization(user)
    return UserWithOrganizationResponse(
        **UserResponse.model_validate(user).model_dump(),
        organization=OrganizationResponse.model_validate(organization) if organization else None,
    )


@router.get("/me/organization", response_model=OrganizationResponse)
async def get_my_organization(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> OrganizationResponse:
    organization = await UserService(session).get_organization(user)
    if organization is None:
        raise APIError("ORGANIZATION_NOT_FOUND", "The organization was not found.", status_code=404)
    return OrganizationResponse.model_validate(organization)


@router.get("", response_model=list[UserWithOrganizationResponse])
async def list_users(
    response: Response,
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    actor: User = Depends(require_roles("admin", "supervisor")),
    session: AsyncSession = Depends(get_database_session),
) -> list[UserWithOrganizationResponse]:
    service = UserService(session)
    users, total, active_count, inactive_count = await service.list_users_with_counts(
        actor=actor,
        search=search,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Active-Count"] = str(active_count)
    response.headers["X-Inactive-Count"] = str(inactive_count)

    result = []
    for u in users:
        org = await service.get_organization(u)
        result.append(
            UserWithOrganizationResponse(
                **UserResponse.model_validate(u).model_dump(),
                organization=OrganizationResponse.model_validate(org) if org else None,
            )
        )
    return result


@router.get("/stats")
async def get_user_stats(
    actor: User = Depends(require_roles("admin", "supervisor")),
    session: AsyncSession = Depends(get_database_session),
) -> dict[str, int]:
    service = UserService(session)
    _, total, active_count, inactive_count = await service.list_users_with_counts(
        actor=actor,
        limit=1,
        offset=0,
    )
    return {
        "total": total,
        "active_count": active_count,
        "inactive_count": inactive_count,
    }


@router.get("/{user_id}", response_model=UserWithOrganizationResponse)
async def get_user_detail(
    user_id: UUID,
    actor: User = Depends(require_roles("admin", "supervisor")),
    session: AsyncSession = Depends(get_database_session),
) -> UserWithOrganizationResponse:
    service = UserService(session)
    user = await service.get_user_for_actor(actor, user_id)
    if user is None:
        raise APIError("USER_NOT_FOUND", "User was not found.", status_code=404)
    org = await service.get_organization(user)
    return UserWithOrganizationResponse(
        **UserResponse.model_validate(user).model_dump(),
        organization=OrganizationResponse.model_validate(org) if org else None,
    )


@router.patch("/{user_id}/status", response_model=UserWithOrganizationResponse)
async def update_user_status(
    user_id: UUID,
    request: UserStatusUpdateRequest,
    actor: User = Depends(require_roles("admin", "supervisor")),
    session: AsyncSession = Depends(get_database_session),
) -> UserWithOrganizationResponse:
    service = UserService(session)
    updated = await service.update_user_status(actor, user_id, request.is_active)
    org = await service.get_organization(updated)
    return UserWithOrganizationResponse(
        **UserResponse.model_validate(updated).model_dump(),
        organization=OrganizationResponse.model_validate(org) if org else None,
    )


@router.delete("/{user_id}", response_model=UserWithOrganizationResponse)
async def delete_user(
    user_id: UUID,
    actor: User = Depends(require_roles("admin", "supervisor")),
    session: AsyncSession = Depends(get_database_session),
) -> UserWithOrganizationResponse:
    service = UserService(session)
    deleted = await service.delete_user(actor, user_id)
    org = await service.get_organization(deleted)
    return UserWithOrganizationResponse(
        **UserResponse.model_validate(deleted).model_dump(),
        organization=OrganizationResponse.model_validate(org) if org else None,
    )
