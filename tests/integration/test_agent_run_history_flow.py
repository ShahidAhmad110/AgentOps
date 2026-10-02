from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.core.config import get_settings
from database.connection.session import engine
from main import app


@pytest.mark.asyncio
async def test_agent_run_history_is_scoped_to_authenticated_user_and_organization() -> None:
    get_settings().auth_secret_key = "agent-run-history-integration-secret-2026"
    first_user_id: UUID | None = None
    second_user_id: UUID | None = None
    first_organization_id: UUID | None = None
    second_organization_id: UUID | None = None
    first_run_id = uuid4()
    second_run_id = uuid4()

    await engine.dispose()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            first_registration = await client.post(
                "/auth/register",
                json={
                    "email": "agent_run_owner@example.com",
                    "username": "agent_run_owner",
                    "password": "agent run owner password",
                    "organization_name": "Agent Run History Organization",
                    "organization_slug": "agent-run-history-org",
                },
            )
            second_registration = await client.post(
                "/auth/register",
                json={
                    "email": "agent_run_other@example.com",
                    "username": "agent_run_other",
                    "password": "agent run other password",
                    "organization_name": "Temporary Agent Run Organization",
                    "organization_slug": "agent-run-other-temp-org",
                },
            )
            assert first_registration.status_code == 201, first_registration.text
            assert second_registration.status_code == 201, second_registration.text
            first_user = first_registration.json()["user"]
            second_user = second_registration.json()["user"]
            first_user_id = UUID(first_user["id"])
            second_user_id = UUID(second_user["id"])
            first_organization_id = UUID(first_user["organization_id"])
            second_organization_id = UUID(second_user["organization_id"])
            first_headers = {"Authorization": f"Bearer {first_registration.json()['access_token']}"}
            second_headers = {"Authorization": f"Bearer {second_registration.json()['access_token']}"}

            async with engine.begin() as connection:
                await connection.execute(
                    text("UPDATE users SET organization_id = :organization_id WHERE id = :user_id"),
                    {"organization_id": first_organization_id, "user_id": second_user_id},
                )
                await connection.execute(
                    text("DELETE FROM organizations WHERE id = :organization_id"),
                    {"organization_id": second_organization_id},
                )
                for run_id, user_id, request in (
                    (first_run_id, first_user_id, "Owner private run"),
                    (second_run_id, second_user_id, "Other private run"),
                ):
                    await connection.execute(
                        text(
                            "INSERT INTO agent_runs "
                            "(id, user_id, organization_id, request, status, final_response, completed_at) "
                            "VALUES (:id, :user_id, :organization_id, :request, 'COMPLETED', 'Done', now())"
                        ),
                        {
                            "id": run_id,
                            "user_id": user_id,
                            "organization_id": first_organization_id,
                            "request": request,
                        },
                    )

            refreshed_second_login = await client.post(
                "/auth/login",
                json={
                    "username_or_email": "agent_run_other",
                    "password": "agent run other password",
                },
            )
            assert refreshed_second_login.status_code == 200, refreshed_second_login.text
            second_headers = {"Authorization": f"Bearer {refreshed_second_login.json()['access_token']}"}

            first_response = await client.get("/agent-runs", headers=first_headers)
            second_response = await client.get("/agent-runs", headers=second_headers)

            assert first_response.status_code == 200, first_response.text
            assert second_response.status_code == 200, second_response.text
            assert [run["request"] for run in first_response.json()] == ["Owner private run"]
            assert [run["request"] for run in second_response.json()] == ["Other private run"]
        finally:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DELETE FROM agent_runs WHERE id IN (:first_run, :second_run)"),
                    {"first_run": first_run_id, "second_run": second_run_id},
                )
                for user_id in (first_user_id, second_user_id):
                    if user_id is not None:
                        await connection.execute(
                            text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id}
                        )
                for organization_id in (first_organization_id, second_organization_id):
                    if organization_id is not None:
                        await connection.execute(
                            text("DELETE FROM organizations WHERE id = :organization_id"),
                            {"organization_id": organization_id},
                        )
            await engine.dispose()