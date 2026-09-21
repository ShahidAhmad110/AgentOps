from fastapi import APIRouter

from backend.services.health_service import get_health_status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    health_status = await get_health_status()
    return {
        "status": health_status.status,
        "database": health_status.database,
    }