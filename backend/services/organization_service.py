from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.organization import Organization
from database.repositories.organization_repository import OrganizationRepository


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = OrganizationRepository(session)

    async def get_active(self, organization_id: UUID) -> Organization | None:
        organization = await self.repository.get_by_id(organization_id)
        if organization is None or not organization.is_active:
            return None
        return organization
