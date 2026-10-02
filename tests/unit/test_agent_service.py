from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from agent.llm import IntentDecision
from backend.core.errors import APIError
from backend.schemas.agent import AgentRequest, AgentResponse
from backend.services.agent_service import AgentService
from mcp.schemas.results import ToolResponse


class MockLLM:
    async def analyze_intent(self, request, conversation_context):
        return IntentDecision("general")

    async def generate_response(self, state):
        return "Service response completed."


@pytest.mark.asyncio
async def test_agent_service_rejects_missing_organization():
    mock_session = AsyncMock()
    service = AgentService(mock_session)
    request = AgentRequest(request="Test request")

    with pytest.raises(APIError) as exc_info:
        await service.execute(request, user_id=uuid4(), organization_id=None)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ORGANIZATION_REQUIRED"


@pytest.mark.asyncio
async def test_agent_service_rejects_nonexistent_conversation():
    mock_session = AsyncMock()
    service = AgentService(mock_session)
    service.conversation_service.get_owned = AsyncMock(return_value=None)
    request = AgentRequest(request="Test request", conversation_id=uuid4())

    with pytest.raises(APIError) as exc_info:
        await service.execute(request, user_id=uuid4(), organization_id=uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "CONVERSATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_agent_service_executes_request_successfully():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    service = AgentService(mock_session)
    user_id = uuid4()
    org_id = uuid4()
    request = AgentRequest(request="Hello Agent")

    response = await service.execute(
        request=request,
        user_id=user_id,
        organization_id=org_id,
        llm=MockLLM(),
    )

    assert isinstance(response, AgentResponse)
    assert response.status == "completed"
    assert response.response == "Service response completed."
    assert response.errors == []
