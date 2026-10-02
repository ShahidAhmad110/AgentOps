from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.core.config import get_settings
from database.connection.session import engine
from documents.embeddings.hash_embeddings import HashEmbeddingProvider
from main import app


@pytest.mark.asyncio
async def test_document_upload_to_retrieval_flow() -> None:
    settings = get_settings()
    settings.auth_secret_key = "document-integration-secret-at-least-32-characters"
    await engine.dispose()
    document_id: UUID | None = None
    user_id: UUID | None = None
    organization_id: UUID | None = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            registration = await client.post(
                "/auth/register",
                json={
                    "email": "document_uploader@example.com",
                    "username": "document_uploader",
                    "password": "secure document password",
                    "organization_name": "Document Organization",
                    "organization_slug": "document-organization",
                },
            )
            assert registration.status_code == 201, registration.text
            user_id = UUID(registration.json()["user"]["id"])
            organization_id = UUID(registration.json()["user"]["organization_id"])
            headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}

            response = await client.post(
                "/documents",
                headers=headers,
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
                headers=headers,
                json={"query": "Who should be notified for incident response?", "limit": 3},
            )

            assert search_response.status_code == 200, search_response.text
            payload = search_response.json()
            assert payload["sources"]
            assert "operations lead" in payload["context"]
            assert any(source["document_id"] == str(document_id) for source in payload["sources"])
        finally:
            async with engine.begin() as connection:
                if document_id is not None:
                    await connection.execute(
                        text("DELETE FROM documents WHERE id = :document_id"),
                        {"document_id": document_id},
                    )
                if user_id is not None:
                    await connection.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
                if organization_id is not None:
                    await connection.execute(
                        text("DELETE FROM organizations WHERE id = :organization_id"),
                        {"organization_id": organization_id},
                    )
            await engine.dispose()


@pytest.mark.asyncio
async def test_document_access_is_scoped_to_user_organization() -> None:
    settings = get_settings()
    settings.auth_secret_key = "document-tenant-secret-at-least-32-characters"
    first_user_id: UUID | None = None
    second_user_id: UUID | None = None
    first_org_id: UUID | None = None
    second_org_id: UUID | None = None
    document_id: UUID | None = None

    await engine.dispose()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            first = await client.post(
                "/auth/register",
                json={
                    "email": "doc_owner@example.com",
                    "username": "doc_owner",
                    "password": "document owner pass",
                    "organization_name": "Document Owner Org",
                    "organization_slug": "doc-owner-org",
                },
            )
            second = await client.post(
                "/auth/register",
                json={
                    "email": "doc_other@example.com",
                    "username": "doc_other",
                    "password": "document other pass",
                    "organization_name": "Other Org",
                    "organization_slug": "other-doc-org",
                },
            )
            assert first.status_code == 201, first.text
            assert second.status_code == 201, second.text
            first_user_id = UUID(first.json()["user"]["id"])
            second_user_id = UUID(second.json()["user"]["id"])
            first_org_id = UUID(first.json()["user"]["organization_id"])
            second_org_id = UUID(second.json()["user"]["organization_id"])

            first_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
            second_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

            upload = await client.post(
                "/documents",
                headers=first_headers,
                files={"file": ("policy.md", b"# Policy\n\nAll incidents must be reported immediately.", "text/markdown")},
            )
            assert upload.status_code == 201, upload.text
            document_id = UUID(upload.json()["id"])

            forbidden_search = await client.post(
                "/documents/search",
                headers=second_headers,
                json={"query": "reported immediately", "limit": 3},
            )
            assert forbidden_search.status_code == 200
            assert forbidden_search.json()["sources"] == []

            forbidden_get = await client.get(f"/documents/{document_id}", headers=second_headers)
            assert forbidden_get.status_code == 404

            anonymous_delete = await client.delete(f"/documents/{document_id}")
            assert anonymous_delete.status_code == 401

            forbidden_delete = await client.delete(
                f"/documents/{document_id}", headers=second_headers
            )
            assert forbidden_delete.status_code == 404

            archive = await client.delete(f"/documents/{document_id}", headers=first_headers)
            assert archive.status_code == 204

            archived_get = await client.get(f"/documents/{document_id}", headers=first_headers)
            assert archived_get.status_code == 404
            archived_search = await client.post(
                "/documents/search",
                headers=first_headers,
                json={"query": "reported immediately", "limit": 3},
            )
            assert archived_search.status_code == 200
            assert archived_search.json()["sources"] == []

            async with engine.connect() as connection:
                archived_timestamp = await connection.execute(
                    text("SELECT deleted_at FROM documents WHERE id = :document_id"),
                    {"document_id": document_id},
                )
                assert archived_timestamp.scalar_one() is not None
        finally:
            async with engine.begin() as connection:
                if document_id is not None:
                    await connection.execute(text("DELETE FROM documents WHERE id = :document_id"), {"document_id": document_id})
                for user_id in (first_user_id, second_user_id):
                    if user_id is not None:
                        await connection.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
                for org_id in (first_org_id, second_org_id):
                    if org_id is not None:
                        await connection.execute(text("DELETE FROM organizations WHERE id = :organization_id"), {"organization_id": org_id})
            await engine.dispose()


