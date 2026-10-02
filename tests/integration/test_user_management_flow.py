from __future__ import annotations

from uuid import UUID
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from database.connection.session import engine
from main import app


@pytest.mark.asyncio
async def test_supervisor_and_admin_user_management_flow() -> None:
    org_a_slug = "test-mgmt-global-org-a"
    org_b_slug = "test-mgmt-global-org-b"

    admin_a_email = "admin_a@globalmgmt.test"
    admin_a_username = "admin_a_global"
    user_a1_email = "user_a1@globalmgmt.test"
    user_a1_username = "user_a1_global"
    user_a2_email = "user_a2@globalmgmt.test"
    user_a2_username = "user_a2_global"

    supervisor_b_email = "supervisor_b@globalmgmt.test"
    supervisor_b_username = "supervisor_b_global"
    user_b1_email = "user_b1@globalmgmt.test"
    user_b1_username = "user_b1_global"

    test_emails = (
        admin_a_email,
        user_a1_email,
        user_a2_email,
        supervisor_b_email,
        user_b1_email,
    )

    await engine.dispose()
    # Pre-clean test records
    async with engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM users WHERE email IN (:e1, :e2, :e3, :e4, :e5)"),
            {
                "e1": admin_a_email,
                "e2": user_a1_email,
                "e3": user_a2_email,
                "e4": supervisor_b_email,
                "e5": user_b1_email,
            },
        )
        await connection.execute(
            text("DELETE FROM organizations WHERE slug IN (:s1, :s2)"),
            {"s1": org_a_slug, "s2": org_b_slug},
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # 1. Register Admin A with Org A
            resp = await client.post(
                "/auth/register",
                json={
                    "email": admin_a_email,
                    "username": admin_a_username,
                    "password": "Password123!",
                    "organization_name": "Management Org A",
                    "organization_slug": org_a_slug,
                },
            )
            assert resp.status_code == 201, resp.text
            admin_a_id = UUID(resp.json()["user"]["id"])
            org_a_id = UUID(resp.json()["user"]["organization_id"])

            # Elevate Admin A to role='admin' in DB
            async with engine.begin() as connection:
                await connection.execute(
                    text("UPDATE users SET role = 'admin' WHERE id = :id"),
                    {"id": admin_a_id},
                )

            # Re-login to get admin token with role='admin'
            resp = await client.post(
                "/auth/login",
                json={"username_or_email": admin_a_email, "password": "Password123!"},
            )
            assert resp.status_code == 200
            token_admin_a = resp.json()["access_token"]

            # 2. Register User A1 and User A2 into Org A
            resp = await client.post(
                "/auth/register",
                json={
                    "email": user_a1_email,
                    "username": user_a1_username,
                    "password": "Password123!",
                    "organization_name": "Management Org A",
                    "organization_slug": org_a_slug,
                },
            )
            assert resp.status_code == 201
            user_a1_id = UUID(resp.json()["user"]["id"])
            token_user_a1 = resp.json()["access_token"]

            resp = await client.post(
                "/auth/register",
                json={
                    "email": user_a2_email,
                    "username": user_a2_username,
                    "password": "Password123!",
                    "organization_name": "Management Org A",
                    "organization_slug": org_a_slug,
                },
            )
            assert resp.status_code == 201
            user_a2_id = UUID(resp.json()["user"]["id"])

            # 3. Register Supervisor B and User B1 into separate Org B
            resp = await client.post(
                "/auth/register",
                json={
                    "email": supervisor_b_email,
                    "username": supervisor_b_username,
                    "password": "Password123!",
                    "organization_name": "Management Org B",
                    "organization_slug": org_b_slug,
                },
            )
            assert resp.status_code == 201
            supervisor_b_id = UUID(resp.json()["user"]["id"])
            org_b_id = UUID(resp.json()["user"]["organization_id"])

            # Elevate Supervisor B to role='supervisor' in DB
            async with engine.begin() as connection:
                await connection.execute(
                    text("UPDATE users SET role = 'supervisor' WHERE id = :id"),
                    {"id": supervisor_b_id},
                )

            # Re-login to get supervisor token
            resp = await client.post(
                "/auth/login",
                json={"username_or_email": supervisor_b_email, "password": "Password123!"},
            )
            assert resp.status_code == 200
            token_supervisor_b = resp.json()["access_token"]

            resp = await client.post(
                "/auth/register",
                json={
                    "email": user_b1_email,
                    "username": user_b1_username,
                    "password": "Password123!",
                    "organization_name": "Management Org B",
                    "organization_slug": org_b_slug,
                },
            )
            assert resp.status_code == 201
            user_b1_id = UUID(resp.json()["user"]["id"])

            # 4. Admin A has GLOBAL visibility across all registered users in the database
            list_resp = await client.get("/users", headers={"Authorization": f"Bearer {token_admin_a}"})
            assert list_resp.status_code == 200
            all_users = list_resp.json()
            all_user_ids = [u["id"] for u in all_users]

            # All 5 registered users must be visible to Admin A
            assert str(admin_a_id) in all_user_ids
            assert str(user_a1_id) in all_user_ids
            assert str(user_a2_id) in all_user_ids
            assert str(supervisor_b_id) in all_user_ids
            assert str(user_b1_id) in all_user_ids

            # Verify organization information is attached to each user
            user_b1_entry = next(u for u in all_users if u["id"] == str(user_b1_id))
            assert user_b1_entry["organization"] is not None
            assert user_b1_entry["organization"]["slug"] == org_b_slug
            assert user_b1_entry["organization"]["name"] == "Management Org B"

            # 5. Search across all users as Admin A
            search_resp = await client.get(
                "/users?search=user_b1", headers={"Authorization": f"Bearer {token_admin_a}"}
            )
            assert search_resp.status_code == 200
            search_data = search_resp.json()
            assert any(u["id"] == str(user_b1_id) for u in search_data)

            # 6. Admin A views user details of a user in Org B
            detail_resp = await client.get(
                f"/users/{user_b1_id}", headers={"Authorization": f"Bearer {token_admin_a}"}
            )
            assert detail_resp.status_code == 200
            detail = detail_resp.json()
            assert detail["id"] == str(user_b1_id)
            assert detail["email"] == user_b1_email
            assert detail["organization"]["slug"] == org_b_slug
            assert "password" not in detail and "password_hash" not in detail

            # 7. Admin A deactivates User B1 (across organizations)
            deact_resp = await client.patch(
                f"/users/{user_b1_id}/status",
                headers={"Authorization": f"Bearer {token_admin_a}"},
                json={"is_active": False},
            )
            assert deact_resp.status_code == 200
            assert deact_resp.json()["is_active"] is False

            # Deactivated user cannot login
            login_fail = await client.post(
                "/auth/login",
                json={"username_or_email": user_b1_email, "password": "Password123!"},
            )
            assert login_fail.status_code == 401

            # 8. Admin A reactivates User B1
            react_resp = await client.patch(
                f"/users/{user_b1_id}/status",
                headers={"Authorization": f"Bearer {token_admin_a}"},
                json={"is_active": True},
            )
            assert react_resp.status_code == 200
            assert react_resp.json()["is_active"] is True

            # Reactivated user can login
            login_ok = await client.post(
                "/auth/login",
                json={"username_or_email": user_b1_email, "password": "Password123!"},
            )
            assert login_ok.status_code == 200

            # 9. Supervisor B visibility is strictly SCOPED to Org B
            sup_list_resp = await client.get(
                "/users", headers={"Authorization": f"Bearer {token_supervisor_b}"}
            )
            assert sup_list_resp.status_code == 200
            sup_users = sup_list_resp.json()
            sup_user_ids = [u["id"] for u in sup_users]

            # Supervisor B only sees Org B users
            assert str(supervisor_b_id) in sup_user_ids
            assert str(user_b1_id) in sup_user_ids
            assert str(admin_a_id) not in sup_user_ids
            assert str(user_a1_id) not in sup_user_ids
            assert str(user_a2_id) not in sup_user_ids

            # Supervisor B cannot view or modify users in Org A
            cross_view = await client.get(
                f"/users/{user_a1_id}", headers={"Authorization": f"Bearer {token_supervisor_b}"}
            )
            assert cross_view.status_code == 404

            cross_deact = await client.patch(
                f"/users/{user_a1_id}/status",
                headers={"Authorization": f"Bearer {token_supervisor_b}"},
                json={"is_active": False},
            )
            assert cross_deact.status_code == 404

            # 10. Normal User (role='user') cannot access any user management endpoint
            forbidden_list = await client.get(
                "/users", headers={"Authorization": f"Bearer {token_user_a1}"}
            )
            assert forbidden_list.status_code == 403

            forbidden_detail = await client.get(
                f"/users/{user_a2_id}", headers={"Authorization": f"Bearer {token_user_a1}"}
            )
            assert forbidden_detail.status_code == 403

            forbidden_status = await client.patch(
                f"/users/{user_a2_id}/status",
                headers={"Authorization": f"Bearer {token_user_a1}"},
                json={"is_active": False},
            )
            assert forbidden_status.status_code == 403

            forbidden_delete = await client.delete(
                f"/users/{user_a2_id}", headers={"Authorization": f"Bearer {token_user_a1}"}
            )
            assert forbidden_delete.status_code == 403

            # 11. Self-deactivation and self-deletion safeguards
            self_deact = await client.patch(
                f"/users/{admin_a_id}/status",
                headers={"Authorization": f"Bearer {token_admin_a}"},
                json={"is_active": False},
            )
            assert self_deact.status_code == 400
            assert "cannot deactivate your own account" in self_deact.json()["error"]["message"]

            self_del = await client.delete(
                f"/users/{admin_a_id}", headers={"Authorization": f"Bearer {token_admin_a}"}
            )
            assert self_del.status_code == 400
            assert "cannot delete your own account" in self_del.json()["error"]["message"]

            # 12. Delete User A2 as Admin
            del_resp = await client.delete(
                f"/users/{user_a2_id}", headers={"Authorization": f"Bearer {token_admin_a}"}
            )
            assert del_resp.status_code == 200

            # Deleted user cannot login
            del_login = await client.post(
                "/auth/login",
                json={"username_or_email": user_a2_email, "password": "Password123!"},
            )
            assert del_login.status_code == 401

        finally:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DELETE FROM users WHERE email IN (:e1, :e2, :e3, :e4, :e5)"),
                    {
                        "e1": admin_a_email,
                        "e2": user_a1_email,
                        "e3": user_a2_email,
                        "e4": supervisor_b_email,
                        "e5": user_b1_email,
                    },
                )
                await connection.execute(
                    text("DELETE FROM organizations WHERE slug IN (:s1, :s2)"),
                    {"s1": org_a_slug, "s2": org_b_slug},
                )
            await engine.dispose()
