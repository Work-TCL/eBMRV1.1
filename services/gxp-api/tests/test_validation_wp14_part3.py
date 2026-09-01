"""WP-14 Document 95 (SPEC-VAL-017) -- Validation Summary Report, Release-to-Production & Go-Live
Authorization. Executable evidence for generate -> approve -> authorize -> deployment-check ->
post-go-live, the Document 106 rows 166/167/169 signatures, VSR-FR-013 "known limitations never
omitted", VSR-FR-019 "a condition cannot bypass a critical GxP control", VSR-FR-015 go-live blockers,
VSR-FR-016/022 deployment fingerprint mismatch, VSR-FR-024 controlled rollback on post-go-live
failure, and SoD independence.
"""

import uuid

import pytest

from app.core.db import SessionLocal
from app.modules.signature import service as signature_service
from app.mutation.hashing import sha256_hex
from app.modules.validation import commands_vsr as vsr
from app.modules.validation.models_wp14 import ValidatedReleaseAuthorization, ValidationSummaryReport
from app.modules.validation.shared import record_hash
from app.mutation.errors import (
    DeploymentValidationMismatchError,
    GoLiveNotReadyError,
    InvalidTransitionError,
    PostGoLiveVerificationFailedError,
    StaleVersionError,
    ValidationFailedError,
    ValidationSummaryBlockedError,
)
from tests.conftest import idem


async def _challenge(s, user_id, record_type, action, record_id, version):
    policy = await signature_service.resolve_signature_requirement(s, record_type=record_type, action=action)
    ch = await signature_service.create_challenge(
        s, user_id=user_id, record_type=record_type, record_id=record_id, record_version=version,
        record_hash=record_hash(record_id, version), meaning=policy.meaning,
    )
    return ch.id


_GATES_OK = {k: "PASS" for k in ("training", "production_config", "backups", "interfaces", "support", "monitoring", "cutover_tasks")}


def _gen_cmd(**over):
    base = dict(
        idempotency_key=idem(), report_number=f"VSR-{uuid.uuid4().hex[:8]}",
        release_ref="ebmr@1.4.0", environment="customer-prod", intended_use="regulated eBMR/eDHR manufacturing",
        config_scope="site SITE1 tenant profile v3", evidence_manifest_ref="vault://val-package/1.4.0",
        recommendation="RECOMMENDED", known_limitations=[{"limitation": "none"}],
        dr_summary={"qualified": True, "achieved_rpo": "5m", "achieved_rto": "1h"},
        security_summary={"critical_open": False, "findings": []},
        deviations=[{"ref": "DEV-1", "state": "CLOSED", "critical": False}],
    )
    base.update(over)
    return vsr.GenerateValidationSummaryReportCommand(**base)


async def _generate_and_approve(s, reviewer, releaser, **gen_over):
    gen = await vsr.generate_validation_summary_report(s, _gen_cmd(**gen_over), reviewer, None)
    row = await s.get(ValidationSummaryReport, gen.aggregate_id)
    ch = await _challenge(s, releaser, "validation_summary_report", "approve", row.id, row.version)
    await vsr.approve_validation_summary(
        s, vsr.ApproveValidationSummaryCommand(
            idempotency_key=idem(), report_id=gen.aggregate_id, expected_version=row.version,
            reason="QA approves release", decision="APPROVED", challenge_id=ch, reauth_password="ChangeMe123!",
        ), releaser, None,
    )
    return gen


def _auth_cmd(vsr_id, **over):
    base = dict(
        idempotency_key=idem(), vsr_id=vsr_id, authorization_number=f"VRA-{uuid.uuid4().hex[:8]}",
        environment="customer-prod", config_fingerprint="cfg-sha-abc123",
        release_identity={"image_digest": "sha256:aaa", "code_commit": "deadbeef", "sbom_ref": "sbom://1.4.0",
                          "schema_version": "0082", "migration_head": "c5d9e2f7a1b4", "config_version": "v3"},
        artifact_digests={"gxp-api": "sha256:aaa", "frappe-app": "sha256:bbb"},
        decision="APPROVED", go_live_gates=dict(_GATES_OK), reason="all gates green",
        challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!", production_performer_user_ids=[],
    )
    base.update(over)
    return vsr.IssueValidatedReleaseAuthorizationCommand(**base)


async def _authorize(s, vsr_id, releaser, **over):
    """Build the authorize command, pre-create the signed-CREATE challenge bound to
    sha256(cmd payload) + version 1, then call the command (mirrors what the router does)."""
    cmd = _auth_cmd(vsr_id, **over)
    ch = await signature_service.create_challenge(
        s, user_id=releaser, record_type="validated_release_authorization", record_id=vsr_id,
        record_version=1, record_hash=vsr.create_challenge_hash(cmd), meaning="Released",
    )
    cmd.challenge_id = ch.id
    return await vsr.issue_validated_release_authorization(s, cmd, releaser, None)


