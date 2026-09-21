from uuid import UUID

import pytest

from agent.graphs.agent_graph import InMemoryExecutionRecorder, run_agent
from agent.llm import IntentDecision, LLMError
from mcp.schemas.results import ToolResponse

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
ORG_ID = UUID("00000000-0000-0000-0000-000000000002")


class FakeLLM:
    def __init__(self, decision: IntentDecision, response: str = "done", error: Exception | None = None):
        self.decision = decision
        self.response = response
        self.error = error

    async def analyze_intent(self, request, conversation_context):
        if self.error:
            raise self.error
        return self.decision

    async def generate_response(self, state):
        if self.error:
            raise self.error
        return self.response


class FakeMCP:
    def __init__(self, result: ToolResponse):
        self.result = result
        self.calls = []

    async def call(self, name, arguments, context):
        self.calls.append((name, arguments, context))
        return self.result


@pytest.mark.asyncio
async def test_general_path_terminates_with_final_response():
    result = await run_agent(
        "Say hello",
        USER_ID,
        ORG_ID,
        FakeMCP(ToolResponse.ok({})),
        FakeLLM(IntentDecision("general"), response="Hello."),
    )

    assert result["status"] == "completed"
    assert result["final_response"] == "Hello."
    assert [step["node_name"] for step in result["steps"]] == [
        "receive_request",
        "analyze_intent",
        "route_request",
        "generate_response",
    ]


@pytest.mark.asyncio
async def test_knowledge_path_uses_search_documents_and_context():
    mcp = FakeMCP(ToolResponse.ok({"context": "source", "sources": [{"filename": "guide.md"}]}))
    result = await run_agent(
        "Where is the guide?",
        USER_ID,
        ORG_ID,
        mcp,
        FakeLLM(IntentDecision("knowledge"), response="It is in the guide."),
    )

    assert result["status"] == "completed"
    assert mcp.calls[0][0] == "search_documents"
    assert result["retrieved_sources"] == [{"filename": "guide.md"}]


@pytest.mark.asyncio
async def test_operational_path_uses_selected_mcp_tool():
    mcp = FakeMCP(ToolResponse.ok({"id": "task-1", "status": "TODO"}))
    result = await run_agent(
        "Create the incident task",
        USER_ID,
        ORG_ID,
        mcp,
        FakeLLM(IntentDecision("operational", "create_task", {"title": "Incident task"}), response="Created."),
    )

    assert result["status"] == "completed"
    assert mcp.calls[0][0] == "create_task"
    assert mcp.calls[0][2].organization_id == ORG_ID


@pytest.mark.asyncio
async def test_tool_failure_routes_to_sanitized_failure_response():
    mcp = FakeMCP(ToolResponse.failure("NOT_FOUND", "private detail"))
    result = await run_agent(
        "Find the task",
        USER_ID,
        ORG_ID,
        mcp,
        FakeLLM(IntentDecision("operational", "get_task", {"task_id": "missing"})),
    )

    assert result["status"] == "failed"
    assert result["final_response"] == "The agent could not complete the request."
    assert "private detail" in result["errors"]


@pytest.mark.asyncio
async def test_llm_failure_routes_to_terminal_failure():
    recorder = InMemoryExecutionRecorder()
    result = await run_agent(
        "Any request",
        USER_ID,
        ORG_ID,
        FakeMCP(ToolResponse.ok({})),
        FakeLLM(IntentDecision("general"), error=LLMError("provider down")),
        recorder=recorder,
    )

    assert result["status"] == "failed"
    assert result["final_response"] == "The agent could not complete the request."
    assert recorder.runs[result["run_id"]]["status"] == "failed"
