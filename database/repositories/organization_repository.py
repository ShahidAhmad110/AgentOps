from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from database.models.organization import Organization
from database.repositories.base_repository import BaseRepository


class OrganizationRepository(BaseRepository):
    model = Organization

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active(self) -> list[Organization]:
        stmt = select(Organization).where(Organization.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, organization_id: UUID) -> Organization | None:
        organization = await self.get_by_id(organization_id)
        if organization is None:
            return None
        organization.is_active = False
        await self.session.commit()
        await self.session.refresh(organization)
        return organization
