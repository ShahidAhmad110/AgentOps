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

    async def ingest(
        self, filename: str, content_type: str, content: bytes, user_id: UUID, organization_id: UUID
    ) -> Document:
        extension = validate_filename(filename)
        if len(content) > get_settings().max_document_size_bytes:
            raise ValueError("The uploaded document exceeds the configured size limit.")

        checksum = hashlib.sha256(content).hexdigest()

        # Check if an identical document already exists and is READY in this organization
        existing_doc = await self.repository.get_by_checksum(checksum, organization_id)
        if existing_doc is not None and existing_doc.status == "READY":
            return existing_doc

        # If a prior version of the same filename exists in this organization, archive it
        prior_named_doc = await self.repository.get_by_filename(filename, organization_id)
        if prior_named_doc is not None and prior_named_doc.id != (existing_doc.id if existing_doc else None):
            await self.repository.soft_delete(prior_named_doc)

        document = Document(
            user_id=user_id,
            organization_id=organization_id,
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
            document_id = document.id
            await self.session.rollback()
            document = await self.repository.get(document_id)
            if document is not None:
                document.status = "FAILED"
                document.error_message = str(exc)
                await self.session.commit()
            raise

    async def get(self, document_id: UUID, organization_id: UUID | None = None) -> Document | None:
        return await self.repository.get(document_id, organization_id)

    async def list(self, limit: int = 50, offset: int = 0, organization_id: UUID | None = None) -> list[Document]:
        return await self.repository.list(limit, offset, organization_id)

    async def archive(self, document_id: UUID, organization_id: UUID) -> bool:
        document = await self.repository.get(document_id, organization_id)
        if document is None:
            return False
        await self.repository.soft_delete(document)
        await self.session.commit()
        return True

    async def search(self, query: str, limit: int = 5, organization_id: UUID | None = None) -> RAGContext:
        import re

        query_embedding = self.embedding_provider.embed(query)
        stop_words = {
            "what", "is", "the", "are", "about", "our", "a", "an", "in", "to", "for", "of",
            "and", "do", "how", "tell", "me", "can", "you", "please", "my", "we", "i", "us",
            "its", "it", "this", "that", "these", "those", "there", "their", "they", "your",
            "yours", "his", "her", "who", "which", "whom", "where", "when", "why", "was",
            "were", "be", "been", "being", "have", "has", "had", "does", "did", "shall",
            "will", "should", "would", "may", "might", "must", "could", "some", "any", "with"
        }
        q_tokens = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in stop_words]
        if not q_tokens:
            q_tokens = re.findall(r"[a-z0-9]+", query.lower())
        q_phrase = " ".join(q_tokens)

        matches: list[RetrievedSource] = []
        for chunk, _version, document in await self.repository.ready_chunks(organization_id):
            emb_score = max(sum(left * right for left, right in zip(query_embedding, chunk.embedding)), 0.0)
            c_lower = chunk.content.lower()
            c_tokens = set(re.findall(r"[a-z0-9]+", c_lower))

            overlap_ratio = (
                sum(1 for t in q_tokens if t in c_tokens) / len(q_tokens)
                if q_tokens
                else 0.0
            )
            phrase_bonus = 0.3 if q_phrase and len(q_tokens) > 1 and q_phrase in c_lower else 0.0

            final_score = (0.35 * emb_score) + (0.50 * overlap_ratio) + (0.15 * phrase_bonus)
            if final_score > 0.01:
                matches.append(
                    RetrievedSource(
                        document_id=document.id,
                        filename=document.filename,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        score=final_score,
                    )
                )

        matches.sort(key=lambda source: source.score, reverse=True)
        return build_rag_context(query, matches[:limit])
