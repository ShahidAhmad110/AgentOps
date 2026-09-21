from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from database.models.user import User
from database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users_for_org(self, organization_id: UUID) -> list[User]:
        stmt = select(User).where(User.organization_id == organization_id, User.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
