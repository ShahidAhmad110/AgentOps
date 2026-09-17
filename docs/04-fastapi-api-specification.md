# 04 — FastAPI API Specification

## Purpose
FastAPI exposes the platform through REST APIs.

## API Boundaries
```text
Frontend → FastAPI → Services → Repositories → PostgreSQL
Frontend → Agent API → LangGraph → Tools/MCP → Services
```

## Planned Endpoint Groups
- `/auth` — authentication and session/token operations.
- `/users` — user profile and user administration where authorized.
- `/conversations` — conversation and message operations.
- `/agent` — submit requests and retrieve agent run information.
- `/documents` — upload, list, retrieve, search, archive/delete.
- `/tasks` — task CRUD, assignment, status, comments and filtering.
- `/agent-runs` — execution inspection.
- `/admin` — administrative monitoring.

## API Requirements
- Pydantic validation.
- Consistent success/error response structure.
- Authentication and authorization.
- Pagination for list resources.
- Request IDs for tracing.
- Controlled exception handling.
- No direct database access from frontend.

## Error Categories
Validation, authentication, authorization, database, LLM, tool, document, embedding, timeout, rate-limit and unexpected-agent-state errors.
