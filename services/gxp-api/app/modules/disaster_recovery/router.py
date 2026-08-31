"""Document 76 (SPEC-DATA-008) REST surface. The 3 operations Document 76 # 7 lists:

  POST /platform/v1/recovery-objectives   -- set/update a component's RPO/RTO tier (state-changing)
  GET  /platform/v1/backups/health        -- backup freshness for every declared component
  POST /platform/v1/restore-tests         -- record an executed restore/PITR drill (state-changing)

No signature (Document 106 has no SPEC-DATA-008 row).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.disaster_recovery import commands
from app.modules.disaster_recovery.models import BackupInventory, RecoveryObjectiveProfile
from app.modules.disaster_recovery.recovery import verify_backup_freshness
from app.modules.policy.service import evaluate_policy
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/platform/v1", tags=["disaster-recovery"])


@router.post("/recovery-objectives", response_model=MutationReceipt)
async def post_recovery_objective(
    cmd: commands.CreateRecoveryObjectiveProfileCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="dr.recovery_objective.manage", site_id=None)
        return await commands.create_recovery_objective_profile(session, cmd, actor.user_id)


@router.get("/backups/health")
async def get_backup_health(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="dr.backup.view", site_id=None)
        components = (
            await session.execute(select(RecoveryObjectiveProfile).where(RecoveryObjectiveProfile.state == "EFFECTIVE"))
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
        await evaluate_policy(session, actor.user_id, action="dr.restore_test.execute", site_id=None)
        return await commands.execute_postgres_restore_test(session, cmd, actor.user_id)