# -------------------------------------------------------------------------------------------------

async def test_vsr_generate_requires_known_limitations(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await vsr.generate_validation_summary_report(s, _gen_cmd(known_limitations=[]), reviewer, None)


async def test_vsr_approve_sod_recommender_cannot_approve(db, seeded):
    """VSR-FR-014: the QA approver is independent of the validation recommender."""
    reviewer = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await vsr.generate_validation_summary_report(s, _gen_cmd(), reviewer, None)
        async with s.begin():
            row = await s.get(ValidationSummaryReport, gen.aggregate_id)
            with pytest.raises(ValidationFailedError):
                await vsr.approve_validation_summary(
                    s, vsr.ApproveValidationSummaryCommand(
                        idempotency_key=idem(), report_id=gen.aggregate_id, expected_version=row.version,
                        reason="self approve", decision="APPROVED", challenge_id=uuid.uuid4(),
                        reauth_password="ChangeMe123!",
                    ), reviewer, None,
                )


async def test_vsr_approve_blocked_by_open_critical_deviation(db, seeded):
    """VSR-FR-006: an open critical exception blocks approval."""
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await vsr.generate_validation_summary_report(
                s, _gen_cmd(deviations=[{"ref": "DEV-9", "state": "OPEN", "critical": True}]), reviewer, None
            )
        async with s.begin():
            row = await s.get(ValidationSummaryReport, gen.aggregate_id)
            ch = await _challenge(s, releaser, "validation_summary_report", "approve", row.id, row.version)
            with pytest.raises(ValidationSummaryBlockedError):
                await vsr.approve_validation_summary(
                    s, vsr.ApproveValidationSummaryCommand(
                        idempotency_key=idem(), report_id=gen.aggregate_id, expected_version=row.version,
                        reason="approve", decision="APPROVED", challenge_id=ch, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )


async def test_vsr_approve_conditional_cannot_name_critical_control(db, seeded):
    """VSR-FR-019: a condition cannot bypass a critical GxP control."""
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await vsr.generate_validation_summary_report(s, _gen_cmd(), reviewer, None)
        async with s.begin():
            row = await s.get(ValidationSummaryReport, gen.aggregate_id)
            ch = await _challenge(s, releaser, "validation_summary_report", "approve", row.id, row.version)
            with pytest.raises(ValidationSummaryBlockedError):
                await vsr.approve_validation_summary(
                    s, vsr.ApproveValidationSummaryCommand(
                        idempotency_key=idem(), report_id=gen.aggregate_id, expected_version=row.version,
                        reason="cond", decision="CONDITIONAL",
                        decision_conditions=[{"condition": "skip audit trail review", "names_critical_control": True}],
                        challenge_id=ch, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )


async def test_vsr_authorize_full_and_blocked_variants(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await _generate_and_approve(s, reviewer, releaser)
        # happy path: APPROVED authorization with all gates green
        async with s.begin():
            auth = await _authorize(s, gen.aggregate_id, releaser)
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            assert a.state == "AUTHORIZED" and a.decision == "APPROVED"
            assert a.go_live_readiness["ready"] is True
            assert a.signature_id is not None
        # deployment-check: matching fingerprint + digests -> DEPLOYMENT_VERIFIED
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            ver = a.version
            ch = await _challenge(s, releaser, "validated_release_authorization", "deployment_check", a.id, ver)
        async with s.begin():
            await vsr.verify_deployment_against_validation_release(
                s, vsr.VerifyDeploymentAgainstValidationReleaseCommand(
                    idempotency_key=idem(), authorization_id=auth.aggregate_id, expected_version=ver,
                    submitted_config_fingerprint="cfg-sha-abc123",
                    submitted_artifact_digests={"gxp-api": "sha256:aaa", "frappe-app": "sha256:bbb"},
                    reason="pipeline verified", challenge_id=ch, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            assert a.state == "DEPLOYMENT_VERIFIED"
            ver = a.version
        # post-go-live PASS -> GO_LIVE_VERIFIED
        async with s.begin():
            await vsr.record_post_go_live_verification(
                s, vsr.RecordPostGoLiveVerificationCommand(
                    idempotency_key=idem(), authorization_id=auth.aggregate_id, expected_version=ver,
                    outcome="PASS", smoke_results=[{"check": "login", "ok": True}],
                ), releaser, None,
            )
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            assert a.state == "GO_LIVE_VERIFIED"


async def test_vsr_authorize_blocked_by_go_live_gate(db, seeded):
    """VSR-FR-015: an APPROVED authorization cannot be issued over an unmet go-live prerequisite."""
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await _generate_and_approve(s, reviewer, releaser)
        async with s.begin():
            bad_gates = dict(_GATES_OK)
            bad_gates["backups"] = "no verified backup"
            with pytest.raises(GoLiveNotReadyError):
                await _authorize(s, gen.aggregate_id, releaser, go_live_gates=bad_gates)


async def test_vsr_deployment_check_mismatch_rejected(db, seeded):
    """VSR-FR-016/017/022: a config-fingerprint / digest mismatch fails the technical gate."""
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await _generate_and_approve(s, reviewer, releaser)
        async with s.begin():
            auth = await _authorize(s, gen.aggregate_id, releaser)
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            with pytest.raises(DeploymentValidationMismatchError):
                await vsr.verify_deployment_against_validation_release(
                    s, vsr.VerifyDeploymentAgainstValidationReleaseCommand(
                        idempotency_key=idem(), authorization_id=auth.aggregate_id, expected_version=a.version,
                        submitted_config_fingerprint="cfg-sha-DIFFERENT",
                        submitted_artifact_digests={"gxp-api": "sha256:aaa", "frappe-app": "sha256:bbb"},
                        reason="check", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            assert a.state == "AUTHORIZED"  # unchanged


async def test_vsr_post_go_live_fail_requires_controlled_rollback(db, seeded):
    """VSR-FR-024: a FAIL post-go-live verification must reference a controlled rollback/incident/change."""
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await _generate_and_approve(s, reviewer, releaser)
        async with s.begin():
            auth = await _authorize(s, gen.aggregate_id, releaser)
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            ver = a.version
            ch = await _challenge(s, releaser, "validated_release_authorization", "deployment_check", a.id, ver)
        async with s.begin():
            await vsr.verify_deployment_against_validation_release(
                s, vsr.VerifyDeploymentAgainstValidationReleaseCommand(
                    idempotency_key=idem(), authorization_id=auth.aggregate_id, expected_version=ver,
                    submitted_config_fingerprint="cfg-sha-abc123",
                    submitted_artifact_digests={"gxp-api": "sha256:aaa", "frappe-app": "sha256:bbb"},
                    reason="ok", challenge_id=ch, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            with pytest.raises(PostGoLiveVerificationFailedError):
                await vsr.record_post_go_live_verification(
                    s, vsr.RecordPostGoLiveVerificationCommand(
                        idempotency_key=idem(), authorization_id=auth.aggregate_id, expected_version=a.version,
                        outcome="FAIL", smoke_results=[{"check": "batch create", "ok": False}],
                    ), releaser, None,
                )
        async with s.begin():
            # with a rollback ref it succeeds and moves to ROLLED_BACK
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            await vsr.record_post_go_live_verification(
                s, vsr.RecordPostGoLiveVerificationCommand(
                    idempotency_key=idem(), authorization_id=auth.aggregate_id, expected_version=a.version,
                    outcome="FAIL", rollback_ref="RB-1", incident_ref="INC-1", change_ref="CHG-1",
                ), releaser, None,
            )
        async with s.begin():
            a = await s.get(ValidatedReleaseAuthorization, auth.aggregate_id)
            assert a.state == "ROLLED_BACK"


async def test_vsr_authorize_requires_approved_vsr(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await vsr.generate_validation_summary_report(s, _gen_cmd(), reviewer, None)
        async with s.begin():
            with pytest.raises(InvalidTransitionError):
                await _authorize(s, gen.aggregate_id, releaser)


async def test_vsr_go_live_readiness_pure_eval(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await vsr.generate_validation_summary_report(
                s, _gen_cmd(dr_summary={"qualified": False}), reviewer, None
            )
            v = await s.get(ValidationSummaryReport, gen.aggregate_id)
            readiness = vsr.evaluate_go_live_readiness(v, {"training": "PASS"})
            assert readiness["ready"] is False
            assert "dr_not_qualified" in readiness["blockers"]
            assert "backups" in readiness["blockers"]


async def test_vsr_post_go_live_stale_version(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            gen = await _generate_and_approve(s, reviewer, releaser)
        async with s.begin():
            auth = await _authorize(s, gen.aggregate_id, releaser)
        async with s.begin():
            with pytest.raises((StaleVersionError, InvalidTransitionError)):
                await vsr.record_post_go_live_verification(
                    s, vsr.RecordPostGoLiveVerificationCommand(
                        idempotency_key=idem(), authorization_id=auth.aggregate_id, expected_version=999,
                        outcome="PASS",
                    ), releaser, None,
                )
