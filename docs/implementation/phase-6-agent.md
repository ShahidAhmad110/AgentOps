# Phase 6 — LangGraph Agent Architecture & Orchestration

## Overview

This phase implements the LangGraph agent architecture and deterministic workflow orchestration for AgentOps, conforming strictly to `06-agent-architecture.md`, `07-langgraph-design.md`, `08-mcp-design.md`, `11-authentication-and-security.md`, and `19-project-structure.md`.

## Implemented Architecture

### 1. LangGraph Workflow Graph & State
- **State Definition**: Defined in `agent/state/agent_state.py` as `AgentState(TypedDict)` containing:
  - `request`: User input query.
  - `user_id`: Authenticated user UUID.
  - `organization_id`: Organization UUID for tenant-scoping.
  - `conversation_id`: Active conversation UUID (optional).
  - `conversation_context`: Historical conversation message turns.
  - `intent`: Classified intent (`knowledge`, `operational`, `general`).
  - `selected_tool`: Tool name chosen during operational intents.
  - `tool_arguments`: Validated arguments dictionary.
  - `tool_result`: Structured output from MCP tool execution.
  - `retrieved_sources`: Retrieved document citations and chunks.
  - `steps`: Sequential execution trace.
  - `tool_calls`: Audited tool execution events.
  - `errors`: Accumulated error log.
  - `status`: Execution status (`pending`, `running`, `completed`, `failed`).
  - `final_response`: User-facing output string.
  - `run_id`: Associated `AgentRun` identifier.
  - `route`: Computed branch target for conditional routing.

### 2. 10 Proposed SDD Nodes
Implemented in `agent/nodes/workflow.py`:
1. `receive_request`: Validates and sanitizes user input, initializes execution run.
2. `analyze_intent`: Calls `LLMClient` to classify intent and extract tool call/arguments.
3. `route_request`: Evaluates intent and error state to set the target branch.
4. `retrieve_knowledge`: Calls `search_documents` via the platform MCP server with grounded parameters.
5. `select_tool`: Validates that a requested operational tool was identified.
6. `execute_tool`: Invokes the target tool through `MCPServer.call` within the authenticated context boundary.
7. `validate_result`: Verifies tool outcomes; transitions to failure if tool reported errors.
8. `generate_response`: Uses `LLMClient` to synthesize final response grounded in sources or tool outcomes.
9. `persist_execution`: Finalizes the run record with status, response, and completion timestamp.
10. `handle_failure`: Sets sanitized user-safe failure message and marks state as failed.

### 3. Routing Branches
- `analyze_intent` → `route_request`
  - `knowledge` → `retrieve_knowledge` → `validate_result`
  - `operational` → `select_tool` → `execute_tool` → `validate_result`
  - `general` → `generate_response` → `persist_execution` → `END`
  - `error` / `failure` → `handle_failure` → `persist_execution` → `END`
- From `validate_result`:
  - `failed` → `handle_failure` → `persist_execution` → `END`
  - `completed` → `generate_response` → `persist_execution` → `END`

### 4. Prompts and Policies
- Created `agent/prompts/templates.py`:
  - `SYSTEM_PROMPT`: Grounding directives, safety rules, no hallucinations.
  - `INTENT_ANALYSIS_PROMPT`: Classification format for knowledge, operational, and general requests.
  - `RESPONSE_GENERATION_PROMPT`: Citations, grounding, and empty-retrieval handling.
- Created `agent/policies/__init__.py`:
  - Execution boundaries (`ALLOWED_INTENTS`, `MAX_RETRIEVAL_LIMIT`, `MAX_AGENT_STEPS`, `EMPTY_RETRIEVAL_MESSAGE`, `SANITIZED_FAILURE_MESSAGE`).

### 5. Backend Domain Service Layer
- Created `backend/services/agent_service.py` to maintain the API → Service → Repository boundary per SDD 03.
- `AgentService` handles organization authorization, conversation ownership verification, MCP server assembly, and execution persistence.
- Refactored `backend/api/routes/agent.py` to keep route handlers free of business logic.

### 6. Authentication Context & Security Boundary
- Tool execution strictly inherits `ToolContext(user_id=state["user_id"], organization_id=state["organization_id"], is_authenticated=True)`.
- Tools reject execution if `organization_id` is missing or cross-organization data access is attempted.
