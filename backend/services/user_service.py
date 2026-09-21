from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.organization_service import OrganizationService
from database.models.user import User
from database.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
        self.organizations = OrganizationService(session)

    async def get_organization(self, user: User):
        if user.organization_id is None:
            return None
        return await self.organizations.get_active(user.organization_id)

    async def list_for_organization(
        self, organization_id: UUID, limit: int, offset: int
    ) -> list[User]:
        users = await self.users.get_active_users_for_org(organization_id)
        return users[offset : offset + limit]
