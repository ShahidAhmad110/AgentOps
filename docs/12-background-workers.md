# 12 — Background Processing & Worker Specification

## Purpose
Long-running work must not block API requests.

## Document Worker
```text
Upload
 ↓
API returns
 ↓
Worker
 ↓
Extraction
 ↓
Chunking
 ↓
Embedding
 ↓
Indexing
```

## Status Lifecycle
UPLOADED → PROCESSING → INDEXING → READY
or
PROCESSING/INDEXING → FAILED

## Worker Modules
```text
workers/
├── document_worker/
├── task_worker/
└── maintenance/
```

## Requirements
- Retry appropriate transient failures.
- Record failures.
- Update processing status.
- Keep API responsive.
- Make work observable and testable.
