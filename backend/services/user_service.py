from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import APIError
from backend.services.organization_service import OrganizationService
from database.models.user import User
from database.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.organizations = OrganizationService(session)

    async def get_organization(self, user: User):
        if user.organization_id is None:
            return None
        return await self.organizations.get_active(user.organization_id)

    async def get_user_for_actor(self, actor: User, user_id: UUID) -> User | None:
        if actor.role == "admin":
            return await self.users.get_by_id(user_id)
        if actor.role == "supervisor":
            if actor.organization_id is None:
                return None
            return await self.users.get_scoped(user_id, actor.organization_id)
        return None

    async def list_users_with_counts(
        self,
        actor: User,
        search: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[User], int, int, int]:
        if actor.role == "admin":
            users = await self.users.list_all(
                search=search,
                is_active=is_active,
                limit=limit,
                offset=offset,
            )
            total = await self.users.count_all(search=search, is_active=None)
            active_count = await self.users.count_all(search=search, is_active=True)
            inactive_count = await self.users.count_all(search=search, is_active=False)
            return users, total, active_count, inactive_count

        if actor.role == "supervisor":
            if actor.organization_id is None:
                return [], 0, 0, 0
            users = await self.users.list_for_organization(
                organization_id=actor.organization_id,
                search=search,
                is_active=is_active,
                limit=limit,
                offset=offset,
            )
            total = await self.users.count_for_organization(
                organization_id=actor.organization_id, search=search, is_active=None
            )
            active_count = await self.users.count_for_organization(
                organization_id=actor.organization_id, search=search, is_active=True
            )
            inactive_count = await self.users.count_for_organization(
                organization_id=actor.organization_id, search=search, is_active=False
            )
            return users, total, active_count, inactive_count

        raise APIError("FORBIDDEN", "You do not have permission to view users.", status_code=403)

    async def update_user_status(
        self, actor: User, target_user_id: UUID, is_active: bool
    ) -> User:
        if actor.role == "admin":
            target = await self.users.get_by_id(target_user_id)
        elif actor.role == "supervisor":
            if actor.organization_id is None:
                raise APIError("ORGANIZATION_REQUIRED", "An organization is required.", status_code=403)
            target = await self.users.get_scoped(target_user_id, actor.organization_id)
        else:
            raise APIError("FORBIDDEN", "You do not have permission to modify users.", status_code=403)

        if target is None:
            raise APIError("USER_NOT_FOUND", "User was not found.", status_code=404)

        if not is_active and target.id == actor.id:
            raise APIError("SELF_DEACTIVATION_PROHIBITED", "You cannot deactivate your own account.", status_code=400)

        if not is_active and target.role in ("admin", "supervisor") and target.is_active and target.organization_id is not None:
            active_admins = await self.users.count_active_admins(target.organization_id)
            if active_admins <= 1:
                raise APIError(
                    "LAST_ADMIN_PROTECTED",
                    "Cannot deactivate the only active administrator in the organization.",
                    status_code=400,
                )

        updated = await self.users.update_status(target, is_active)
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def delete_user(self, actor: User, target_user_id: UUID) -> User:
        if actor.role == "admin":
            target = await self.users.get_by_id(target_user_id)
        elif actor.role == "supervisor":
            if actor.organization_id is None:
                raise APIError("ORGANIZATION_REQUIRED", "An organization is required.", status_code=403)
            target = await self.users.get_scoped(target_user_id, actor.organization_id)
        else:
            raise APIError("FORBIDDEN", "You do not have permission to delete users.", status_code=403)

        if target is None:
            raise APIError("USER_NOT_FOUND", "User was not found.", status_code=404)

        if target.id == actor.id:
            raise APIError("SELF_DELETION_PROHIBITED", "You cannot delete your own account.", status_code=400)

        if target.role in ("admin", "supervisor") and target.is_active and target.organization_id is not None:
            active_admins = await self.users.count_active_admins(target.organization_id)
            if active_admins <= 1:
                raise APIError(
                    "LAST_ADMIN_PROTECTED",
                    "Cannot delete the only active administrator in the organization.",
                    status_code=400,
                )

        deleted = await self.users.soft_delete(target)
        await self.session.commit()
        await self.session.refresh(deleted)
        return deleted
