from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from database.connection.session import engine
from main import app


@pytest.mark.asyncio
async def test_document_upload_to_retrieval_flow() -> None:
    await engine.dispose()
    document_id: UUID | None = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            response = await client.post(
                "/documents",
                files={
                    "file": (
                        "handbook.md",
                        b"# Handbook\n\nIncident response requires notifying the operations lead.",
                        "text/markdown",
                    )
                },
            )

            if response.status_code in {502, 503}:
                pytest.skip("Database is not available in this environment")
            assert response.status_code == 201, response.text
            document_id = UUID(response.json()["id"])
            assert response.json()["status"] == "READY"

            search_response = await client.post(
                "/documents/search",
                json={"query": "Who should be notified for incident response?", "limit": 3},
            )

            assert search_response.status_code == 200, search_response.text
            payload = search_response.json()
            assert payload["sources"]
            assert "operations lead" in payload["context"]
            assert any(source["document_id"] == str(document_id) for source in payload["sources"])
        finally:
            if document_id is not None:
                async with engine.begin() as connection:
                    await connection.execute(
                        text("DELETE FROM documents WHERE id = :document_id"),
                        {"document_id": document_id},
                    )
            await engine.dispose()