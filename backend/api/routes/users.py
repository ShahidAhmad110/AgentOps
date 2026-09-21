from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import get_current_user, require_roles
from backend.core.errors import APIError
from backend.schemas.auth import OrganizationResponse, UserResponse, UserWithOrganizationResponse
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


@router.get("", response_model=list[UserResponse])
async def list_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_database_session),
) -> list[UserResponse]:
    if admin.organization_id is None:
        return []
    users = await UserService(session).list_for_organization(admin.organization_id, limit, offset)
    return [UserResponse.model_validate(user) for user in users]
