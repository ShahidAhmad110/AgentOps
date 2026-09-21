from fastapi import FastAPI

from backend.api.routes.auth import router as auth_router
from backend.api.routes.agent import router as agent_router
from backend.api.routes.conversations import router as conversations_router
from backend.api.routes.documents import router as documents_router
from backend.api.routes.health import router as health_router
from backend.api.routes.tasks import router as tasks_router
from backend.api.routes.users import router as users_router
from backend.core.config import get_settings
from backend.core.errors import register_exception_handlers
from backend.core.logging import configure_logging
from backend.middleware.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(title=settings.app_name, debug=settings.debug)
    application.add_middleware(RequestIdMiddleware)
    application.include_router(auth_router)
    application.include_router(agent_router)
    application.include_router(conversations_router)
    application.include_router(health_router)
    application.include_router(documents_router)
    application.include_router(tasks_router)
    application.include_router(users_router)
    register_exception_handlers(application)

    @application.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "status": "running",
            "docs": "/docs",
            "health": "/health",
        }

    return application