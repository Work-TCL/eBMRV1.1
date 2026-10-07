"""Client gap-analysis Phase 1 (2026-10-05): bulk user onboarding via invite email, and the single-row
POST /users/invite alternative to POST /users. Covers preview validation, all-or-nothing commit, and the
public accept-invite flow (token single-use/expiry, no password set until accepted)."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import verify_password
from app.modules.iam.models import Role, User, UserInvite, UserSiteRole
from tests.conftest import auth_headers, idem, login


async def _promote_to_admin(db, user_id, site_id):
    async with db.begin():
        admin_role = (await db.execute(select(Role).where(Role.name == "Admin"))).scalar_one()
        db.add(UserSiteRole(user_id=user_id, site_id=site_id, role_id=admin_role.id))


async def test_invite_user_requires_admin(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/users/invite",
        json={"idempotency_key": idem(), "username": "invitee1", "email": "invitee1@example.com", "full_name": "Invitee One"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_invite_user_creates_pending_user_with_no_usable_password(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/users/invite",
        json={"idempotency_key": idem(), "username": "invitee2", "email": "invitee2@example.com", "full_name": "Invitee Two"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # The raw invite token must never be in the HTTP response (CTR-FR-018).
    assert "raw_invite_token" not in body
    assert "token" not in body

    user = await db.get(User, uuid.UUID(body["aggregate_id"]))
    assert user.status == "pending_activation"
    # No login is possible yet -- the placeholder password is random and never communicated.
    login_resp = await client.post("/auth/token", data={"username": "invitee2", "password": "anything"})
    assert login_resp.status_code == 401

    invite = (
        await db.execute(select(UserInvite).where(UserInvite.user_id == user.id))
    ).scalar_one()
    assert invite.consumed_at is None
    assert invite.expires_at > datetime.now(timezone.utc)


async def test_accept_invite_activates_user_and_token_is_single_use(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    # Can't get the raw token through the API by design -- mint one through the command layer directly,
    # same as the production code path, to exercise accept_invite() as a black-box HTTP caller would.
    from app.modules.iam.commands import InviteUserCommand, invite_user

    async with db.begin():
        result = await invite_user(
            db,
            InviteUserCommand(idempotency_key=idem(), username="invitee3", email="invitee3@example.com", full_name="Invitee Three"),
            seeded["users"]["operator1"].id,
        )
    raw_token = result.raw_invite_token

    resp = await client.post("/auth/accept-invite", json={"token": raw_token, "password": "NewPassword123!"})
    assert resp.status_code == 200, resp.text

    user = await db.get(User, result.user_id)
    assert user.status == "active"
    assert verify_password("NewPassword123!", user.password_hash)

    # Now logs in for real.
    login_resp = await client.post("/auth/token", data={"username": "invitee3", "password": "NewPassword123!"})
    assert login_resp.status_code == 200

    # Re-using the same token a second time must fail (single-use).
    resp2 = await client.post("/auth/accept-invite", json={"token": raw_token, "password": "AnotherPassword123!"})
    assert resp2.status_code == 422
    assert resp2.json()["code"] == "VALIDATION_FAILED"


async def test_accept_invite_rejects_unknown_and_expired_token(client, seeded, db):
    resp = await client.post("/auth/accept-invite", json={"token": "not-a-real-token", "password": "NewPassword123!"})
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"

    from app.modules.iam.commands import InviteUserCommand, invite_user

    async with db.begin():
        result = await invite_user(
            db,
            InviteUserCommand(idempotency_key=idem(), username="invitee4", email="invitee4@example.com", full_name="Invitee Four"),
            seeded["users"]["operator1"].id,
        )
    async with db.begin():
        invite = (await db.execute(select(UserInvite).where(UserInvite.user_id == result.user_id))).scalar_one()
        invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

    resp = await client.post("/auth/accept-invite", json={"token": result.raw_invite_token, "password": "NewPassword123!"})
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"
    assert "expired" in resp.json()["message"].lower()


async def test_bulk_import_preview_reports_per_row_errors(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/users/bulk-import/preview",
        json={
            "rows": [
                {"full_name": "Good Row", "email": "goodrow@example.com", "role_name": "Operator", "site_code": "T1"},
                {"full_name": "Bad Role", "email": "badrole@example.com", "role_name": "Nonexistent Role", "site_code": "T1"},
                {"full_name": "Bad Site", "email": "badsite@example.com", "role_name": "Operator", "site_code": "ZZ"},
                {"full_name": "Dup Email", "email": "goodrow@example.com", "role_name": "Operator", "site_code": "T1"},
            ]
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert rows[0]["ok"] is True
    assert rows[1]["ok"] is False and "role" in rows[1]["error"]
    assert rows[2]["ok"] is False and "site" in rows[2]["error"]
    assert rows[3]["ok"] is False and "duplicate" in rows[3]["error"]

    # Preview never writes anything.
    count = (await db.execute(select(User).where(User.username == "goodrow@example.com"))).scalar_one_or_none()
    assert count is None


async def test_bulk_import_commit_is_all_or_nothing(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/users/bulk-import/commit",
        json={
            "idempotency_key": idem(),
            "rows": [
                {"full_name": "Valid Row", "email": "validrow@example.com", "role_name": "Operator", "site_code": "T1"},
                {"full_name": "Invalid Role", "email": "invalidrole@example.com", "role_name": "Nonexistent Role", "site_code": "T1"},
            ],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"
    # Nothing committed, including the row that was individually valid.
    none_created = (await db.execute(select(User).where(User.username == "validrow@example.com"))).scalar_one_or_none()
    assert none_created is None


async def test_bulk_import_commit_creates_users_and_assigns_roles(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/users/bulk-import/commit",
        json={
            "idempotency_key": idem(),
            "rows": [
                {"full_name": "Bulk One", "email": "bulkone@example.com", "role_name": "Operator", "site_code": "T1"},
                {"full_name": "Bulk Two", "email": "bulktwo@example.com", "role_name": "Operator", "site_code": "T1"},
            ],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created_count"] == 2
    # No SMTP configured in the test environment -- send is expected to fail closed (skipped, logged),
    # not raise or block the commit.
    assert body["emails_sent"] == 0

    user_one = (await db.execute(select(User).where(User.username == "bulkone@example.com"))).scalar_one()
    assert user_one.status == "pending_activation"
    role = (await db.execute(select(Role).where(Role.name == "Operator"))).scalar_one()
    assignment = (
        await db.execute(
            select(UserSiteRole).where(
                UserSiteRole.user_id == user_one.id,
                UserSiteRole.site_id == seeded["site_id"],
                UserSiteRole.role_id == role.id,
            )
        )
    ).scalar_one_or_none()
    assert assignment is not None


async def test_bulk_import_commit_rejects_empty_rows(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/users/bulk-import/commit",
        json={"idempotency_key": idem(), "rows": []},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"
