from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    file_extension: str
    size_bytes: int
    status: str
    error_message: str | None = None
    metadata_json: dict


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class SourceResponse(BaseModel):
    document_id: UUID
    filename: str
    chunk_index: int
    content: str
    score: float


class SearchResponse(BaseModel):
    context: str
    sources: list[SourceResponse]
    limitation: str | None = None
