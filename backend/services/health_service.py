from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from database.connection.session import engine


@dataclass
class HealthStatus:
    status: str
    database: str
    details: dict[str, Any] | None = None


async def get_health_status() -> HealthStatus:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return HealthStatus(status="ok", database="connected")
    except Exception as exc:  # pragma: no cover - real DB failure path
        return HealthStatus(
            status="degraded",
            database="unavailable",
            details={"error": str(exc)},
        )
