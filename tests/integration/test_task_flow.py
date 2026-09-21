from datetime import datetime, timezone
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.core.config import get_settings
from database.connection.session import engine
from main import app


@pytest.mark.asyncio
async def test_task_crud_lifecycle_comments_and_organization_isolation() -> None:
    settings = get_settings()
    settings.auth_secret_key = "task-integration-secret-at-least-32-characters"
    owner_id: UUID | None = None
    assignee_id: UUID | None = None
    other_user_id: UUID | None = None
    organization_id: UUID | None = None
    other_organization_id: UUID | None = None
    task_id: UUID | None = None

    await engine.dispose()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            owner_registration = await client.post(
                "/auth/register",
                json={
                    "email": "task_owner@example.com",
                    "username": "task_owner",
                    "password": "task owner password",
                    "organization_name": "Task Organization",
                    "organization_slug": "task-organization",
                },
            )
            assert owner_registration.status_code == 201, owner_registration.text
            owner_payload = owner_registration.json()
            owner_id = UUID(owner_payload["user"]["id"])
            organization_id = UUID(owner_payload["user"]["organization_id"])
            owner_headers = {"Authorization": f"Bearer {owner_payload['access_token']}"}

            assignee_registration = await client.post(
                "/auth/register",
                json={
                    "email": "task_assignee@example.com",
                    "username": "task_assignee",
                    "password": "task assignee password",
                    "organization_name": "Assignee Organization",
                    "organization_slug": "assignee-organization",
                },
            )
            assert assignee_registration.status_code == 201, assignee_registration.text
            assignee_payload = assignee_registration.json()
            assignee_id = UUID(assignee_payload["user"]["id"])
            assignee_organization_id = UUID(assignee_payload["user"]["organization_id"])

            async with engine.begin() as connection:
                await connection.execute(
                    text("UPDATE users SET organization_id = :organization_id WHERE id = :user_id"),
                    {"organization_id": organization_id, "user_id": assignee_id},
                )
                await connection.execute(
                    text("DELETE FROM organizations WHERE id = :organization_id"),
                    {"organization_id": assignee_organization_id},
                )

            create_response = await client.post(
                "/tasks",
                headers=owner_headers,
                json={
                    "title": "Prepare incident report",
                    "description": "Summarize the incident timeline.",
                    "assignee_id": str(assignee_id),
                    "status": "TODO",
                    "priority": "HIGH",
                    "due_date": datetime.now(timezone.utc).isoformat(),
                },
            )
            assert create_response.status_code == 201, create_response.text
            task_payload = create_response.json()
            task_id = UUID(task_payload["id"])
            assert task_payload["owner_id"] == str(owner_id)
            assert task_payload["organization_id"] == str(organization_id)
            assert task_payload["assignee_id"] == str(assignee_id)

            get_response = await client.get(f"/tasks/{task_id}", headers=owner_headers)
            assert get_response.status_code == 200
            assert get_response.json()["comments"] == []

            update_response = await client.patch(
                f"/tasks/{task_id}",
                headers=owner_headers,
                json={"status": "IN_PROGRESS", "priority": "URGENT"},
            )
            assert update_response.status_code == 200
            assert update_response.json()["status"] == "IN_PROGRESS"
            assert update_response.json()["priority"] == "URGENT"

            comment_response = await client.post(
                f"/tasks/{task_id}/comments",
                headers=owner_headers,
                json={"content": "The report is underway."},
            )
            assert comment_response.status_code == 201

            comments_response = await client.get(f"/tasks/{task_id}/comments", headers=owner_headers)
            assert comments_response.status_code == 200
            assert comments_response.json()[0]["content"] == "The report is underway."

            filtered = await client.get(
                "/tasks", headers=owner_headers, params={"status": "IN_PROGRESS", "search": "incident"}
            )
            assert filtered.status_code == 200
            assert [item["id"] for item in filtered.json()] == [str(task_id)]

            invalid_status = await client.patch(
                f"/tasks/{task_id}", headers=owner_headers, json={"status": "INVALID"}
            )
            assert invalid_status.status_code == 422

            invalid_assignee = await client.patch(
                f"/tasks/{task_id}",
                headers=owner_headers,
                json={"assignee_id": "00000000-0000-0000-0000-000000000000"},
            )
            assert invalid_assignee.status_code == 422

            other_registration = await client.post(
                "/auth/register",
                json={
                    "email": "task_other@example.com",
                    "username": "task_other",
                    "password": "task other password",
                    "organization_name": "Other Task Organization",
                    "organization_slug": "other-task-organization",
                },
            )
            assert other_registration.status_code == 201, other_registration.text
            other_payload = other_registration.json()
            other_user_id = UUID(other_payload["user"]["id"])
            other_organization_id = UUID(other_payload["user"]["organization_id"])
            other_headers = {"Authorization": f"Bearer {other_payload['access_token']}"}

            assert (await client.get(f"/tasks/{task_id}", headers=other_headers)).status_code == 404
            assert (await client.patch(f"/tasks/{task_id}", headers=other_headers, json={"title": "Bypass"})).status_code == 404
            assert (await client.delete(f"/tasks/{task_id}", headers=other_headers)).status_code == 404

            archived = await client.delete(f"/tasks/{task_id}", headers=owner_headers)
            assert archived.status_code == 204
            assert (await client.get(f"/tasks/{task_id}", headers=owner_headers)).status_code == 404
        finally:
            async with engine.begin() as connection:
                if task_id is not None:
                    await connection.execute(text("DELETE FROM tasks WHERE id = :task_id"), {"task_id": task_id})
                for user_id in (owner_id, assignee_id, other_user_id):
                    if user_id is not None:
                        await connection.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
                for organization in (organization_id, other_organization_id):
                    if organization is not None:
                        await connection.execute(
                            text("DELETE FROM organizations WHERE id = :organization_id"),
                            {"organization_id": organization},
                        )
            await engine.dispose()
