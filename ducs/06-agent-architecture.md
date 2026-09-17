# 06 — Agent Architecture Specification

## Purpose
The agent converts user requests into controlled knowledge retrieval and operational workflows.

## Required Graph
```text
User Request
 ↓
Intent / Request Analysis
 ├── Knowledge Task → Retrieval → Reasoning
 └── Operational Task → Tool Selection → Tool Execution
 ↓
Response Generation
 ↓
Persist Execution
```

## Agent Capabilities
- LLM-powered reasoning.
- Structured outputs.
- State management.
- Tool calling.
- Conditional routing.
- Human-in-the-loop where appropriate.
- Failure detection and recovery.

## Safety/Correctness Rules
- Never claim an action succeeded without an actual successful tool result.
- Do not invent knowledge when retrieval returns insufficient evidence.
- Validate tool inputs before execution.
- Record important execution events.
- Do not implement the agent as a single while-loop around an LLM.

## Required Scenarios
Knowledge question, no-tool question, task creation, combined retrieval + task action, invalid tool, tool failure, empty retrieval.
