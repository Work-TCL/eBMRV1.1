"""Document 76 (SPEC-DATA-008) REST surface. The 3 operations Document 76 # 7 lists:

  POST /platform/v1/recovery-objectives   -- set/update a component's RPO/RTO tier (state-changing)
  GET  /platform/v1/backups/health        -- backup freshness for every declared component
  POST /platform/v1/restore-tests         -- record an executed restore/PITR drill (state-changing)

No signature (Document 106 has no SPEC-DATA-008 row).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.disaster_recovery import commands
from app.modules.disaster_recovery.models import BackupInventory, RecoveryObjectiveProfile, RestoreTest
from app.modules.disaster_recovery.recovery import verify_backup_freshness
from app.modules.policy.service import evaluate_policy, resolve_site_scope
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/platform/v1", tags=["disaster-recovery"])


@router.post("/recovery-objectives", response_model=MutationReceipt)
async def post_recovery_objective(
    cmd: commands.CreateRecoveryObjectiveProfileCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        # SG-213 NOT mechanically fixable: recovery_objective_profile.site_id exists and is nullable
        # (T5 edge objectives are per-site, models.py docstring), but
        # CreateRecoveryObjectiveProfileCommand carries no site_id field at all, and this handler never
        # sets one on the created row -- every row created through this endpoint today is the
        # platform-wide None case. Giving this command a per-site create path is a schema/command change
        # (and a call on who may set a T5 edge site's objective), not a wrong-argument fix -- flagged for
        # a human call rather than guessed.
        await evaluate_policy(session, actor.user_id, action="dr.recovery_objective.manage", site_id=None)
        return await commands.create_recovery_objective_profile(session, cmd, actor.user_id)


@router.get("/backups/health")
async def get_backup_health(
    site_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        # SG-213 fix: recovery_objective_profile.site_id is nullable (T5 edge objectives are per-site;
        # T0-T4 components are platform-wide with site_id=NULL). This was gating on "holds dr.backup.view
        # anywhere" and then returning every site's T5 rows regardless. resolve_site_scope turns an
        # omitted site_id into only the sites the actor actually holds the action at; the platform-wide
        # (site_id IS NULL) components stay visible to anyone holding the permission at any site, since
        # they belong to no single site.
        site_scope = await resolve_site_scope(session, actor.user_id, site_id, action="dr.backup.view")
        components = (
            await session.execute(
                select(RecoveryObjectiveProfile).where(
                    RecoveryObjectiveProfile.state == "EFFECTIVE",
                    or_(
                        RecoveryObjectiveProfile.site_id.is_(None),
                        RecoveryObjectiveProfile.site_id.in_(site_scope),
                    ),
                )
            )
        ).scalars().all()
        results = []
        for c in components:
            last_backup = (
                await session.execute(
                    select(BackupInventory.completed_at)
                    .where(BackupInventory.component == c.component, BackupInventory.status == "SUCCESS")
                    .order_by(BackupInventory.completed_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            results.append(await verify_backup_freshness(session, component=c.component, last_backup_completed_at=last_backup))
    return {"count": len(results), "components": results}


@router.post("/restore-tests", response_model=MutationReceipt)
async def post_restore_test(
    cmd: commands.ExecutePostgresRestoreTestCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        # SG-213 reviewed: backup_inventory and restore_test (models.py) have no site_id column at all
        # -- a Postgres backup/restore test is platform infrastructure, not a site-scoped record, and
        # ExecutePostgresRestoreTestCommand has no site_id field either. Genuinely platform-wide;
        # site_id=None is correct.
        await evaluate_policy(session, actor.user_id, action="dr.restore_test.execute", site_id=None)
        return await commands.execute_postgres_restore_test(session, cmd, actor.user_id)


RESTORE_TEST_SORTABLE = {"started_at": RestoreTest.started_at, "created_at": RestoreTest.created_at}


def _restore_test_dict(r: RestoreTest) -> dict:
    return {
        "id": str(r.id), "backup_id": str(r.backup_id), "target_environment": r.target_environment,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "rpo_achieved_seconds": r.rpo_achieved_seconds, "rto_achieved_seconds": r.rto_achieved_seconds,
        "result": r.result, "evidence_ref": r.evidence_ref, "version": r.version,
    }


@router.get("/restore-tests")
async def list_restore_tests(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Browsable list backing platform's redesigned Backup & DR tab -- the restore_test table (Document
    76 #6) already existed but had no GET, only the POST that records an executed drill. Same
    dr.backup.view policy gate as the health check above."""
    async with session.begin():
        # SG-213 reviewed: restore_test (models.py) has no site_id column -- same platform-infra
        # reasoning as post_restore_test above. site_id=None is correct.
        await evaluate_policy(session, actor.user_id, action="dr.backup.view", site_id=None)
        stmt = select(RestoreTest)
        rows, envelope = await paginate(
            session, stmt, params, sortable=RESTORE_TEST_SORTABLE, default_sort=RestoreTest.started_at
        )
        return {**envelope, "items": [_restore_test_dict(r) for (r,) in rows]}
