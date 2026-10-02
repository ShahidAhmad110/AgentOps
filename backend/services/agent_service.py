from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agent.graphs import run_agent
from agent.llm import LLMClient, UnconfiguredLLMClient, get_default_llm_client
from agent.persistence import DatabaseExecutionRecorder
from backend.core.errors import APIError
from backend.schemas.agent import (
    AgentRequest,
    AgentResponse,
    AgentRunResponse,
    AgentStepResponse,
    AgentToolCallResponse,
)
from backend.services.conversation_service import ConversationService
from database.models.agent_execution import AgentRun
from database.repositories.agent_execution_repository import AgentExecutionRepository
from mcp.servers.platform import create_platform_server


class AgentService:
    """Domain service for orchestrating agent requests and managing execution lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversation_service = ConversationService(session)
        self.execution_repository = AgentExecutionRepository(session)

    async def execute(
        self,
        request: AgentRequest,
        user_id: UUID,
        organization_id: UUID | None,
        llm: LLMClient | None = None,
    ) -> AgentResponse:
        if organization_id is None:
            raise APIError("ORGANIZATION_REQUIRED", "An organization is required.", status_code=403)

        conversation_context: list[dict[str, Any]] = []
        if request.conversation_id is not None:
            conversation = await self.conversation_service.get_owned(
                request.conversation_id, user_id, organization_id
            )
            if conversation is None:
                raise APIError("CONVERSATION_NOT_FOUND", "The conversation was not found.", status_code=404)
            messages = await self.conversation_service.list_messages(
                conversation.id, user_id, organization_id
            )
            conversation_context = [
                {"role": message.role, "content": message.content, "sequence": message.sequence}
                for message in (messages or [])
            ]

        mcp_server = create_platform_server(self.session)
        llm_client = llm or get_default_llm_client()
        recorder = DatabaseExecutionRecorder(self.session)

        state = await run_agent(
            request=request.request,
            user_id=user_id,
            organization_id=organization_id,
            conversation_id=request.conversation_id,
            conversation_context=conversation_context,
            mcp_server=mcp_server,
            llm=llm_client,
            recorder=recorder,
        )

        return AgentResponse(
            run_id=state.get("run_id"),
            status=state.get("status", "failed"),
            response=state.get("final_response"),
            errors=state.get("errors", []),
            retrieved_sources=state.get("retrieved_sources", []),
            tool_calls=state.get("tool_calls", []),
        )

    async def get_run(self, run_id: UUID) -> AgentRun | None:
        return await self.execution_repository.get_run(run_id)

    async def list_runs(
        self, user_id: UUID, organization_id: UUID, limit: int, offset: int
    ) -> list[AgentRunResponse]:
        runs = await self.execution_repository.list_runs_scoped(
            user_id, organization_id, limit, offset
        )
        run_ids = [run.id for run in runs]
        steps = await self.execution_repository.list_steps(run_ids)
        tool_calls = await self.execution_repository.list_tool_calls(run_ids)
        steps_by_run: dict[UUID, list[AgentStepResponse]] = {run_id: [] for run_id in run_ids}
        calls_by_run: dict[UUID, list[AgentToolCallResponse]] = {run_id: [] for run_id in run_ids}
        sources_by_run: dict[UUID, list[dict[str, Any]]] = {run_id: [] for run_id in run_ids}

        for step in steps:
            steps_by_run[step.run_id].append(
                AgentStepResponse(
                    sequence=step.sequence,
                    node_name=step.node_name,
                    status=step.status,
                    error_message=step.error_message,
                )
            )
        for call in tool_calls:
            calls_by_run[call.run_id].append(
                AgentToolCallResponse(
                    tool_name=call.tool_name,
                    success=call.success,
                    result=call.result,
                    error_message=call.error_message,
                    created_at=call.created_at,
                )
            )
            if call.tool_name == "search_documents" and isinstance(call.result, dict):
                result_data = call.result.get("data")
                if isinstance(result_data, dict) and isinstance(result_data.get("sources"), list):
                    sources_by_run[call.run_id].extend(result_data["sources"])

        responses: list[AgentRunResponse] = []
        for run in runs:
            duration_ms = None
            if run.completed_at is not None:
                duration_ms = max(0, int((run.completed_at - run.created_at).total_seconds() * 1000))
            responses.append(
                AgentRunResponse(
                    run_id=run.id,
                    conversation_id=run.conversation_id,
                    request=run.request,
                    status=run.status,
                    response=run.final_response,
                    errors=[run.error_message] if run.error_message else [],
                    started_at=run.created_at,
                    completed_at=run.completed_at,
                    duration_ms=duration_ms,
                    nodes=steps_by_run[run.id],
                    tool_calls=calls_by_run[run.id],
                    retrieved_sources=sources_by_run[run.id],
                )
            )
        return responses
