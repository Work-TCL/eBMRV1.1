"""Document 43 (SPEC-EDGE-001) server-side slice: enroll a gateway (SG-118 signature) -> the SG-120
service credential it receives calls observations:batch/health/security-events -> a CRITICAL security
event moves the gateway to SECURITY_HOLD and blocks further ingestion -> certificate rotation (Document
106 row 119 signature, independent of the enrolling actor). The on-prem gateway runtime itself is out of
scope (plan-mode sign-off); every call here is a direct HTTP call against the server API, standing in for
what a real gateway process would send.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.security import hash_password
from app.modules.edge.models import EdgeEnrollmentToken, EdgeGateway, EdgeObservation
from app.modules.iam.models import User, UserSiteRole
from app.mutation.hashing import sha256_hex
from tests.conftest import DEMO_EDGE_BOOTSTRAP_TOKEN, auth_headers, idem, login


async def _make_user(db, seeded, username, role_name):
    user = User(
        username=username, email=f"{username}@example.com", full_name=username,
        password_hash=hash_password("ChangeMe123!"), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


async def _make_admin(db, seeded, username="admin.edge"):
    return await _make_user(db, seeded, username, "Admin")


async def _enroll_gateway(client, admin_token, site_id, *, fingerprint="GW-FINGERPRINT-1", token=DEMO_EDGE_BOOTSTRAP_TOKEN):
    challenge_resp = await client.post(
        "/edge/v1/enrollments/signature-challenges",
        json={"bootstrap_token": token, "gateway_fingerprint": fingerprint},
        headers=auth_headers(admin_token),
    )
    assert challenge_resp.status_code == 200, challenge_resp.text
    challenge_id = challenge_resp.json()["challenge_id"]

    return await client.post(
        "/edge/v1/enrollments",
        json={
            "idempotency_key": idem(), "bootstrap_token": token, "site_id": str(site_id),
            "gateway_fingerprint": fingerprint, "reason": "New plant gateway commissioning",
            "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(admin_token),
    )


async def test_enroll_gateway_issues_service_credential(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")

    resp = await _enroll_gateway(client, admin_token, seeded["site_id"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["gateway_id"]
    assert body["bearer_token"].startswith("sid_")
    assert body["config_endpoint"] == f"/edge/v1/gateways/{body['gateway_id']}/configuration"
    assert body["signature_id"]
    assert body["resulting_version"] == 1

    gateway = await db.get(EdgeGateway, uuid.UUID(body["gateway_id"]))
    assert gateway.lifecycle_state == "ENROLLED"
    assert gateway.certificate_fingerprint == "GW-FINGERPRINT-1"


async def test_enroll_reused_token_rejected(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")

    first = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-A")
    assert first.status_code == 200, first.text

    # The consumed token is rejected as soon as a second challenge/enrollment attempts to use it --
    # whichever surface catches it first, both are the same ENROLLMENT_TOKEN_INVALID resolution.
    second = await client.post(
        "/edge/v1/enrollments/signature-challenges",
        json={"bootstrap_token": DEMO_EDGE_BOOTSTRAP_TOKEN, "gateway_fingerprint": "GW-B"},
        headers=auth_headers(admin_token),
    )
    assert second.status_code == 422
    assert second.json()["code"] == "ENROLLMENT_TOKEN_INVALID"


async def test_enroll_duplicate_fingerprint_rejected(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.edge1")
        await _make_admin(db, seeded, "admin.edge2")
        db.add(
            EdgeEnrollmentToken(
                site_id=seeded["site_id"], token_hash=sha256_hex("second-token"), status="unused",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
    admin1 = await login(client, "admin.edge1")
    admin2 = await login(client, "admin.edge2")

    first = await _enroll_gateway(client, admin1, seeded["site_id"], fingerprint="GW-DUP")
    assert first.status_code == 200, first.text

    second = await _enroll_gateway(client, admin2, seeded["site_id"], fingerprint="GW-DUP", token="second-token")
    assert second.status_code == 409
    assert second.json()["code"] == "DUPLICATE_GATEWAY"


async def test_enroll_without_admin_role_rejected(client, seeded, db):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/edge/v1/enrollments/signature-challenges",
        json={"bootstrap_token": DEMO_EDGE_BOOTSTRAP_TOKEN, "gateway_fingerprint": "GW-X"},
        headers=auth_headers(op_token),
    )
    # Challenge creation itself has no permission gate (matches equipment's signature-challenge
    # endpoints) -- the enrollment command itself is where RBAC is enforced.
    assert resp.status_code == 200, resp.text
    challenge_id = resp.json()["challenge_id"]

    resp = await client.post(
        "/edge/v1/enrollments",
        json={
            "idempotency_key": idem(), "bootstrap_token": DEMO_EDGE_BOOTSTRAP_TOKEN, "site_id": str(seeded["site_id"]),
            "gateway_fingerprint": "GW-X", "reason": "test", "challenge_id": challenge_id,
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_enroll_wrong_password_rejected(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")

    challenge_resp = await client.post(
        "/edge/v1/enrollments/signature-challenges",
        json={"bootstrap_token": DEMO_EDGE_BOOTSTRAP_TOKEN, "gateway_fingerprint": "GW-WRONGPW"},
        headers=auth_headers(admin_token),
    )
    challenge_id = challenge_resp.json()["challenge_id"]

    resp = await client.post(
        "/edge/v1/enrollments",
        json={
            "idempotency_key": idem(), "bootstrap_token": DEMO_EDGE_BOOTSTRAP_TOKEN, "site_id": str(seeded["site_id"]),
            "gateway_fingerprint": "GW-WRONGPW", "reason": "test", "challenge_id": challenge_id,
            "reauth_password": "wrong-password",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 428
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_unauthenticated_enroll_rejected(client, seeded):
    resp = await client.post(
        "/edge/v1/enrollments",
        json={
            "idempotency_key": idem(), "bootstrap_token": DEMO_EDGE_BOOTSTRAP_TOKEN, "site_id": str(seeded["site_id"]),
            "gateway_fingerprint": "GW-NOAUTH", "reason": "test", "challenge_id": str(uuid.uuid4()),
            "reauth_password": "ChangeMe123!",
        },
    )
    assert resp.status_code == 401


async def test_observation_batch_accept_duplicate_and_stale_version(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-OBS")
    gateway_id = enroll_resp.json()["gateway_id"]
    service_token = enroll_resp.json()["bearer_token"]
    service_headers = {"Authorization": f"Bearer {service_token}"}

    event_id = str(uuid.uuid4())
    resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/observations:batch",
        json={
            "idempotency_key": idem(), "expected_version": 1,
            "observations": [
                {"event_id": event_id, "gateway_sequence": 1, "quality": "GOOD", "raw": {"value": "12.3"}}
            ],
        },
        headers=service_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted_event_ids"] == [event_id]
    assert body["duplicate_event_ids"] == []
    assert body["resulting_version"] == 2

    # Same event_id resent (gateway resending an overlapping range after reconnect) -> classified as
    # duplicate, not an error, and does not double-count (EDGE-FR-015/016).
    resp2 = await client.post(
        f"/edge/v1/gateways/{gateway_id}/observations:batch",
        json={
            "idempotency_key": idem(), "expected_version": 2,
            "observations": [
                {"event_id": event_id, "gateway_sequence": 1, "quality": "GOOD", "raw": {"value": "12.3"}}
            ],
        },
        headers=service_headers,
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["duplicate_event_ids"] == [event_id]
    assert resp2.json()["accepted_event_ids"] == []

    # Stale expected_version.
    resp3 = await client.post(
        f"/edge/v1/gateways/{gateway_id}/observations:batch",
        json={"idempotency_key": idem(), "expected_version": 1, "observations": []},
        headers=service_headers,
    )
    assert resp3.status_code == 409
    assert resp3.json()["code"] == "STALE_VERSION"


async def test_observation_batch_wrong_gateway_service_identity_rejected(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
        db.add(
            EdgeEnrollmentToken(
                site_id=seeded["site_id"], token_hash=sha256_hex("second-token"), status="unused",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
    admin_token = await login(client, "admin.edge")
    gw_a = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-A-CRED")
    gw_b = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-B-CRED", token="second-token")

    # Gateway A's credential used against Gateway B's URL -- must be rejected, not silently accepted
    # (BOLA-class control: a gateway's credential authorizes only its own subject_ref).
    resp = await client.post(
        f"/edge/v1/gateways/{gw_b.json()['gateway_id']}/observations:batch",
        json={"idempotency_key": idem(), "expected_version": 1, "observations": []},
        headers={"Authorization": f"Bearer {gw_a.json()['bearer_token']}"},
    )
    assert resp.status_code == 404


async def test_human_token_rejected_on_service_route(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-HUMANTOK")
    gateway_id = enroll_resp.json()["gateway_id"]

    resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/observations:batch",
        json={"idempotency_key": idem(), "expected_version": 1, "observations": []},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 401


async def test_health_report_updates_gateway(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-HEALTH")
    gateway_id = enroll_resp.json()["gateway_id"]
    service_headers = {"Authorization": f"Bearer {enroll_resp.json()['bearer_token']}"}

    resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/health",
        json={
            "idempotency_key": idem(), "expected_version": 1, "operational_state": "RUNNING",
            "metrics": {"outbox_depth": 0}, "cert_expiry_days": 300,
        },
        headers=service_headers,
    )
    assert resp.status_code == 200, resp.text

    gateway = await db.get(EdgeGateway, uuid.UUID(gateway_id))
    assert gateway.last_reported_operational_state == "RUNNING"
    assert gateway.version == 2


async def test_critical_security_event_holds_gateway_and_blocks_ingestion(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-SEC")
    gateway_id = enroll_resp.json()["gateway_id"]
    service_headers = {"Authorization": f"Bearer {enroll_resp.json()['bearer_token']}"}

    resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/security-events",
        json={
            "idempotency_key": idem(), "expected_version": 1, "event_type": "CERT_PIN_MISMATCH",
            "severity": "CRITICAL", "evidence": {"observed_fingerprint": "unexpected"},
        },
        headers=service_headers,
    )
    assert resp.status_code == 200, resp.text

    gateway = await db.get(EdgeGateway, uuid.UUID(gateway_id))
    assert gateway.lifecycle_state == "SECURITY_HOLD"

    blocked = await client.post(
        f"/edge/v1/gateways/{gateway_id}/observations:batch",
        json={"idempotency_key": idem(), "expected_version": 2, "observations": []},
        headers=service_headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "INVALID_TRANSITION"


async def test_certificate_rotation_signed_and_independent(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.edge")
    admin_token = await login(client, "admin.edge")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-CERT")
    gateway_id = enroll_resp.json()["gateway_id"]

    qa_releaser_token = await login(client, "qa.releaser")
    challenge_resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/signature-challenges",
        json={"action": "certificate_rotation"},
        headers=auth_headers(qa_releaser_token),
    )
    assert challenge_resp.status_code == 200, challenge_resp.text
    challenge_id = challenge_resp.json()["challenge_id"]

    resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/certificate-rotation",
        json={
            "idempotency_key": idem(), "expected_version": 1, "new_fingerprint": "GW-CERT-ROTATED",
            "reason": "Scheduled annual rotation", "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"]

    gateway = await db.get(EdgeGateway, uuid.UUID(gateway_id))
    assert gateway.certificate_fingerprint == "GW-CERT-ROTATED"


async def test_certificate_rotation_rejects_enrolling_actor_as_signer(client, seeded, db):
    """Document 106 row 119: the signer must be independent of every production performer on the
    record -- here, the actor who enrolled (approved trust for) this gateway."""
    async with db.begin():
        admin_releaser = await _make_admin(db, seeded, "admin.edge.releaser")
        db.add(UserSiteRole(user_id=admin_releaser.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
    admin_token = await login(client, "admin.edge.releaser")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-SELFSIGN")
    gateway_id = enroll_resp.json()["gateway_id"]

    challenge_resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/signature-challenges",
        json={"action": "certificate_rotation"},
        headers=auth_headers(admin_token),
    )
    challenge_id = challenge_resp.json()["challenge_id"]

    resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/certificate-rotation",
        json={
            "idempotency_key": idem(), "expected_version": 1, "new_fingerprint": "GW-SELFSIGN-2",
            "reason": "test", "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-IDEM")
    gateway_id = enroll_resp.json()["gateway_id"]
    service_headers = {"Authorization": f"Bearer {enroll_resp.json()['bearer_token']}"}

    key = idem()
    payload = {"idempotency_key": key, "expected_version": 1, "operational_state": "RUNNING"}
    first = await client.post(f"/edge/v1/gateways/{gateway_id}/health", json=payload, headers=service_headers)
    second = await client.post(f"/edge/v1/gateways/{gateway_id}/health", json=payload, headers=service_headers)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["command_id"] == second.json()["command_id"]


# ---------------------------------------------------------------------------
# Gap closures: EDGE-FR-012 (TC-043-012-02), cross-site enrollment (TC-043-M04), dependency-outage
# fail-closed / no orphan state (TC-043-M12/M13) -- all real code paths already existed, just not yet
# independently exercised by a dedicated test this pass.
# ---------------------------------------------------------------------------


async def test_observation_batch_rejects_invalid_quality_enum(client, seeded, db):
    """EDGE-FR-012: an out-of-enum quality value is rejected per-envelope (ENVELOPE_INVALID), not
    silently accepted or substituted -- the batch call itself still succeeds (200), and the invalid
    envelope is neither persisted nor counted as accepted."""
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-BADQ")
    gateway_id = enroll_resp.json()["gateway_id"]
    service_headers = {"Authorization": f"Bearer {enroll_resp.json()['bearer_token']}"}

    event_id = str(uuid.uuid4())
    resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/observations:batch",
        json={
            "idempotency_key": idem(), "expected_version": 1,
            "observations": [
                {"event_id": event_id, "gateway_sequence": 1, "quality": "NOT_A_REAL_QUALITY", "raw": {"value": "1"}}
            ],
        },
        headers=service_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted_event_ids"] == []
    assert body["duplicate_event_ids"] == []
    assert body["rejected"] == [{"event_id": event_id, "code": "ENVELOPE_INVALID"}]

    row = await db.get(EdgeObservation, uuid.UUID(event_id))
    assert row is None


async def test_enroll_token_scoped_to_wrong_site_rejected(client, seeded, db):
    """TC-043-M04: a bootstrap token issued for one site cannot enroll a gateway claiming a different
    site -- ENROLLMENT_TOKEN_INVALID (site scoping, EDGE-FR-003)."""
    from app.modules.iam.models import Site

    async with db.begin():
        admin_user = await _make_admin(db, seeded)
        other_site = Site(organization_id=seeded["org_id"], code="T2-EDGE", name="Second Edge Site")
        db.add(other_site)
        await db.flush()
        other_token = EdgeEnrollmentToken(
            site_id=other_site.id, token_hash=sha256_hex("other-site-token"), status="unused",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(other_token)
        db.add(UserSiteRole(user_id=admin_user.id, site_id=other_site.id, role_id=seeded["roles"]["Admin"].id))
        other_site_id = other_site.id
    admin_token = await login(client, "admin.edge")

    # Bootstrap token belongs to other_site_id, but the enrollment command claims seeded["site_id"].
    challenge_resp = await client.post(
        "/edge/v1/enrollments/signature-challenges",
        json={"bootstrap_token": "other-site-token", "gateway_fingerprint": "GW-CROSS-SITE"},
        headers=auth_headers(admin_token),
    )
    assert challenge_resp.status_code == 200, challenge_resp.text
    challenge_id = challenge_resp.json()["challenge_id"]

    resp = await client.post(
        "/edge/v1/enrollments",
        json={
            "idempotency_key": idem(), "bootstrap_token": "other-site-token", "site_id": str(seeded["site_id"]),
            "gateway_fingerprint": "GW-CROSS-SITE", "reason": "Cross-site attempt",
            "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "ENROLLMENT_TOKEN_INVALID"

    # Correctly scoped, the same token/fingerprint succeeds against its own site.
    challenge_resp2 = await client.post(
        "/edge/v1/enrollments/signature-challenges",
        json={"bootstrap_token": "other-site-token", "gateway_fingerprint": "GW-CROSS-SITE"},
        headers=auth_headers(admin_token),
    )
    resp2 = await client.post(
        "/edge/v1/enrollments",
        json={
            "idempotency_key": idem(), "bootstrap_token": "other-site-token", "site_id": str(other_site_id),
            "gateway_fingerprint": "GW-CROSS-SITE", "reason": "Correctly scoped enrollment",
            "challenge_id": challenge_resp2.json()["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(admin_token),
    )
    assert resp2.status_code == 200, resp2.text


async def test_observation_batch_dependency_outage_fails_closed_no_orphan_state(client, seeded, db):
    """TC-043-M12/M13: an outage of the shared Mutation Gateway's audit-write dependency mid-transaction
    fails the whole request closed (no degraded-mode commit) and leaves no orphan state -- neither the
    observation row nor the gateway's version-bump/sequence-advance persist."""
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.edge")
    enroll_resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint="GW-OUTAGE")
    gateway_id = enroll_resp.json()["gateway_id"]
    service_headers = {"Authorization": f"Bearer {enroll_resp.json()['bearer_token']}"}

    event_id = str(uuid.uuid4())
    with patch(
        "app.modules.edge.commands.write_audit_event",
        side_effect=OperationalError("connection lost", None, None),
    ):
        resp = await client.post(
            f"/edge/v1/gateways/{gateway_id}/observations:batch",
            json={
                "idempotency_key": idem(), "expected_version": 1,
                "observations": [
                    {"event_id": event_id, "gateway_sequence": 1, "quality": "GOOD", "raw": {"value": "1"}}
                ],
            },
            headers=service_headers,
        )
    assert resp.status_code >= 400
    assert resp.json()["code"] in ("DEPENDENCY_UNAVAILABLE", "SYSTEM_FAULT")

    row = await db.get(EdgeObservation, uuid.UUID(event_id))
    assert row is None
    gateway = await db.get(EdgeGateway, uuid.UUID(gateway_id))
    assert gateway.last_observation_sequence is None
    assert gateway.version == 1

    # The gateway is not left wedged -- a subsequent, non-failing call at the same expected_version
    # succeeds normally, proving the failed attempt's transaction left no partial trace to reconcile.
    resp2 = await client.post(
        f"/edge/v1/gateways/{gateway_id}/observations:batch",
        json={
            "idempotency_key": idem(), "expected_version": 1,
            "observations": [
                {"event_id": event_id, "gateway_sequence": 1, "quality": "GOOD", "raw": {"value": "1"}}
            ],
        },
        headers=service_headers,
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["accepted_event_ids"] == [event_id]
