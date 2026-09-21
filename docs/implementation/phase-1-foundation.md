# Phase 1 Foundation

## Overview

This phase establishes the project foundation for AgentOps according to the SDD requirements. It includes the required production-level package scaffolding, environment configuration support, database layer foundation, initial ORM entities, FastAPI app bootstrap, and a minimal health path.

## Implemented

- Project structure directories for backend, agent, database, documents, mcp, frontend, workers, tests, docs, and scripts.
- Centralized application settings using `.env` with an example file.
- Async SQLAlchemy database session layer and DB engine configuration.
- Base ORM declarations for timestamps and soft delete fields.
- Initial models for `Organization` and `User`.
- Repository layer with basic CRUD helpers and domain-specific query methods.
- Alembic migration scaffold and a first migration creating the base schema.
- Minimal seed mechanism for a default organization and admin user.
- FastAPI application factory and health endpoint connected to the backend service layer.
- Basic request ID middleware and error handlers.
- Initial tests for startup, configuration, and health behavior.

## Files Created

- [backend/api/app.py](../../backend/api/app.py)
- [backend/api/routes/health.py](../../backend/api/routes/health.py)
- [backend/core/config.py](../../core/config.py)
- [backend/core/errors.py](../../core/errors.py)
- [backend/core/logging.py](../../core/logging.py)
- [backend/middleware/request_id.py](../../middleware/request_id.py)
- [backend/services/health_service.py](../../services/health_service.py)
- [database/base.py](../../database/base.py)
- [database/connection/session.py](../../database/connection/session.py)
- [database/models/organization.py](../../database/models/organization.py)
- [database/models/user.py](../../database/models/user.py)
- [database/repositories/base_repository.py](../../database/repositories/base_repository.py)
- [database/repositories/organization_repository.py](../../database/repositories/organization_repository.py)
- [database/repositories/user_repository.py](../../database/repositories/user_repository.py)
- [database/migrations/versions/20260919_0001_initial_foundation.py](../../database/migrations/versions/20260919_0001_initial_foundation.py)
- [database/seeds/seed_data.py](../../database/seeds/seed_data.py)
- [tests/unit/test_config.py](../../tests/unit/test_config.py)
- [tests/unit/test_app_startup.py](../../tests/unit/test_app_startup.py)
- [tests/integration/test_database_connectivity.py](../../tests/integration/test_database_connectivity.py)

## Architecture Decisions

- The backend keeps the dependency direction: API → Service → Repository → Database.
- Business logic is separated from the API route layer.
- Environment configuration remains in `.env` with `.env.example` documenting required variables.
- PostgreSQL is the SDD-selected database technology.
- The initial schema focuses only on the essential domain objects required for the foundation: organizations and users.

## How to Run

```bash
# create the environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or use uv sync --dev

# start the app
uvicorn main:app --reload
```

## How to Run Migrations

```bash
alembic upgrade head
```

## How to Run Tests

```bash
pytest -q
```

## Remaining Incomplete

- Authentication and RBAC
- Conversation/task domain models
- Document ingestion and RAG
- Agent/LangGraph workflow
- MCP tool layer
- Frontend implementation
- Workers
- Full production deployment configuration
