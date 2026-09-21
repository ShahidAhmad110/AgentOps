from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RetrievedSource:
    document_id: UUID
    filename: str
    chunk_index: int
    content: str
    score: float


@dataclass(frozen=True)
class RAGContext:
    context: str
    sources: list[RetrievedSource]
    limitation: str | None = None


def build_rag_context(
    query: str, sources: list[RetrievedSource], minimum_score: float = 0.15
) -> RAGContext:
    useful_sources = [source for source in sources if source.score >= minimum_score]
    if not useful_sources:
        return RAGContext(
            context="",
            sources=[],
            limitation="No sufficiently relevant document evidence was found.",
        )

    sections = [
        f"[Source: {source.filename}, chunk {source.chunk_index}]\n{source.content}"
        for source in useful_sources
    ]
    return RAGContext(context="\n\n".join(sections), sources=useful_sources)
