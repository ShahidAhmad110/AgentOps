# AgentOps — Demonstration & Technical Walkthrough

## 1. System Overview
AgentOps is an agentic operations platform bridging enterprise knowledge retrieval, conversational reasoning, task orchestration, and background worker automation into a unified operational console.

```text
┌────────────────────────────────────────────────────────┐
│               AgentOps Next.js Frontend                │
│ (Dashboard, AI Chat, Knowledge Library, Task Board)    │
└───────────────────────────┬────────────────────────────┘
                            │ REST API + JWT Bearer
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI Backend                     │
│ (Auth, RBAC, Services, LangGraph Agent, Observability) │
└─────────────┬──────────────────────────┬───────────────┘
              │                          │
┌─────────────▼─────────────┐ ┌──────────▼───────────────┐
│       PostgreSQL 16       │ │    Background Worker     │
│ (Users, Tasks, Docs, Runs)│ │ (Ingestion & Hygiene)    │
└───────────────────────────┘ └──────────────────────────┘
```

---

## 2. Technical Walkthrough & Key Capabilities

### A. Authentication & Organization Multi-Tenancy
- Users register an organization and receive scoped JWT tokens.
- All documents, tasks, conversations, and agent runs are strictly isolated per organization.

### B. Operations Dashboard
- Live operational health counters (open/completed tasks, indexed documents, agent runs).
- Quick navigation and workspace summary.

### C. AI Workspace & LangGraph Agent
- 10-node StateGraph executing intent routing, policy evaluation, task/conversation tool calling, and RAG retrieval.
- Displays transparent execution details: retrieved source chunks with relevance percentages and MCP tool calls.

### D. Knowledge Library (RAG Pipeline)
- Upload `.pdf`, `.txt`, and `.md` files.
- Text extraction, sliding window chunking, embedding generation, and vector/hybrid retrieval.

### E. Task Kanban & Collaboration
- Create and assign operational tasks with priority levels and due dates.
- Status transitions (`TODO` -> `IN_PROGRESS` -> `COMPLETED`).
- Comment history per task.

### F. Asynchronous Background Workers & Docker Topology
- Resilient background worker processing document ingestion queues and maintaining system hygiene.
- Multi-container Docker Compose setup with healthchecks and security hardening.
