"""Document 69 (SPEC-DATA-001) REST surface, prefix `/platform/v1`. Exactly the 4 operations
Document 69 # 7 lists:

  GET  /platform/v1/data-ownership/{entityType}              -- resolve the authoritative owner/store
  GET  /platform/v1/projections/{type}/{id}/freshness        -- is this projected record stale?
  POST /platform/v1/projections/{type}:rebuild               -- rebuild a projection (state-changing)
  GET  /platform/v1/data-dictionary                          -- the generated ownership dictionary

Reads are RBAC-gated only. The one state-changing operation carries `expected_version` +
`idempotency_key` and returns a `MutationReceipt`; it is **not** signed (Document 106 # 10 exempts
projection rebuilds).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.dataops import commands
from app.modules.dataops.consistency import get_projection_freshness
from app.modules.dataops.registry import build_data_dictionary, resolve_data_owner
from app.modules.dataops.signals import emit_projection_stale_detected
from app.modules.policy.service import evaluate_policy
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/platform/v1", tags=["dataops"])


@router.get("/data-ownership/{entity_type}")
async def get_data_ownership(
    entity_type: str,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """`resolveDataOwner()` -- DATA-FR-001. Fail-closed: an unregistered entity type is
    `DATA_OWNER_UNKNOWN` (404), never a guessed owner."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="data_ownership.view", site_id=None)
        row = await resolve_data_owner(session, entity_type)
        return {
            "entity_type": row.entity_type,
            "authoritative_service": row.authoritative_service,
            "authoritative_store": row.authoritative_store,
            "projection_targets": row.projection_targets,
            "tenant_scoped": row.tenant_scoped,
            "site_scoped": row.site_scoped,
            "classification": row.classification,
            "retention_policy_id": str(row.retention_policy_id) if row.retention_policy_id else None,
            "encryption_profile_id": str(row.encryption_profile_id) if row.encryption_profile_id else None,
            "source_reference": row.source_reference,
            "state": row.state,
            "version": row.version,
        }


@router.get("/projections/{projection_type}/{entity_id}/freshness")
async def get_freshness(
    projection_type: str, entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """`getProjectionFreshness()` -- DATA-FR-008. Returns source version, projected_at and
    stale/degraded status so a caller can decide whether to re-read the authoritative record before a
    regulated action (DATA-FR-007)."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="data_ownership.view", site_id=None)
        result = await get_projection_freshness(
            session, projection_type=projection_type, entity_id=entity_id, raise_if_stale=False
        )
    if result["stale"]:
        # Operational signal, best-effort, its own committed transaction (never blocks the read).
        await emit_projection_stale_detected(result)
    return result


@router.post("/projections/{projection_type}:rebuild", response_model=MutationReceipt)
async def post_rebuild_projection(
    projection_type: str, cmd: commands.RebuildProjectionCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """`rebuildProjection()` -- DATA-FR-011/028. State-changing; RBAC-gated; no signature
    (Document 106 # 10). Returns a `MutationReceipt`."""
    if cmd.projection_type != projection_type:
        from app.mutation.errors import ValidationFailedError

        raise ValidationFailedError("projection_type in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="projection.rebuild", site_id=None)
        return await commands.rebuild_projection(session, cmd, actor.user_id)


@router.get("/data-dictionary")
async def get_data_dictionary(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """`DATA-FR-027` -- the machine-readable entity / owner / store / classification / projection
    dictionary, generated from the live registry."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="data_dictionary.view", site_id=None)
        return await build_data_dictionary(session)
