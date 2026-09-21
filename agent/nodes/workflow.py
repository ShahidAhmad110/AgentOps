from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from agent.llm import IntentDecision, LLMClient, LLMError
from agent.persistence import ExecutionRecorder
from agent.state.agent_state import AgentState
from mcp.schemas.context import ToolContext
from mcp.servers.registry import MCPServer


def _context(state: AgentState) -> ToolContext:
    return ToolContext(
        user_id=state["user_id"],
        organization_id=state["organization_id"],
        is_authenticated=True,
    )


async def _step(
    state: AgentState,
    recorder: ExecutionRecorder,
    node_name: str,
    status: str,
    error: str | None = None,
) -> None:
    steps = list(state.get("steps", []))
    step = {"sequence": len(steps) + 1, "node_name": node_name, "status": status}
    if error:
        step["error"] = error
    steps.append(step)
    state["steps"] = steps
    if state.get("run_id") is not None:
        await recorder.record_step(state["run_id"], step)


async def receive_request(state: AgentState, recorder: ExecutionRecorder) -> AgentState:
    request = state.get("request", "").strip()
    if not request:
        state["errors"] = ["The agent request cannot be empty."]
        state["status"] = "failed"
        state["final_response"] = "The request could not be processed."
        return state
    state["request"] = request
    state["steps"] = []
    state["tool_calls"] = []
    state["errors"] = []
    state["status"] = "running"
    state["final_response"] = None
    state["run_id"] = await recorder.start_run(state)
    await _step(state, recorder, "receive_request", "completed")
    return state


async def analyze_intent(
    state: AgentState, llm: LLMClient, recorder: ExecutionRecorder
) -> AgentState:
    try:
        decision: IntentDecision = await llm.analyze_intent(
            state["request"], state.get("conversation_context", [])
        )
        state["intent"] = decision.intent
        state["selected_tool"] = decision.selected_tool
        state["tool_arguments"] = decision.tool_arguments or {}
        await _step(state, recorder, "analyze_intent", "completed")
    except LLMError as exc:
        return await fail(state, recorder, "analyze_intent", "The agent could not analyze the request.", exc)
    except Exception as exc:
        return await fail(state, recorder, "analyze_intent", "The agent encountered an unexpected error.", exc)
    return state


async def route_request(state: AgentState, recorder: ExecutionRecorder) -> AgentState:
    if state.get("errors"):
        state["route"] = "handle_failure"
    elif state.get("intent") == "knowledge":
        state["route"] = "retrieve_knowledge"
    elif state.get("intent") == "operational":
        state["route"] = "select_tool"
    elif state.get("intent") == "general":
        state["route"] = "generate_response"
    else:
        await fail(state, recorder, "route_request", "The agent produced an invalid intent.", None)
        state["route"] = "handle_failure"
        return state
    await _step(state, recorder, "route_request", "completed")
    return state


async def retrieve_knowledge(
    state: AgentState, mcp_server: MCPServer, recorder: ExecutionRecorder
) -> AgentState:
    result = await mcp_server.call(
        "search_documents", {"query": state["request"], "limit": 5}, _context(state)
    )
    _store_tool_result(state, "search_documents", {"query": state["request"], "limit": 5}, result)
    await _record_tool_call(state, recorder, "search_documents", {"query": state["request"], "limit": 5}, result)
    await _step(state, recorder, "retrieve_knowledge", "completed" if result.success else "failed")
    return state


async def select_tool(state: AgentState, recorder: ExecutionRecorder) -> AgentState:
    if not state.get("selected_tool"):
        await fail(state, recorder, "select_tool", "No operational tool was selected.", None)
    else:
        await _step(state, recorder, "select_tool", "completed")
    return state


async def execute_tool(
    state: AgentState, mcp_server: MCPServer, recorder: ExecutionRecorder
) -> AgentState:
    tool_name = state.get("selected_tool")
    arguments = state.get("tool_arguments", {})
    if not tool_name:
        await fail(state, recorder, "execute_tool", "No tool was selected.", None)
        return state
    result = await mcp_server.call(tool_name, arguments, _context(state))
    _store_tool_result(state, tool_name, arguments, result)
    await _record_tool_call(state, recorder, tool_name, arguments, result)
    await _step(state, recorder, "execute_tool", "completed" if result.success else "failed")
    return state


async def validate_result(state: AgentState, recorder: ExecutionRecorder) -> AgentState:
    result = state.get("tool_result")
    if result is not None and not result.get("success", False):
        error = result.get("error", {}).get("message", "The tool operation failed.")
        state["errors"] = [*state.get("errors", []), error]
        state["status"] = "failed"
        await _step(state, recorder, "validate_result", "failed", error)
    else:
        await _step(state, recorder, "validate_result", "completed")
    return state


async def generate_response(
    state: AgentState, llm: LLMClient, recorder: ExecutionRecorder
) -> AgentState:
    try:
        state["final_response"] = await llm.generate_response(state)
        state["status"] = "completed"
        await _step(state, recorder, "generate_response", "completed")
    except LLMError as exc:
        await fail(state, recorder, "generate_response", "The agent could not generate a response.", exc)
    except Exception as exc:
        await fail(state, recorder, "generate_response", "The agent encountered an unexpected error.", exc)
    return state


async def handle_failure(state: AgentState, recorder: ExecutionRecorder) -> AgentState:
    state["status"] = "failed"
    state["final_response"] = "The agent could not complete the request."
    await _step(state, recorder, "handle_failure", "completed")
    return state


async def persist_execution(state: AgentState, recorder: ExecutionRecorder) -> AgentState:
    if state.get("run_id") is not None:
        await recorder.finish_run(state["run_id"], state)
    return state


async def fail(
    state: AgentState,
    recorder: ExecutionRecorder,
    node_name: str,
    public_message: str,
    error: Exception | None,
) -> AgentState:
    state["errors"] = [*state.get("errors", []), public_message]
    state["status"] = "failed"
    state["final_response"] = public_message
    await _step(state, recorder, node_name, "failed", public_message)
    return state


def _store_tool_result(state: AgentState, name: str, arguments: dict[str, Any], result: Any) -> None:
    state["tool_result"] = result.model_dump(mode="json")
    if name == "search_documents" and result.success:
        state["retrieved_sources"] = result.data.get("sources", [])


def _record_tool_call(
    state: AgentState,
    recorder: ExecutionRecorder,
    name: str,
    arguments: dict[str, Any],
    result: Any,
) -> Any:
    state["tool_calls"] = [
        *state.get("tool_calls", []),
        {"tool_name": name, "arguments": arguments, **result.model_dump(mode="json")},
    ]
    if state.get("run_id") is not None:
        return recorder.record_tool_call(state["run_id"], state["tool_calls"][-1])
    return None
