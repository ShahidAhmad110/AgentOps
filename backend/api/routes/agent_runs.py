from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import get_current_user
from backend.core.errors import APIError
from backend.schemas.agent import AgentRunResponse
from backend.services.agent_service import AgentService
from database.connection.session import get_database_session
from database.models.user import User

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@router.get("", response_model=list[AgentRunResponse])
async def list_agent_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> list[AgentRunResponse]:
    if user.organization_id is None:
        raise APIError("ORGANIZATION_REQUIRED", "An organization is required.", status_code=403)
    return await AgentService(session).list_runs(user.id, user.organization_id, limit, offset)