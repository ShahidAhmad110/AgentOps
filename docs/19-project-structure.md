# 19 — Production Project Structure Specification

```text
agentops/
├── backend/
│   ├── api/
│   ├── core/
│   ├── services/
│   ├── repositories/
│   ├── schemas/
│   └── middleware/
├── agent/
│   ├── graphs/
│   ├── nodes/
│   ├── tools/
│   ├── prompts/
│   ├── state/
│   └── policies/
├── database/
│   ├── migrations/
│   ├── models/
│   ├── repositories/
│   ├── seeds/
│   └── connection/
├── documents/
│   ├── ingestion/
│   ├── loaders/
│   ├── chunking/
│   ├── embeddings/
│   ├── retrieval/
│   └── storage/
├── mcp/
│   ├── servers/
│   ├── tools/
│   └── schemas/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── dashboard/
│   ├── conversations/
│   ├── documents/
│   ├── tasks/
│   └── api/
├── workers/
├── tests/
├── docs/
├── scripts/
├── docker/
├── .env.example
├── docker-compose.yml
└── README.md
```

The exact structure may evolve only when justified by architecture decisions.
