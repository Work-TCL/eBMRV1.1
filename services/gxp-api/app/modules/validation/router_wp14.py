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

from pydantic import BaseModel

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.modules.validation import commands_migration, commands_pq, commands_vsr
from app.modules.validation.models_wp14 import MigrationRun, PqScenario, ValidatedReleaseAuthorization, ValidationSummaryReport
from app.modules.validation.signature_support import SignatureChallengeRequest, create_validation_signature_challenge
from app.mutation.errors import NotFoundError
from app.mutation.hashing import sha256_hex
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


@router.post("/pq/{scenario_id}/signature-challenges")
async def post_pq_signature_challenge(
    scenario_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        scenario = await session.get(PqScenario, scenario_id)
        if scenario is None:
            raise NotFoundError("PQ scenario not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="pq_scenario", record=scenario,
            action=body.action, allowed_actions=("approve",),
        )


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


@router.post("/migrations/{run_id}/signature-challenges")
async def post_migration_signature_challenge(
    run_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        run = await session.get(MigrationRun, run_id)
        if run is None:
            raise NotFoundError("Migration run not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="migration_run", record=run,
            action=body.action, allowed_actions=("approve",),
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


@router.post("/summary-reports/{report_id}/signature-challenges")
async def post_summary_report_signature_challenge(
    report_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        report = await session.get(ValidationSummaryReport, report_id)
        if report is None:
            raise NotFoundError("validation summary report not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="validation_summary_report", record=report,
            action=body.action, allowed_actions=("approve",),
        )


class IssueReleaseAuthorizationChallengeBody(BaseModel):
    """Mirrors `commands_vsr.IssueValidatedReleaseAuthorizationCommand` minus the transport-only
    `challenge_id`/`reauth_password`/`idempotency_key` fields -- field-for-field, so this body's
    `model_dump(mode="json")` reproduces exactly what `create_challenge_hash()` computes from the real
    command at consume time (Document 106 row 166 signs the authorization decision itself, not a
    placeholder row -- see `commands_vsr.py::_apply_signature_for_create`)."""

    authorization_number: str
    environment: str
    config_fingerprint: str
    release_identity: dict
    artifact_digests: dict
    decision: str
    go_live_gates: dict
    reason: str
    conditions: list[dict] = []
    production_performer_user_ids: list[str] = []
    site_id: uuid.UUID | None = None


@router.post("/releases/{vsr_id}/authorize/signature-challenges")
async def post_release_authorize_signature_challenge(
    vsr_id: uuid.UUID, body: IssueReleaseAuthorizationChallengeBody, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Signed-CREATE, content-hash-bound (Document 106 row 166). `body` must carry the exact same field
    values the client then submits to `POST /releases/{vsr_id}/authorize` -- any difference invalidates
    the challenge (`SIGNATURE_CHALLENGE_INVALID`), by design (SIG-FR-012/013/014 equivalent)."""
    async with session.begin():
        vsr = await session.get(ValidationSummaryReport, vsr_id)
        if vsr is None:
            raise NotFoundError("validation summary report not found")
        policy = await commands_vsr.resolve_signature(
            session, record_type=commands_vsr.RECORD_TYPE_RELEASE_AUTH, action="authorize"
        )
        payload_hash = sha256_hex({"vsr_id": str(vsr_id), **body.model_dump(mode="json")})
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type=commands_vsr.RECORD_TYPE_RELEASE_AUTH,
            record_id=vsr_id, record_version=1, record_hash=payload_hash, meaning=policy.meaning,
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


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


@router.post("/releases/{authorization_id}/deployment-check/signature-challenges")
async def post_release_deployment_check_signature_challenge(
    authorization_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        authorization = await session.get(ValidatedReleaseAuthorization, authorization_id)
        if authorization is None:
            raise NotFoundError("validated release authorization not found")
        return await create_validation_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="validated_release_authorization",
            record=authorization, action=body.action, allowed_actions=("deployment_check",),
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
