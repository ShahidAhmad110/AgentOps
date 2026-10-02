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
        if existing_user.scalars().first() is not None:
            raise AuthenticationError("A user with that email or username already exists.")

        org_name = request.organization_name.strip()
        slug = request.organization_slug.strip().lower()

        # Check existing organizations by slug and by name
        res_slug = await self.session.execute(select(Organization).where(Organization.slug == slug))
        org_by_slug = res_slug.scalar_one_or_none()

        res_name = await self.session.execute(select(Organization).where(Organization.name == org_name))
        org_by_name = res_name.scalar_one_or_none()

        if org_by_slug is not None and org_by_name is not None:
            if org_by_slug.id != org_by_name.id:
                raise AuthenticationError("An organization with that name or slug already exists.")
            organization = org_by_slug
        elif org_by_slug is not None and org_by_name is None:
            organization = org_by_slug
        elif org_by_name is not None and org_by_slug is None:
            raise AuthenticationError("An organization with that name already exists.")
        else:
            organization = Organization(name=org_name, slug=slug, is_active=True)
            self.session.add(organization)
            await self.session.flush()

        user = User(
            email=email,
            username=username,
            password_hash=self.password_hasher.hash(request.password),
            role="user",
            is_active=True,
            organization_id=organization.id,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user, self._issue_token(user)

    async def login(self, request: LoginRequest) -> tuple[User, str]:
        identity = request.username_or_email.strip()
        if not identity or not request.password:
            raise AuthenticationError("Invalid credentials.")
        result = await self.session.execute(
            select(User).where(
                or_(User.email == identity.lower(), User.username == identity),
                User.deleted_at.is_(None),
            )
        )
        user = result.scalars().first()
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid credentials.")
        try:
            if not self.password_hasher.verify(request.password, user.password_hash):
                raise AuthenticationError("Invalid credentials.")
        except Exception:
            raise AuthenticationError("Invalid credentials.")
        return user, self._issue_token(user)

    def _issue_token(self, user: User) -> str:
        return self.token_service.issue(
            subject=str(user.id),
            role=user.role,
            organization_id=str(user.organization_id) if user.organization_id else None,
        )
