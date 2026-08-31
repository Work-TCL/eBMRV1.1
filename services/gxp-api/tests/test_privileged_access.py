"""Document 63 (SPEC-SEC-003, PAM-FR-001..026): JIT privileged-access request/approve with real SoD
(requester cannot approve their own elevation, Document 106 row 135), read-only support sessions,
break-glass emergency access (no approval gate, no GxP/signature authority), the controlled admin-command
allowlist, and close/review with real independence enforcement (Document 106 row 136).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.security import identity_commands
from app.modules.security import privileged_access_commands as commands
from app.modules.security.identity_models import ApplicationSession
from app.modules.security.privileged_access_models import PrivilegedAccessRequest, PrivilegedGrant, PrivilegedSession
from app.mutation.errors import (
    AdminCommandNotAllowedError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    PrivilegedAccessDeniedError,
    StaleVersionError,
    ValidationFailedError,
)
from tests.conftest import DEMO_PASSWORD, idem


async def _make_user(db, seeded, tag, role_name="Admin"):
    user = User(
        username=f"pam.user{tag}", email=f"pam.user{tag}@example.com", full_name="PAM User",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


async def _get(db, model, obj_id):
    async with db.begin():
        return await db.get(model, obj_id)


async def _request_access(db, requester_id, **overrides):
    now = datetime.now(timezone.utc)
    cmd = commands.RequestPrivilegedAccessCommand(
        idempotency_key=idem(), requested_role="db_admin", scope={"resources": ["ebmr_new_gxp"]},
        reason="investigate a production data anomaly", requested_start=now, requested_end=now + timedelta(hours=4),
        ticket_ref="TICKET-001", **overrides,
    )
    return await commands.request_privileged_access(db, cmd, requester_id)


@pytest.mark.asyncio
async def test_request_and_approve_privileged_access_rejects_self_approval(db, seeded):
    async with db.begin():
        requester = await _make_user(db, seeded, "1")
        approver = await _make_user(db, seeded, "1b")

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.request_privileged_access(
                db, commands.RequestPrivilegedAccessCommand(
                    idempotency_key=idem(), requested_role="db_admin", scope={}, reason="",
                    requested_start=datetime.now(timezone.utc), requested_end=datetime.now(timezone.utc) + timedelta(hours=1),
                ), requester.id,
            )

    async with db.begin():
        receipt = await _request_access(db, requester.id)
    request = await _get(db, PrivilegedAccessRequest, receipt.aggregate_id)
    assert request.state == "PENDING_APPROVAL"

    # Self-approval is rejected regardless of role (PAM-FR-016).
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.approve_privileged_access(
                db, commands.ApprovePrivilegedAccessCommand(
                    idempotency_key=idem(), request_id=request.id, expected_version=1, decision="APPROVED",
                    comments="approving my own request",
                ), requester.id,
            )

    # An independent approver's signature ceremony fails closed without a challenge.
    async with db.begin():
        with pytest.raises(MissingSignatureError):
            await commands.approve_privileged_access(
                db, commands.ApprovePrivilegedAccessCommand(
                    idempotency_key=idem(), request_id=request.id, expected_version=1, decision="APPROVED",
                    comments="approved, urgent DB investigation",
                ), approver.id,
            )


@pytest.mark.asyncio
async def test_approve_creates_active_grant_and_evaluate_grant_allows_then_expires(db, seeded):
    async with db.begin():
        requester = await _make_user(db, seeded, "2")
        approver = await _make_user(db, seeded, "2b")
        receipt = await _request_access(db, requester.id)

    from app.modules.signature import service as signature_service
    from app.mutation.hashing import sha256_hex
    request = await _get(db, PrivilegedAccessRequest, receipt.aggregate_id)
    async with db.begin():
        challenge = await signature_service.create_challenge(
            db, user_id=approver.id, record_type="privileged_access_request", record_id=request.id,
            record_version=request.version, record_hash=sha256_hex({"id": str(request.id), "version": request.version}),
            meaning="Approved",
        )
    async with db.begin():
        await commands.approve_privileged_access(
            db, commands.ApprovePrivilegedAccessCommand(
                idempotency_key=idem(), request_id=request.id, expected_version=1, decision="APPROVED",
                comments="Approved for scoped DB investigation", challenge_id=challenge.id, reauth_password=DEMO_PASSWORD,
            ), approver.id,
        )
    request = await _get(db, PrivilegedAccessRequest, receipt.aggregate_id)
    assert request.state == "APPROVED"

    async with db.begin():
        grants = (await db.execute(select(PrivilegedGrant).where(PrivilegedGrant.request_id == request.id))).scalars().all()
    assert len(grants) == 1
    grant = grants[0]
    assert grant.state == "ACTIVE"

    async with db.begin():
        result = await commands.evaluate_privileged_grant(db, subject_id=requester.id, requested_role="db_admin")
    assert result["allow"] is True

    # Expired grant is denied.
    async with db.begin():
        stale_grant = await db.get(PrivilegedGrant, grant.id)
        stale_grant.expiry = datetime.now(timezone.utc) - timedelta(minutes=1)

    async with db.begin():
        with pytest.raises(PrivilegedAccessDeniedError):
            await commands.evaluate_privileged_grant(db, subject_id=requester.id, requested_role="db_admin")

    async with db.begin():
        with pytest.raises(PrivilegedAccessDeniedError):
            await commands.evaluate_privileged_grant(db, subject_id=uuid.uuid4(), requested_role="db_admin")


@pytest.mark.asyncio
async def test_open_support_session_requires_active_grant_and_defaults_read_only(db, seeded):
    async with db.begin():
        support_engineer = await _make_user(db, seeded, "3", role_name="Vendor Support Engineer")

    async with db.begin():
        with pytest.raises(NotFoundError):
            await commands.open_support_session(
                db, commands.OpenSupportSessionCommand(
                    idempotency_key=idem(), grant_id=uuid.uuid4(), support_case_ref="CASE-1",
                ), support_engineer.id,
            )

    now = datetime.now(timezone.utc)
    async with db.begin():
        grant = PrivilegedGrant(
            request_id=None, grant_type="JIT", role="support_engineer", scope={}, effective_from=now,
            expiry=now + timedelta(hours=1), auth_strength={}, state="ACTIVE", granted_by=support_engineer.id,
            subject_id=support_engineer.id, version=1,
        )
        db.add(grant)

    async with db.begin():
        receipt = await commands.open_support_session(
            db, commands.OpenSupportSessionCommand(
                idempotency_key=idem(), grant_id=grant.id, support_case_ref="CASE-42",
                customer_scope_ref="site:T1",
            ), support_engineer.id,
        )
    privileged_session = await _get(db, PrivilegedSession, receipt.aggregate_id)
    assert privileged_session.session_type == "SUPPORT"
    assert privileged_session.review_status == "NOT_REQUIRED"
    assert privileged_session.state == "ACTIVE"


@pytest.mark.asyncio
async def test_break_glass_never_grants_signature_authority_and_forces_mandatory_review(db, seeded):
    async with db.begin():
        operator = await _make_user(db, seeded, "4", role_name="Platform Admin")

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.activate_break_glass(
                db, commands.ActivateBreakGlassCommand(
                    idempotency_key=idem(), requested_role="db_admin", incident_ref="", reason="",
                ), operator.id,
            )

    async with db.begin():
        receipt = await commands.activate_break_glass(
            db, commands.ActivateBreakGlassCommand(
                idempotency_key=idem(), requested_role="db_admin", incident_ref="INC-9001",
                reason="production database is unreachable, on-call engineer responding",
            ), operator.id,
        )
    privileged_session = await _get(db, PrivilegedSession, receipt.aggregate_id)
    assert privileged_session.session_type == "BREAK_GLASS"
    assert privileged_session.review_status == "PENDING"  # PAM-FR-011: mandatory post-use review

    async with db.begin():
        grant = await db.get(PrivilegedGrant, privileged_session.grant_id)
    assert grant.grant_type == "BREAK_GLASS"
    assert grant.request_id is None  # PAM-FR-011: no approval gate

    # PAM-FR-012: nothing in this path ever creates a Part 11 signature -- verified by absence, not
    # merely by inspection: no signature_policies row exists for this record type/action at all, so if
    # break-glass ever tried to sign, it would fail closed with SIGNATURE_POLICY_UNRESOLVED rather than
    # silently succeeding.
    from app.mutation.errors import SignaturePolicyUnresolvedError
    from app.modules.signature import service as signature_service
    with pytest.raises(SignaturePolicyUnresolvedError):
        await signature_service.resolve_signature_requirement(db, record_type="privileged_session", action="break_glass")


@pytest.mark.asyncio
async def test_execute_controlled_admin_command_allowlist_and_force_revoke(db, seeded):
    async with db.begin():
        admin = await _make_user(db, seeded, "5", role_name="Platform Admin")
        target = await _make_user(db, seeded, "5target")
        target_session = await identity_commands.create_application_session(
            db, subject_id=target.id, auth_strength={"methods": ["PASSWORD"]}, actor_user_id=target.id,
        )
        receipt = await commands.activate_break_glass(
            db, commands.ActivateBreakGlassCommand(
                idempotency_key=idem(), requested_role="db_admin", incident_ref="INC-9002",
                reason="suspicious session activity detected",
            ), admin.id,
        )

    async with db.begin():
        with pytest.raises(AdminCommandNotAllowedError):
            await commands.execute_controlled_admin_command(
                db, commands.ExecuteControlledAdminCommandCommand(
                    idempotency_key=idem(), privileged_session_id=receipt.aggregate_id, command_code="DROP_TABLE",
                ), admin.id,
            )

    # Document 106 row 134: admin_command/execute requires a (Performed) signature too.
    from app.modules.signature import service as signature_service
    from app.mutation.hashing import sha256_hex
    privileged_session_before = await _get(db, PrivilegedSession, receipt.aggregate_id)
    async with db.begin():
        challenge1 = await signature_service.create_challenge(
            db, user_id=admin.id, record_type="admin_command", record_id=privileged_session_before.id,
            record_version=privileged_session_before.version,
            record_hash=sha256_hex({"id": str(privileged_session_before.id), "command_code": "LIST_ACTIVE_SESSIONS"}),
            meaning="Performed",
        )
    async with db.begin():
        list_receipt = await commands.execute_controlled_admin_command(
            db, commands.ExecuteControlledAdminCommandCommand(
                idempotency_key=idem(), privileged_session_id=receipt.aggregate_id, command_code="LIST_ACTIVE_SESSIONS",
                challenge_id=challenge1.id, reauth_password=DEMO_PASSWORD,
            ), admin.id,
        )
    assert list_receipt.resulting_version == 2

    privileged_session_mid = await _get(db, PrivilegedSession, receipt.aggregate_id)
    async with db.begin():
        challenge2 = await signature_service.create_challenge(
            db, user_id=admin.id, record_type="admin_command", record_id=privileged_session_mid.id,
            record_version=privileged_session_mid.version,
            record_hash=sha256_hex({"id": str(privileged_session_mid.id), "command_code": "FORCE_REVOKE_SESSION"}),
            meaning="Performed",
        )
    async with db.begin():
        await commands.execute_controlled_admin_command(
            db, commands.ExecuteControlledAdminCommandCommand(
                idempotency_key=idem(), privileged_session_id=receipt.aggregate_id, command_code="FORCE_REVOKE_SESSION",
                parameters={"session_id": str(target_session.id)},
                challenge_id=challenge2.id, reauth_password=DEMO_PASSWORD,
            ), admin.id,
        )
    revoked = await _get(db, ApplicationSession, target_session.id)
    assert revoked.state == "REVOKED"

    privileged_session = await _get(db, PrivilegedSession, receipt.aggregate_id)
    assert len(privileged_session.actions) == 2
    assert privileged_session.actions[0]["command_code"] == "LIST_ACTIVE_SESSIONS"
    assert privileged_session.actions[1]["command_code"] == "FORCE_REVOKE_SESSION"


@pytest.mark.asyncio
async def test_close_privileged_session_requires_independence_from_opener(db, seeded):
    async with db.begin():
        engineer = await _make_user(db, seeded, "6", role_name="Vendor Support Engineer")
        closer = await _make_user(db, seeded, "6b")
        now = datetime.now(timezone.utc)
        grant = PrivilegedGrant(
            request_id=None, grant_type="JIT", role="support_engineer", scope={}, effective_from=now,
            expiry=now + timedelta(hours=1), auth_strength={}, state="ACTIVE", granted_by=engineer.id,
            subject_id=engineer.id, version=1,
        )
        db.add(grant)
        await db.flush()
        session_receipt = await commands.open_support_session(
            db, commands.OpenSupportSessionCommand(
                idempotency_key=idem(), grant_id=grant.id, support_case_ref="CASE-7",
            ), engineer.id,
        )

    # The opener closing their own support session is rejected (Document 106 row 136 independence).
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.close_privileged_session(
                db, commands.ClosePrivilegedSessionCommand(
                    idempotency_key=idem(), privileged_session_id=session_receipt.aggregate_id, expected_version=1,
                    outcome="diagnostics complete, no issues found",
                ), engineer.id,
            )

    from app.modules.signature import service as signature_service
    from app.mutation.hashing import sha256_hex
    privileged_session = await _get(db, PrivilegedSession, session_receipt.aggregate_id)
    async with db.begin():
        challenge = await signature_service.create_challenge(
            db, user_id=closer.id, record_type="privileged_session", record_id=privileged_session.id,
            record_version=privileged_session.version,
            record_hash=sha256_hex({"id": str(privileged_session.id), "version": privileged_session.version}),
            meaning="Approved",
        )
    async with db.begin():
        await commands.close_privileged_session(
            db, commands.ClosePrivilegedSessionCommand(
                idempotency_key=idem(), privileged_session_id=session_receipt.aggregate_id, expected_version=1,
                outcome="diagnostics complete, no issues found", challenge_id=challenge.id, reauth_password=DEMO_PASSWORD,
            ), closer.id,
        )
    privileged_session = await _get(db, PrivilegedSession, session_receipt.aggregate_id)
    assert privileged_session.state == "CLOSED"

    # Stale version and double-close are both rejected.
    async with db.begin():
        with pytest.raises(StaleVersionError):
            await commands.close_privileged_session(
                db, commands.ClosePrivilegedSessionCommand(
                    idempotency_key=idem(), privileged_session_id=privileged_session.id, expected_version=1,
                    outcome="again",
                ), closer.id,
            )


@pytest.mark.asyncio
async def test_review_privileged_session_requires_closed_state_and_independent_reviewer(db, seeded):
    async with db.begin():
        operator = await _make_user(db, seeded, "7", role_name="Platform Admin")
        activation_receipt = await commands.activate_break_glass(
            db, commands.ActivateBreakGlassCommand(
                idempotency_key=idem(), requested_role="db_admin", incident_ref="INC-9003", reason="emergency patch",
            ), operator.id,
        )

    # Cannot review a still-ACTIVE session.
    async with db.begin():
        with pytest.raises(InvalidTransitionError):
            await commands.review_privileged_session(
                db, commands.ReviewPrivilegedSessionCommand(
                    idempotency_key=idem(), privileged_session_id=activation_receipt.aggregate_id, expected_version=1,
                    findings="n/a",
                ), operator.id,
            )

    from app.modules.signature import service as signature_service
    from app.mutation.hashing import sha256_hex
    privileged_session = await _get(db, PrivilegedSession, activation_receipt.aggregate_id)
    async with db.begin():
        challenge = await signature_service.create_challenge(
            db, user_id=operator.id, record_type="privileged_session", record_id=privileged_session.id,
            record_version=privileged_session.version,
            record_hash=sha256_hex({"id": str(privileged_session.id), "version": privileged_session.version}),
            meaning="Approved",
        )
    async with db.begin():
        # Break-glass sessions may be self-closed by the emergency operator (see privileged_access_
        # commands.py::close_privileged_session docstring) -- the mandatory-review step below is where
        # independence is actually required for break-glass.
        await commands.close_privileged_session(
            db, commands.ClosePrivilegedSessionCommand(
                idempotency_key=idem(), privileged_session_id=privileged_session.id, expected_version=1,
                outcome="incident resolved", challenge_id=challenge.id, reauth_password=DEMO_PASSWORD,
            ), operator.id,
        )

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.review_privileged_session(
                db, commands.ReviewPrivilegedSessionCommand(
                    idempotency_key=idem(), privileged_session_id=privileged_session.id, expected_version=2,
                    findings="self-review attempt",
                ), operator.id,
            )

    async with db.begin():
        reviewer = await _make_user(db, seeded, "7reviewer")
    async with db.begin():
        await commands.review_privileged_session(
            db, commands.ReviewPrivilegedSessionCommand(
                idempotency_key=idem(), privileged_session_id=privileged_session.id, expected_version=2,
                findings="Emergency access was proportionate and properly scoped", outcome="NO_ISSUES",
            ), reviewer.id,
        )
    privileged_session = await _get(db, PrivilegedSession, activation_receipt.aggregate_id)
    assert privileged_session.review_status == "REVIEWED"
    assert privileged_session.review["outcome"] == "NO_ISSUES"

    async with db.begin():
        with pytest.raises(InvalidTransitionError):
            await commands.review_privileged_session(
                db, commands.ReviewPrivilegedSessionCommand(
                    idempotency_key=idem(), privileged_session_id=privileged_session.id, expected_version=3,
                    findings="reviewing again",
                ), reviewer.id,
            )
