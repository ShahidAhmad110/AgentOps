from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.document import DocumentResponse
from backend.services.document_service import DocumentService
from mcp.schemas.context import ToolContext
from mcp.tools.base import RegisteredTool


class SearchDocumentsInput(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class GetDocumentInput(BaseModel):
    document_id: UUID


class KnowledgeTools:
    def __init__(self, document_service: DocumentService) -> None:
        self.document_service = document_service

    def registered_tools(self) -> list[RegisteredTool[Any]]:
        return [
            RegisteredTool(
                name="search_documents",
                description="Search indexed organizational documents and return grounded sources.",
                input_model=SearchDocumentsInput,
                handler=self.search_documents,
            ),
            RegisteredTool(
                name="get_document",
                description="Retrieve metadata for an indexed document by ID.",
                input_model=GetDocumentInput,
                handler=self.get_document,
            ),
        ]

    async def search_documents(
        self, arguments: SearchDocumentsInput, context: ToolContext
    ) -> dict[str, Any]:
        result = await self.document_service.search(arguments.query, arguments.limit)
        return {
            "context": result.context,
            "limitation": result.limitation,
            "sources": [
                {
                    "document_id": source.document_id,
                    "filename": source.filename,
                    "chunk_index": source.chunk_index,
                    "content": source.content,
                    "score": source.score,
                }
                for source in result.sources
            ],
        }

    async def get_document(self, arguments: GetDocumentInput, context: ToolContext) -> dict[str, Any]:
        document = await self.document_service.get(arguments.document_id)
        if document is None:
            raise LookupError("Document was not found.")
        return DocumentResponse.model_validate(document).model_dump(mode="json")
