"""Document 68 (SPEC-SEC-008, SDLC-FR-001..034): the vulnerability register (register -> assess ->
exception), the CI security-release-gate + artifact-verification library, and the read-only release
security-evidence endpoint. `approve_vulnerability_exception()` fails closed with
SIGNATURE_POLICY_UNRESOLVED (Document 106 row 141 unresolvable, SG-165 -- same precedent as SG-161).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.mutation.models import OutboxEvent
from app.modules.security import supplychain, supplychain_commands as commands
from app.modules.security.supplychain_models import ReleaseSecurityEvidence, VulnerabilityRecord
from app.mutation.errors import (
    InvalidTransitionError,
    SecurityReleaseBlockedError,
    SignaturePolicyUnresolvedError,
    StaleVersionError,
    UntrustedArtifactError,
    ValidationFailedError,
)
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _user(db, seeded, tag, role="Admin"):
    u = User(username=f"sc.u{tag}", email=f"sc.u{tag}@x.com", full_name="SC U",
             password_hash=hash_password(DEMO_PASSWORD), status="active")
    db.add(u)
    await db.flush()
    db.add(UserSiteRole(user_id=u.id, site_id=seeded["site_id"], role_id=seeded["roles"][role].id))
    return u


async def _get(db, model, oid):
    async with db.begin():
        return await db.get(model, oid)


# =================================================================================================
# vulnerability register -> assess -> exception (fails closed)
# =================================================================================================


@pytest.mark.asyncio
async def test_register_and_assess_vulnerability(db, seeded):
    async with db.begin():
        actor = await _user(db, seeded, "1")
        r = await commands.register_vulnerability(db, commands.RegisterVulnerabilityCommand(
            idempotency_key=idem(), vulnerability_id="CVE-2026-9999", source="SCA",
            component={"name": "left-pad", "version": "1.0.0"}, affected_releases=["2026.8.0"],
            reason="SCA flagged a transitive dependency"), actor.id)
    rec = await _get(db, VulnerabilityRecord, r.aggregate_id)
    assert rec.state == "OPEN" and rec.kev_status is False
    async with db.begin():
        a = await db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.aggregate_id == rec.id))
        o = await db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == rec.id))
    assert a == 1 and o.event_type == "VulnerabilityRegistered"

    async with db.begin():
        await commands.assess_vulnerability_severity(db, commands.AssessVulnerabilitySeverityCommand(
            idempotency_key=idem(), vulnerability_id=rec.id, expected_version=1, severity="HIGH",
            kev_status=True, gxp_impact={"affects": "batch execution import path"},
            remediation_due=datetime.now(timezone.utc) + timedelta(days=7),
            assessment={"cvss": "8.1", "exposure": "internet-facing"}, reason="triaged HIGH + KEV"), actor.id)
    rec = await _get(db, VulnerabilityRecord, rec.id)
    assert rec.state == "ASSESSED" and rec.severity == "HIGH" and rec.kev_status is True

    # bad source / stale version
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.register_vulnerability(db, commands.RegisterVulnerabilityCommand(
                idempotency_key=idem(), vulnerability_id="X", source="MAGIC", component={"name": "x"}, reason="r"), actor.id)
    async with db.begin():
        with pytest.raises(StaleVersionError):
            await commands.assess_vulnerability_severity(db, commands.AssessVulnerabilitySeverityCommand(
                idempotency_key=idem(), vulnerability_id=rec.id, expected_version=1, severity="LOW", kev_status=False,
                gxp_impact={}, remediation_due=datetime.now(timezone.utc) + timedelta(days=1),
                assessment={}, reason="again"), actor.id)


@pytest.mark.asyncio
async def test_approve_vulnerability_exception_fails_closed(db, seeded):
    async with db.begin():
        approver = await _user(db, seeded, "2")
        r = await commands.register_vulnerability(db, commands.RegisterVulnerabilityCommand(
            idempotency_key=idem(), vulnerability_id="CVE-2026-0001", source="CONTAINER_SCAN",
            component={"name": "base-image", "version": "3.19"}, reason="base image finding"), approver.id)
        rec = await db.get(VulnerabilityRecord, r.aggregate_id)
        await commands.assess_vulnerability_severity(db, commands.AssessVulnerabilitySeverityCommand(
            idempotency_key=idem(), vulnerability_id=rec.id, expected_version=1, severity="MEDIUM",
            kev_status=False, gxp_impact={}, remediation_due=datetime.now(timezone.utc) + timedelta(days=30),
            assessment={}, reason="assessed"), approver.id)
    rec = await _get(db, VulnerabilityRecord, r.aggregate_id)

    # Document 106 row 141 role is unresolvable (SG-165) -> fail closed, no state change.
    async with db.begin():
        with pytest.raises(SignaturePolicyUnresolvedError):
            await commands.approve_vulnerability_exception(db, commands.ApproveVulnerabilityExceptionCommand(
                idempotency_key=idem(), vulnerability_id=rec.id, expected_version=rec.version,
                rationale="no fix available yet, low real-world exposure",
                compensating_controls=["network policy blocks the affected path"],
                expiry=datetime.now(timezone.utc) + timedelta(days=60), reason="time-bounded acceptance"), approver.id)
    rec = await _get(db, VulnerabilityRecord, rec.id)
    assert rec.state == "ASSESSED" and rec.exception is None  # unchanged

    # expiry in the past is rejected before the signature step is even reached
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.approve_vulnerability_exception(db, commands.ApproveVulnerabilityExceptionCommand(
                idempotency_key=idem(), vulnerability_id=rec.id, expected_version=rec.version,
                rationale="r", compensating_controls=["c"],
                expiry=datetime.now(timezone.utc) - timedelta(days=1), reason="r"), approver.id)


# =================================================================================================
# CI library — evaluateSecurityReleaseGate / verifyDeploymentArtifact / generateReleaseSBOM
# =================================================================================================


def test_evaluate_security_release_gate():
    # clean -> PASS
    d = supplychain.evaluate_security_release_gate(scan_report={}, open_vulnerabilities=[])
    assert d["result"] == "PASS"

    # a HIGH with no exception -> BLOCK
    vulns = [{"vulnerability_id": "CVE-1", "severity": "HIGH", "state": "ASSESSED"}]
    d = supplychain.evaluate_security_release_gate(scan_report={}, open_vulnerabilities=vulns)
    assert d["result"] == "BLOCK" and d["blocking_findings"][0]["vulnerability_id"] == "CVE-1"

    # same HIGH covered by a valid approved exception -> PASS
    ex = [{"vulnerability_id": "CVE-1", "approved": True,
           "expiry": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()}]
    d = supplychain.evaluate_security_release_gate(scan_report={}, open_vulnerabilities=vulns, accepted_exceptions=ex)
    assert d["result"] == "PASS" and d["accepted_exception_count"] == 1

    # expired exception -> still BLOCK
    ex_expired = [{"vulnerability_id": "CVE-1", "approved": True,
                   "expiry": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}]
    d = supplychain.evaluate_security_release_gate(scan_report={}, open_vulnerabilities=vulns, accepted_exceptions=ex_expired)
    assert d["result"] == "BLOCK"

    # KEV at MEDIUM still blocks
    kev = [{"vulnerability_id": "CVE-2", "severity": "MEDIUM", "kev_status": True, "state": "ASSESSED"}]
    assert supplychain.evaluate_security_release_gate(scan_report={}, open_vulnerabilities=kev)["result"] == "BLOCK"

    # failed control test blocks
    d = supplychain.evaluate_security_release_gate(scan_report={}, open_vulnerabilities=[], control_test_results={"bola_suite": False})
    assert d["result"] == "BLOCK"

    # enforce=True raises
    with pytest.raises(SecurityReleaseBlockedError):
        supplychain.evaluate_security_release_gate(scan_report={"enforce": True}, open_vulnerabilities=vulns)


def test_verify_deployment_artifact():
    approved = {"release_id": "2026.8.0", "artifact_digest": "sha256:abc", "sbom_ref": "sbom:2026.8.0",
                "gate_result": "PASS", "provenance": {"allowed_builders": ["ci://github-actions"]}}
    good = {"digest": "sha256:abc", "sbom_ref": "sbom:2026.8.0", "signature": "sig", "signed_by": "release-key",
            "tag": "v2026.8.0", "provenance": {"builder": "ci://github-actions"}}
    assert supplychain.verify_deployment_artifact(artifact=good, expected_release=approved, trust_roots=["release-key"])["trusted"]

    for bad in (
        {**good, "digest": "sha256:zzz"},          # digest mismatch
        {**good, "signature": None},                # unsigned
        {**good, "signed_by": "rogue-key"},         # untrusted signer
        {**good, "sbom_ref": "sbom:other"},         # SBOM mismatch
        {**good, "tag": "latest", "digest": None},  # mutable tag, no digest
        {**good, "provenance": {"builder": "laptop"}},  # untrusted builder
    ):
        with pytest.raises(UntrustedArtifactError):
            supplychain.verify_deployment_artifact(artifact=bad, expected_release=approved, trust_roots=["release-key"])

    # approved release itself blocked -> untrusted
    with pytest.raises(UntrustedArtifactError):
        supplychain.verify_deployment_artifact(artifact=good, expected_release={**approved, "gate_result": "BLOCK"}, trust_roots=["release-key"])


def test_generate_release_sbom():
    out = supplychain.generate_release_sbom(
        artifact_digest="sha256:abc",
        components=[{"name": "fastapi", "version": "0.115.0", "license": "MIT"},
                    {"name": "sqlalchemy", "version": "2.0.35", "license": "MIT"}],
        build_metadata={"commit": "deadbeef"})
    assert out["component_count"] == 2 and out["sbom"]["bomFormat"] == "CycloneDX" and len(out["sbom_digest"]) == 64


# =================================================================================================
# release security-evidence endpoint + module suite
# =================================================================================================


@pytest.mark.asyncio
async def test_release_security_evidence_endpoint_and_rbac(db, seeded, client):
    async with db.begin():
        await _user(db, seeded, "adm")
        db.add(ReleaseSecurityEvidence(release_id="2026.8.0", commit_sha="deadbeefcafe",
                                       build_provenance={"builder": "ci://github-actions"}, sbom_ref="sbom:2026.8.0",
                                       scan_reports={"sast": "clean"}, gate_result="PASS",
                                       artifact_digest="sha256:abc", signature_ref="sig:release-key"))
        await db.flush()
    token = await login(client, "sc.uadm")

    r = await client.get("/security/v1/releases/2026.8.0/security-evidence", headers=auth_headers(token))
    assert r.status_code == 200 and r.json()["gate_result"] == "PASS"
    r = await client.get("/security/v1/releases/nope/security-evidence", headers=auth_headers(token))
    assert r.status_code == 404
    r = await client.get("/security/v1/releases/2026.8.0/security-evidence")
    assert r.status_code == 401

    async with db.begin():
        await _user(db, seeded, "op", role="Operator")
    optoken = await login(client, "sc.uop")
    r = await client.post("/security/v1/vulnerabilities", headers=auth_headers(optoken), json={
        "idempotency_key": idem(), "vulnerability_id": "CVE-x", "source": "SCA",
        "component": {"name": "x"}, "reason": "r",
    })
    assert r.status_code == 403
