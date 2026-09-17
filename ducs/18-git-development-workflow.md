# 18 — Git & Development Workflow Specification

## Branches
```text
main
develop
feature/authentication
feature/database
feature/agent
feature/rag
feature/mcp
feature/frontend
feature/observability
```

## Commit Style
Use focused commits such as:
- `feat: add conversation schema`
- `feat: implement document ingestion pipeline`
- `feat: add MCP task tools`
- `feat: implement LangGraph agent`
- `feat: add agent execution dashboard`

Avoid large commits such as `complete project`.

## SDD Rule
Implementation changes that alter architecture must be reflected in the relevant SDD before or with the implementation change.
