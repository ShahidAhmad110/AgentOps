from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.core.config import get_settings
from database.connection.session import engine
from main import app


@pytest.mark.asyncio
async def test_authentication_rbac_and_organization_access() -> None:
    settings = get_settings()
    settings.auth_secret_key = "integration-secret-key-with-at-least-32-characters"
    username = "phase4_user"
    email = "phase4_user@example.com"
    slug = "phase4-organization"
    user_id: UUID | None = None
    organization_id: UUID | None = None
    other_user_id: UUID | None = None
    other_organization_id: UUID | None = None

    await engine.dispose()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            unauthenticated = await client.get("/users/me")
            assert unauthenticated.status_code == 401

            registration = await client.post(
                "/auth/register",
                json={
                    "email": email,
                    "username": username,
                    "password": "correct horse battery staple",
                    "organization_name": "Phase 4 Organization",
                    "organization_slug": slug,
                },
            )
            assert registration.status_code == 201, registration.text
            registration_payload = registration.json()
            user_id = UUID(registration_payload["user"]["id"])
            organization_id = UUID(registration_payload["user"]["organization_id"])
            token = registration_payload["access_token"]

            invalid_login = await client.post(
                "/auth/login",
                json={"username_or_email": username, "password": "incorrect password"},
            )
            assert invalid_login.status_code == 401

            login = await client.post(
                "/auth/login",
                json={"username_or_email": email, "password": "correct horse battery staple"},
            )
            assert login.status_code == 200
            token = login.json()["access_token"]

            profile = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert profile.status_code == 200
            assert profile.json()["organization_id"] == str(organization_id)

            organization = await client.get(
                "/users/me/organization", headers={"Authorization": f"Bearer {token}"}
            )
            assert organization.status_code == 200
            assert organization.json()["slug"] == slug

            non_admin = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
            assert non_admin.status_code == 403

            other_registration = await client.post(
                "/auth/register",
                json={
                    "email": "phase4_other@example.com",
                    "username": "phase4_other",
                    "password": "another secure password",
                    "organization_name": "Other Organization",
                    "organization_slug": "other-organization",
                },
            )
            assert other_registration.status_code == 201, other_registration.text
            other_payload = other_registration.json()["user"]
            other_user_id = UUID(other_payload["id"])
            other_organization_id = UUID(other_payload["organization_id"])

            async with engine.begin() as connection:
                await connection.execute(
                    text("UPDATE users SET role = 'admin' WHERE id = :user_id"),
                    {"user_id": user_id},
                )

            admin_login = await client.post(
                "/auth/login",
                json={"username_or_email": username, "password": "correct horse battery staple"},
            )
            assert admin_login.status_code == 200
            admin_users = await client.get(
                "/users", headers={"Authorization": f"Bearer {admin_login.json()['access_token']}"}
            )
            assert admin_users.status_code == 200
            assert all(item["organization_id"] == str(organization_id) for item in admin_users.json())
            assert all(item["id"] != str(other_user_id) for item in admin_users.json())

            invalid_token = await client.get(
                "/users/me", headers={"Authorization": "Bearer invalid-token"}
            )
            assert invalid_token.status_code == 401
        finally:
            async with engine.begin() as connection:
                if user_id is not None:
                    await connection.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
                if other_user_id is not None:
                    await connection.execute(
                        text("DELETE FROM users WHERE id = :user_id"), {"user_id": other_user_id}
                    )
                if organization_id is not None:
                    await connection.execute(
                        text("DELETE FROM organizations WHERE id = :organization_id"),
                        {"organization_id": organization_id},
                    )
                if other_organization_id is not None:
                    await connection.execute(
                        text("DELETE FROM organizations WHERE id = :organization_id"),
                        {"organization_id": other_organization_id},
                    )
            await engine.dispose()
