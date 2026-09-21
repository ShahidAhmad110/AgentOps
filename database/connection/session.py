from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_database_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def init_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync_conn: None)
