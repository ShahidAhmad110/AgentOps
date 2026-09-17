# 10 — Frontend Architecture Specification

## Stack
- Next.js
- React
- TypeScript
- Tailwind CSS

## Main Areas
```text
frontend/
├── app/
├── components/
├── dashboard/
├── conversations/
├── documents/
├── tasks/
└── api/
```

## Pages
### Dashboard
Conversations, active/completed tasks, uploaded documents, recent agent runs and activity.

### AI Chat
Messages, responses, loading states, errors, source references, tool execution indicators and history.

### Documents
Upload, list, metadata, processing status, search and delete/archive.

### Tasks
Table, filters, search, status, priority, assignee, due date and task details.

### Agent Runs
Run ID, request, status, duration, nodes, tools, retrieval results and errors.

## API Integration
Frontend communicates only with backend APIs. It never connects directly to PostgreSQL.
