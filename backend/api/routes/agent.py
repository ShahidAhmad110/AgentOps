from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import get_current_user
from backend.schemas.agent import AgentRequest, AgentResponse
from backend.services.agent_service import AgentService
from database.connection.session import get_database_session
from database.models.user import User

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("", response_model=AgentResponse)
async def execute_agent(
    request: AgentRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> AgentResponse:
    return await AgentService(session).execute(
        request=request,
        user_id=user.id,
        organization_id=user.organization_id,
    )

