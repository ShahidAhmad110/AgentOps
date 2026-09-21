from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph

from agent.llm import LLMClient
from agent.nodes.workflow import (
    analyze_intent,
    execute_tool,
    generate_response,
    handle_failure,
    persist_execution,
    receive_request,
    retrieve_knowledge,
    route_request,
    select_tool,
    validate_result,
)
from agent.persistence import ExecutionRecorder
from agent.state.agent_state import AgentState
from mcp.schemas.context import ToolContext
from mcp.servers.registry import MCPServer


class InMemoryExecutionRecorder:
    def __init__(self) -> None:
        self.runs: dict[UUID, dict[str, Any]] = {}

    async def start_run(self, state: Mapping[str, Any]) -> UUID:
        run_id = uuid4()
        self.runs[run_id] = {"steps": [], "tool_calls": [], "status": "RUNNING"}
        return run_id

    async def record_step(self, run_id: UUID, step: Mapping[str, Any]) -> None:
        self.runs[run_id]["steps"].append(dict(step))

    async def record_tool_call(self, run_id: UUID, tool_call: Mapping[str, Any]) -> None:
        self.runs[run_id]["tool_calls"].append(dict(tool_call))

    async def finish_run(self, run_id: UUID, state: Mapping[str, Any]) -> None:
        self.runs[run_id].update(
            status=state.get("status"), final_response=state.get("final_response"), errors=state.get("errors", [])
        )


def create_agent_graph(
    mcp_server: MCPServer,
    llm: LLMClient,
    recorder: ExecutionRecorder | None = None,
):
    execution_recorder = recorder or InMemoryExecutionRecorder()
    graph = StateGraph(AgentState)

    async def receive(state: AgentState) -> AgentState:
        return await receive_request(state, execution_recorder)

    async def analyze(state: AgentState) -> AgentState:
        return await analyze_intent(state, llm, execution_recorder)

    async def route(state: AgentState) -> AgentState:
        return await route_request(state, execution_recorder)

    async def retrieve(state: AgentState) -> AgentState:
        return await retrieve_knowledge(state, mcp_server, execution_recorder)

    async def select(state: AgentState) -> AgentState:
        return await select_tool(state, execution_recorder)

    async def execute(state: AgentState) -> AgentState:
        return await execute_tool(state, mcp_server, execution_recorder)

    async def validate(state: AgentState) -> AgentState:
        return await validate_result(state, execution_recorder)

    async def respond(state: AgentState) -> AgentState:
        return await generate_response(state, llm, execution_recorder)

    async def failure(state: AgentState) -> AgentState:
        return await handle_failure(state, execution_recorder)

    async def persist(state: AgentState) -> AgentState:
        return await persist_execution(state, execution_recorder)

    graph.add_node("receive_request", receive)
    graph.add_node("analyze_intent", analyze)
    graph.add_node("route_request", route)
    graph.add_node("retrieve_knowledge", retrieve)
    graph.add_node("select_tool", select)
    graph.add_node("execute_tool", execute)
    graph.add_node("validate_result", validate)
    graph.add_node("generate_response", respond)
    graph.add_node("handle_failure", failure)
    graph.add_node("persist_execution", persist)

    graph.add_edge(START, "receive_request")
    graph.add_edge("receive_request", "analyze_intent")
    graph.add_edge("analyze_intent", "route_request")
    graph.add_conditional_edges(
        "route_request",
        lambda state: state.get("route", "handle_failure"),
        {
            "retrieve_knowledge": "retrieve_knowledge",
            "select_tool": "select_tool",
            "generate_response": "generate_response",
            "handle_failure": "handle_failure",
        },
    )
    graph.add_edge("retrieve_knowledge", "validate_result")
    graph.add_edge("select_tool", "execute_tool")
    graph.add_edge("execute_tool", "validate_result")
    graph.add_conditional_edges(
        "validate_result",
        lambda state: "handle_failure" if state.get("status") == "failed" else "generate_response",
        {"handle_failure": "handle_failure", "generate_response": "generate_response"},
    )
    graph.add_edge("generate_response", "persist_execution")
    graph.add_edge("handle_failure", "persist_execution")
    graph.add_edge("persist_execution", END)
    return graph.compile()


async def run_agent(
    request: str,
    user_id: UUID,
    organization_id: UUID,
    mcp_server: MCPServer,
    llm: LLMClient,
    conversation_id: UUID | None = None,
    conversation_context: list[dict[str, Any]] | None = None,
    recorder: ExecutionRecorder | None = None,
) -> AgentState:
    graph = create_agent_graph(mcp_server, llm, recorder)
    initial_state: AgentState = {
        "request": request,
        "user_id": user_id,
        "organization_id": organization_id,
        "conversation_id": conversation_id,
        "conversation_context": conversation_context or [],
    }
    return await graph.ainvoke(initial_state)
