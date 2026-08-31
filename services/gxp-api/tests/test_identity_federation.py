"""Document 62 (SPEC-SEC-002, IAMSEC-FR-001..026): identity provider config, external identity mapping,
federated token validation (real HS256 signature/issuer/audience/expiry checks against a locally-generated
test secret -- no live external IdP is reachable from this environment, see
app/modules/security/identity_models.py module docstring), MFA-requirement policy, application sessions
wired into the real `/auth/token` login flow (revocation actually invalidates a live bearer token), and
service-identity provisioning/registry checks.
"""

import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam import commands as iam_commands
from app.modules.iam.models import User, UserSiteRole
from app.modules.security import identity_commands as commands
from app.modules.security.identity_models import ApplicationSession, IdentityProviderConfig, SecurityServiceIdentity
from app.mutation.errors import (
    FreshAuthenticationRequiredError,
    InvalidTransitionError,
    NotFoundError,
    StaleVersionError,
    TokenInvalidError,
    ValidationFailedError,
)
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, tag):
    user = User(
        username=f"idp.admin{tag}", email=f"idp.admin{tag}@example.com", full_name="Identity Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


async def _get(db, model, obj_id):
    async with db.begin():
        return await db.get(model, obj_id)


TEST_SECRET = "test-idp-symmetric-secret-not-a-real-credential"


async def _create_idp(db, owner_id, **overrides):
    cmd = commands.CreateIdentityProviderConfigCommand(
        idempotency_key=idem(), deployment_label="test-deployment", issuer="https://idp.test.invalid",
        protocol="OIDC", trust_metadata={"algorithm": "HS256", "secret": TEST_SECRET, "clock_skew_seconds": 30},
        claim_mapping_version="v1", **overrides,
    )
    return await commands.create_identity_provider_config(db, cmd, owner_id)


def _sign_test_token(*, issuer, audience, subject, expires_in_seconds=300, secret=TEST_SECRET):
    now = int(time.time())
    return jwt.encode(
        {"iss": issuer, "aud": audience, "sub": subject, "iat": now, "exp": now + expires_in_seconds},
        secret, algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_create_identity_provider_config_rejects_bad_protocol_then_succeeds(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "1")

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.create_identity_provider_config(
                db, commands.CreateIdentityProviderConfigCommand(
                    idempotency_key=idem(), deployment_label="x", issuer="https://x.invalid",
                    protocol="NOT_A_PROTOCOL", trust_metadata={"algorithm": "HS256", "secret": "x"},
                    claim_mapping_version="v1",
                ), owner.id,
            )

    async with db.begin():
        receipt = await _create_idp(db, owner.id)
    idp = await _get(db, IdentityProviderConfig, receipt.aggregate_id)
    assert idp.state == "ACTIVE"
    assert idp.protocol == "OIDC"


@pytest.mark.asyncio
async def test_validate_identity_token_real_signature_issuer_audience_expiry_checks(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "2")
        idp_receipt = await _create_idp(db, owner.id)

    good_token = _sign_test_token(issuer="https://idp.test.invalid", audience="ebmr-app", subject="ext-subject-001")
    async with db.begin():
        result = await commands.validate_identity_token(
            db, commands.ValidateIdentityTokenCommand(
                idempotency_key=idem(), identity_provider_config_id=idp_receipt.aggregate_id,
                token=good_token, expected_audience="ebmr-app",
            ),
        )
    assert result["subject"] == "ext-subject-001"
    assert result["issuer"] == "https://idp.test.invalid"

    # Wrong audience.
    wrong_aud_token = _sign_test_token(issuer="https://idp.test.invalid", audience="some-other-app", subject="ext-subject-001")
    async with db.begin():
        with pytest.raises(TokenInvalidError):
            await commands.validate_identity_token(
                db, commands.ValidateIdentityTokenCommand(
                    idempotency_key=idem(), identity_provider_config_id=idp_receipt.aggregate_id,
                    token=wrong_aud_token, expected_audience="ebmr-app",
                ),
            )

    # Wrong issuer.
    wrong_iss_token = _sign_test_token(issuer="https://attacker.invalid", audience="ebmr-app", subject="ext-subject-001")
    async with db.begin():
        with pytest.raises(TokenInvalidError):
            await commands.validate_identity_token(
                db, commands.ValidateIdentityTokenCommand(
                    idempotency_key=idem(), identity_provider_config_id=idp_receipt.aggregate_id,
                    token=wrong_iss_token, expected_audience="ebmr-app",
                ),
            )

    # Expired token (issued to have already expired, beyond the configured 30s clock-skew leeway).
    expired_token = _sign_test_token(issuer="https://idp.test.invalid", audience="ebmr-app", subject="ext-subject-001", expires_in_seconds=-120)
    async with db.begin():
        with pytest.raises(TokenInvalidError):
            await commands.validate_identity_token(
                db, commands.ValidateIdentityTokenCommand(
                    idempotency_key=idem(), identity_provider_config_id=idp_receipt.aggregate_id,
                    token=expired_token, expected_audience="ebmr-app",
                ),
            )

    # Wrong signature (signed with a different secret entirely).
    bad_sig_token = _sign_test_token(issuer="https://idp.test.invalid", audience="ebmr-app", subject="ext-subject-001", secret="not-the-configured-secret")
    async with db.begin():
        with pytest.raises(TokenInvalidError):
            await commands.validate_identity_token(
                db, commands.ValidateIdentityTokenCommand(
                    idempotency_key=idem(), identity_provider_config_id=idp_receipt.aggregate_id,
                    token=bad_sig_token, expected_audience="ebmr-app",
                ),
            )


@pytest.mark.asyncio
async def test_map_external_identity_writes_user_columns_and_rejects_collision(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "3")
        other = await _make_admin(db, seeded, "3b")
        idp_receipt = await _create_idp(db, owner.id)

    async with db.begin():
        await commands.map_external_identity(
            db, commands.MapExternalIdentityCommand(
                idempotency_key=idem(), identity_provider_config_id=idp_receipt.aggregate_id,
                user_id=owner.id, issuer="https://idp.test.invalid", subject="ext-subject-042",
                claims={"groups": ["engineering"]},
            ), owner.id,
        )
    user = await _get(db, User, owner.id)
    assert user.external_issuer == "https://idp.test.invalid"
    assert user.external_subject == "ext-subject-042"
    idp = await _get(db, IdentityProviderConfig, idp_receipt.aggregate_id)
    assert len(idp.identity_mappings) == 1
    assert idp.identity_mappings[0]["subject"] == "ext-subject-042"

    # Same (issuer, subject) pair cannot be bound to a second, different user.
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.map_external_identity(
                db, commands.MapExternalIdentityCommand(
                    idempotency_key=idem(), identity_provider_config_id=idp_receipt.aggregate_id,
                    user_id=other.id, issuer="https://idp.test.invalid", subject="ext-subject-042",
                ), owner.id,
            )

    # Wrong issuer for this provider is rejected.
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.map_external_identity(
                db, commands.MapExternalIdentityCommand(
                    idempotency_key=idem(), identity_provider_config_id=idp_receipt.aggregate_id,
                    user_id=other.id, issuer="https://not-this-provider.invalid", subject="ext-subject-999",
                ), owner.id,
            )


def test_evaluate_mfa_requirement_privileged_vs_standard_role():
    privileged = commands.evaluate_mfa_requirement_sync({"Admin"})
    assert privileged["mfa_required"] is True
    assert "SMS" not in privileged["allowed_methods"]
    assert set(privileged["allowed_methods"]) == {"WEBAUTHN", "TOTP", "IDP_MFA"}

    standard = commands.evaluate_mfa_requirement_sync({"Operator"})
    assert standard["mfa_required"] is False

    high_risk = commands.evaluate_mfa_requirement_sync({"Operator"}, {"risk": "high"})
    assert high_risk["mfa_required"] is True
    assert high_risk["reason"] == "elevated_risk_context"


@pytest.mark.asyncio
async def test_login_creates_session_and_revocation_actually_invalidates_the_token(client, db, seeded):
    async with db.begin():
        await _make_admin(db, seeded, "4")

    token = await login(client, "idp.admin4")
    resp = await client.get("/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text

    # Find the session this login created and confirm it is real, DB-backed and ACTIVE.
    async with db.begin():
        me = await client.get("/auth/me", headers=auth_headers(token))
        user_id = uuid.UUID(me.json()["user_id"])
        active_sessions = (
            await db.execute(select(ApplicationSession).where(ApplicationSession.subject_id == user_id))
        ).scalars().all()
    assert len(active_sessions) == 1
    assert active_sessions[0].state == "ACTIVE"

    # Admin-driven revocation of that session immediately invalidates the still-unexpired JWT.
    async with db.begin():
        admin_row = await db.get(User, user_id)
        await commands.revoke_session(
            db, commands.RevokeSessionCommand(idempotency_key=idem(), session_id=active_sessions[0].id, reason="test revoke"),
            admin_row.id,
        )
    resp = await client.get("/auth/me", headers=auth_headers(token))
    assert resp.status_code == 401

    # Revoking an already-revoked session is an invalid transition, not a silent no-op.
    async with db.begin():
        with pytest.raises(InvalidTransitionError):
            await commands.revoke_session(
                db, commands.RevokeSessionCommand(idempotency_key=idem(), session_id=active_sessions[0].id, reason="again"),
                admin_row.id,
            )


@pytest.mark.asyncio
async def test_logout_revokes_current_session_via_http(client, db, seeded):
    async with db.begin():
        await _make_admin(db, seeded, "5")
    token = await login(client, "idp.admin5")

    resp = await client.post("/auth/logout", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text

    resp = await client.get("/auth/me", headers=auth_headers(token))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_deactivate_user_revokes_all_active_sessions_and_privileged_grants(client, db, seeded):
    from datetime import timedelta
    from app.modules.security.privileged_access_models import PrivilegedGrant

    async with db.begin():
        target = await _make_admin(db, seeded, "6")
        admin = await _make_admin(db, seeded, "6admin")
        now = datetime.now(timezone.utc)
        grant = PrivilegedGrant(
            request_id=None, grant_type="JIT", role="db_admin", scope={}, effective_from=now,
            expiry=now + timedelta(hours=4), auth_strength={}, state="ACTIVE", granted_by=admin.id,
            subject_id=target.id, version=1,
        )
        db.add(grant)

    token = await login(client, "idp.admin6")
    resp = await client.get("/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200

    async with db.begin():
        await iam_commands.deactivate_user(
            db, iam_commands.SetUserStatusCommand(idempotency_key=idem(), user_id=target.id), admin.id,
        )
    resp = await client.get("/auth/me", headers=auth_headers(token))
    assert resp.status_code == 401

    async with db.begin():
        sessions = (await db.execute(select(ApplicationSession).where(ApplicationSession.subject_id == target.id))).scalars().all()
    assert all(s.state == "REVOKED" for s in sessions)
    assert any(s.revoked_reason and "IAMSEC-FR-010" in s.revoked_reason for s in sessions)

    # PAM-FR-025: offboarding also revokes the JIT grant, not only the session.
    async with db.begin():
        revoked_grant = await db.get(PrivilegedGrant, grant.id)
    assert revoked_grant.state == "REVOKED"


@pytest.mark.asyncio
async def test_require_fresh_authentication_fresh_then_stale(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "7")
        session_row = await commands.create_application_session(
            db, subject_id=owner.id, auth_strength={"methods": ["PASSWORD"]}, actor_user_id=owner.id,
        )

    async with db.begin():
        result = await commands.require_fresh_authentication(db, session_row.id, required_age_seconds=3600)
    assert result["fresh"] is True

    async with db.begin():
        stale_session = await db.get(ApplicationSession, session_row.id)
        stale_session.auth_time = datetime.now(timezone.utc) - timedelta(hours=2)

    async with db.begin():
        with pytest.raises(FreshAuthenticationRequiredError):
            await commands.require_fresh_authentication(db, session_row.id, required_age_seconds=60)

    async with db.begin():
        with pytest.raises(FreshAuthenticationRequiredError):
            await commands.require_fresh_authentication(db, uuid.uuid4(), required_age_seconds=60)


@pytest.mark.asyncio
async def test_provision_service_identity_rejects_duplicate_and_bad_auth_method_then_registry_checks(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "8")

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.provision_service_identity(
                db, commands.ProvisionServiceIdentityCommand(
                    idempotency_key=idem(), service_name="lims-adapter", auth_method="NOT_A_METHOD",
                    credential_ref="vault:secret/lims-adapter",
                ), owner.id,
            )

    async with db.begin():
        receipt = await commands.provision_service_identity(
            db, commands.ProvisionServiceIdentityCommand(
                idempotency_key=idem(), service_name="lims-adapter", auth_method="MTLS",
                credential_ref="vault:secret/lims-adapter", allowed_audiences=["gxp-api"], allowed_scopes=["lims.ingest"],
            ), owner.id,
        )
    identity = await _get(db, SecurityServiceIdentity, receipt.aggregate_id)
    assert identity.lifecycle_status == "ACTIVE"

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.provision_service_identity(
                db, commands.ProvisionServiceIdentityCommand(
                    idempotency_key=idem(), service_name="lims-adapter", auth_method="MTLS",
                    credential_ref="vault:secret/lims-adapter-2",
                ), owner.id,
            )

    async with db.begin():
        confirmed = await commands.validate_service_registration(
            db, service_name="lims-adapter", presented_audience="gxp-api", presented_scopes=["lims.ingest"],
        )
    assert confirmed.id == identity.id

    async with db.begin():
        with pytest.raises(TokenInvalidError):
            await commands.validate_service_registration(db, service_name="lims-adapter", presented_audience="wrong-audience")

    async with db.begin():
        with pytest.raises(TokenInvalidError):
            await commands.validate_service_registration(
                db, service_name="lims-adapter", presented_audience="gxp-api", presented_scopes=["lims.ingest", "lims.admin"],
            )

    async with db.begin():
        with pytest.raises(NotFoundError):
            await commands.validate_service_registration(db, service_name="not-registered", presented_audience="gxp-api")


@pytest.mark.asyncio
async def test_revoke_service_identity_stale_version_and_double_revoke_rejected(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "9")
        receipt = await commands.provision_service_identity(
            db, commands.ProvisionServiceIdentityCommand(
                idempotency_key=idem(), service_name="erp-adapter", auth_method="CLIENT_CREDENTIALS",
                credential_ref="vault:secret/erp-adapter",
            ), owner.id,
        )

    async with db.begin():
        with pytest.raises(StaleVersionError):
            await commands.revoke_service_identity(
                db, commands.RevokeServiceIdentityCommand(
                    idempotency_key=idem(), service_identity_id=receipt.aggregate_id, expected_version=99, reason="x",
                ), owner.id,
            )

    async with db.begin():
        await commands.revoke_service_identity(
            db, commands.RevokeServiceIdentityCommand(
                idempotency_key=idem(), service_identity_id=receipt.aggregate_id, expected_version=1, reason="rotation complete",
            ), owner.id,
        )
    identity = await _get(db, SecurityServiceIdentity, receipt.aggregate_id)
    assert identity.lifecycle_status == "REVOKED"

    async with db.begin():
        with pytest.raises(InvalidTransitionError):
            await commands.revoke_service_identity(
                db, commands.RevokeServiceIdentityCommand(
                    idempotency_key=idem(), service_identity_id=receipt.aggregate_id, expected_version=2, reason="again",
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_revoke_user_sessions_bulk_via_http(client, db, seeded):
    async with db.begin():
        target = await _make_admin(db, seeded, "10")
        admin = await _make_admin(db, seeded, "10admin")
    token1 = await login(client, "idp.admin10")
    admin_token = await login(client, "idp.admin10admin")

    resp = await client.post(
        "/security/v1/sessions:revoke-all",
        json={"idempotency_key": idem(), "subject_id": str(target.id), "reason": "security incident response"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resulting_version"] == 1

    resp = await client.get("/auth/me", headers=auth_headers(token1))
    assert resp.status_code == 401
