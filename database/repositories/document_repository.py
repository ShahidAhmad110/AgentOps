from __future__ import annotations

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

    async def get(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id, Document.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int) -> list[Document]:
        result = await self.session.execute(
            select(Document)
            .where(Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def ready_chunks(self) -> list[tuple[DocumentChunk, DocumentVersion, Document]]:
        result = await self.session.execute(
            select(DocumentChunk, DocumentVersion, Document)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.status == "READY", Document.deleted_at.is_(None))
        )
        return list(result.all())
