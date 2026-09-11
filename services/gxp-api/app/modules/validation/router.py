"""WP-12 REST surface -- every `/validation/v1/...` operation Document 79's own API list declares for
Documents 79-96 (minus 85/87/95, WP-14 scope). One router per module keeps `main.py` to a single
`include_router()` call, same shape as every other multi-concern module (security, qms).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.validation import (
    commands_dr,
    commands_exception,
    commands_infra,
    commands_integrity,
    commands_interface,
    commands_iq,
    commands_oq,
    commands_part11,
    commands_performance,
    commands_periodic,
    commands_plan,
    commands_risk,
    commands_security,
    commands_test,
    commands_trace,
)
from app.modules.validation.models import (
    DataIntegrityTestProfile,
    DrQualificationExecution,
    FunctionRiskAssessment,
    InfrastructureFingerprint,
    InterfaceValidationProfile,
    IqExecution,
    OqExecution,
    Part11ScopeAssessment,
    PerformanceRun,
    PeriodicValidationReview,
    SecurityQualificationSuite,
    ValidationException,
    ValidationMasterPlan,
    ValidationTestDefinition,
    ValidationTestExecution,
)
from app.modules.validation.signature_support import (
    SignatureChallengeRequest,
    create_validation_signature_challenge,
    create_validation_signature_challenge_for_new_record,
)
from app.mutation.errors import NotFoundError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/validation/v1", tags=["validation"])


async def _actor_site(actor: AuthenticatedActor) -> uuid.UUID | None:
    return getattr(actor, "site_id", None)


# =====================================================================================================
# Document 79 -- Validation Master Plan & CSA Strategy
# =====================================================================================================


@router.post("/master-plans", response_model=MutationReceipt)
async def post_master_plans(
    cmd: commands_plan.CreateOrUpdateMasterPlanCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.plan.manage", site_id=None)
        return await commands_plan.create_or_update_master_plan(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/master-plans/{plan_id}/release", response_model=MutationReceipt)
async def post_master_plan_release(
    plan_id: uuid.UUID, cmd: commands_plan.ReleaseMasterPlanCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.plan_id = plan_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.plan.release", site_id=None)
        return await commands_plan.release_master_plan(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/master-plans/{plan_id}/signature-challenges")
async def post_master_plan_signature_challenge(
    plan_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        plan = await session.get(ValidationMasterPlan, plan_id)
        if plan is None:
            raise NotFoundError("Validation master plan not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="validation_master_plan", record=plan,
            action=body.action, allowed_actions=("release",),
        )


@router.get("/releases/{plan_id}/gate")
async def get_release_gate(
    plan_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.gate.view", site_id=None)
        return await commands_plan.get_release_gate(session, plan_id)


@router.get("/packages/{scope}")
async def get_package(
    scope: str, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.package.view", site_id=None)
        return await commands_plan.get_package(session, scope)


@router.get("/packages/{scope}/export")
async def get_package_export(
    scope: str, format: str = Query("csv", pattern="^(csv|pdf)$"),
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> Response:
    """VAL-FR-023: CSV (default) or PDF export of the vendor/customer validation package (SG-169
    resolved 2026-09-01 -- ReportLab, see work-packages/WP-12/14_DEPENDENCY_JUSTIFICATION_SG169.md)."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.package.view", site_id=None)
        if format == "pdf":
            pdf_bytes = await commands_plan.export_package_pdf(session, scope)
            return Response(
                content=pdf_bytes, media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="validation-package-{scope}.pdf"'},
            )
        csv_text = await commands_plan.export_package_csv(session, scope)
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="validation-package-{scope}.csv"'},
    )


# =====================================================================================================
# Document 80 -- Intended Use, GxP Criticality & Software Function Risk Classification
# =====================================================================================================


