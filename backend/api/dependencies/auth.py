from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.errors import APIError
from backend.core.security import SecurityError, TokenService
from database.connection.session import get_database_session
from database.models.user import User
from database.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_service() -> TokenService:
    settings = get_settings()
    if not settings.auth_secret_key:
        raise APIError("AUTH_CONFIGURATION_ERROR", "Authentication is not configured.", status_code=500)
    try:
        return TokenService(settings.auth_secret_key, settings.access_token_lifetime_seconds)
    except ValueError as exc:
        raise APIError("AUTH_CONFIGURATION_ERROR", str(exc), status_code=500) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
    token_service: TokenService = Depends(get_token_service),
) -> User:
    if credentials is None:
        raise APIError("AUTHENTICATION_REQUIRED", "Authentication is required.", status_code=401)
    try:
        token = token_service.verify(credentials.credentials)
        user_id = UUID(token.subject)
    except (SecurityError, ValueError) as exc:
        raise APIError("INVALID_TOKEN", "The access token is invalid or expired.", status_code=401) from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise APIError("AUTHENTICATION_REQUIRED", "The authenticated user is unavailable.", status_code=401)
    if user.role != token.role or str(user.organization_id) != (token.organization_id or ""):
        raise APIError("INVALID_TOKEN", "The access token is invalid.", status_code=401)
    return user


def require_roles(*roles: str) -> Callable:
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise APIError("FORBIDDEN", "You do not have permission to access this resource.", status_code=403)
        return user

    return dependency
