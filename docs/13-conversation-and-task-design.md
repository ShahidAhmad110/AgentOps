# 13 — Conversation & Task Domain Specification

## Conversations
A conversation contains messages and associated agent runs.

```text
Conversation
├── Message
├── Message
└── Agent Run
    ├── Node
    ├── Tool Call
    ├── Retrieval
    └── Final Response
```

Users can reopen previous conversations.

## Tasks
Users can:
- Create tasks.
- Assign tasks.
- Update status.
- Add comments.
- Set priority.
- Set due dates.
- Search and filter.

## Statuses
TODO, IN_PROGRESS, BLOCKED, COMPLETED, CANCELLED.

The agent can interact with tasks through controlled tools/MCP.
