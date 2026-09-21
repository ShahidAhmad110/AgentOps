from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.core.config import get_settings
from database.connection.session import engine
from main import app


@pytest.mark.asyncio
async def test_conversation_messages_access_and_ordering() -> None:
    settings = get_settings()
    settings.auth_secret_key = "conversation-integration-secret-at-least-32-characters"
    first_user_id: UUID | None = None
    first_organization_id: UUID | None = None
    second_user_id: UUID | None = None
    second_organization_id: UUID | None = None
    conversation_id: UUID | None = None

    await engine.dispose()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            first_registration = await client.post(
                "/auth/register",
                json={
                    "email": "conversation_owner@example.com",
                    "username": "conversation_owner",
                    "password": "conversation owner password",
                    "organization_name": "Conversation Organization",
                    "organization_slug": "conversation-organization",
                },
            )
            assert first_registration.status_code == 201, first_registration.text
            first_payload = first_registration.json()
            first_user_id = UUID(first_payload["user"]["id"])
            first_organization_id = UUID(first_payload["user"]["organization_id"])
            first_token = first_payload["access_token"]
            first_headers = {"Authorization": f"Bearer {first_token}"}

            second_registration = await client.post(
                "/auth/register",
                json={
                    "email": "conversation_other@example.com",
                    "username": "conversation_other",
                    "password": "conversation other password",
                    "organization_name": "Other Conversation Organization",
                    "organization_slug": "other-conversation-organization",
                },
            )
            assert second_registration.status_code == 201, second_registration.text
            second_payload = second_registration.json()
            second_user_id = UUID(second_payload["user"]["id"])
            second_organization_id = UUID(second_payload["user"]["organization_id"])
            second_headers = {"Authorization": f"Bearer {second_payload['access_token']}"}

            created = await client.post(
                "/conversations",
                headers=first_headers,
                json={"title": "Incident discussion"},
            )
            assert created.status_code == 201, created.text
            conversation_id = UUID(created.json()["id"])
            assert created.json()["user_id"] == str(first_user_id)
            assert created.json()["organization_id"] == str(first_organization_id)

            first_message = await client.post(
                f"/conversations/{conversation_id}/messages",
                headers=first_headers,
                json={"role": "user", "content": "What happened?"},
            )
            second_message = await client.post(
                f"/conversations/{conversation_id}/messages",
                headers=first_headers,
                json={"role": "assistant", "content": "The incident was contained."},
            )
            assert first_message.status_code == 201
            assert second_message.status_code == 201
            assert first_message.json()["sequence"] == 1
            assert second_message.json()["sequence"] == 2

            reopened = await client.get(f"/conversations/{conversation_id}", headers=first_headers)
            assert reopened.status_code == 200
            assert [item["sequence"] for item in reopened.json()["messages"]] == [1, 2]
            assert [item["role"] for item in reopened.json()["messages"]] == ["user", "assistant"]

            listed_messages = await client.get(
                f"/conversations/{conversation_id}/messages", headers=first_headers
            )
            assert listed_messages.status_code == 200
            assert [item["content"] for item in listed_messages.json()] == [
                "What happened?",
                "The incident was contained.",
            ]

            other_access = await client.get(f"/conversations/{conversation_id}", headers=second_headers)
            assert other_access.status_code == 404
            other_message = await client.post(
                f"/conversations/{conversation_id}/messages",
                headers=second_headers,
                json={"role": "user", "content": "Unauthorized"},
            )
            assert other_message.status_code == 404

            invalid_message = await client.post(
                f"/conversations/{conversation_id}/messages",
                headers=first_headers,
                json={"role": "not-a-role", "content": "Invalid"},
            )
            assert invalid_message.status_code == 422
        finally:
            async with engine.begin() as connection:
                if conversation_id is not None:
                    await connection.execute(
                        text("DELETE FROM conversations WHERE id = :conversation_id"),
                        {"conversation_id": conversation_id},
                    )
                for user_id in (first_user_id, second_user_id):
                    if user_id is not None:
                        await connection.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
                for organization_id in (first_organization_id, second_organization_id):
                    if organization_id is not None:
                        await connection.execute(
                            text("DELETE FROM organizations WHERE id = :organization_id"),
                            {"organization_id": organization_id},
                        )
            await engine.dispose()
