from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from database.models.user import User
from database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.organization))
            .where(User.email == email, User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.organization))
            .where(User.username == username, User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.organization))
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_scoped(self, user_id: UUID, organization_id: UUID) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.organization))
            .where(
                User.id == user_id,
                User.organization_id == organization_id,
                User.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users_for_org(self, organization_id: UUID) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.organization))
            .where(
                User.organization_id == organization_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.organization))
            .where(User.deleted_at.is_(None))
        )
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(User.username.ilike(pattern), User.email.ilike(pattern)))
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(
        self,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        stmt = select(func.count(User.id)).where(User.deleted_at.is_(None))
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(User.username.ilike(pattern), User.email.ilike(pattern)))
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_for_organization(
        self,
        organization_id: UUID,
        search: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.organization))
            .where(
                User.organization_id == organization_id,
                User.deleted_at.is_(None),
            )
        )
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(User.username.ilike(pattern), User.email.ilike(pattern)))
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_organization(
        self,
        organization_id: UUID,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        stmt = select(func.count(User.id)).where(
            User.organization_id == organization_id,
            User.deleted_at.is_(None),
        )
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(User.username.ilike(pattern), User.email.ilike(pattern)))
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_active_admins(self, organization_id: UUID) -> int:
        stmt = select(func.count(User.id)).where(
            User.organization_id == organization_id,
            User.role.in_(["admin", "supervisor"]),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def update_status(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        await self.session.flush()
        return user

    async def soft_delete(self, user: User) -> User:
        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        await self.session.flush()
        return user