@pytest.mark.asyncio
async def test_document_upload_failures_are_recorded_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    settings.auth_secret_key = "document-failure-secret-at-least-32-characters"
    user_id: UUID | None = None
    organization_id: UUID | None = None

    await engine.dispose()
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        try:
            registration = await client.post(
                "/auth/register",
                json={
                    "email": "document_failures@example.com",
                    "username": "document_failures",
                    "password": "document failure pass",
                    "organization_name": "Document Failure Org",
                    "organization_slug": "document-failure-org",
                },
            )
            assert registration.status_code == 201, registration.text
            user_id = UUID(registration.json()["user"]["id"])
            organization_id = UUID(registration.json()["user"]["organization_id"])
            headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}

            unsupported = await client.post(
                "/documents",
                headers=headers,
                files={"file": ("unsupported.docx", b"content", "application/octet-stream")},
            )
            assert unsupported.status_code == 400

            empty = await client.post(
                "/documents",
                headers=headers,
                files={"file": ("empty.md", b"", "text/markdown")},
            )
            assert empty.status_code == 400

            extraction_failure = await client.post(
                "/documents",
                headers=headers,
                files={"file": ("invalid.pdf", b"not a PDF", "application/pdf")},
            )
            assert extraction_failure.status_code == 500
            assert extraction_failure.json()["error"]["code"] == "INTERNAL_ERROR"
            assert "PdfReadError" not in extraction_failure.text

            def fail_embedding(_provider: HashEmbeddingProvider, _content: str) -> list[float]:
                raise RuntimeError("embedding provider failed")

            with monkeypatch.context() as patch:
                patch.setattr(HashEmbeddingProvider, "embed", fail_embedding)
                processing_failure = await client.post(
                    "/documents",
                    headers=headers,
                    files={
                        "file": (
                            "embedding-failure.md",
                            b"A valid document with searchable text.",
                            "text/markdown",
                        )
                    },
                )
            assert processing_failure.status_code == 500
            assert processing_failure.json()["error"]["code"] == "INTERNAL_ERROR"
            assert "embedding provider failed" not in processing_failure.text

            listing = await client.get("/documents", headers=headers)
            assert listing.status_code == 200
            failed_documents = {
                document["filename"]: document
                for document in listing.json()
                if document["filename"] in {"empty.md", "invalid.pdf", "embedding-failure.md"}
            }
            assert set(failed_documents) == {"empty.md", "invalid.pdf", "embedding-failure.md"}
            statuses = {filename: document["status"] for filename, document in failed_documents.items()}
            assert all(status == "FAILED" for status in statuses.values()), statuses
            assert all(document["error_message"] for document in failed_documents.values()), failed_documents
        finally:
            async with engine.begin() as connection:
                if user_id is not None:
                    await connection.execute(
                        text("DELETE FROM documents WHERE user_id = :user_id"),
                        {"user_id": user_id},
                    )
                    await connection.execute(
                        text("DELETE FROM users WHERE id = :user_id"),
                        {"user_id": user_id},
                    )
                if organization_id is not None:
                    await connection.execute(
                        text("DELETE FROM organizations WHERE id = :organization_id"),
                        {"organization_id": organization_id},
                    )
            await engine.dispose()