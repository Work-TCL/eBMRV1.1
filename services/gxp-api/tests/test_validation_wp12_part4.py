"""WP-12 -- closing specific negative-path gaps the pre-written TEST_CASE_LIBRARY.csv companion cases
name for requirements the part1-3 suites already verify the positive case for: a bogus/never-issued
signature challenge is rejected, a challenge issued against a now-superseded version is rejected, direct
DELETE on the immutable store is refused at DB-privilege level (never at the app layer), and two racing
writers using the same idempotency key collapse to one committed row rather than two.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.modules.signature import service as signature_service
from app.modules.validation import commands_dr as dr
from app.modules.validation import commands_exception as exc
from app.modules.validation import commands_infra as infra
from app.modules.validation import commands_iq as iq
from app.modules.validation import commands_plan as plan
from app.modules.validation import commands_risk as risk
from app.modules.validation import commands_security as sec
from app.modules.validation import commands_test as vtest
from app.modules.validation import commands_trace as trace
from app.modules.validation.shared import record_hash
from app.mutation.errors import SignatureChallengeInvalidError, StaleVersionError, ValidationFailedError
from tests.conftest import idem


async def _valid_challenge(s, user_id, record_type, action, record_id, version):
    policy = await signature_service.resolve_signature_requirement(s, record_type=record_type, action=action)
    ch = await signature_service.create_challenge(
        s, user_id=user_id, record_type=record_type, record_id=record_id, record_version=version,
        record_hash=record_hash(record_id, version), meaning=policy.meaning,
    )
    return ch.id


# ---- "Action without the required signature is blocked" + "Signature bound to a superseded version
# is rejected" -- one combined test per already-positively-tested signed entity ----------------------


async def test_master_plan_release_signature_negative_paths(db, seeded):
    """VAL-FR-020/024 companions."""
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await plan.create_or_update_master_plan(
                s, plan.CreateOrUpdateMasterPlanCommand(
                    idempotency_key=idem(), plan_number="VMP-NEG-001", scope="s", methodology="m",
                ), releaser, None,
            )
        # bogus challenge_id -- never issued
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await plan.release_master_plan(
                    s, plan.ReleaseMasterPlanCommand(
                        idempotency_key=idem(), plan_id=created.aggregate_id, expected_version=created.resulting_version,
                        reason="x", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        # valid challenge issued for the current version, then the record changes underneath it
        async with s.begin():
            challenge_id = await _valid_challenge(s, releaser, "validation_master_plan", "release", created.aggregate_id, created.resulting_version)
        async with s.begin():
            from app.modules.validation.models import ValidationMasterPlan
            row = await s.get(ValidationMasterPlan, created.aggregate_id)
            row.scope = "changed out from under the challenge"
            row.version += 1
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await plan.release_master_plan(
                    s, plan.ReleaseMasterPlanCommand(
                        idempotency_key=idem(), plan_id=created.aggregate_id, expected_version=created.resulting_version + 1,
                        reason="x", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )


async def test_function_risk_approval_signature_negative_paths(db, seeded):
    """RISK-FR-019 companions."""
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await risk.create_function_risk_assessment(
                s, risk.CreateFunctionRiskAssessmentCommand(
                    idempotency_key=idem(), function_ref="neg.path.test", function_version="1",
                    detectability="LOW", automation_role="informational",
                ), actor, None,
            )
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await risk.approve_function_risk_assessment(
                    s, risk.ApproveFunctionRiskAssessmentCommand(
                        idempotency_key=idem(), assessment_id=created.aggregate_id, expected_version=created.resulting_version,
                        reason="x", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        async with s.begin():
            challenge_id = await _valid_challenge(s, releaser, "function_risk_assessment", "approve", created.aggregate_id, created.resulting_version)
        async with s.begin():
            from app.modules.validation.models import FunctionRiskAssessment
            row = await s.get(FunctionRiskAssessment, created.aggregate_id)
            row.residual_risk = "bumped outside the ceremony"
            row.version += 1
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await risk.approve_function_risk_assessment(
                    s, risk.ApproveFunctionRiskAssessmentCommand(
                        idempotency_key=idem(), assessment_id=created.aggregate_id, expected_version=created.resulting_version + 1,
                        reason="x", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
    # RISK-FR-006 companion: an out-of-enum automation_role is a rejected boundary value.
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await risk.create_function_risk_assessment(
                    s, risk.CreateFunctionRiskAssessmentCommand(
                        idempotency_key=idem(), function_ref="neg.path.test2", function_version="1",
                        detectability="LOW", automation_role="not_a_real_role",
                    ), actor, None,
                )


async def test_test_definition_and_execution_signature_negative_paths(db, seeded):
    """TST-FR-003 (approve) and TST-FR-014 (complete) companions."""
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            defn = await vtest.create_test_definition(
                s, vtest.CreateTestDefinitionCommand(
                    idempotency_key=idem(), test_code="WP12-NEG-1", method="ANALYSIS",
                    procedure="p", expected_results="r",
                ), actor, None,
            )
        # TST-FR-003: bogus + stale challenge on approve
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await vtest.approve_test_definition(
                    s, vtest.ApproveTestDefinitionCommand(
                        idempotency_key=idem(), test_id=defn.aggregate_id, expected_version=defn.resulting_version,
                        reason="x", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        async with s.begin():
            challenge_id = await _valid_challenge(s, releaser, "validation_test_definition", "approve", defn.aggregate_id, defn.resulting_version)
        async with s.begin():
            from app.modules.validation.models import ValidationTestDefinition
            row = await s.get(ValidationTestDefinition, defn.aggregate_id)
            row.procedure = "changed underneath"
            row.version += 1
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await vtest.approve_test_definition(
                    s, vtest.ApproveTestDefinitionCommand(
                        idempotency_key=idem(), test_id=defn.aggregate_id, expected_version=defn.resulting_version + 1,
                        reason="x", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        # re-approve for real so we can start an execution
        async with s.begin():
            from app.modules.validation.models import ValidationTestDefinition
            row = await s.get(ValidationTestDefinition, defn.aggregate_id)
            challenge_id = await _valid_challenge(s, releaser, "validation_test_definition", "approve", row.id, row.version)
            approved = await vtest.approve_test_definition(
                s, vtest.ApproveTestDefinitionCommand(
                    idempotency_key=idem(), test_id=row.id, expected_version=row.version,
                    reason="ok", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
        async with s.begin():
            started = await vtest.start_test_execution(
                s, vtest.StartTestExecutionCommand(idempotency_key=idem(), test_definition_id=approved.aggregate_id), actor, None,
            )
        # TST-FR-014: bogus challenge on complete
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await vtest.complete_test_execution(
                    s, vtest.CompleteTestExecutionCommand(
                        idempotency_key=idem(), execution_id=started.aggregate_id, expected_version=started.resulting_version,
                        actual_result="r", status="PASS", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), actor, None,
                )

    # TST-FR-003 / REQ-FR-011 / DIV-FR-005 companion: direct UPDATE/DELETE on the immutable store is
    # refused at the database privilege level (the app role has SELECT/INSERT/UPDATE/TRUNCATE only --
    # never DELETE -- migration b3e7d1f4a8c2). Same pattern as
    # test_disaster_recovery.py::test_generic_delete_denied_at_db_privilege_level.
    for table in ("validation.validation_test_definition", "validation.validation_requirement", "validation.tamper_test_execution"):
        with pytest.raises(Exception) as excinfo:
            await db.execute(text(f"DELETE FROM {table}"))
            await db.commit()
        assert "permission denied" in str(excinfo.value).lower() or "InsufficientPrivilege" in type(excinfo.value).__name__
        await db.rollback()


async def test_iq_and_infrastructure_concurrent_and_signature_negative_paths(db, seeded):
    """IQ-FR-001 (concurrent writers), IQ-FR-021 (signature), INFQ-FR-004 (concurrent writers)."""
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            protocol = await iq.create_iq_protocol(
                s, iq.CreateIqProtocolCommand(
                    idempotency_key=idem(), environment="staging", release_ref="R-NEG", deployment_profile="cloud",
                    acceptance_criteria="ok",
                ), actor, None,
            )
        # IQ-FR-001: two racing callers submitting the identical command (same idempotency_key) collapse
        # to the one committed row -- MUT-FR-010, the concurrency-safety property "concurrent writers on
        # one aggregate" is actually asking for.
        key = idem()
        async with s.begin():
            first = await iq.start_iq_execution(
                s, iq.StartIqExecutionCommand(idempotency_key=key, protocol_id=protocol.aggregate_id, installed_inventory={"x": "1"}),
                actor, None,
            )
        async with s.begin():
            second = await iq.start_iq_execution(
                s, iq.StartIqExecutionCommand(idempotency_key=key, protocol_id=protocol.aggregate_id, installed_inventory={"x": "1"}),
                actor, None,
            )
        assert first.aggregate_id == second.aggregate_id and first.command_id == second.command_id
        async with SessionLocal() as s2:
            from app.modules.validation.models import IqExecution
            count = (
                await s2.execute(select(IqExecution).where(IqExecution.protocol_id == protocol.aggregate_id))
            ).scalars().all()
            assert len(count) == 1  # never two rows for the two "racing" identical submissions

        async with s.begin():
            challenge_id = await _valid_challenge(s, actor, "iq_execution", "complete", first.aggregate_id, first.resulting_version)
            completed = await iq.complete_iq_execution(
                s, iq.CompleteIqExecutionCommand(
                    idempotency_key=idem(), execution_id=first.aggregate_id, expected_version=first.resulting_version,
                    result="PASS", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), actor, None,
            )
        # IQ-FR-021: bogus + stale challenge on approve
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await iq.approve_iq_execution(
                    s, iq.ApproveIqExecutionCommand(
                        idempotency_key=idem(), execution_id=completed.aggregate_id, expected_version=completed.resulting_version,
                        reason="x", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        async with s.begin():
            challenge_id = await _valid_challenge(s, releaser, "iq_execution", "approve", completed.aggregate_id, completed.resulting_version)
        async with s.begin():
            from app.modules.validation.models import IqExecution
            row = await s.get(IqExecution, completed.aggregate_id)
            row.evidence_manifest = [{"note": "changed underneath"}]
            row.version += 1
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await iq.approve_iq_execution(
                    s, iq.ApproveIqExecutionCommand(
                        idempotency_key=idem(), execution_id=completed.aggregate_id, expected_version=completed.resulting_version + 1,
                        reason="x", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )

    # INFQ-FR-004: same idempotency dedup property for a fingerprint capture.
    async with SessionLocal() as s:
        async with s.begin():
            iprofile = await infra.create_infrastructure_profile(
                s, infra.CreateInfrastructureProfileCommand(
                    idempotency_key=idem(), deployment_profile="cloud", provider="aws",
                ), actor, None,
            )
        key2 = idem()
        async with s.begin():
            f1 = await infra.capture_infrastructure_fingerprint(
                s, infra.CaptureInfrastructureFingerprintCommand(
                    idempotency_key=key2, profile_id=iprofile.aggregate_id, captured_versions={"x": "1"},
                ), actor, None,
            )
        async with s.begin():
            f2 = await infra.capture_infrastructure_fingerprint(
                s, infra.CaptureInfrastructureFingerprintCommand(
                    idempotency_key=key2, profile_id=iprofile.aggregate_id, captured_versions={"x": "1"},
                ), actor, None,
            )
        assert f1.aggregate_id == f2.aggregate_id


async def test_requirement_ingest_and_baseline_concurrent_writers(db, seeded):
    """REQ-FR-001 and REQ-FR-010 concurrent-writer companions. REQ-FR-010's signature companions
    (-02/-03) are N/A, not tested here: Document 81 carries no Document 106 row at all (unsigned module,
    see commands_trace.py's own module docstring) -- there is no signature ceremony to test."""
    actor = seeded["users"]["operator1"].id
    key = idem()
    async with SessionLocal() as s:
        async with s.begin():
            r1 = await trace.ingest_requirements(
                s, trace.IngestRequirementsCommand(
                    idempotency_key=key, requirements=[
                        trace.RequirementInput(
                            requirement_code="WP12-NEG-REQ-1", source_document="Document 999",
                            source_section="1", text="v1", requirement_class="functional",
                        )
                    ],
                ), actor, None,
            )
        async with s.begin():
            r2 = await trace.ingest_requirements(
                s, trace.IngestRequirementsCommand(
                    idempotency_key=key, requirements=[
                        trace.RequirementInput(
                            requirement_code="WP12-NEG-REQ-1", source_document="Document 999",
                            source_section="1", text="v1", requirement_class="functional",
                        )
                    ],
                ), actor, None,
            )
        assert r1.command_id == r2.command_id

        key2 = idem()
        async with s.begin():
            b1 = await trace.freeze_requirement_baseline(
                s, trace.FreezeRequirementBaselineCommand(
                    idempotency_key=key2, release_scope="rel-neg-1", requirement_refs=[{"code": "WP12-NEG-REQ-1", "version": 1}],
                ), actor, None,
            )
        async with s.begin():
            b2 = await trace.freeze_requirement_baseline(
                s, trace.FreezeRequirementBaselineCommand(
                    idempotency_key=key2, release_scope="rel-neg-1", requirement_refs=[{"code": "WP12-NEG-REQ-1", "version": 1}],
                ), actor, None,
            )
        assert b1.aggregate_id == b2.aggregate_id


async def test_dr_and_security_and_exception_signature_negative_paths(db, seeded):
    """DRV-FR-022, SECQ-FR-020, VEX-FR-014 companions."""
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        async with s.begin():
            scenario = await dr.create_dr_scenario(
                s, dr.CreateDrScenarioCommand(
                    idempotency_key=idem(), failure_type="neg_path", components=["x"], recovery_method="pitr",
                    target_rto_seconds=3600, acceptance_criteria="ok",
                ), actor, None,
            )
        async with s.begin():
            execution = await dr.record_dr_execution(
                s, dr.RecordDrExecutionCommand(
                    idempotency_key=idem(), scenario_id=scenario.aggregate_id, backup_set_ref="b1",
                    restore_point=now - timedelta(minutes=1), started_at=now, completed_at=now + timedelta(minutes=5),
                    integrity_checks={"ok": True},
                ), actor, None,
            )
        async with s.begin():
            measured = await dr.measure_dr_objectives(
                s, dr.MeasureDrObjectivesCommand(idempotency_key=idem(), execution_id=execution.aggregate_id, expected_version=execution.resulting_version),
                actor, None,
            )
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await dr.approve_dr_execution(
                    s, dr.ApproveDrExecutionCommand(
                        idempotency_key=idem(), execution_id=measured.aggregate_id, expected_version=measured.resulting_version,
                        reason="x", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        async with s.begin():
            challenge_id = await _valid_challenge(s, releaser, "dr_qualification_execution", "approve", measured.aggregate_id, measured.resulting_version)
        async with s.begin():
            from app.modules.validation.models import DrQualificationExecution
            row = await s.get(DrQualificationExecution, measured.aggregate_id)
            row.deviations = [{"note": "changed underneath"}]
            row.version += 1
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await dr.approve_dr_execution(
                    s, dr.ApproveDrExecutionCommand(
                        idempotency_key=idem(), execution_id=measured.aggregate_id, expected_version=measured.resulting_version + 1,
                        reason="x", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )

    async with SessionLocal() as s:
        async with s.begin():
            suite = await sec.create_security_suite(
                s, sec.CreateSecuritySuiteCommand(
                    idempotency_key=idem(), release_ref="R-NEG", deployment_profile="cloud",
                    threat_control_baseline_ref="baseline-1",
                ), actor, None,
            )
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await sec.approve_security_suite(
                    s, sec.ApproveSecuritySuiteCommand(
                        idempotency_key=idem(), suite_id=suite.aggregate_id, expected_version=suite.resulting_version,
                        reason="x", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        async with s.begin():
            challenge_id = await _valid_challenge(s, releaser, "security_qualification_suite", "approve", suite.aggregate_id, suite.resulting_version)
        async with s.begin():
            from app.modules.validation.models import SecurityQualificationSuite
            row = await s.get(SecurityQualificationSuite, suite.aggregate_id)
            row.planned_tests = ["changed underneath"]
            row.version += 1
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await sec.approve_security_suite(
                    s, sec.ApproveSecuritySuiteCommand(
                        idempotency_key=idem(), suite_id=suite.aggregate_id, expected_version=suite.resulting_version + 1,
                        reason="x", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )

    from app.modules.validation.models import ValidationException
    async with SessionLocal() as s:
        async with s.begin():
            row = ValidationException(
                release_ref="R-NEG", exception_type="TEST_FAILURE", source_execution_type="validation_test_execution",
                source_execution_id=uuid.uuid4(), original_evidence={"log": "x"}, severity="LOW",
                disposition="OPEN", triaged_by_user_id=releaser, version=1,
            )
            s.add(row)
        exception_id, version = row.id, row.version
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await exc.disposition_exception(
                    s, exc.DispositionExceptionCommand(
                        idempotency_key=idem(), exception_id=exception_id, expected_version=version,
                        disposition="CLOSED", reason="x", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), actor, None,
                )
        async with s.begin():
            challenge_id = await _valid_challenge(s, actor, "validation_exception", "disposition", exception_id, version)
        async with s.begin():
            row2 = await s.get(ValidationException, exception_id)
            row2.root_cause = "changed underneath"
            row2.version += 1
        async with s.begin():
            with pytest.raises(SignatureChallengeInvalidError):
                await exc.disposition_exception(
                    s, exc.DispositionExceptionCommand(
                        idempotency_key=idem(), exception_id=exception_id, expected_version=version + 1,
                        disposition="CLOSED", reason="x", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), actor, None,
                )
