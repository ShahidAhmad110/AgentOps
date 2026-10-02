from __future__ import annotations

from uuid import UUID
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from database.connection.session import engine, session_factory
from database.models.organization import Organization
from database.models.user import User
from database.models.document import Document
from main import app


@pytest.mark.asyncio
async def test_shared_organization_knowledge_and_registration_flow() -> None:
    org_name = "Acme Global Dynamics"
    org_slug = "acme-global-dynamics"
    diff_org_name = "Beta Innovative Systems"
    diff_org_slug = "beta-innovative-systems"

    user_a_email = "alice@acmeglobal.test"
    user_a_username = "alice_acme"
    user_b_email = "bob@acmeglobal.test"
    user_b_username = "bob_acme"
    user_d_email = "dave@acmeglobal.test"
    user_d_username = "dave_acme"
    user_c_email = "charlie@betasystems.test"
    user_c_username = "charlie_beta"

    await engine.dispose()
    # Pre-clean any leftover records
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "DELETE FROM tool_calls WHERE run_id IN "
                "(SELECT id FROM agent_runs WHERE user_id IN "
                "(SELECT id FROM users WHERE email IN (:e1, :e2, :e3, :e4)))"
            ),
            {"e1": user_a_email, "e2": user_b_email, "e3": user_c_email, "e4": user_d_email},
        )
        await connection.execute(
            text(
                "DELETE FROM agent_steps WHERE run_id IN "
                "(SELECT id FROM agent_runs WHERE user_id IN "
                "(SELECT id FROM users WHERE email IN (:e1, :e2, :e3, :e4)))"
            ),
            {"e1": user_a_email, "e2": user_b_email, "e3": user_c_email, "e4": user_d_email},
        )
        await connection.execute(
            text(
                "DELETE FROM agent_runs WHERE user_id IN "
                "(SELECT id FROM users WHERE email IN (:e1, :e2, :e3, :e4))"
            ),
            {"e1": user_a_email, "e2": user_b_email, "e3": user_c_email, "e4": user_d_email},
        )
        await connection.execute(
            text("DELETE FROM documents WHERE filename = 'company_rules.md'")
        )
        await connection.execute(
            text("DELETE FROM users WHERE email IN (:e1, :e2, :e3, :e4)"),
            {"e1": user_a_email, "e2": user_b_email, "e3": user_c_email, "e4": user_d_email},
        )
        await connection.execute(
            text("DELETE FROM organizations WHERE slug IN (:s1, :s2)"),
            {"s1": org_slug, "s2": diff_org_slug},
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # 1. Register User A with a new organization
            resp_a = await client.post(
                "/auth/register",
                json={
                    "email": user_a_email,
                    "username": user_a_username,
                    "password": "Password123!",
                    "organization_name": org_name,
                    "organization_slug": org_slug,
                },
            )
            assert resp_a.status_code == 201, resp_a.text
            token_a = resp_a.json()["access_token"]
            org_id_a = resp_a.json()["user"]["organization_id"]

            # 2. Upload organization knowledge file as User A
            company_rules_content = (
                "# Acme Global Dynamics Employee Rules\n\n"
                "All employees at Acme Global are entitled to 25 days of annual paid time off.\n"
                "The standard working hours are from 9:00 AM to 5:00 PM Eastern Time.\n"
                "Employees can expense up to $500 per year for home office equipment and ergonomics.\n"
            ).encode("utf-8")

            upload_resp = await client.post(
                "/documents",
                headers={"Authorization": f"Bearer {token_a}"},
                files={"file": ("company_rules.md", company_rules_content, "text/markdown")},
            )
            assert upload_resp.status_code == 201, upload_resp.text
            doc_id = upload_resp.json()["id"]
            assert upload_resp.json()["status"] == "READY"

            # 3. User A asks a question about the document
            agent_resp_a = await client.post(
                "/agent",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"request": "How many days of annual paid time off do employees get?"},
            )
            assert agent_resp_a.status_code == 200, agent_resp_a.text
            agent_data_a = agent_resp_a.json()
            assert agent_data_a["status"] == "completed"
            assert len(agent_data_a["retrieved_sources"]) > 0
            assert "25 days" in (agent_data_a["response"] or "")

            # 4. Register User B for the SAME organization
            resp_b = await client.post(
                "/auth/register",
                json={
                    "email": user_b_email,
                    "username": user_b_username,
                    "password": "Password123!",
                    "organization_name": org_name,
                    "organization_slug": org_slug,
                },
            )
            assert resp_b.status_code == 201, resp_b.text
            token_b = resp_b.json()["access_token"]
            org_id_b = resp_b.json()["user"]["organization_id"]
            assert org_id_b == org_id_a, "User B must belong to the exact same organization as User A"

            # 5. Verify only ONE organization record exists in DB for this slug
            async with session_factory() as session:
                matching_orgs = (
                    await session.execute(
                        select(Organization).where(Organization.slug == org_slug)
                    )
                ).scalars().all()
                assert len(matching_orgs) == 1, "There must be exactly one organization record created"

            # 6. User B asks the same question WITHOUT uploading any document
            agent_resp_b = await client.post(
                "/agent",
                headers={"Authorization": f"Bearer {token_b}"},
                json={"request": "What is the annual paid time off policy?"},
            )
            assert agent_resp_b.status_code == 200, agent_resp_b.text
            agent_data_b = agent_resp_b.json()
            assert agent_data_b["status"] == "completed"
            assert len(agent_data_b["retrieved_sources"]) > 0
            assert "company_rules.md" in agent_data_b["retrieved_sources"][0]["filename"]
            assert "25 days" in (agent_data_b["response"] or "")

            # 7. Register User D for the SAME organization (testing 3+ members)
            resp_d = await client.post(
                "/auth/register",
                json={
                    "email": user_d_email,
                    "username": user_d_username,
                    "password": "Password123!",
                    "organization_name": org_name,
                    "organization_slug": org_slug,
                },
            )
            assert resp_d.status_code == 201, resp_d.text
            token_d = resp_d.json()["access_token"]
            assert resp_d.json()["user"]["organization_id"] == org_id_a

            # 8. Register User C for a DIFFERENT organization
            resp_c = await client.post(
                "/auth/register",
                json={
                    "email": user_c_email,
                    "username": user_c_username,
                    "password": "Password123!",
                    "organization_name": diff_org_name,
                    "organization_slug": diff_org_slug,
                },
            )
            assert resp_c.status_code == 201, resp_c.text
            token_c = resp_c.json()["access_token"]
            org_id_c = resp_c.json()["user"]["organization_id"]
            assert org_id_c != org_id_a, "User C must belong to a different organization"

            # 9. User C queries for Acme's rules -> must NOT retrieve Acme's documents
            agent_resp_c = await client.post(
                "/agent",
                headers={"Authorization": f"Bearer {token_c}"},
                json={"request": "How many days of annual paid time off do employees get?"},
            )
            assert agent_resp_c.status_code == 200
            agent_data_c = agent_resp_c.json()
            assert len(agent_data_c["retrieved_sources"]) == 0
            assert "No relevant documents were found" in (agent_data_c["response"] or "")

        finally:
            # Clean up test records
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "DELETE FROM tool_calls WHERE run_id IN "
                        "(SELECT id FROM agent_runs WHERE user_id IN "
                        "(SELECT id FROM users WHERE email IN (:e1, :e2, :e3, :e4)))"
                    ),
                    {"e1": user_a_email, "e2": user_b_email, "e3": user_c_email, "e4": user_d_email},
                )
                await connection.execute(
                    text(
                        "DELETE FROM agent_steps WHERE run_id IN "
                        "(SELECT id FROM agent_runs WHERE user_id IN "
                        "(SELECT id FROM users WHERE email IN (:e1, :e2, :e3, :e4)))"
                    ),
                    {"e1": user_a_email, "e2": user_b_email, "e3": user_c_email, "e4": user_d_email},
                )
                await connection.execute(
                    text(
                        "DELETE FROM agent_runs WHERE user_id IN "
                        "(SELECT id FROM users WHERE email IN (:e1, :e2, :e3, :e4))"
                    ),
                    {"e1": user_a_email, "e2": user_b_email, "e3": user_c_email, "e4": user_d_email},
                )
                await connection.execute(
                    text("DELETE FROM documents WHERE filename = 'company_rules.md'")
                )
                await connection.execute(
                    text("DELETE FROM users WHERE email IN (:e1, :e2, :e3, :e4)"),
                    {"e1": user_a_email, "e2": user_b_email, "e3": user_c_email, "e4": user_d_email},
                )
                await connection.execute(
                    text("DELETE FROM organizations WHERE slug IN (:s1, :s2)"),
                    {"s1": org_slug, "s2": diff_org_slug},
                )
            await engine.dispose()
