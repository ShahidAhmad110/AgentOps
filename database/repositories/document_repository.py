from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.document import Document, DocumentChunk, DocumentVersion


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_document(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.flush()
        return document

    async def add_version(self, version: DocumentVersion) -> DocumentVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        self.session.add_all(chunks)
        await self.session.flush()

    async def soft_delete(self, document: Document) -> None:
        document.deleted_at = datetime.now(timezone.utc)

    async def get(self, document_id: UUID, organization_id: UUID | None = None) -> Document | None:
        statement = select(Document).where(Document.id == document_id, Document.deleted_at.is_(None))
        if organization_id is not None:
            statement = statement.where(Document.organization_id == organization_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_checksum(self, checksum: str, organization_id: UUID) -> Document | None:
        statement = select(Document).where(
            Document.checksum == checksum,
            Document.organization_id == organization_id,
            Document.deleted_at.is_(None),
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_by_filename(self, filename: str, organization_id: UUID) -> Document | None:
        statement = select(Document).where(
            Document.filename == filename,
            Document.organization_id == organization_id,
            Document.deleted_at.is_(None),
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list(self, limit: int, offset: int, organization_id: UUID | None = None) -> list[Document]:
        statement = select(Document).where(Document.deleted_at.is_(None))
        if organization_id is not None:
            statement = statement.where(Document.organization_id == organization_id)
        statement = statement.order_by(Document.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def ready_chunks(
        self, organization_id: UUID | None = None
    ) -> list[tuple[DocumentChunk, DocumentVersion, Document]]:
        statement = (
            select(DocumentChunk, DocumentVersion, Document)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.status == "READY", Document.deleted_at.is_(None))
        )
        if organization_id is not None:
            statement = statement.where(Document.organization_id == organization_id)
        result = await self.session.execute(statement)
        return list(result.all())
