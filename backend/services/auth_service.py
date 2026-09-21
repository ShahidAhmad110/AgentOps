from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import PasswordHasher, TokenService
from backend.schemas.auth import LoginRequest, RegisterRequest
from database.models.organization import Organization
from database.models.user import User
from database.repositories.user_repository import UserRepository


class AuthenticationError(ValueError):
    pass


class AuthService:
    def __init__(self, session: AsyncSession, token_service: TokenService) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.token_service = token_service
        self.password_hasher = PasswordHasher()

    async def register(self, request: RegisterRequest) -> tuple[User, str]:
        email = request.email.strip().lower()
        username = request.username.strip()
        existing_user = await self.session.execute(
            select(User).where(or_(User.email == email, User.username == username))
        )
        if existing_user.scalar_one_or_none() is not None:
            raise AuthenticationError("A user with that email or username already exists.")

        existing_org = await self.session.execute(
            select(Organization).where(Organization.slug == request.organization_slug)
        )
        if existing_org.scalar_one_or_none() is not None:
            raise AuthenticationError("An organization with that slug already exists.")

        organization = Organization(name=request.organization_name.strip(), slug=request.organization_slug)
        user = User(
            email=email,
            username=username,
            password_hash=self.password_hasher.hash(request.password),
            role="user",
            is_active=True,
            organization=organization,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user, self._issue_token(user)

    async def login(self, request: LoginRequest) -> tuple[User, str]:
        identity = request.username_or_email.strip()
        result = await self.session.execute(
            select(User).where(or_(User.email == identity.lower(), User.username == identity))
        )
        user = result.scalar_one_or_none()
        if user is None or not user.is_active or not self.password_hasher.verify(request.password, user.password_hash):
            raise AuthenticationError("Invalid credentials.")
        return user, self._issue_token(user)

    def _issue_token(self, user: User) -> str:
        return self.token_service.issue(
            subject=str(user.id),
            role=user.role,
            organization_id=str(user.organization_id) if user.organization_id else None,
        )
