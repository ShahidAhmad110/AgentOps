from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger("agentops.scripts.migrations")


def run_migrations() -> None:
    """Applies all pending Alembic database migrations to head."""
    root_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = root_dir / "alembic.ini"

    if not alembic_ini_path.exists():
        logger.error(f"alembic.ini not found at {alembic_ini_path}")
        sys.exit(1)

    logger.info(f"Running database migrations using config: {alembic_ini_path}")
    alembic_cfg = Config(str(alembic_ini_path))
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations successfully applied to head.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    run_migrations()
