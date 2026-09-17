# 03 — Backend Architecture Specification

## Responsibility
The backend is the application boundary between clients and internal platform capabilities.

## Layers
```text
API Routes
 ↓
Schemas / Validation
 ↓
Service Layer
 ↓
Repository Layer
 ↓
Database
```

## Backend Modules
```text
backend/
├── api/
├── core/
├── services/
├── repositories/
├── schemas/
└── middleware/
```

## Responsibilities
### API
HTTP endpoints, authentication dependencies, request/response handling.

### Core
Configuration, security primitives, shared exceptions, logging and application infrastructure.

### Services
Business rules for users, conversations, documents, tasks, agent runs and knowledge operations.

### Repositories
Database persistence and query abstraction.

### Schemas
Pydantic request/response models.

### Middleware
Authentication context, request IDs, error handling and other cross-cutting concerns.

## Rules
Business logic should not be embedded in route handlers. Database-specific operations should not be scattered throughout the application.
