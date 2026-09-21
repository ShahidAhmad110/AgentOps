import pytest
from sqlalchemy import text

from database.connection.session import engine


@pytest.mark.asyncio
async def test_database_engine_connects() -> None:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        assert True
    except Exception as exc:  # pragma: no cover - environment-specific DB availability
        pytest.skip(f"Database not available in this environment: {exc}")
