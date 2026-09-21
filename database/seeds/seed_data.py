from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.security import PasswordHasher
from database.models.organization import Organization
from database.models.user import User


async def seed_initial_data(session: AsyncSession) -> None:
    existing_org = await session.execute(select(Organization).limit(1))
    if existing_org.scalar_one_or_none() is not None:
        return

    org = Organization(id=uuid4(), name="Default Organization", slug="default")
    session.add(org)
    await session.flush()

    seed_password = get_settings().seed_admin_password
    if not seed_password:
        raise RuntimeError("SEED_ADMIN_PASSWORD must be configured before seeding an admin user.")

    user = User(
        id=uuid4(),
        email="admin@example.com",
        username="admin",
        password_hash=PasswordHasher().hash(seed_password),
        role="admin",
        is_active=True,
        organization_id=org.id,
    )
    session.add(user)
    await session.commit()
