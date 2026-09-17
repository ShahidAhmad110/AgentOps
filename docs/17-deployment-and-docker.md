# 17 — Deployment & Docker Specification

## Containerized Services
The development environment should support the required services through Docker Compose where appropriate:

```text
Frontend
Backend
PostgreSQL
Worker
MCP Server
```

## Configuration
Environment-specific settings are provided through environment variables. `.env.example` documents required variables without exposing secrets.

## Deployment Documentation
Document:
- Local startup.
- Service dependencies.
- Environment configuration.
- Database migrations.
- Worker startup.
- MCP startup.
- Frontend/backend communication.
- Production deployment process.
- Health checks and troubleshooting.

## Principle
The same architectural boundaries used locally should remain understandable in deployment.
