# 05 — Database Design Specification

## Database
PostgreSQL is the primary application database.

## Core Entities
```text
users
organizations
roles
conversations
messages
agents
agent_runs
agent_steps
tools
tool_calls
documents
document_versions
document_chunks
tasks
task_comments
audit_logs
knowledge_sources
```

## Design Requirements
- Primary and foreign keys.
- Appropriate indexes.
- Constraints for data integrity.
- Transactions for multi-step writes.
- Relationships documented through an ERD.
- Pagination for list queries.
- Timestamps.
- Soft deletion where appropriate.
- Audit history.
- Version-controlled migrations.

## Data Flow
Agent/MCP → Service → Repository → PostgreSQL.

The agent must not directly manipulate the database.

## Migration Policy
Every schema change is represented by a version-controlled migration. The database should not be created by manually clicking through a GUI.
