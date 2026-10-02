from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from database.connection.session import engine

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("agentops.scripts.health")


async def check_health() -> bool:
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                logger.info("Database connection healthy: SELECT 1 succeeded.")
                return True
            else:
                logger.error("Unexpected database query response.")
                return False
    except Exception as exc:
        logger.error(f"Health check failed to connect to database: {exc}")
        return False


if __name__ == "__main__":
    healthy = asyncio.run(check_health())
    sys.exit(0 if healthy else 1)
