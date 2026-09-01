"""WP-12 Documents 84, 86, 88, 89, 90 (SPEC-VAL-006/008/010/011/012) -- Operational Qualification,
Infrastructure Qualification, Part 11 validation, Data Integrity validation, Interface validation.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.signature import service as signature_service
from app.modules.validation import commands_infra as infra
from app.modules.validation import commands_integrity as integrity
from app.modules.validation import commands_interface as iface
from app.modules.validation import commands_oq as oq
from app.modules.validation import commands_part11 as part11
from app.modules.validation.shared import record_hash
from app.mutation.errors import InvalidTransitionError, ValidationFailedError
from tests.conftest import idem


async def _challenge(s, user_id, record_type, action, record_id, version):
    policy = await signature_service.resolve_signature_requirement(s, record_type=record_type, action=action)
    ch = await signature_service.create_challenge(
        s, user_id=user_id, record_type=record_type, record_id=record_id, record_version=version,
        record_hash=record_hash(record_id, version), meaning=policy.meaning,
    )
    return ch.id


# ---- Document 84: Operational Qualification -------------------------------------------------------


async def test_oq_coverage_basis_points_and_approval_gate(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            suite = await oq.create_oq_suite(
                s, oq.CreateOqSuiteCommand(
                    idempotency_key=idem(), baseline_id=uuid.uuid4(),
                    selected_test_refs=[{"test_ref": "T1"}, {"test_ref": "T2"}, {"test_ref": "T3"}, {"test_ref": "T4"}],
                ), actor, None,
            )
        async with s.begin():
            execution = await oq.record_oq_execution(
                s, oq.RecordOqExecutionCommand(
                    idempotency_key=idem(), suite_id=suite.aggregate_id,
                    executed_test_refs=[
                        {"test_ref": "T1", "result": "PASS"}, {"test_ref": "T2", "result": "PASS"},
                        {"test_ref": "T3", "result": "PASS"}, {"test_ref": "T4", "result": "FAIL"},
                    ],
                ), actor, None,
            )
        async with SessionLocal() as s2:
            cov = await oq.get_oq_coverage(s2, execution.aggregate_id)
            assert cov["coverage_basis_points"] == 7500  # 3/4 = 75.00%
            assert cov["status"] == "FAIL"
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "oq_execution", "approve", execution.aggregate_id, execution.resulting_version)
            approved = await oq.approve_oq_execution(
                s, oq.ApproveOqExecutionCommand(
                    idempotency_key=idem(), execution_id=execution.aggregate_id, expected_version=execution.resulting_version,
                    reason="failure investigated, deviation raised separately", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
        async with s.begin():
            with pytest.raises(InvalidTransitionError):
                # already approved
                await oq.approve_oq_execution(
                    s, oq.ApproveOqExecutionCommand(
                        idempotency_key=idem(), execution_id=execution.aggregate_id, expected_version=approved.resulting_version,
                        reason="again", challenge_id=uuid.uuid4(), reauth_password="x",
                    ), releaser, None,
                )


# ---- Document 86: Infrastructure Qualification ------------------------------------------------------


async def test_infrastructure_drift_blocks_approval_until_resolved(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            profile = await infra.create_infrastructure_profile(
                s, infra.CreateInfrastructureProfileCommand(
                    idempotency_key=idem(), deployment_profile="cloud", provider="aws",
                    required_components=[{"name": "postgres", "version": "16.4"}],
                ), actor, None,
            )
        async with s.begin():
            fingerprint = await infra.capture_infrastructure_fingerprint(
                s, infra.CaptureInfrastructureFingerprintCommand(
                    idempotency_key=idem(), profile_id=profile.aggregate_id, captured_versions={"postgres": "16.2"},
                ), actor, None,
            )
        async with SessionLocal() as s2:
            from app.modules.validation.models import InfrastructureFingerprint
            row = await s2.get(InfrastructureFingerprint, fingerprint.aggregate_id)
            assert row.drift_detected is True
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "infrastructure_fingerprint", "approve", fingerprint.aggregate_id, fingerprint.resulting_version)
            with pytest.raises(InvalidTransitionError):
                await infra.approve_infrastructure_fingerprint(
                    s, infra.ApproveInfrastructureFingerprintCommand(
                        idempotency_key=idem(), fingerprint_id=fingerprint.aggregate_id, expected_version=fingerprint.resulting_version,
                        reason="approve despite drift", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        # re-run control tests against a profile whose requirement now matches -> drift clears
        async with s.begin():
            from app.modules.validation.models import InfrastructureQualificationProfile
            prof_row = await s.get(InfrastructureQualificationProfile, profile.aggregate_id)
            prof_row.required_components = [{"name": "postgres", "version": "16.2"}]
        async with s.begin():
            from app.modules.validation.models import InfrastructureFingerprint
            fp_row = await s.get(InfrastructureFingerprint, fingerprint.aggregate_id)
            reevaluated = await infra.run_infrastructure_control_tests(
                s, infra.RunInfrastructureControlTestsCommand(
                    idempotency_key=idem(), fingerprint_id=fp_row.id, expected_version=fp_row.version,
                ), actor, None,
            )
        async with SessionLocal() as s2:
            from app.modules.validation.models import InfrastructureFingerprint
            row = await s2.get(InfrastructureFingerprint, reevaluated.aggregate_id)
            assert row.drift_detected is False
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "infrastructure_fingerprint", "approve", reevaluated.aggregate_id, reevaluated.resulting_version)
            approved = await infra.approve_infrastructure_fingerprint(
                s, infra.ApproveInfrastructureFingerprintCommand(
                    idempotency_key=idem(), fingerprint_id=reevaluated.aggregate_id, expected_version=reevaluated.resulting_version,
                    reason="drift resolved", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import InfrastructureFingerprint
        row = await s.get(InfrastructureFingerprint, approved.aggregate_id)
        assert row.status == "APPROVED"


# ---- Document 88: Part 11 validation -----------------------------------------------------------------


async def test_part11_assessment_approval_requires_all_controls_pass(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            assessment = await part11.create_part11_scope_assessment(
                s, part11.CreatePart11ScopeAssessmentCommand(
                    idempotency_key=idem(), record_or_signature_type="validation_exception.disposition",
                    predicate_use="quality decision", system_component="validation",
                ), actor, None,
            )
        async with s.begin():
            derived = await part11.derive_part11_test_suite(
                s, part11.DerivePart11TestSuiteCommand(
                    idempotency_key=idem(), assessment_id=assessment.aggregate_id,
                    control_citations=["11.10(e)", "11.50"],
                ), actor, None,
            )
        from app.modules.validation.models import Part11ControlEvidence
        async with SessionLocal() as s2:
            evidence_rows = (
                await s2.execute(select(Part11ControlEvidence).where(Part11ControlEvidence.scope_assessment_id == assessment.aggregate_id))
            ).scalars().all()
            assert len(evidence_rows) == 2
        # approval blocked while one control is unresolved
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "part11_scope_assessment", "approve", assessment.aggregate_id, assessment.resulting_version)
            with pytest.raises(Exception):
                await part11.approve_part11_assessment(
                    s, part11.ApprovePart11AssessmentCommand(
                        idempotency_key=idem(), assessment_id=assessment.aggregate_id, expected_version=assessment.resulting_version,
                        reason="approve early", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        async with s.begin():
            for row in evidence_rows:
                fresh = await s.get(Part11ControlEvidence, row.id)
                await part11.record_part11_control_result(
                    s, part11.RecordPart11ControlResultCommand(
                        idempotency_key=idem(), control_evidence_id=fresh.id, expected_version=fresh.version, result="PASS",
                    ), actor, None,
                )
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "part11_scope_assessment", "approve", assessment.aggregate_id, assessment.resulting_version)
            approved = await part11.approve_part11_assessment(
                s, part11.ApprovePart11AssessmentCommand(
                    idempotency_key=idem(), assessment_id=assessment.aggregate_id, expected_version=assessment.resulting_version,
                    reason="all controls pass", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import Part11ScopeAssessment
        row = await s.get(Part11ScopeAssessment, approved.aggregate_id)
        assert row.state == "QUALIFIED"


# ---- Document 89: Data Integrity validation ------------------------------------------------------


async def test_tamper_test_detected_false_is_a_failure_not_a_pass(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            profile = await integrity.create_data_integrity_profile(
                s, integrity.CreateDataIntegrityProfileCommand(idempotency_key=idem(), data_class="audit_event", lifecycle="append-only"), actor, None,
            )
        async with s.begin():
            undetected = await integrity.record_tamper_test(
                s, integrity.RecordTamperTestCommand(
                    idempotency_key=idem(), profile_id=profile.aggregate_id, isolated_snapshot_ref="snap-1",
                    tamper_action="reorder", verifier_version="v1", detected=False,
                ), actor, None,
            )
        from app.modules.validation.models import TamperTestExecution
        async with SessionLocal() as s2:
            row = await s2.get(TamperTestExecution, undetected.aggregate_id)
            assert row.status == "FAIL"  # a real tamper going undetected is a critical failure
        async with s.begin():
            detected = await integrity.record_tamper_test(
                s, integrity.RecordTamperTestCommand(
                    idempotency_key=idem(), profile_id=profile.aggregate_id, isolated_snapshot_ref="snap-2",
                    tamper_action="delete", verifier_version="v1", detected=True,
                ), actor, None,
            )
        async with s.begin():
            with pytest.raises(InvalidTransitionError):
                challenge_id = await _challenge(s, releaser, "data_integrity_test_profile", "approve", profile.aggregate_id, profile.resulting_version)
                await integrity.approve_data_integrity_profile(
                    s, integrity.ApproveDataIntegrityProfileCommand(
                        idempotency_key=idem(), profile_id=profile.aggregate_id, expected_version=profile.resulting_version,
                        reason="approve with failure", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )


# ---- Document 90: Interface validation -------------------------------------------------------------


async def test_interface_profile_approval_requires_all_scenarios_pass(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            profile = await iface.create_interface_profile(
                s, iface.CreateInterfaceProfileCommand(
                    idempotency_key=idem(), provider_or_device="ERP-SAP", contract_ref="erp-v1", contract_version="1.0",
                    intended_use="post consumption", risk_category="HIGHER-PROCESS-RISK", auth_expectation="mTLS",
                ), actor, None,
            )
        async with s.begin():
            await iface.record_interface_test(
                s, iface.RecordInterfaceTestCommand(idempotency_key=idem(), profile_id=profile.aggregate_id, scenario="duplicate_replay", status="PASS"),
                actor, None,
            )
        async with s.begin():
            await iface.record_edge_outage_test(
                s, iface.RecordEdgeOutageTestCommand(idempotency_key=idem(), profile_id=profile.aggregate_id, status="PASS"), actor, None,
            )
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "interface_validation_profile", "approve", profile.aggregate_id, profile.resulting_version)
            approved = await iface.approve_interface_profile(
                s, iface.ApproveInterfaceProfileCommand(
                    idempotency_key=idem(), profile_id=profile.aggregate_id, expected_version=profile.resulting_version,
                    reason="all scenarios pass", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import InterfaceValidationProfile
        row = await s.get(InterfaceValidationProfile, approved.aggregate_id)
        assert row.state == "QUALIFIED"
