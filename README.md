# AgentOps

AgentOps is an agentic operations and knowledge platform. This repository is
being implemented in phases from the specifications in [`ducs/`](ducs/).

## Phase 3 foundation

The current implementation provides:

- a FastAPI application factory;
- environment-backed settings and structured request logging;
- request IDs and controlled error responses;
- PostgreSQL Docker Compose configuration;
- async database connection and migration scaffolding;
- a focused health endpoint and test setup.

## Local development

Install the project and development dependencies, then run:

```powershell
uv sync --dev
uv run uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with health status at
`http://127.0.0.1:8000/health`.

Start PostgreSQL with:

```powershell
docker compose up -d postgres
```

Environment variables are documented in [`.env.example`](.env.example).
