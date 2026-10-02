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


@pytest.mark.asyncio
async def test_invalid_tool_request_fails_safely():
    mcp = FakeMCP(ToolResponse.failure("UNKNOWN_TOOL", "MCP tool 'unknown_tool' is not registered."))
    result = await run_agent(
        "Do something impossible",
        USER_ID,
        ORG_ID,
        mcp,
        FakeLLM(IntentDecision("operational", "unknown_tool", {})),
    )

    assert result["status"] == "failed"
    assert result["final_response"] == "The agent could not complete the request."
    assert any("not registered" in str(err) for err in result["errors"])
    assert any(step["node_name"] == "validate_result" and step["status"] == "failed" for step in result["steps"])


@pytest.mark.asyncio
async def test_empty_retrieval_scenario_completes_honestly():
    mcp = FakeMCP(ToolResponse.ok({"context": "", "sources": []}))
    result = await run_agent(
        "What is secret project X?",
        USER_ID,
        ORG_ID,
        mcp,
        FakeLLM(IntentDecision("knowledge"), response="No matching documents were found in the knowledge base."),
    )

    assert result["status"] == "completed"
    assert result["retrieved_sources"] == []
    assert "No matching documents" in result["final_response"]


@pytest.mark.asyncio
async def test_empty_request_fails_cleanly():
    recorder = InMemoryExecutionRecorder()
    result = await run_agent(
        "   ",
        USER_ID,
        ORG_ID,
        FakeMCP(ToolResponse.ok({})),
        FakeLLM(IntentDecision("general")),
        recorder=recorder,
    )

    assert result["status"] == "failed"
    assert result["final_response"] == "The agent could not complete the request."
    assert "The agent request cannot be empty." in result["errors"]
    assert result["run_id"] in recorder.runs
    assert recorder.runs[result["run_id"]]["status"] == "failed"


@pytest.mark.asyncio
async def test_conversation_tool_operational_path():
    mcp = FakeMCP(ToolResponse.ok({"id": "msg-1", "content": "Follow up"}))
    result = await run_agent(
        "Send message to thread",
        USER_ID,
        ORG_ID,
        mcp,
        FakeLLM(
            IntentDecision(
                "operational",
                "add_message",
                {"conversation_id": "00000000-0000-0000-0000-000000000003", "role": "user", "content": "Follow up"},
            ),
            response="Message added.",
        ),
    )

    assert result["status"] == "completed"
    assert mcp.calls[0][0] == "add_message"
    assert mcp.calls[0][2].user_id == USER_ID
    assert mcp.calls[0][2].organization_id == ORG_ID
    assert mcp.calls[0][2].is_authenticated is True


@pytest.mark.asyncio
async def test_agent_graph_contains_all_sdd_nodes():
    from agent.graphs.agent_graph import create_agent_graph

    graph = create_agent_graph(FakeMCP(ToolResponse.ok({})), FakeLLM(IntentDecision("general")))
    node_names = set(graph.nodes.keys())
    expected_nodes = {
        "receive_request",
        "analyze_intent",
        "route_request",
        "retrieve_knowledge",
        "select_tool",
        "execute_tool",
        "validate_result",
        "generate_response",
        "handle_failure",
        "persist_execution",
    }
    for expected in expected_nodes:
        assert expected in node_names, f"Node {expected} missing from graph"


@pytest.mark.asyncio
async def test_state_initialization_and_updates():
    from agent.state.agent_state import AgentState

    initial: AgentState = {
        "request": "Test request",
        "user_id": USER_ID,
        "organization_id": ORG_ID,
        "conversation_id": None,
        "conversation_context": [],
    }
    assert initial["request"] == "Test request"
    assert initial["user_id"] == USER_ID
    assert initial["organization_id"] == ORG_ID
    assert initial.get("route") is None


@pytest.mark.asyncio
async def test_tool_context_authorization_propagation():
    mcp = FakeMCP(ToolResponse.ok({"id": "task-abc"}))
    result = await run_agent(
        "List my team's tasks",
        USER_ID,
        ORG_ID,
        mcp,
        FakeLLM(IntentDecision("operational", "list_tasks", {"limit": 10}), response="Tasks listed."),
    )

    assert result["status"] == "completed"
    context = mcp.calls[0][2]
    assert context.user_id == USER_ID
    assert context.organization_id == ORG_ID
    assert context.is_authenticated is True


@pytest.mark.asyncio
async def test_unexpected_exception_in_tool_execution():
    class CrashingMCP:
        async def call(self, name, arguments, context):
            raise RuntimeError("Database connection timeout during MCP call")

    result = await run_agent(
        "Run operational task",
        USER_ID,
        ORG_ID,
        CrashingMCP(),
        FakeLLM(IntentDecision("operational", "create_task", {"title": "Crashing task"})),
    )

    assert result["status"] == "failed"
    assert result["final_response"] == "The agent could not complete the request."