@router.post("/intended-use", response_model=MutationReceipt)
async def post_intended_use(
    cmd: commands_risk.CreateIntendedUseCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.intended_use.manage", site_id=None)
        return await commands_risk.create_intended_use(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/function-risks", response_model=MutationReceipt)
async def post_function_risks(
    cmd: commands_risk.CreateFunctionRiskAssessmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.function_risk.manage", site_id=None)
        return await commands_risk.create_function_risk_assessment(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/function-risks/{assessment_id}/approve", response_model=MutationReceipt)
async def post_function_risk_approve(
    assessment_id: uuid.UUID, cmd: commands_risk.ApproveFunctionRiskAssessmentCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.assessment_id = assessment_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.function_risk.approve", site_id=None)
        return await commands_risk.approve_function_risk_assessment(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/function-risks/{assessment_id}/signature-challenges")
async def post_function_risk_signature_challenge(
    assessment_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        assessment = await session.get(FunctionRiskAssessment, assessment_id)
        if assessment is None:
            raise NotFoundError("Function risk assessment not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="function_risk_assessment", record=assessment,
            action=body.action, allowed_actions=("approve",),
        )


@router.get("/functions/{function_ref}/assurance")
async def get_function_assurance(
    function_ref: str, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.function_risk.view", site_id=None)
        return await commands_risk.get_function_assurance(session, function_ref)


# =====================================================================================================
# Document 81 -- Requirements, Design Inputs & Validation Traceability Management
# =====================================================================================================


@router.post("/requirements:ingest", response_model=MutationReceipt)
async def post_requirements_ingest(
    cmd: commands_trace.IngestRequirementsCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.requirement.manage", site_id=None)
        return await commands_trace.ingest_requirements(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/trace-links", response_model=MutationReceipt)
async def post_trace_links(
    cmd: commands_trace.CreateTraceLinkCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.trace_link.manage", site_id=None)
        return await commands_trace.create_trace_link(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/baselines", response_model=MutationReceipt)
async def post_baselines(
    cmd: commands_trace.FreezeRequirementBaselineCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.baseline.manage", site_id=None)
        return await commands_trace.freeze_requirement_baseline(session, cmd, actor.user_id, await _actor_site(actor))


@router.get("/traceability")
async def get_traceability(
    baseline_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.traceability.view", site_id=None)
        return await commands_trace.get_traceability(session, baseline_id)


@router.get("/traceability/export")
async def get_traceability_export(
    baseline_id: uuid.UUID, format: str = Query("csv", pattern="^(csv|pdf)$"),
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> Response:
    """REQ-FR-022: CSV (default) or PDF export of the authoritative traceability graph for a frozen
    baseline (SG-169 resolved 2026-09-01 -- ReportLab, see
    work-packages/WP-12/14_DEPENDENCY_JUSTIFICATION_SG169.md)."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.traceability.view", site_id=None)
        if format == "pdf":
            pdf_bytes = await commands_trace.export_traceability_pdf(session, baseline_id)
            return Response(
                content=pdf_bytes, media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="traceability-{baseline_id}.pdf"'},
            )
        csv_text = await commands_trace.export_traceability_csv(session, baseline_id)
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="traceability-{baseline_id}.csv"'},
    )


@router.get("/traceability/gaps")
async def get_traceability_gaps(
    baseline_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.traceability.view", site_id=None)
        return await commands_trace.get_traceability_gaps(session, baseline_id)


# =====================================================================================================
# Document 82 -- Validation Test Strategy, Test Methods & Objective Evidence Governance
# =====================================================================================================


@router.post("/tests", response_model=MutationReceipt)
async def post_tests(
    cmd: commands_test.CreateTestDefinitionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.test_definition.manage", site_id=None)
        return await commands_test.create_test_definition(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/tests/{test_id}/approve", response_model=MutationReceipt)
async def post_tests_approve(
    test_id: uuid.UUID, cmd: commands_test.ApproveTestDefinitionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.test_id = test_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.test_definition.approve", site_id=None)
        return await commands_test.approve_test_definition(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/tests/{test_id}/signature-challenges")
async def post_test_signature_challenge(
    test_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        test_def = await session.get(ValidationTestDefinition, test_id)
        if test_def is None:
            raise NotFoundError("Validation test definition not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="validation_test_definition", record=test_def,
            action=body.action, allowed_actions=("approve",),
        )


@router.post("/executions", response_model=MutationReceipt)
async def post_executions(
    cmd: commands_test.StartTestExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.test_execution.manage", site_id=None)
        return await commands_test.start_test_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/executions/{execution_id}/complete", response_model=MutationReceipt)
async def post_executions_complete(
    execution_id: uuid.UUID, cmd: commands_test.CompleteTestExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.execution_id = execution_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.test_execution.complete", site_id=None)
        return await commands_test.complete_test_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/executions/{execution_id}/signature-challenges")
async def post_test_execution_signature_challenge(
    execution_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        execution = await session.get(ValidationTestExecution, execution_id)
        if execution is None:
            raise NotFoundError("Validation test execution not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="validation_test_execution", record=execution,
            action=body.action, allowed_actions=("complete",),
        )


@router.post("/automated-evidence", response_model=MutationReceipt)
async def post_automated_evidence(
    cmd: commands_test.ImportAutomatedEvidenceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.test_execution.manage", site_id=None)
        return await commands_test.import_automated_evidence(session, cmd, actor.user_id, await _actor_site(actor))


# =====================================================================================================
# Document 83 -- Installation Qualification (IQ)
# =====================================================================================================


@router.post("/iq/protocols", response_model=MutationReceipt)
async def post_iq_protocols(
    cmd: commands_iq.CreateIqProtocolCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.iq.manage", site_id=None)
        return await commands_iq.create_iq_protocol(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/iq/executions", response_model=MutationReceipt)
async def post_iq_executions(
    cmd: commands_iq.StartIqExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.iq.manage", site_id=None)
        return await commands_iq.start_iq_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/iq/executions/{execution_id}/complete", response_model=MutationReceipt)
async def post_iq_executions_complete(
    execution_id: uuid.UUID, cmd: commands_iq.CompleteIqExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.execution_id = execution_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.iq.complete", site_id=None)
        return await commands_iq.complete_iq_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/iq/executions/{execution_id}/approve", response_model=MutationReceipt)
async def post_iq_executions_approve(
    execution_id: uuid.UUID, cmd: commands_iq.ApproveIqExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.execution_id = execution_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.iq.approve", site_id=None)
        return await commands_iq.approve_iq_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/iq/executions/{execution_id}/signature-challenges")
async def post_iq_execution_signature_challenge(
    execution_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        execution = await session.get(IqExecution, execution_id)
        if execution is None:
            raise NotFoundError("IQ execution not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="iq_execution", record=execution,
            action=body.action, allowed_actions=("complete", "approve"),
        )


# =====================================================================================================
# Document 84 -- Operational Qualification (OQ)
# =====================================================================================================


@router.post("/oq:suites", response_model=MutationReceipt)
async def post_oq_suites(
    cmd: commands_oq.CreateOqSuiteCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.oq.manage", site_id=None)
        return await commands_oq.create_oq_suite(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/oq/executions", response_model=MutationReceipt)
async def post_oq_executions(
    cmd: commands_oq.RecordOqExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.oq.manage", site_id=None)
        return await commands_oq.record_oq_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.get("/oq/{execution_id}/coverage")
async def get_oq_coverage(
    execution_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.oq.view", site_id=None)
        return await commands_oq.get_oq_coverage(session, execution_id)


@router.post("/oq/{execution_id}/approve", response_model=MutationReceipt)
async def post_oq_approve(
    execution_id: uuid.UUID, cmd: commands_oq.ApproveOqExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.execution_id = execution_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.oq.approve", site_id=None)
        return await commands_oq.approve_oq_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/oq/{execution_id}/signature-challenges")
async def post_oq_signature_challenge(
    execution_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        execution = await session.get(OqExecution, execution_id)
        if execution is None:
            raise NotFoundError("OQ execution not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="oq_execution", record=execution,
            action=body.action, allowed_actions=("approve",),
        )


# =====================================================================================================
# Document 86 -- Infrastructure, Cloud, Platform & Environment Qualification
# =====================================================================================================


@router.post("/infrastructure/profiles", response_model=MutationReceipt)
async def post_infrastructure_profiles(
    cmd: commands_infra.CreateInfrastructureProfileCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.infrastructure.manage", site_id=None)
        return await commands_infra.create_infrastructure_profile(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/infrastructure/fingerprints", response_model=MutationReceipt)
async def post_infrastructure_fingerprints(
    cmd: commands_infra.CaptureInfrastructureFingerprintCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.infrastructure.manage", site_id=None)
        return await commands_infra.capture_infrastructure_fingerprint(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/infrastructure/tests", response_model=MutationReceipt)
async def post_infrastructure_tests(
    cmd: commands_infra.RunInfrastructureControlTestsCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.infrastructure.manage", site_id=None)
        return await commands_infra.run_infrastructure_control_tests(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/infrastructure/{fingerprint_id}/approve", response_model=MutationReceipt)
async def post_infrastructure_approve(
    fingerprint_id: uuid.UUID, cmd: commands_infra.ApproveInfrastructureFingerprintCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.fingerprint_id = fingerprint_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.infrastructure.approve", site_id=None)
        return await commands_infra.approve_infrastructure_fingerprint(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/infrastructure/{fingerprint_id}/signature-challenges")
async def post_infrastructure_signature_challenge(
    fingerprint_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        fingerprint = await session.get(InfrastructureFingerprint, fingerprint_id)
        if fingerprint is None:
            raise NotFoundError("Infrastructure fingerprint not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="infrastructure_fingerprint", record=fingerprint,
            action=body.action, allowed_actions=("approve",),
        )


# =====================================================================================================
# Document 88 -- 21 CFR Part 11 Electronic Records & Electronic Signature Validation
# =====================================================================================================


@router.post("/part11/assessments", response_model=MutationReceipt)
async def post_part11_assessments(
    cmd: commands_part11.CreatePart11ScopeAssessmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.part11.manage", site_id=None)
        return await commands_part11.create_part11_scope_assessment(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/part11/{assessment_id}/test-suite", response_model=MutationReceipt)
async def post_part11_test_suite(
    assessment_id: uuid.UUID, cmd: commands_part11.DerivePart11TestSuiteCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.assessment_id = assessment_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.part11.manage", site_id=None)
        return await commands_part11.derive_part11_test_suite(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/part11/control-results", response_model=MutationReceipt)
async def post_part11_control_results(
    cmd: commands_part11.RecordPart11ControlResultCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.part11.manage", site_id=None)
        return await commands_part11.record_part11_control_result(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/part11/{assessment_id}/approve", response_model=MutationReceipt)
async def post_part11_approve(
    assessment_id: uuid.UUID, cmd: commands_part11.ApprovePart11AssessmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.assessment_id = assessment_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.part11.approve", site_id=None)
        return await commands_part11.approve_part11_assessment(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/part11/{assessment_id}/signature-challenges")
async def post_part11_signature_challenge(
    assessment_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        assessment = await session.get(Part11ScopeAssessment, assessment_id)
        if assessment is None:
            raise NotFoundError("Part 11 scope assessment not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="part11_scope_assessment", record=assessment,
            action=body.action, allowed_actions=("approve",),
        )


# =====================================================================================================
# Document 89 -- Audit Trail, Record Version Vault & Data Integrity Validation
# =====================================================================================================


@router.post("/data-integrity/suites", response_model=MutationReceipt)
async def post_data_integrity_suites(
    cmd: commands_integrity.CreateDataIntegrityProfileCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.data_integrity.manage", site_id=None)
        return await commands_integrity.create_data_integrity_profile(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/data-integrity/tamper-tests", response_model=MutationReceipt)
async def post_data_integrity_tamper_tests(
    cmd: commands_integrity.RecordTamperTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.data_integrity.manage", site_id=None)
        return await commands_integrity.record_tamper_test(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/data-integrity/{profile_id}/approve", response_model=MutationReceipt)
async def post_data_integrity_approve(
    profile_id: uuid.UUID, cmd: commands_integrity.ApproveDataIntegrityProfileCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.profile_id = profile_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.data_integrity.approve", site_id=None)
        return await commands_integrity.approve_data_integrity_profile(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/data-integrity/{profile_id}/signature-challenges")
async def post_data_integrity_signature_challenge(
    profile_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        profile = await session.get(DataIntegrityTestProfile, profile_id)
        if profile is None:
            raise NotFoundError("Data integrity test profile not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="data_integrity_test_profile", record=profile,
            action=body.action, allowed_actions=("approve",),
        )


# =====================================================================================================
# Document 90 -- Integration, Edge, Device, Peripheral & Interface Validation
# =====================================================================================================


@router.post("/interfaces/profiles", response_model=MutationReceipt)
async def post_interfaces_profiles(
    cmd: commands_interface.CreateInterfaceProfileCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.interface.manage", site_id=None)
        return await commands_interface.create_interface_profile(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/interfaces/tests", response_model=MutationReceipt)
async def post_interfaces_tests(
    cmd: commands_interface.RecordInterfaceTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.interface.manage", site_id=None)
        return await commands_interface.record_interface_test(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/interfaces/edge-outage-tests", response_model=MutationReceipt)
async def post_interfaces_edge_outage_tests(
    cmd: commands_interface.RecordEdgeOutageTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.interface.manage", site_id=None)
        return await commands_interface.record_edge_outage_test(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/interfaces/{profile_id}/approve", response_model=MutationReceipt)
async def post_interfaces_approve(
    profile_id: uuid.UUID, cmd: commands_interface.ApproveInterfaceProfileCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.profile_id = profile_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.interface.approve", site_id=None)
        return await commands_interface.approve_interface_profile(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/interfaces/{profile_id}/signature-challenges")
async def post_interfaces_signature_challenge(
    profile_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        profile = await session.get(InterfaceValidationProfile, profile_id)
        if profile is None:
            raise NotFoundError("Interface validation profile not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="interface_validation_profile", record=profile,
            action=body.action, allowed_actions=("approve",),
        )


# =====================================================================================================
# Document 91 -- Backup, Restore, PITR & Disaster Recovery Qualification
# =====================================================================================================


@router.post("/dr/scenarios", response_model=MutationReceipt)
async def post_dr_scenarios(
    cmd: commands_dr.CreateDrScenarioCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.dr.manage", site_id=None)
        return await commands_dr.create_dr_scenario(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/dr/executions", response_model=MutationReceipt)
async def post_dr_executions(
    cmd: commands_dr.RecordDrExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.dr.manage", site_id=None)
        return await commands_dr.record_dr_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/dr/{execution_id}/measure", response_model=MutationReceipt)
async def post_dr_measure(
    execution_id: uuid.UUID, cmd: commands_dr.MeasureDrObjectivesCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.execution_id = execution_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.dr.manage", site_id=None)
        return await commands_dr.measure_dr_objectives(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/dr/{execution_id}/approve", response_model=MutationReceipt)
async def post_dr_approve(
    execution_id: uuid.UUID, cmd: commands_dr.ApproveDrExecutionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.execution_id = execution_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.dr.approve", site_id=None)
        return await commands_dr.approve_dr_execution(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/dr/{execution_id}/signature-challenges")
async def post_dr_signature_challenge(
    execution_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        execution = await session.get(DrQualificationExecution, execution_id)
        if execution is None:
            raise NotFoundError("DR qualification execution not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="dr_qualification_execution", record=execution,
            action=body.action, allowed_actions=("approve",),
        )


# =====================================================================================================
# Document 92 -- Security Qualification, Vulnerability Verification & Penetration Testing
# =====================================================================================================


@router.post("/security/suites", response_model=MutationReceipt)
async def post_security_suites(
    cmd: commands_security.CreateSecuritySuiteCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.security.manage", site_id=None)
        return await commands_security.create_security_suite(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/security/tests", response_model=MutationReceipt)
async def post_security_tests(
    cmd: commands_security.RecordSecurityTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.security.manage", site_id=None)
        return await commands_security.record_security_test(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/security/findings", response_model=MutationReceipt)
async def post_security_findings(
    cmd: commands_security.ImportFindingCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.security.manage", site_id=None)
        return await commands_security.import_finding(session, cmd, actor.user_id, await _actor_site(actor))


@router.get("/security/{suite_id}/gate")
async def get_security_gate(
    suite_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.security.view", site_id=None)
        return await commands_security.get_security_gate(session, suite_id)


@router.post("/security/{suite_id}/approve", response_model=MutationReceipt)
async def post_security_approve(
    suite_id: uuid.UUID, cmd: commands_security.ApproveSecuritySuiteCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.suite_id = suite_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.security.approve", site_id=None)
        return await commands_security.approve_security_suite(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/security/{suite_id}/signature-challenges")
async def post_security_signature_challenge(
    suite_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        suite = await session.get(SecurityQualificationSuite, suite_id)
        if suite is None:
            raise NotFoundError("Security qualification suite not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="security_qualification_suite", record=suite,
            action=body.action, allowed_actions=("approve",),
        )


# =====================================================================================================
# Document 93 -- Performance, Load, Capacity & Reliability Qualification
# =====================================================================================================


@router.post("/performance/scenarios", response_model=MutationReceipt)
async def post_performance_scenarios(
    cmd: commands_performance.CreatePerformanceScenarioCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.performance.manage", site_id=None)
        return await commands_performance.create_performance_scenario(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/performance/scenarios/signature-challenges")
async def post_performance_scenario_signature_challenge(
    body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Signed-CREATE (Document 106 rows 159-161) -- see `signature_support.py` module docstring and
    `commands_performance.py::create_performance_scenario`. The returned `new_record_id` must be passed
    back as `CreatePerformanceScenarioCommand.new_record_id`."""
    async with session.begin():
        new_id = uuid.uuid4()
        result = await create_validation_signature_challenge_for_new_record(
            session, actor_user_id=actor.user_id, record_type="performance_qualification_scenario",
            record_id=new_id, action=body.action, allowed_actions=("create",),
        )
        return {**result, "new_record_id": str(new_id)}


@router.post("/performance/runs", response_model=MutationReceipt)
async def post_performance_runs(
    cmd: commands_performance.RecordPerformanceRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.performance.manage", site_id=None)
        return await commands_performance.record_performance_run(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/performance/runs/signature-challenges")
async def post_performance_run_signature_challenge(
    body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Signed-CREATE (Document 106 row 159) -- see `commands_performance.py::record_performance_run`.
    The returned `new_record_id` must be passed back as `RecordPerformanceRunCommand.new_record_id`."""
    async with session.begin():
        new_id = uuid.uuid4()
        result = await create_validation_signature_challenge_for_new_record(
            session, actor_user_id=actor.user_id, record_type="performance_run",
            record_id=new_id, action=body.action, allowed_actions=("create",),
        )
        return {**result, "new_record_id": str(new_id)}


@router.post("/performance/{run_id}/evaluate", response_model=MutationReceipt)
async def post_performance_evaluate(
    run_id: uuid.UUID, cmd: commands_performance.EvaluatePerformanceRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.run_id = run_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.performance.manage", site_id=None)
        return await commands_performance.evaluate_performance_run(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/performance/{run_id}/signature-challenges")
async def post_performance_run_evaluate_signature_challenge(
    run_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        run = await session.get(PerformanceRun, run_id)
        if run is None:
            raise NotFoundError("Performance run not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="performance_run", record=run,
            action=body.action, allowed_actions=("evaluate",),
        )


@router.get("/performance/sizing")
async def get_performance_sizing(
    scenario_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.performance.view", site_id=None)
        return await commands_performance.get_deployment_sizing(session, scenario_id)


# =====================================================================================================
# Document 94 -- Validation Defect, Deviation, Test Exception & Remediation Management
# =====================================================================================================


@router.post("/exceptions", response_model=MutationReceipt)
async def post_exceptions(
    cmd: commands_exception.CreateExceptionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.exception.create", site_id=None)
        return await commands_exception.create_exception(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/exceptions/signature-challenges")
async def post_exception_create_signature_challenge(
    body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Signed-CREATE (Document 106 row 162) -- see `commands_exception.py::create_exception`. The
    returned `new_record_id` must be passed back as `CreateExceptionCommand.new_record_id`."""
    async with session.begin():
        new_id = uuid.uuid4()
        result = await create_validation_signature_challenge_for_new_record(
            session, actor_user_id=actor.user_id, record_type="validation_exception",
            record_id=new_id, action=body.action, allowed_actions=("create",),
        )
        return {**result, "new_record_id": str(new_id)}


@router.post("/exceptions/{exception_id}/triage", response_model=MutationReceipt)
async def post_exceptions_triage(
    exception_id: uuid.UUID, cmd: commands_exception.TriageExceptionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.exception_id = exception_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.exception.triage", site_id=None)
        return await commands_exception.triage_exception(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/exceptions/{exception_id}/retest-plan", response_model=MutationReceipt)
async def post_exceptions_retest_plan(
    exception_id: uuid.UUID, cmd: commands_exception.DefineRetestScopeCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.exception_id = exception_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.exception.retest_plan", site_id=None)
        return await commands_exception.define_retest_scope(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/exceptions/{exception_id}/disposition", response_model=MutationReceipt)
async def post_exceptions_disposition(
    exception_id: uuid.UUID, cmd: commands_exception.DispositionExceptionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.exception_id = exception_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.exception.disposition", site_id=None)
        return await commands_exception.disposition_exception(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/exceptions/{exception_id}/signature-challenges")
async def post_exception_signature_challenge(
    exception_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        exception = await session.get(ValidationException, exception_id)
        if exception is None:
            raise NotFoundError("Validation exception not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="validation_exception", record=exception,
            action=body.action, allowed_actions=("triage", "retest_plan", "disposition"),
        )


@router.get("/releases/{release_ref}/exception-gate")
async def get_exception_gate(
    release_ref: str, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.exception.view", site_id=None)
        return await commands_exception.get_exception_gate(session, release_ref)


# =====================================================================================================
# Document 96 -- Periodic Review, Change Impact, Revalidation & Validated-State Maintenance
# =====================================================================================================


@router.post("/change-impacts", response_model=MutationReceipt)
async def post_change_impacts(
    cmd: commands_periodic.CreateChangeImpactCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.change_impact.manage", site_id=None)
        return await commands_periodic.create_change_impact(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/revalidation-plans", response_model=MutationReceipt)
async def post_revalidation_plans(
    cmd: commands_periodic.ApproveRevalidationPlanCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.change_impact.manage", site_id=None)
        return await commands_periodic.approve_revalidation_plan(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/revalidations", response_model=MutationReceipt)
async def post_revalidations(
    cmd: commands_periodic.CompleteRevalidationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.change_impact.manage", site_id=None)
        return await commands_periodic.complete_revalidation(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/periodic-reviews", response_model=MutationReceipt)
async def post_periodic_reviews(
    cmd: commands_periodic.CreatePeriodicReviewCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.periodic_review.manage", site_id=None)
        return await commands_periodic.create_periodic_review(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/periodic-reviews/signature-challenges")
async def post_periodic_review_create_signature_challenge(
    body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Signed-CREATE (Document 106 row 170) -- see `commands_periodic.py::create_periodic_review`. The
    returned `new_record_id` must be passed back as `CreatePeriodicReviewCommand.new_record_id`."""
    async with session.begin():
        new_id = uuid.uuid4()
        result = await create_validation_signature_challenge_for_new_record(
            session, actor_user_id=actor.user_id, record_type="periodic_validation_review",
            record_id=new_id, action=body.action, allowed_actions=("create",),
        )
        return {**result, "new_record_id": str(new_id)}


@router.post("/periodic-reviews/{review_id}/decision", response_model=MutationReceipt)
async def post_periodic_reviews_decision(
    review_id: uuid.UUID, cmd: commands_periodic.DecidePeriodicReviewCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.review_id = review_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.periodic_review.decide", site_id=None)
        return await commands_periodic.decide_periodic_review(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/periodic-reviews/{review_id}/signature-challenges")
async def post_periodic_review_decision_signature_challenge(
    review_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        review = await session.get(PeriodicValidationReview, review_id)
        if review is None:
            raise NotFoundError("Periodic validation review not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="periodic_validation_review", record=review,
            action=body.action, allowed_actions=("decision",),
        )


@router.post("/decommission", response_model=MutationReceipt)
async def post_decommission(
    cmd: commands_periodic.DecommissionValidatedSystemCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.state_baseline.decommission", site_id=None)
        return await commands_periodic.decommission_validated_system(session, cmd, actor.user_id, await _actor_site(actor))
