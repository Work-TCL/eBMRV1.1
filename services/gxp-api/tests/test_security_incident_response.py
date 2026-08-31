"""Document 67 (SPEC-SEC-007, MON-FR-001..030): security-incident lifecycle — open, allowlisted
containment, forensic evidence with chain-of-custody, GxP-impact assessment, and signed independent
closure (Document 106 row 140). Closure is blocked without the GxP-impact assessment and without a
containment action; the closer must be independent of the incident owner.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.mutation.models import OutboxEvent
from app.modules.security import incident_commands as commands
from app.modules.security.incident_models import ForensicEvidence, SecurityIncident
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    GxpImpactAssessmentRequiredError,
    IncidentContainmentNotAllowedError,
    IncidentEvidenceRequiredError,
    MissingSignatureError,
    SodIndependenceRequiredError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.hashing import sha256_hex
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _user(db, seeded, tag, role="Admin"):
    u = User(username=f"inc.u{tag}", email=f"inc.u{tag}@x.com", full_name="Inc U",
             password_hash=hash_password(DEMO_PASSWORD), status="active")
    db.add(u)
    await db.flush()
    db.add(UserSiteRole(user_id=u.id, site_id=seeded["site_id"], role_id=seeded["roles"][role].id))
    return u


async def _get(db, model, oid):
    async with db.begin():
        return await db.get(model, oid)


async def _open_incident(db, owner_id, severity="HIGH"):
    return await commands.open_security_incident(
        db, commands.OpenSecurityIncidentCommand(
            idempotency_key=idem(), title="suspicious cross-tenant access burst", severity=severity,
            detected_at=datetime.now(timezone.utc), affected_scope={"tenants": ["T1"], "data_classes": ["GXP"]},
            reason="SOC alert triage escalated to incident"),
        owner_id,
    )


@pytest.mark.asyncio
async def test_full_incident_lifecycle_with_signed_close(db, seeded):
    async with db.begin():
        owner = await _user(db, seeded, "1")
        releaser = await _user(db, seeded, "1r", role="QA Releaser")
        r = await _open_incident(db, owner.id)
    inc = await _get(db, SecurityIncident, r.aggregate_id)
    assert inc.state == "OPEN" and inc.gxp_impact_state == "NOT_ASSESSED"
    async with db.begin():
        a = await db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.aggregate_id == inc.id))
        o = await db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == inc.id))
    assert a == 1 and o.event_type == "SecurityIncidentOpened"

    # containment — allowlist enforced
    async with db.begin():
        with pytest.raises(IncidentContainmentNotAllowedError):
            await commands.execute_incident_containment(db, commands.ExecuteIncidentContainmentCommand(
                idempotency_key=idem(), incident_id=inc.id, expected_version=1, containment_command="RM_RF",
                target={}, reason="x"), owner.id)
    async with db.begin():
        await commands.execute_incident_containment(db, commands.ExecuteIncidentContainmentCommand(
            idempotency_key=idem(), incident_id=inc.id, expected_version=1,
            containment_command="REVOKE_SESSIONS", target={"subject_id": str(uuid.uuid4())},
            reason="revoke sessions of the compromised account"), owner.id)
    inc = await _get(db, SecurityIncident, inc.id)
    assert inc.state == "CONTAINED" and len(inc.containment_actions) == 1 and inc.contained_at is not None

    # forensic evidence with chain-of-custody
    async with db.begin():
        ev_r = await commands.preserve_forensic_evidence(db, commands.PreserveForensicEvidenceCommand(
            idempotency_key=idem(), incident_id=inc.id, source="api-gateway access log 2026-08-31",
            acquisition_at=datetime.now(timezone.utc), digest=sha256_hex({"log": "bytes"}),
            custody_note="pulled by IR analyst, hashed at acquisition", reason="preserve access-log evidence"),
            owner.id)
    ev = await _get(db, ForensicEvidence, ev_r.aggregate_id)
    assert ev.chain_of_custody[0]["event"] == "ACQUIRED" and ev.digest

    # cannot close before GxP impact is assessed
    async with db.begin():
        with pytest.raises(GxpImpactAssessmentRequiredError):
            await commands.close_security_incident(db, commands.CloseSecurityIncidentCommand(
                idempotency_key=idem(), incident_id=inc.id, expected_version=inc.version, root_cause="rc",
                corrective_actions=[], residual_risk="low", reason="closing"), releaser.id)

    # assess GxP impact — IMPACT_CONFIRMED requires a qms_reference
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.assess_gxp_incident_impact(db, commands.AssessGxpIncidentImpactCommand(
                idempotency_key=idem(), incident_id=inc.id, expected_version=inc.version,
                impact_state="IMPACT_CONFIRMED", assessment={"records": 3}, reason="assessing"), owner.id)
    async with db.begin():
        await commands.assess_gxp_incident_impact(db, commands.AssessGxpIncidentImpactCommand(
            idempotency_key=idem(), incident_id=inc.id, expected_version=inc.version,
            impact_state="IMPACT_CONFIRMED", assessment={"records": 3}, qms_reference="DEV-2026-114",
            reason="3 batch records viewed cross-tenant"), owner.id)
    inc = await _get(db, SecurityIncident, inc.id)
    assert inc.state == "GXP_IMPACT_ASSESSED" and inc.gxp_impact["qms_reference"] == "DEV-2026-114"

    # close — owner cannot close their own incident (Document 106 row 140 independence, SOD_INDEPENDENCE_REQUIRED)
    async with db.begin():
        with pytest.raises(SodIndependenceRequiredError):
            await commands.close_security_incident(db, commands.CloseSecurityIncidentCommand(
                idempotency_key=idem(), incident_id=inc.id, expected_version=inc.version, root_cause="rc",
                corrective_actions=[{"id": "CAPA-1"}], residual_risk="low", reason="closing"), owner.id)
    # missing signature -> fail closed
    async with db.begin():
        with pytest.raises(MissingSignatureError):
            await commands.close_security_incident(db, commands.CloseSecurityIncidentCommand(
                idempotency_key=idem(), incident_id=inc.id, expected_version=inc.version, root_cause="rc",
                corrective_actions=[{"id": "CAPA-1"}], residual_risk="low", reason="closing"), releaser.id)
    # signed close by an independent QA Releaser
    async with db.begin():
        ch = await signature_service.create_challenge(
            db, user_id=releaser.id, record_type="security_incident", record_id=inc.id,
            record_version=inc.version, record_hash=sha256_hex({"id": str(inc.id), "version": inc.version}),
            meaning="Approved")
    async with db.begin():
        await commands.close_security_incident(db, commands.CloseSecurityIncidentCommand(
            idempotency_key=idem(), incident_id=inc.id, expected_version=inc.version,
            root_cause="over-broad support role granted cross-tenant read", corrective_actions=[{"id": "CAPA-1"}],
            residual_risk="low after role scope fix", reason="incident resolved, CAPA raised",
            challenge_id=ch.id, reauth_password=DEMO_PASSWORD), releaser.id)
    inc = await _get(db, SecurityIncident, inc.id)
    assert inc.state == "CLOSED" and inc.signature_id is not None and inc.closed_at is not None

    # evidence survives closure (Document 67 # 14)
    async with db.begin():
        n = await db.scalar(select(func.count()).select_from(ForensicEvidence).where(ForensicEvidence.incident_id == inc.id))
    assert n == 1


@pytest.mark.asyncio
async def test_close_blocked_without_containment_action(db, seeded):
    async with db.begin():
        owner = await _user(db, seeded, "2")
        releaser = await _user(db, seeded, "2r", role="QA Releaser")
        r = await _open_incident(db, owner.id, severity="MEDIUM")
    inc = await _get(db, SecurityIncident, r.aggregate_id)
    async with db.begin():
        await commands.assess_gxp_incident_impact(db, commands.AssessGxpIncidentImpactCommand(
            idempotency_key=idem(), incident_id=inc.id, expected_version=inc.version, impact_state="NO_IMPACT",
            assessment={"rationale": "no regulated data touched"}, reason="assessed - no impact"), owner.id)
    inc = await _get(db, SecurityIncident, inc.id)
    async with db.begin():
        with pytest.raises(IncidentEvidenceRequiredError):
            await commands.close_security_incident(db, commands.CloseSecurityIncidentCommand(
                idempotency_key=idem(), incident_id=inc.id, expected_version=inc.version, root_cause="rc",
                corrective_actions=[], residual_risk="none", reason="closing"), releaser.id)


@pytest.mark.asyncio
async def test_containment_stale_version_rejected(db, seeded):
    async with db.begin():
        owner = await _user(db, seeded, "3")
        r = await _open_incident(db, owner.id)
    inc = await _get(db, SecurityIncident, r.aggregate_id)
    async with db.begin():
        await commands.execute_incident_containment(db, commands.ExecuteIncidentContainmentCommand(
            idempotency_key=idem(), incident_id=inc.id, expected_version=1, containment_command="ISOLATE_SERVICE",
            target={"service": "gxp-api"}, reason="isolate"), owner.id)
    async with db.begin():
        with pytest.raises(StaleVersionError):
            await commands.execute_incident_containment(db, commands.ExecuteIncidentContainmentCommand(
                idempotency_key=idem(), incident_id=inc.id, expected_version=1, containment_command="BLOCK_INTEGRATION",
                target={"provider": "erp"}, reason="block"), owner.id)


@pytest.mark.asyncio
async def test_module_suite_unauth_and_rbac(db, seeded, client):
    resp = await client.post("/security/v1/incidents", json={
        "idempotency_key": idem(), "title": "x", "severity": "LOW",
        "detected_at": datetime.now(timezone.utc).isoformat(), "reason": "r",
    })
    assert resp.status_code == 401
    async with db.begin():
        n = await db.scalar(select(func.count()).select_from(SecurityIncident))
    assert n == 0

    async with db.begin():
        await _user(db, seeded, "op", role="Operator")
    token = await login(client, "inc.uop")
    resp = await client.post("/security/v1/incidents", headers=auth_headers(token), json={
        "idempotency_key": idem(), "title": "x", "severity": "LOW",
        "detected_at": datetime.now(timezone.utc).isoformat(), "reason": "r",
    })
    assert resp.status_code == 403
