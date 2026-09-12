"""Document 65 (SPEC-SEC-005, KEY-FR-001..028): secret-rotation metadata, PKI certificate lifecycle
(issue/rotate/revoke, each `Released`-signed by an independent QA Releaser per Document 106 rows
137-139), the field-encryption / hash / trust-all crypto library, and the crypto-health self-test.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.mutation.models import OutboxEvent
from app.modules.security import crypto, crypto_commands as commands
from app.modules.security.crypto_models import CertificateMetadata, CryptoProfile, SecretMetadata, SecretValue
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    FieldDecryptionDeniedError,
    MissingSignatureError,
    SecretAccessDeniedError,
    SecretAlreadyExistsError,
    SecretProviderNotIntegratedError,
    SecretValueNotSetError,
    StaleVersionError,
    TrustAllProhibitedError,
    ValidationFailedError,
)
from app.mutation.hashing import sha256_hex
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _user(db, seeded, tag, role="Admin"):
    u = User(username=f"crypto.u{tag}", email=f"crypto.u{tag}@x.com", full_name="Crypto U",
             password_hash=hash_password(DEMO_PASSWORD), status="active")
    db.add(u)
    await db.flush()
    db.add(UserSiteRole(user_id=u.id, site_id=seeded["site_id"], role_id=seeded["roles"][role].id))
    return u


async def _get(db, model, oid):
    async with db.begin():
        return await db.get(model, oid)


async def _seed_secret(db, ref="db/gxp-app", consumers=None):
    s = SecretMetadata(secret_ref=ref, provider="K8S_SECRET", purpose="gxp app DB password",
                       owner="platform-team", consumer_identities=consumers or [], rotation_interval_days=90,
                       state="ACTIVE", version=1)
    db.add(s)
    await db.flush()
    return s


async def _seed_effective_profile(db):
    p = CryptoProfile(
        profile_name="platform-default", tls_baseline={"min_version": "1.2", "disabled": ["TLS1.0", "TLS1.1"]},
        hash_algorithms={"evidence": "SHA-256", "audit_checkpoint": "SHA-256"},
        symmetric_algorithms={"field_encryption": "AES-256-GCM"},
        asymmetric_algorithms={"signing": "ECDSA-P256"}, key_sizes={"rsa": 3072, "ec": "P-256"},
        effective_from=datetime.now(timezone.utc) - timedelta(days=1), state="EFFECTIVE", version=1,
    )
    db.add(p)
    await db.flush()
    return p


async def _cert_challenge(db, signer_id, cert, action):
    """For rotate/revoke the challenge binds to the existing cert id/version; for a signed CREATE
    (issue) pass the IssueServiceCertificateCommand as `cert` and bind to its request hash."""
    if action == "issue":
        from app.modules.security.crypto_commands import issue_request_hash
        return await signature_service.create_challenge(
            db, user_id=signer_id, record_type="certificate", record_id=uuid.uuid4(),
            record_version=1, record_hash=issue_request_hash(cert), meaning="Released",
        )
    return await signature_service.create_challenge(
        db, user_id=signer_id, record_type="certificate", record_id=cert.id,
        record_version=cert.version, record_hash=sha256_hex({"id": str(cert.id), "version": cert.version}),
        meaning="Released",
    )


# =================================================================================================
# rotateSecret() — no signature
# =================================================================================================


@pytest.mark.asyncio
async def test_rotate_secret_bumps_version_and_writes_audit_outbox(db, seeded):
    async with db.begin():
        actor = await _user(db, seeded, "1")
        s = await _seed_secret(db)

    async with db.begin():
        receipt = await commands.rotate_secret(
            db, commands.RotateSecretCommand(idempotency_key=idem(), secret_id=s.id, expected_version=1,
                                             reason="quarterly rotation"), actor.id,
        )
    row = await _get(db, SecretMetadata, s.id)
    assert row.version == 2 and row.state == "ACTIVE" and row.last_rotated_at is not None

    async with db.begin():
        a = await db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.aggregate_id == s.id))
        o = await db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == s.id))
    assert a == 1 and o.event_type == "SecretRotated"

    # stale + missing reason
    async with db.begin():
        with pytest.raises(StaleVersionError):
            await commands.rotate_secret(db, commands.RotateSecretCommand(
                idempotency_key=idem(), secret_id=s.id, expected_version=1, reason="again"), actor.id)
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.rotate_secret(db, commands.RotateSecretCommand(
                idempotency_key=idem(), secret_id=s.id, expected_version=2, reason=""), actor.id)


@pytest.mark.asyncio
async def test_rotate_secret_emergency_carries_incident_ref(db, seeded):
    async with db.begin():
        actor = await _user(db, seeded, "2")
        s = await _seed_secret(db, ref="oauth/erp")
    async with db.begin():
        await commands.rotate_secret(db, commands.RotateSecretCommand(
            idempotency_key=idem(), secret_id=s.id, expected_version=1, reason="credential leak found",
            incident_ref="INC-7788"), actor.id)
    row = await _get(db, SecretMetadata, s.id)
    assert row.incident_ref == "INC-7788"


# =================================================================================================
# createSecret() / setSecretValue() / fetchSecretValue() — SG-126 gap resolution, no signature
# =================================================================================================


@pytest.mark.asyncio
async def test_create_secret_registers_row_and_rejects_duplicate_ref(db, seeded):
    async with db.begin():
        actor = await _user(db, seeded, "cs1")
    async with db.begin():
        receipt = await commands.create_secret(db, commands.CreateSecretCommand(
            idempotency_key=idem(), secret_ref="oauth/lims-new", provider="AWS_SM", purpose="LIMS OAuth secret",
            owner="platform-team", consumer_identities=["svc:lims-adapter"]), actor.id)
    row = await _get(db, SecretMetadata, receipt.aggregate_id)
    assert row.provider == "AWS_SM" and row.state == "ACTIVE" and row.version == 1

    async with db.begin():
        with pytest.raises(SecretAlreadyExistsError):
            await commands.create_secret(db, commands.CreateSecretCommand(
                idempotency_key=idem(), secret_ref="oauth/lims-new", provider="AWS_SM", purpose="dup",
                owner="platform-team"), actor.id)

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.create_secret(db, commands.CreateSecretCommand(
                idempotency_key=idem(), secret_ref="bad", provider="NOT_A_PROVIDER", purpose="x", owner="y"), actor.id)


@pytest.mark.asyncio
async def test_create_secret_on_prem_with_initial_value_is_encrypted_and_fetchable(db, seeded):
    async with db.begin():
        actor = await _user(db, seeded, "cs2")
    async with db.begin():
        receipt = await commands.create_secret(db, commands.CreateSecretCommand(
            idempotency_key=idem(), secret_ref="on-prem/erp-adapter-1", provider="ON_PREM",
            purpose="ERP adapter credential", owner="platform-team", consumer_identities=["svc:erp-adapter"],
            initial_value="s3cr3t-credential"), actor.id)

    # never stored/returned in the clear
    async with db.begin():
        value_row = (await db.execute(select(SecretValue).where(SecretValue.secret_id == receipt.aggregate_id))).scalar_one()
        assert "s3cr3t-credential" not in str(value_row.envelope)

    async with db.begin():
        value = await crypto.fetch_secret_value(
            db, secret_ref="on-prem/erp-adapter-1", service_identity="svc:erp-adapter", purpose="test")
        assert value == b"s3cr3t-credential"

    # wrong consumer identity still fails closed through resolve_secret's own allowlist check
    async with db.begin():
        with pytest.raises(SecretAccessDeniedError):
            await crypto.fetch_secret_value(
                db, secret_ref="on-prem/erp-adapter-1", service_identity="svc:someone-else", purpose="test")


@pytest.mark.asyncio
async def test_create_secret_rejects_initial_value_for_non_on_prem_provider(db, seeded):
    async with db.begin():
        actor = await _user(db, seeded, "cs3")
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.create_secret(db, commands.CreateSecretCommand(
                idempotency_key=idem(), secret_ref="vault/thing", provider="VAULT", purpose="x", owner="y",
                initial_value="oops"), actor.id)


@pytest.mark.asyncio
async def test_fetch_secret_value_fails_closed_for_unintegrated_provider(db, seeded):
    async with db.begin():
        await _seed_secret(db, ref="k8s/thing", consumers=["svc:x"])
    async with db.begin():
        with pytest.raises(SecretProviderNotIntegratedError):
            await crypto.fetch_secret_value(db, secret_ref="k8s/thing", service_identity="svc:x", purpose="test")


@pytest.mark.asyncio
async def test_set_secret_value_creates_then_updates_with_optimistic_concurrency(db, seeded):
    async with db.begin():
        actor = await _user(db, seeded, "sv1")
        receipt = await commands.create_secret(db, commands.CreateSecretCommand(
            idempotency_key=idem(), secret_ref="on-prem/rotatable", provider="ON_PREM", purpose="x",
            owner="platform-team", consumer_identities=["svc:x"]), actor.id)
        secret_id = receipt.aggregate_id

    # no value yet -> SECRET_VALUE_NOT_SET
    async with db.begin():
        with pytest.raises(SecretValueNotSetError):
            await crypto.fetch_secret_value(db, secret_ref="on-prem/rotatable", service_identity="svc:x", purpose="t")

    # first set: expected_version 0 (nothing exists yet)
    async with db.begin():
        await commands.set_secret_value(db, commands.SetSecretValueCommand(
            idempotency_key=idem(), secret_id=secret_id, expected_version=0, value="v1", reason="initial load"), actor.id)
    async with db.begin():
        assert await crypto.fetch_secret_value(db, secret_ref="on-prem/rotatable", service_identity="svc:x", purpose="t") == b"v1"

    # stale expected_version rejected
    async with db.begin():
        with pytest.raises(StaleVersionError):
            await commands.set_secret_value(db, commands.SetSecretValueCommand(
                idempotency_key=idem(), secret_id=secret_id, expected_version=0, value="v2", reason="rotate"), actor.id)

    # correct expected_version updates it
    async with db.begin():
        await commands.set_secret_value(db, commands.SetSecretValueCommand(
            idempotency_key=idem(), secret_id=secret_id, expected_version=1, value="v2", reason="rotate"), actor.id)
    async with db.begin():
        assert await crypto.fetch_secret_value(db, secret_ref="on-prem/rotatable", service_identity="svc:x", purpose="t") == b"v2"


@pytest.mark.asyncio
async def test_set_secret_value_rejects_non_on_prem_provider(db, seeded):
    async with db.begin():
        actor = await _user(db, seeded, "sv2")
        s = await _seed_secret(db, ref="vault/other")  # K8S_SECRET provider from _seed_secret's default
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.set_secret_value(db, commands.SetSecretValueCommand(
                idempotency_key=idem(), secret_id=s.id, expected_version=0, value="x", reason="r"), actor.id)


@pytest.mark.asyncio
async def test_is_registered_secret_distinguishes_managed_from_unmanaged_refs(db, seeded):
    async with db.begin():
        await _seed_secret(db, ref="managed/one")
    async with db.begin():
        assert await crypto.is_registered_secret(db, "managed/one") is True
        assert await crypto.is_registered_secret(db, "totally-unregistered-ref") is False


@pytest.mark.asyncio
async def test_secret_endpoints_rbac_denied_for_unprivileged_user(db, seeded, client):
    async with db.begin():
        await _user(db, seeded, "csop", role="Operator")
    token = await login(client, "crypto.ucsop")
    r = await client.post("/security/v1/secrets", headers=auth_headers(token), json={
        "idempotency_key": idem(), "secret_ref": "x/y", "provider": "ON_PREM", "purpose": "p", "owner": "o",
    })
    assert r.status_code == 403


# =================================================================================================
# issue / rotate / revoke certificate — Released signature (Document 106 rows 137-139)
# =================================================================================================


@pytest.mark.asyncio
async def test_issue_certificate_requires_released_signature(db, seeded):
    # The QA Releaser both invokes and signs (same pattern as Document 63's privileged_session.close);
    # the signature service binds the challenge to the acting user.
    async with db.begin():
        releaser = await _user(db, seeded, "3r", role="QA Releaser")

    issue_cmd = commands.IssueServiceCertificateCommand(
        idempotency_key=idem(), subject_sans={"subject": "svc.gxp", "sans": ["svc.gxp.internal"]},
        profile="SERVICE_MTLS", validity_days=365, issuer_ref="ca:platform-issuing",
        reason="new mTLS identity for gxp-api")

    # No challenge -> fail closed, nothing created.
    async with db.begin():
        with pytest.raises(MissingSignatureError):
            await commands.issue_service_certificate(db, issue_cmd, releaser.id)
    async with db.begin():
        assert (await db.execute(select(CertificateMetadata))).scalars().first() is None

    # Issue for real: challenge binds to the request hash (signed CREATE).
    async with db.begin():
        challenge = await _cert_challenge(db, releaser.id, issue_cmd, "issue")
    async with db.begin():
        receipt = await commands.issue_service_certificate(db, commands.IssueServiceCertificateCommand(
            idempotency_key=idem(), subject_sans={"subject": "svc.gxp", "sans": ["svc.gxp.internal"]},
            profile="SERVICE_MTLS", validity_days=365, issuer_ref="ca:platform-issuing",
            reason="new mTLS identity for gxp-api", challenge_id=challenge.id, reauth_password=DEMO_PASSWORD), releaser.id)
    cert = await _get(db, CertificateMetadata, receipt.aggregate_id)
    assert cert.state == "ACTIVE" and cert.signature_id is not None
    async with db.begin():
        o = await db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == cert.id, OutboxEvent.event_type == "CertificateIssued"))
    assert o is not None

    # bad SAN set is rejected before anything is created
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.issue_service_certificate(db, commands.IssueServiceCertificateCommand(
                idempotency_key=idem(), subject_sans={"subject": "x"}, profile="SERVICE_MTLS",
                validity_days=10, issuer_ref="ca:x", reason="r"), releaser.id)


@pytest.mark.asyncio
async def test_rotate_certificate_overlap_and_revoke(db, seeded):
    async with db.begin():
        admin = await _user(db, seeded, "4")
        releaser = await _user(db, seeded, "4r", role="QA Releaser")
        now = datetime.now(timezone.utc)
        cert = CertificateMetadata(serial="aa" * 16, subject_sans={"subject": "edge-1", "sans": ["edge-1.plant"]},
                                   profile="EDGE_GATEWAY", issued_at=now, expires_at=now + timedelta(days=30),
                                   state="ACTIVE", issuer_ref="ca:edge", version=1)
        db.add(cert)
        await db.flush()

    async with db.begin():
        ch = await _cert_challenge(db, releaser.id, cert, "rotate")
    async with db.begin():
        r = await commands.rotate_certificate(db, commands.RotateCertificateCommand(
            idempotency_key=idem(), certificate_id=cert.id, expected_version=1, validity_days=90,
            reason="scheduled edge cert rotation", challenge_id=ch.id, reauth_password=DEMO_PASSWORD), releaser.id)
    new_cert = await _get(db, CertificateMetadata, r.aggregate_id)
    old_cert = await _get(db, CertificateMetadata, cert.id)
    assert new_cert.state == "ACTIVE" and new_cert.supersedes_id == cert.id
    assert old_cert.state == "ROTATING"  # KEY-FR-009 overlap window, not immediately revoked

    # revoke the old (ROTATING) cert with KEY_COMPROMISE
    async with db.begin():
        ch2 = await _cert_challenge(db, releaser.id, old_cert, "revoke")
    async with db.begin():
        await commands.revoke_certificate(db, commands.RevokeCertificateCommand(
            idempotency_key=idem(), certificate_id=old_cert.id, expected_version=old_cert.version,
            revocation_reason="KEY_COMPROMISE", reason="private key exposed in a log",
            challenge_id=ch2.id, reauth_password=DEMO_PASSWORD), releaser.id)
    revoked = await _get(db, CertificateMetadata, old_cert.id)
    assert revoked.state == "REVOKED" and revoked.revocation_reason == "KEY_COMPROMISE"

    # bad revocation reason
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.revoke_certificate(db, commands.RevokeCertificateCommand(
                idempotency_key=idem(), certificate_id=new_cert.id, expected_version=new_cert.version,
                revocation_reason="NOPE", reason="r"), releaser.id)


# =================================================================================================
# crypto library — resolveSecret / field encryption / hashEvidence / trust-all
# =================================================================================================


@pytest.mark.asyncio
async def test_resolve_secret_enforces_consumer_allowlist(db, seeded):
    async with db.begin():
        await _seed_secret(db, ref="api/lims", consumers=["svc:lims-adapter"])
    async with db.begin():
        ok = await crypto.resolve_secret(db, secret_ref="api/lims", service_identity="svc:lims-adapter", purpose="pull")
        assert ok["resolved"] is True and "value" not in ok
    async with db.begin():
        with pytest.raises(SecretAccessDeniedError):
            await crypto.resolve_secret(db, secret_ref="api/lims", service_identity="svc:erp-adapter", purpose="pull")
    async with db.begin():
        with pytest.raises(SecretAccessDeniedError):
            await crypto.resolve_secret(db, secret_ref="api/nope", service_identity="svc:lims-adapter", purpose="pull")

    # both denials emitted a SecretAccessDenied security-telemetry event (KEY-FR-004/022 / MUT-FR-031).
    async with db.begin():
        n = await db.scalar(select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.event_type == "SecretAccessDenied", OutboxEvent.aggregate_type == "security_event"))
    assert n == 2


def test_field_encryption_round_trip_and_wrong_key_context():
    env = crypto.encrypt_sensitive_field(key_context="tenant-A/complaint", plaintext=b"patient-name", aad=b"complaint:42")
    assert env["algorithm"] == "AES-256-GCM" and "patient-name" not in env["ciphertext"]
    assert crypto.decrypt_sensitive_field(envelope=env, access_context={"key_context": "tenant-A/complaint"}) == b"patient-name"
    # wrong tenant key context -> denied
    with pytest.raises(FieldDecryptionDeniedError):
        crypto.decrypt_sensitive_field(envelope=env, access_context={"key_context": "tenant-B/complaint"})
    # tampered ciphertext -> AEAD failure -> denied
    bad = dict(env, ciphertext=("00" + env["ciphertext"][2:]))
    with pytest.raises(FieldDecryptionDeniedError):
        crypto.decrypt_sensitive_field(envelope=bad)


def test_hash_evidence_records_algorithm_and_rejects_unknown():
    h = crypto.hash_evidence(b"evidence-bytes", algorithm="SHA-256")
    assert h["algorithm"] == "SHA-256" and len(h["digest"]) == 64 and h["digest_bits"] == 256
    with pytest.raises(ValueError):
        crypto.hash_evidence(b"x", algorithm="MD5")


def test_assert_not_trust_all_blocks_accept_all_modes():
    crypto.assert_not_trust_all({"mode": "explicit", "trust_anchors": ["ca:partner-1"]})  # ok
    for bad in ({"mode": "trust_all"}, {"verify": False}, {"trust_anchors": ["*"]}, {"mode": "insecure_skip_verify"}):
        with pytest.raises(TrustAllProhibitedError):
            crypto.assert_not_trust_all(bad)


# =================================================================================================
# crypto-health + module suite (client)
# =================================================================================================


@pytest.mark.asyncio
async def test_crypto_health_503_without_profile_then_200_with_profile(db, seeded, client):
    async with db.begin():
        await _user(db, seeded, "adm")
    token = await login(client, "crypto.uadm")

    # No EFFECTIVE crypto_profile yet -> 503 CRYPTO_HEALTH_FAILED (fail safe, KEY-FR-028)
    r = await client.get("/security/v1/crypto-health", headers=auth_headers(token))
    assert r.status_code == 503 and r.json()["code"] == "CRYPTO_HEALTH_FAILED"

    # the failed self-test emitted a CryptoHealthFailed security-telemetry event (KEY-FR-028 / MUT-FR-031)
    async with db.begin():
        n = await db.scalar(select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.event_type == "CryptoHealthFailed", OutboxEvent.aggregate_type == "security_event"))
    assert n == 1

    async with db.begin():
        await _seed_effective_profile(db)
    r = await client.get("/security/v1/crypto-health", headers=auth_headers(token))
    assert r.status_code == 200 and r.json()["healthy"] is True
    assert r.json()["effective_crypto_profile"] == "platform-default"

    # unauthenticated
    r = await client.get("/security/v1/crypto-health")
    assert r.status_code == 401
    # security headers still present (Doc 64 middleware)
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.asyncio
async def test_module_suite_unprivileged_denied(db, seeded, client):
    async with db.begin():
        await _user(db, seeded, "op", role="Operator")
        s = await _seed_secret(db, ref="db/other")
    token = await login(client, "crypto.uop")
    r = await client.post(f"/security/v1/secrets/{s.id}/rotate", headers=auth_headers(token), json={
        "idempotency_key": idem(), "secret_id": str(s.id), "expected_version": 1, "reason": "x",
    })
    assert r.status_code == 403
