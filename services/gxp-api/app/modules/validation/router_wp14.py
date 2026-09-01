"""WP-14 REST surface -- the `/validation/v1/...` operations Documents 85 / 87 / 95 §7 declare for
SPEC-VAL-007 / 009 / 017. A separate router object from `router.py` (WP-12's) so this file is purely
additive; `main.py` includes both under the same `/validation/v1` prefix.

Two GET/POST surfaces are added beyond each document's §7 enumeration, driven by the function
catalogue and required events/requirements that the §7 POST lists do not cover (same precedent as
WP-12 adding UI-screen GETs such as `/releases/{id}/gate` and `/oq/{id}/coverage`):
  * `GET  /validation/v1/migrations/{plan_id}/legacy-trace` -- `verifyLegacyRecordTrace()` (FN-0846),
    an inspection read for the Document 87 §8 "Legacy Trace" screen.
  * `POST /validation/v1/releases/{authorization_id}/post-go-live-verification` --
    `recordPostGoLiveVerification()` (FN-0922) and its `PostGoLiveVerificationCompleted` event
    (VSR-FR-023/024, Document 95 §8 "Post-Go-Live" screen).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.validation import commands_migration, commands_pq, commands_vsr
from app.modules.validation.models_wp14 import ValidationSummaryReport
from app.mutation.errors import NotFoundError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/validation/v1", tags=["validation"])


async def _actor_site(actor: AuthenticatedActor) -> uuid.UUID | None:
    return getattr(actor, "site_id", None)


# =====================================================================================================
# Document 85 (SPEC-VAL-007) -- Performance Qualification (PQ), UAT & Business Process Verification
# =====================================================================================================


@router.post("/pq/scenarios", response_model=MutationReceipt)
async def post_pq_scenarios(
    cmd: commands_pq.CreatePqScenarioCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.pq.manage", site_id=None)
        return await commands_pq.create_pq_scenario(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/pq/scenarios/{scenario_id}/participants", response_model=MutationReceipt)
async def post_pq_participants(
    scenario_id: uuid.UUID, cmd: commands_pq.AssignPqParticipantsCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.scenario_id = scenario_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.pq.manage", site_id=None)
        return await commands_pq.assign_pq_participants(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/pq/executions", response_model=MutationReceipt)
async def post_pq_executions(
    cmd: commands_pq.ExecutePqScenarioCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.pq.execute", site_id=None)
        return await commands_pq.execute_pq_scenario(session, cmd, actor.user_id, await _actor_site(actor))


@router.post("/pq/{scenario_id}/approve", response_model=MutationReceipt)
async def post_pq_approve(
    scenario_id: uuid.UUID, cmd: commands_pq.ApprovePqCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.scenario_id = scenario_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.pq.approve", site_id=None)
        return await commands_pq.approve_pq(session, cmd, actor.user_id, await _actor_site(actor))


# =====================================================================================================
# Document 87 (SPEC-VAL-009) -- Data Migration, Conversion, Cutover & Reconciliation Validation
# =====================================================================================================


@router.post("/migrations/plans", response_model=MutationReceipt)
async def post_migration_plans(
    cmd: commands_migration.CreateMigrationValidationPlanCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.migration.manage", site_id=None)
        return await commands_migration.create_migration_validation_plan(
            session, cmd, actor.user_id, await _actor_site(actor)
        )


@router.post("/migrations/runs", response_model=MutationReceipt)
async def post_migration_runs(
    cmd: commands_migration.ExecuteMigrationRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.migration.manage", site_id=None)
        return await commands_migration.execute_migration_dry_run(
            session, cmd, actor.user_id, await _actor_site(actor)
        )


@router.post("/migrations/{run_id}/reconcile", response_model=MutationReceipt)
async def post_migration_reconcile(
    run_id: uuid.UUID, cmd: commands_migration.ReconcileMigrationRunCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.run_id = run_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.migration.manage", site_id=None)
        return await commands_migration.reconcile_migration_run(
            session, cmd, actor.user_id, await _actor_site(actor)
        )


@router.post("/migrations/{run_id}/approve", response_model=MutationReceipt)
async def post_migration_approve(
    run_id: uuid.UUID, cmd: commands_migration.ApproveMigrationCutoverCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.run_id = run_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.migration.approve", site_id=None)
        return await commands_migration.approve_migration_cutover(
            session, cmd, actor.user_id, await _actor_site(actor)
        )


@router.get("/migrations/{plan_id}/legacy-trace")
async def get_migration_legacy_trace(
    plan_id: uuid.UUID, legacy_id: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.migration.trace_view", site_id=None)
        return await commands_migration.verify_legacy_record_trace(session, plan_id, legacy_id)


# =====================================================================================================
# Document 95 (SPEC-VAL-017) -- Validation Summary Report, Release-to-Production & Go-Live Authorization
# =====================================================================================================


@router.post("/summary-reports", response_model=MutationReceipt)
async def post_summary_reports(
    cmd: commands_vsr.GenerateValidationSummaryReportCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.vsr.manage", site_id=None)
        return await commands_vsr.generate_validation_summary_report(
            session, cmd, actor.user_id, await _actor_site(actor)
        )


@router.get("/releases/{vsr_id}/go-live-readiness")
async def get_go_live_readiness(
    vsr_id: uuid.UUID,
    training: str | None = Query(None), production_config: str | None = Query(None),
    backups: str | None = Query(None), interfaces: str | None = Query(None),
    support: str | None = Query(None), monitoring: str | None = Query(None),
    cutover_tasks: str | None = Query(None),
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.release_auth.view", site_id=None)
        vsr = await session.get(ValidationSummaryReport, vsr_id)
        if vsr is None:
            raise NotFoundError("validation summary report not found")
        gates = {
            "training": training, "production_config": production_config, "backups": backups,
            "interfaces": interfaces, "support": support, "monitoring": monitoring,
            "cutover_tasks": cutover_tasks,
        }
        return commands_vsr.evaluate_go_live_readiness(vsr, gates)


@router.post("/summary-reports/{report_id}/approve", response_model=MutationReceipt)
async def post_summary_report_approve(
    report_id: uuid.UUID, cmd: commands_vsr.ApproveValidationSummaryCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.report_id = report_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.vsr.approve", site_id=None)
        return await commands_vsr.approve_validation_summary(
            session, cmd, actor.user_id, await _actor_site(actor)
        )


@router.post("/releases/{vsr_id}/authorize", response_model=MutationReceipt)
async def post_release_authorize(
    vsr_id: uuid.UUID, cmd: commands_vsr.IssueValidatedReleaseAuthorizationCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.vsr_id = vsr_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.release_auth.authorize", site_id=None)
        return await commands_vsr.issue_validated_release_authorization(
            session, cmd, actor.user_id, await _actor_site(actor)
        )


@router.post("/releases/{authorization_id}/deployment-check", response_model=MutationReceipt)
async def post_release_deployment_check(
    authorization_id: uuid.UUID, cmd: commands_vsr.VerifyDeploymentAgainstValidationReleaseCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.authorization_id = authorization_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.release_auth.deployment_check", site_id=None)
        return await commands_vsr.verify_deployment_against_validation_release(
            session, cmd, actor.user_id, await _actor_site(actor)
        )


@router.post("/releases/{authorization_id}/post-go-live-verification", response_model=MutationReceipt)
async def post_release_post_go_live(
    authorization_id: uuid.UUID, cmd: commands_vsr.RecordPostGoLiveVerificationCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.authorization_id = authorization_id
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="validation.post_go_live.record", site_id=None)
        return await commands_vsr.record_post_go_live_verification(
            session, cmd, actor.user_id, await _actor_site(actor)
        )
