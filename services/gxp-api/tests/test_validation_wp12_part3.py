"""WP-12 Documents 91, 92, 93, 94, 96 (SPEC-VAL-013/014/015/016/018) -- DR Qualification, Security
Qualification, Performance Qualification, Validation Exception management, Periodic Review/Change
Impact/Validated-State Maintenance.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.signature import service as signature_service
from app.modules.validation import commands_dr as dr
from app.modules.validation import commands_exception as exc
from app.modules.validation import commands_performance as perf
from app.modules.validation import commands_periodic as periodic
from app.modules.validation import commands_security as sec
from app.modules.validation.shared import record_hash
from app.mutation.errors import (
    InvalidTransitionError,
    SecurityReleaseBlockedError,
    ValidationFailedError,
)
from tests.conftest import idem


async def _challenge(s, user_id, record_type, action, record_id, version):
    policy = await signature_service.resolve_signature_requirement(s, record_type=record_type, action=action)
    ch = await signature_service.create_challenge(
        s, user_id=user_id, record_type=record_type, record_id=record_id, record_version=version,
        record_hash=record_hash(record_id, version), meaning=policy.meaning,
    )
    return ch.id


# ---- Document 91: DR Qualification ------------------------------------------------------------------


async def test_dr_qualification_measures_rpo_rto_and_blocks_approval_on_fail(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        async with s.begin():
            scenario = await dr.create_dr_scenario(
                s, dr.CreateDrScenarioCommand(
                    idempotency_key=idem(), failure_type="primary_db_loss", components=["postgres_gxp"],
                    recovery_method="pitr", target_rpo_seconds=0, target_rto_seconds=3600,
                    acceptance_criteria="RPO 0 / RTO <= 1h",
                ), actor, None,
            )
        async with s.begin():
            execution = await dr.record_dr_execution(
                s, dr.RecordDrExecutionCommand(
                    idempotency_key=idem(), scenario_id=scenario.aggregate_id, backup_set_ref="bkp-1",
                    restore_point=now - timedelta(minutes=1), started_at=now, completed_at=now + timedelta(hours=2),
                    integrity_checks={"row_counts_match": True},
                ), actor, None,
            )
        async with s.begin():
            measured = await dr.measure_dr_objectives(
                s, dr.MeasureDrObjectivesCommand(idempotency_key=idem(), execution_id=execution.aggregate_id, expected_version=execution.resulting_version),
                actor, None,
            )
        from app.modules.validation.models import DrQualificationExecution
        async with SessionLocal() as s2:
            row = await s2.get(DrQualificationExecution, measured.aggregate_id)
            assert row.rpo_achieved_seconds == 0  # PITR-targeted restore
            assert row.rto_achieved_seconds == 2 * 3600  # exceeds the 1h target -> FAIL
            assert row.status == "FAIL"
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "dr_qualification_execution", "approve", measured.aggregate_id, measured.resulting_version)
            with pytest.raises(InvalidTransitionError):
                await dr.approve_dr_execution(
                    s, dr.ApproveDrExecutionCommand(
                        idempotency_key=idem(), execution_id=measured.aggregate_id, expected_version=measured.resulting_version,
                        reason="approve anyway", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )


# ---- Document 92: Security Qualification -------------------------------------------------------------


async def test_security_qualification_gate_blocks_on_open_critical_finding(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            suite = await sec.create_security_suite(
                s, sec.CreateSecuritySuiteCommand(
                    idempotency_key=idem(), release_ref="R1", deployment_profile="cloud",
                    threat_control_baseline_ref="docs61-68-v1",
                ), actor, None,
            )
        async with s.begin():
            await sec.import_finding(
                s, sec.ImportFindingCommand(
                    idempotency_key=idem(), suite_id=suite.aggregate_id, source="PENTEST", control_ref="APPSEC-FR-001",
                    severity="CRITICAL",
                ), actor, None,
            )
        async with SessionLocal() as s2:
            gate = await sec.get_security_gate(s2, suite.aggregate_id)
            assert gate["gate_state"] == "BLOCKED"
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "security_qualification_suite", "approve", suite.aggregate_id, suite.resulting_version)
            with pytest.raises(SecurityReleaseBlockedError):
                await sec.approve_security_suite(
                    s, sec.ApproveSecuritySuiteCommand(
                        idempotency_key=idem(), suite_id=suite.aggregate_id, expected_version=suite.resulting_version,
                        reason="release anyway", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        # resolve the finding, then approval succeeds
        async with s.begin():
            from app.modules.validation.models import SecurityQualificationFinding
            finding = (
                await s.execute(select(SecurityQualificationFinding).where(SecurityQualificationFinding.suite_id == suite.aggregate_id))
            ).scalar_one()
            finding.state = "CLOSED"
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "security_qualification_suite", "approve", suite.aggregate_id, suite.resulting_version)
            approved = await sec.approve_security_suite(
                s, sec.ApproveSecuritySuiteCommand(
                    idempotency_key=idem(), suite_id=suite.aggregate_id, expected_version=suite.resulting_version,
                    reason="finding closed", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import SecurityQualificationSuite
        row = await s.get(SecurityQualificationSuite, approved.aggregate_id)
        assert row.state == "QUALIFIED"


# ---- Document 93: Performance Qualification (Document 106 rows 159-161: signed scenario/run/evaluate) --


async def test_performance_scenario_run_evaluate_all_require_signature(db, seeded):
    """Document 106 rows 159-161 sign scenario-create, run-create and evaluate. The two creates use the
    same pre-generated-id ceremony as `qms/signature_support.py::create_qms_signature_challenge_for_new_
    record`: the caller picks the id, binds the challenge to (id, version=1), then passes that same id
    into the command so the inserted row matches what was signed."""
    actor = seeded["users"]["operator1"].id
    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(Exception):  # MISSING_SIGNATURE: wrong password against a real challenge
                new_id = uuid.uuid4()
                policy = await signature_service.resolve_signature_requirement(s, record_type="performance_qualification_scenario", action="create")
                bad_challenge = await signature_service.create_challenge(
                    s, user_id=actor, record_type="performance_qualification_scenario", record_id=new_id,
                    record_version=1, record_hash=record_hash(new_id, 1), meaning=policy.meaning,
                )
                await perf.create_performance_scenario(
                    s, perf.CreatePerformanceScenarioCommand(
                        idempotency_key=idem(), release_ref="R1", environment="staging", load_model={"users": 100},
                        planned_duration_seconds=3600, thresholds={"p95_ms": 500}, new_record_id=new_id,
                        challenge_id=bad_challenge.id, reauth_password="wrong-password",
                    ), actor, None,
                )
        async with s.begin():
            scenario_id = uuid.uuid4()
            policy = await signature_service.resolve_signature_requirement(s, record_type="performance_qualification_scenario", action="create")
            challenge = await signature_service.create_challenge(
                s, user_id=actor, record_type="performance_qualification_scenario", record_id=scenario_id,
                record_version=1, record_hash=record_hash(scenario_id, 1), meaning=policy.meaning,
            )
            scenario = await perf.create_performance_scenario(
                s, perf.CreatePerformanceScenarioCommand(
                    idempotency_key=idem(), release_ref="R1", environment="staging", load_model={"users": 100},
                    planned_duration_seconds=3600, thresholds={"p95_ms": 500}, new_record_id=scenario_id,
                    challenge_id=challenge.id, reauth_password="ChangeMe123!",
                ), actor, None,
            )
        async with s.begin():
            run_id = uuid.uuid4()
            policy = await signature_service.resolve_signature_requirement(s, record_type="performance_run", action="create")
            run_challenge = await signature_service.create_challenge(
                s, user_id=actor, record_type="performance_run", record_id=run_id, record_version=1,
                record_hash=record_hash(run_id, 1), meaning=policy.meaning,
            )
            run = await perf.record_performance_run(
                s, perf.RecordPerformanceRunCommand(
                    idempotency_key=idem(), scenario_id=scenario.aggregate_id, build_ref="build-1", harness_ref="k6",
                    started_at=now, completed_at=now + timedelta(minutes=10), metrics={"p95_ms": 650},
                    new_record_id=run_id, challenge_id=run_challenge.id, reauth_password="ChangeMe123!",
                ), actor, None,
            )
        async with s.begin():
            challenge_id = await _challenge(s, actor, "performance_run", "evaluate", run.aggregate_id, run.resulting_version)
            evaluated = await perf.evaluate_performance_run(
                s, perf.EvaluatePerformanceRunCommand(
                    idempotency_key=idem(), run_id=run.aggregate_id, expected_version=run.resulting_version,
                    challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), actor, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import PerformanceRun
        row = await s.get(PerformanceRun, evaluated.aggregate_id)
        assert row.acceptance_result == "FAIL"  # p95_ms 650 > threshold 500


# ---- Document 94: Validation Exception Management (SG-167 resolved: create/triage/retest-plan signed
# `Approved` by an independent QA Releaser) --------------------------------------------------------------


async def test_exception_create_signed_by_independent_releaser_sg167_resolved(db, seeded):
    """Document 106 row 162, now resolved: QA Releaser signs create, independent of requested_by_user_id."""
    requester = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    new_id = uuid.uuid4()
    async with SessionLocal() as s:
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "validation_exception", "create", new_id, 1)
            receipt = await exc.create_exception(
                s, exc.CreateExceptionCommand(
                    idempotency_key=idem(), exception_type="TEST_FAILURE", source_execution_type="validation_test_execution",
                    source_execution_id=uuid.uuid4(), original_evidence={"log": "failure"}, severity="HIGH",
                    requested_by_user_id=requester, new_record_id=new_id,
                    challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    assert receipt.aggregate_id == new_id
    assert receipt.signature_id is not None
    async with SessionLocal() as s:
        from app.modules.validation.models import ValidationException
        row = await s.get(ValidationException, new_id)
        assert row.requested_by_user_id == requester


async def test_exception_create_rejects_signer_same_as_requester(db, seeded):
    """Independence check fires before any DB row is committed -- signer cannot also be the requester."""
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await exc.create_exception(
                    s, exc.CreateExceptionCommand(
                        idempotency_key=idem(), exception_type="TEST_FAILURE", source_execution_type="validation_test_execution",
                        source_execution_id=uuid.uuid4(), original_evidence={"log": "failure"}, severity="HIGH",
                        requested_by_user_id=actor, challenge_id=uuid.uuid4(), reauth_password="x",
                    ), actor, None,
                )


async def test_exception_triage_and_retest_plan_require_independent_releaser_signature(db, seeded):
    """Document 106 rows 164/165, now resolved: same independence rule applies to triage and retest-plan,
    checked against the exception's own requested_by_user_id (captured once at create time)."""
    requester = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    from app.modules.validation.models import ValidationException
    async with SessionLocal() as s:
        async with s.begin():
            row = ValidationException(
                release_ref="R-SG167", exception_type="TEST_FAILURE", source_execution_type="validation_test_execution",
                source_execution_id=uuid.uuid4(), original_evidence={"log": "failure"}, severity="HIGH",
                requested_by_user_id=requester, disposition="OPEN", version=1,
            )
            s.add(row)
        exception_id, version = row.id, row.version

    # The requester themself cannot triage/retest-plan their own exception (not independent).
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await exc.triage_exception(
                    s, exc.TriageExceptionCommand(
                        idempotency_key=idem(), exception_id=exception_id, expected_version=version,
                        severity="HIGH", gxp_impact=True, release_impact="BLOCKING",
                        challenge_id=uuid.uuid4(), reauth_password="x",
                    ), requester, None,
                )

    # An independent QA Releaser succeeds.
    async with SessionLocal() as s:
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "validation_exception", "triage", exception_id, version)
            triaged = await exc.triage_exception(
                s, exc.TriageExceptionCommand(
                    idempotency_key=idem(), exception_id=exception_id, expected_version=version,
                    severity="CRITICAL", gxp_impact=True, release_impact="BLOCKING", root_cause="root cause text",
                    challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    assert triaged.signature_id is not None
    async with SessionLocal() as s:
        row = await s.get(ValidationException, exception_id)
        # VEX-FR-010 (Root cause): captured on the triage action.
        assert row.root_cause == "root cause text" and row.triaged_by_user_id == releaser

    async with SessionLocal() as s:
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "validation_exception", "retest_plan", exception_id, triaged.resulting_version)
            defined = await exc.define_retest_scope(
                s, exc.DefineRetestScopeCommand(
                    idempotency_key=idem(), exception_id=exception_id, expected_version=triaged.resulting_version,
                    retest_plan={"scope": "rerun TC-082-014"}, fix_ref="CAPA-2026-001",
                    challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    assert defined.signature_id is not None
    async with SessionLocal() as s:
        row = await s.get(ValidationException, exception_id)
        # VEX-FR-011 (Fix link): correction/change reference is linked onto the exception record.
        assert row.issue_ref == "CAPA-2026-001"
        # VEX-FR-012 (Retest scope): disposition routes to RETEST once a plan is defined.
        assert row.disposition == "RETEST" and row.retest_plan == {"scope": "rerun TC-082-014"}


async def test_exception_disposition_resolves_and_requires_independence(db, seeded):
    """Document 106 row 163 resolves for real (unlike create/triage/retest-plan) -- inserted directly
    since createException() itself is blocked by SG-167 (see the test above)."""
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    from app.modules.validation.models import ValidationException
    async with SessionLocal() as s:
        async with s.begin():
            row = ValidationException(
                release_ref="R1", exception_type="TEST_FAILURE", source_execution_type="validation_test_execution",
                source_execution_id=uuid.uuid4(), original_evidence={"log": "failure"}, severity="HIGH",
                disposition="OPEN", triaged_by_user_id=releaser, version=1,
            )
            s.add(row)
        exception_id, version = row.id, row.version
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "validation_exception", "disposition", exception_id, version)
            with pytest.raises(ValidationFailedError):
                # releaser is also the triager -- must fail independence
                await exc.disposition_exception(
                    s, exc.DispositionExceptionCommand(
                        idempotency_key=idem(), exception_id=exception_id, expected_version=version,
                        disposition="ACCEPTED_WITH_RATIONALE", residual_risk_rationale="low impact",
                        reason="accepting", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )
        async with s.begin():
            challenge_id = await _challenge(s, actor, "validation_exception", "disposition", exception_id, version)
            dispositioned = await exc.disposition_exception(
                s, exc.DispositionExceptionCommand(
                    idempotency_key=idem(), exception_id=exception_id, expected_version=version,
                    disposition="ACCEPTED_WITH_RATIONALE", residual_risk_rationale="low impact, documented",
                    reason="accepting residual risk", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), actor, None,
            )
    async with SessionLocal() as s:
        gate = await exc.get_exception_gate(s, "R1")
        assert exception_id.__str__() in gate["accepted_with_rationale"]
        assert gate["gate_state"] == "PASSED"


# ---- Document 96: Periodic Review, Change Impact, Validated-State Maintenance --------------------------


async def test_change_impact_and_revalidation_lifecycle(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            impact = await periodic.create_change_impact(
                s, periodic.CreateChangeImpactCommand(
                    idempotency_key=idem(), change_ref="CHG-1", change_type="config",
                    revalidation_level="TARGETED_TEST", rationale="config-only change, scoped tests suffice",
                ), actor, None,
            )
        async with s.begin():
            planned = await periodic.approve_revalidation_plan(
                s, periodic.ApproveRevalidationPlanCommand(
                    idempotency_key=idem(), change_impact_id=impact.aggregate_id, expected_version=impact.resulting_version,
                    revalidation_ref="REVAL-1",
                ), actor, None,
            )
        async with s.begin():
            completed = await periodic.complete_revalidation(
                s, periodic.CompleteRevalidationCommand(
                    idempotency_key=idem(), change_impact_id=impact.aggregate_id, expected_version=planned.resulting_version,
                    evidence_ref="evidence-1",
                ), actor, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import ValidationChangeImpact
        row = await s.get(ValidationChangeImpact, completed.aggregate_id)
        assert row.completed_at is not None


async def test_periodic_review_decision_requires_independent_reviewer(db, seeded):
    performer = seeded["users"]["operator1"].id
    reviewer = seeded["users"]["qa.reviewer"].id
    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        async with s.begin():
            # Document 106 row 170 signs the create action itself -- same pre-generated-id ceremony as
            # commands_performance.py's signed creates.
            policy = await signature_service.resolve_signature_requirement(s, record_type="periodic_validation_review", action="create")
            new_id = uuid.uuid4()
            real_challenge = await signature_service.create_challenge(
                s, user_id=performer, record_type="periodic_validation_review", record_id=new_id, record_version=1,
                record_hash=record_hash(new_id, 1), meaning=policy.meaning,
            )
            review = await periodic.create_periodic_review(
                s, periodic.CreatePeriodicReviewCommand(
                    idempotency_key=idem(), release_ref="R1", period_start=now - timedelta(days=90), period_end=now,
                    inputs_considered={"changes": ["CHG-1"], "incidents": []}, new_record_id=new_id,
                    challenge_id=real_challenge.id, reauth_password="ChangeMe123!",
                ), performer, None,
            )
        async with s.begin():
            challenge_id = await _challenge(s, performer, "periodic_validation_review", "decision", review.aggregate_id, review.resulting_version)
            with pytest.raises(ValidationFailedError):
                await periodic.decide_periodic_review(
                    s, periodic.DecidePeriodicReviewCommand(
                        idempotency_key=idem(), review_id=review.aggregate_id, expected_version=review.resulting_version,
                        decision="VALIDATED_CONFIRMED", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), performer, None,
                )
        async with s.begin():
            challenge_id = await _challenge(s, reviewer, "periodic_validation_review", "decision", review.aggregate_id, review.resulting_version)
            decided = await periodic.decide_periodic_review(
                s, periodic.DecidePeriodicReviewCommand(
                    idempotency_key=idem(), review_id=review.aggregate_id, expected_version=review.resulting_version,
                    decision="VALIDATED_CONFIRMED", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), reviewer, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import PeriodicValidationReview
        row = await s.get(PeriodicValidationReview, decided.aggregate_id)
        assert row.state == "DECIDED" and row.decision == "VALIDATED_CONFIRMED"
