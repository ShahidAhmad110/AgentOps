from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graphs import run_agent
from agent.llm import UnconfiguredLLMClient
from agent.persistence import DatabaseExecutionRecorder
from backend.api.dependencies.auth import get_current_user
from backend.core.errors import APIError
from backend.schemas.agent import AgentRequest, AgentResponse
from backend.services.conversation_service import ConversationService
from database.connection.session import get_database_session
from database.models.user import User
from mcp.servers.platform import create_platform_server

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("", response_model=AgentResponse)
async def execute_agent(
    request: AgentRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> AgentResponse:
    if user.organization_id is None:
        raise APIError("ORGANIZATION_REQUIRED", "An organization is required.", status_code=403)

    conversation_context: list[dict] = []
    if request.conversation_id is not None:
        conversation = await ConversationService(session).get_owned(
            request.conversation_id, user.id, user.organization_id
        )
        if conversation is None:
            raise APIError("CONVERSATION_NOT_FOUND", "The conversation was not found.", status_code=404)
        messages = await ConversationService(session).list_messages(
            conversation.id, user.id, user.organization_id
        )
        conversation_context = [
            {"role": message.role, "content": message.content, "sequence": message.sequence}
            for message in messages or []
        ]

    state = await run_agent(
        request=request.request,
        user_id=user.id,
        organization_id=user.organization_id,
        conversation_id=request.conversation_id,
        conversation_context=conversation_context,
        mcp_server=create_platform_server(session),
        llm=UnconfiguredLLMClient(),
        recorder=DatabaseExecutionRecorder(session),
    )
    return AgentResponse(
        run_id=state.get("run_id"),
        status=state.get("status", "failed"),
        response=state.get("final_response"),
        errors=state.get("errors", []),
        retrieved_sources=state.get("retrieved_sources", []),
        tool_calls=state.get("tool_calls", []),
    )
