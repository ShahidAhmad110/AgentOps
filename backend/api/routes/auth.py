from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies.auth import get_current_user, get_token_service
from backend.core.errors import APIError
from backend.core.security import TokenService
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.services.auth_service import AuthService, AuthenticationError
from database.connection.session import get_database_session
from database.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_database_session),
    token_service: TokenService = Depends(get_token_service),
) -> TokenResponse:
    try:
        user, token = await AuthService(session, token_service).register(request)
    except AuthenticationError as exc:
        await session.rollback()
        raise APIError("REGISTRATION_ERROR", str(exc), status_code=409) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise APIError("REGISTRATION_ERROR", "A user or organization with those details already exists.", status_code=409) from exc
    except ValueError as exc:
        await session.rollback()
        raise APIError("REGISTRATION_ERROR", str(exc), status_code=400) from exc
    return TokenResponse(
        access_token=token,
        expires_in=token_service.lifetime_seconds,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_database_session),
    token_service: TokenService = Depends(get_token_service),
) -> TokenResponse:
    try:
        user, token = await AuthService(session, token_service).login(request)
    except AuthenticationError as exc:
        raise APIError("INVALID_CREDENTIALS", str(exc), status_code=401) from exc
    except ValueError as exc:
        raise APIError("INVALID_CREDENTIALS", str(exc), status_code=400) from exc
    return TokenResponse(
        access_token=token,
        expires_in=token_service.lifetime_seconds,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def current_user(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
