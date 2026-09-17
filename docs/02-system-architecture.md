# 02 — System Architecture Specification

## Architecture Goal
Define a modular production architecture in which frontend, API, services, repositories, agent, documents, MCP, workers, and database have clear responsibilities.

## High-Level Flow
```text
User
 ↓
Next.js Frontend
 ↓
FastAPI
 ↓
Application Services
 ├── LangGraph Agent
 ├── Document/RAG Services
 └── Task/Conversation Services
 ↓
Repositories / Controlled MCP Tools
 ↓
PostgreSQL + Document Storage
```

## Agent Flow
```text
Request
 ↓
Intent Analysis
 ├── Knowledge Task → Retrieval → Reasoning
 └── Operational Task → Tool Selection → Tool Execution
 ↓
Response Generation
 ↓
Persist Execution
```

## Architectural Rules
- No giant main.py.
- Frontend never connects directly to PostgreSQL.
- Agent does not execute arbitrary SQL.
- MCP exposes controlled capabilities.
- Services contain business logic.
- Repositories isolate persistence.
- Long-running document processing uses workers.
- Architecture changes must be reflected in SDD.

## Major Modules
backend, agent, database, documents, mcp, frontend, workers, tests, docs, scripts, docker.
