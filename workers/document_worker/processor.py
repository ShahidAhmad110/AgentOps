from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from database.models.document import Document, DocumentChunk, DocumentVersion
from database.repositories.document_repository import DocumentRepository
from documents.chunking.text_chunker import chunk_text
from documents.embeddings.hash_embeddings import HashEmbeddingProvider
from documents.loaders.extractor import extract_text
from documents.storage.file_storage import LocalDocumentStorage

logger = logging.getLogger("agentops.workers.document")


class DocumentWorkerProcessor:
    """Asynchronous worker processor for document ingestion pipeline.
    
    Status Lifecycle: UPLOADED -> PROCESSING -> INDEXING -> READY (or FAILED)
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DocumentRepository(session)
        self.embedding_provider = HashEmbeddingProvider()
        self.storage = LocalDocumentStorage(get_settings().document_storage_path)

    async def process_document(self, document_id: UUID, retry_limit: int = 3) -> Document:
        """Process a single document through extraction, chunking, and embedding."""
        document = await self.repository.get(document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found.")

        if document.status in ("READY", "ARCHIVED"):
            return document

        logger.info(f"Worker processing document {document.id} ({document.filename})")
        document.status = "PROCESSING"
        await self.session.commit()

        try:
            content = await self.storage.load(document.storage_path)
            text, metadata = extract_text(document.filename, document.content_type, content)
            chunks = chunk_text(text)
            if not chunks:
                raise ValueError("The document produced no searchable chunks.")

            document.status = "INDEXING"
            document.metadata_json = metadata
            version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                extracted_text=text,
                metadata_json=metadata,
            )
            await self.repository.add_version(version)
            await self.session.flush()

            chunk_records = [
                DocumentChunk(
                    version_id=version.id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=self.embedding_provider.embed(chunk.content),
                    metadata_json={**metadata, "filename": document.filename, "chunk_index": chunk.index},
                )
                for chunk in chunks
            ]
            await self.repository.add_chunks(chunk_records)
            document.status = "READY"
            document.error_message = None
            await self.session.commit()
            logger.info(f"Document {document.id} successfully indexed with {len(chunk_records)} chunks.")
            return document

        except Exception as exc:
            logger.error(f"Failed to process document {document.id}: {exc}", exc_info=True)
            await self.session.rollback()
            doc_to_update = await self.repository.get(document_id)
            if doc_to_update is not None:
                doc_to_update.status = "FAILED"
                doc_to_update.error_message = str(exc)
                await self.session.commit()
            raise

    async def process_pending_documents(self, batch_size: int = 10) -> int:
        """Finds documents in UPLOADED or stuck in PROCESSING and processes them."""
        stmt = (
            select(Document)
            .where(Document.status.in_(["UPLOADED", "UPLOADING"]))
            .limit(batch_size)
        )
        result = await self.session.execute(stmt)
        pending = list(result.scalars().all())

        processed_count = 0
        for doc in pending:
            try:
                await self.process_document(doc.id)
                processed_count += 1
            except Exception as exc:
                logger.warning(f"Error processing pending document {doc.id}: {exc}")
        return processed_count
