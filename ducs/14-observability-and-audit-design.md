# 14 — Observability & Audit Specification

## Goal
Make agent execution understandable and traceable.

## Agent Run View
```text
Run
 ↓
User Request
 ↓
Intent Analysis
 ↓
Retrieval / Tool Selection
 ↓
Tool or Retrieval Result
 ↓
Reasoning
 ↓
Final Response
```

## Record
- Agent run ID.
- User request.
- Execution status.
- Duration.
- Nodes executed.
- Tools called.
- Retrieval results/metadata.
- Errors.
- Final outcome.

## Audit
Record security-sensitive and operational actions sufficiently to explain what happened.

## Failure Visibility
A tool/database failure must be recorded and must never be represented to the user as successful execution.
