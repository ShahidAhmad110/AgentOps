from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from backend.api.app import create_app
from backend.services.agent_service import AgentService


@pytest.mark.asyncio
async def test_agent_run_history_maps_persisted_steps_tools_and_sources() -> None:
    user_id = uuid4()
    organization_id = uuid4()
    run_id = uuid4()
    started_at = datetime.now(timezone.utc)
    completed_at = started_at + timedelta(milliseconds=1475)
    source = {
        "document_id": str(uuid4()),
        "filename": "handbook.md",
        "chunk_index": 2,
        "content": "Notify the operations lead.",
        "score": 0.82,
    }
    run = SimpleNamespace(
        id=run_id,
        conversation_id=uuid4(),
        request="Who should we notify?",
        status="completed",
        final_response="Notify the operations lead.",
        error_message=None,
        created_at=started_at,
        completed_at=completed_at,
    )
    step = SimpleNamespace(
        run_id=run_id,
        sequence=1,
        node_name="retrieve_knowledge",
        status="completed",
        error_message=None,
    )
    tool_call = SimpleNamespace(
        run_id=run_id,
        tool_name="search_documents",
        success=True,
        result={"success": True, "data": {"context": "evidence", "sources": [source]}},
        error_message=None,
        created_at=completed_at,
    )
    repository = SimpleNamespace(
        list_runs_scoped=AsyncMock(return_value=[run]),
        list_steps=AsyncMock(return_value=[step]),
        list_tool_calls=AsyncMock(return_value=[tool_call]),
    )
    service = AgentService(AsyncMock())
    service.execution_repository = repository

    history = await service.list_runs(user_id, organization_id, 25, 5)

    repository.list_runs_scoped.assert_awaited_once_with(user_id, organization_id, 25, 5)
    assert len(history) == 1
    assert history[0].run_id == run_id
    assert history[0].duration_ms == 1475
    assert history[0].nodes[0].node_name == "retrieve_knowledge"
    assert history[0].tool_calls[0].tool_name == "search_documents"
    assert history[0].retrieved_sources == [source]


def test_agent_run_history_route_is_registered() -> None:
    application = create_app()

    assert "/agent-runs" in application.openapi()["paths"]