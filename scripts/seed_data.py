from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from sqlalchemy import select

from backend.core.config import get_settings
from backend.core.security import PasswordHasher, TokenService
from database.connection.session import session_factory
from database.models.organization import Organization
from database.models.user import User

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("agentops.scripts.seed")


async def seed_data() -> None:
    settings = get_settings()
    admin_password = settings.seed_admin_password or "AgentOps2026!Admin"

    async with session_factory() as session:
        # Check if default organization exists
        stmt = select(Organization).where(Organization.slug == "default-org")
        result = await session.execute(stmt)
        org = result.scalar_one_or_none()

        if org is None:
            logger.info("Creating default organization: Default Operations")
            org = Organization(
                name="Default Operations",
                slug="default-org",
            )
            session.add(org)
            await session.flush()
        else:
            logger.info(f"Default organization already exists: {org.name} ({org.id})")

        # Check if default admin user exists
        stmt_user = select(User).where(User.username == "admin")
        result_user = await session.execute(stmt_user)
        user = result_user.scalar_one_or_none()

        if user is None:
            logger.info("Creating default admin user: admin (admin@agentops.local)")
            user = User(
                username="admin",
                email="admin@agentops.local",
                password_hash=PasswordHasher().hash(admin_password),
                role="admin",
                organization_id=org.id,
            )
            session.add(user)
            await session.commit()
            logger.info("Admin user created successfully.")
        else:
            logger.info(f"Admin user already exists: {user.username} ({user.id})")


if __name__ == "__main__":
    asyncio.run(seed_data())
