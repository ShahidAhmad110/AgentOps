# 16 — Testing Strategy

## Unit Tests
Test individual functions, services, schemas and domain rules.

## Integration Tests
Verify:
```text
API → Service → Repository → Database
```

## Agent Tests
Required scenarios:
- RAG knowledge question.
- Question requiring no tool.
- Task creation.
- Invalid tool request.
- Tool failure.
- Empty retrieval.

## End-to-End
```text
Login
 ↓
Upload Document
 ↓
Background Processing
 ↓
Ask Question
 ↓
Agent Retrieval
 ↓
Answer
```

## Test Principles
Tests should be repeatable, isolated where practical, and included in the development workflow.
