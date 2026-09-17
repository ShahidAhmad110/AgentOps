# 09 — Document Processing & RAG Specification

## Ingestion Pipeline
```text
Upload
 ↓
Validate
 ↓
Store File
 ↓
Create Document Record
 ↓
Extract Text
 ↓
Clean / Normalize
 ↓
Chunk
 ↓
Generate Embeddings
 ↓
Store Chunks
 ↓
Index
 ↓
READY
```

## Supported Formats
Required: PDF, TXT, Markdown.
Optional: DOCX.

## RAG Query Flow
```text
User Query
 ↓
Embedding
 ↓
Semantic Search
 ↓
Rank / Filter
 ↓
Relevant Chunks
 ↓
Context
 ↓
Agent/LLM
 ↓
Answer + Sources
```

## Grounding Rules
- Preserve source metadata.
- Return source references with knowledge answers.
- Do not invent unsupported information.
- Empty or weak retrieval should produce an appropriate limitation response.

## Document Status
UPLOADING → PROCESSING → INDEXING → READY; failures become FAILED with an error record.
