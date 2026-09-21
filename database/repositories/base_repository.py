from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository:
    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, model_id: Any) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == model_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ModelType]:
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
