"""MDS-FR-004/005/008/024, ERP-ARC-006/007 — the automated master-data pull pipeline: `fetch_changes()`
-> normalize -> match -> propose/reconcile/suspend.

Per Document 113 §6 (see `router.py`'s module docstring), Document 52's master-data sync is "jobs behind
the Document 53 integration gateway; no independent public API" -- `sync_master_data()` is therefore a
plain internal entry point (invoked by a scheduler/operator/test, same posture as `dispatch_erp_command`
being invoked by a worker rather than exposed as its own public write endpoint) and never gets its own
router route.

Both MDS-FR-004 ("bulk initial import uses staging, validation and reconciliation before activation") and
MDS-FR-005 ("ongoing incremental sync") are the same operation at a different starting cursor -- Document
52 draws no functional line between them, so both share this one function: `cursor=None` (no prior
`ErpSyncCheckpoint`) is the bulk/initial case, `cursor=<checkpoint>` is the incremental case. "Staging" is
the existing `ErpExternalMapping` row at `mapping_status=PROPOSED` (no separate staging table is needed --
propose-then-approve already *is* stage-then-activate); "validation" is `matching.normalize_master_record`
+ `match_internal_entity`; "reconciliation before activation" is the existing human `approve_mapping()`
call this pipeline deliberately never bypasses (SG-124's "never auto-accept" posture applied to identity
matching, not just reconciliation-difference tolerances).

Structured like `dispatch_erp_command()` (commands.py docstring, rule 01: no external I/O inside a
Mutation Gateway transaction): the one external `fetch_changes()` HTTP call happens first, with no
transaction open; every persisted outcome after that runs through the existing per-record Mutation
Gateway command functions, each its own freshly-loaded, separately committed transaction -- no ORM
instance is ever carried across a transaction boundary (each block re-`session.get()`s what it needs,
same discipline `dispatch_erp_command` and `_load_command_for_update` already use).
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp import commands as erp_commands
from app.modules.erp import matching
from app.modules.erp.commands import (
    AdvanceSyncCheckpointCommand,
    ApplyExternalChangeCommand,
    ProposeMappingCommand,
    SuspendMappingCommand,
    advance_sync_checkpoint,
    apply_external_change,
    propose_mapping,
    suspend_mapping,
)
from app.modules.erp.models import MAPPING_ENTITY_TYPES, ErpExternalMapping, ErpInstance, ErpSyncCheckpoint
from app.mutation.errors import ErpMappingConflictError, NotFoundError, ValidationFailedError


@dataclass
class MasterSyncOutcome:
    fetched: int = 0
    pages_fetched: int = 0
    skipped_unrecognized: int = 0
    proposed_explicit: int = 0
    proposed_fuzzy: int = 0
    reconciled_active: int = 0
    conflicts: int = 0
    suspended: int = 0
    unmatched: int = 0
    proposal_ids: list[str] = field(default_factory=list)


async def sync_master_data(
    session: AsyncSession, *, erp_instance_id: uuid.UUID, entity_type: str, actor_user_id: uuid.UUID, max_pages: int = 1,
) -> MasterSyncOutcome:
    """The automated pull: `fetch_changes()` from the last checkpoint (or from the beginning, for a
    first/bulk run) -> normalize each record -> match or reconcile or suspend -> advance the checkpoint.
    `max_pages` bounds how many `has_more` pages this single call will walk (a real scheduler calls this
    repeatedly on an interval; a bulk initial import passes a higher `max_pages` to drain the vendor's
    full backlog in one operator-triggered run)."""

    if entity_type not in MAPPING_ENTITY_TYPES:
        raise ValidationFailedError("Unrecognized entity_type", allowed=list(MAPPING_ENTITY_TYPES))

    async with session.begin():
        instance = await session.get(ErpInstance, erp_instance_id)
        if instance is None:
            raise NotFoundError("ERP instance not found")
        vendor, site_id = instance.vendor, instance.site_id
        adapter = erp_commands.build_adapter(instance)

        checkpoint = (
            await session.execute(
                select(ErpSyncCheckpoint).where(
                    ErpSyncCheckpoint.erp_instance_id == erp_instance_id, ErpSyncCheckpoint.entity_type == entity_type,
                )
            )
        ).scalar_one_or_none()
        cursor = checkpoint.cursor_value if checkpoint else None

    outcome = MasterSyncOutcome()

    for _ in range(max(1, max_pages)):
        page = await adapter.fetch_changes(entity_type, cursor)  # external I/O -- no open transaction
        outcome.pages_fetched += 1
        outcome.fetched += len(page.records)

        for raw in page.records:
            normalized = matching.normalize_master_record(vendor, entity_type, raw)
            if normalized is None:
                outcome.skipped_unrecognized += 1
                continue
            async with session.begin():
                await _process_record(session, erp_instance_id, vendor, site_id, entity_type, normalized, actor_user_id, outcome)

        if page.next_cursor and page.next_cursor != cursor:
            async with session.begin():
                await advance_sync_checkpoint(
                    session,
                    AdvanceSyncCheckpointCommand(
                        erp_instance_id=erp_instance_id, entity_type=entity_type, cursor_value=page.next_cursor,
                        idempotency_key=f"sync-checkpoint:{erp_instance_id}:{entity_type}:{page.next_cursor}",
                    ),
                    actor_user_id,
                )
        cursor = page.next_cursor
        if not page.has_more:
            break

    return outcome


async def _process_record(
    session: AsyncSession, erp_instance_id: uuid.UUID, vendor: str, site_id: uuid.UUID | None, entity_type: str,
    normalized: matching.NormalizedMasterRecord, actor_user_id: uuid.UUID, outcome: MasterSyncOutcome,
) -> None:
    existing = (
        await session.execute(
            select(ErpExternalMapping).where(
                ErpExternalMapping.erp_instance_id == erp_instance_id,
                ErpExternalMapping.entity_type == entity_type,
                ErpExternalMapping.external_id == normalized.external_id,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        # MDS-FR-024: an explicit vendor deactivation signal on an already-active mapping suspends the
        # projection -- it never deletes the mapping row or the GxP history behind it (SuspendMapping).
        if normalized.is_active is False and existing.mapping_status == "ACTIVE":
            await suspend_mapping(
                session,
                SuspendMappingCommand(
                    mapping_id=existing.id, expected_version=existing.version,
                    reason=f"External record '{normalized.external_id}' reported inactive by {vendor}",
                    idempotency_key=f"sync-suspend:{existing.id}:{existing.version}",
                ),
                actor_user_id,
            )
            outcome.suspended += 1
            return

        if (
            existing.mapping_status == "ACTIVE" and normalized.external_code
            and normalized.external_code != existing.external_code
        ):
            try:
                await apply_external_change(
                    session,
                    ApplyExternalChangeCommand(
                        mapping_id=existing.id, expected_version=existing.version, field_name="external_code",
                        proposed_value={"external_code": normalized.external_code},
                        idempotency_key=f"sync-apply:{existing.id}:{existing.version}:{normalized.external_code}",
                    ),
                    actor_user_id,
                )
                outcome.reconciled_active += 1
            except ErpMappingConflictError:
                outcome.conflicts += 1
        return  # already mapped (any status) -- never re-propose an external_id this pipeline has seen

    if normalized.is_active is False:
        # A never-before-mapped record that is already reported inactive: nothing to stage or suspend.
        outcome.unmatched += 1
        return

    candidate = await matching.match_internal_entity(
        session, entity_type=entity_type, site_id=site_id,
        external_code=normalized.external_code, display_name=normalized.display_name,
    )
    if candidate is None:
        outcome.unmatched += 1
        return

    try:
        receipt = await propose_mapping(
            session,
            ProposeMappingCommand(
                erp_instance_id=erp_instance_id, entity_type=entity_type, internal_id=candidate.internal_id,
                external_id=normalized.external_id, external_code=normalized.external_code,
                match_method=candidate.match_method, confidence=f"{candidate.score:.4f}",
                evidence={"source": "automated_sync", "vendor_display_name": normalized.display_name},
                idempotency_key=f"sync-propose:{erp_instance_id}:{entity_type}:{normalized.external_id}",
            ),
            actor_user_id,
        )
    except ErpMappingConflictError:
        outcome.conflicts += 1
        return

    outcome.proposal_ids.append(str(receipt.aggregate_id))
    if candidate.match_method == "EXPLICIT_ID":
        outcome.proposed_explicit += 1
    else:
        outcome.proposed_fuzzy += 1
