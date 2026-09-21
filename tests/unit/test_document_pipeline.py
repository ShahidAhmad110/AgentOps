from uuid import uuid4

from documents.chunking.text_chunker import chunk_text
from documents.embeddings.hash_embeddings import HashEmbeddingProvider
from documents.loaders.extractor import extract_text
from documents.retrieval.rag_context import RetrievedSource, build_rag_context


def test_text_pipeline_extracts_chunks_and_preserves_source_context() -> None:
    text, metadata = extract_text(
        "operations.md",
        "text/markdown",
        b"# Operations\n\nThe incident response guide is stored in the operations handbook.",
    )
    chunks = chunk_text(text, max_characters=80, overlap=10)
    embedding = HashEmbeddingProvider().embed(chunks[0].content)
    source = RetrievedSource(uuid4(), "operations.md", chunks[0].index, chunks[0].content, 1.0)

    context = build_rag_context("incident response", [source])

    assert metadata["format"] == "markdown"
    assert chunks
    assert len(embedding) == HashEmbeddingProvider.dimension
    assert "operations.md" in context.context
    assert context.limitation is None


def test_rag_context_reports_insufficient_evidence() -> None:
    source = RetrievedSource(uuid4(), "unrelated.txt", 0, "unrelated content", 0.01)

    context = build_rag_context("missing topic", [source])

    assert context.context == ""
    assert context.sources == []
    assert context.limitation is not None