from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from database.models.document import Document, DocumentChunk, DocumentVersion
from database.repositories.document_repository import DocumentRepository
from documents.chunking.text_chunker import chunk_text
from documents.embeddings.hash_embeddings import HashEmbeddingProvider
from documents.loaders.extractor import extract_text, validate_filename
from documents.retrieval.rag_context import RAGContext, RetrievedSource, build_rag_context
from documents.storage.file_storage import LocalDocumentStorage


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = DocumentRepository(session)
        self.session = session
        self.embedding_provider = HashEmbeddingProvider()
        self.storage = LocalDocumentStorage(get_settings().document_storage_path)

    async def ingest(self, filename: str, content_type: str, content: bytes) -> Document:
        extension = validate_filename(filename)
        if len(content) > get_settings().max_document_size_bytes:
            raise ValueError("The uploaded document exceeds the configured size limit.")

        checksum = hashlib.sha256(content).hexdigest()
        document = Document(
            filename=filename,
            content_type=content_type or "application/octet-stream",
            file_extension=extension,
            size_bytes=len(content),
            checksum=checksum,
            storage_path="",
            status="UPLOADING",
            metadata_json={},
        )
        await self.repository.add_document(document)
        await self.session.commit()

        try:
            document.storage_path = await self.storage.save(document.id, filename, content)
            document.status = "PROCESSING"
            await self.session.commit()

            text, metadata = extract_text(filename, content_type, content)
            chunks = chunk_text(text)
            if not chunks:
                raise ValueError("The document did not produce any searchable chunks.")

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
            await self.repository.add_chunks(
                [
                    DocumentChunk(
                        version_id=version.id,
                        chunk_index=chunk.index,
                        content=chunk.content,
                        embedding=self.embedding_provider.embed(chunk.content),
                        metadata_json={**metadata, "filename": filename, "chunk_index": chunk.index},
                    )
                    for chunk in chunks
                ]
            )
            document.status = "READY"
            await self.session.commit()
            return document
        except Exception as exc:
            await self.session.rollback()
            document = await self.repository.get(document.id)
            if document is not None:
                document.status = "FAILED"
                document.error_message = str(exc)
                await self.session.commit()
            raise

    async def get(self, document_id: UUID) -> Document | None:
        return await self.repository.get(document_id)

    async def list(self, limit: int = 50, offset: int = 0) -> list[Document]:
        return await self.repository.list(limit, offset)

    async def search(self, query: str, limit: int = 5) -> RAGContext:
        query_embedding = self.embedding_provider.embed(query)
        matches: list[RetrievedSource] = []
        for chunk, _version, document in await self.repository.ready_chunks():
            score = sum(left * right for left, right in zip(query_embedding, chunk.embedding))
            matches.append(
                RetrievedSource(
                    document_id=document.id,
                    filename=document.filename,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=score,
                )
            )
        matches.sort(key=lambda source: source.score, reverse=True)
        return build_rag_context(query, matches[:limit])
