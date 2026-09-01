"""Document 87 (SPEC-VAL-009) Mutation Gateway command handlers -- Data Migration, Conversion, Cutover
& Reconciliation Validation.

Signature policy (Document 106):
  * Row 153 -- `POST /validation/v1/migrations/{id}/approve` requires an `Approved` signature from an
    independent QA Releaser ("Module approver role (QA Manager / Head of Quality per record class)",
    resolved to `QA Releaser` -- the same mapping WP-12 uses), reason mandatory, signer independent of
    the migration plan author. `record_type="migration_run"`, `action="approve"`.
  * `migrations/plans`, `migrations/runs`, `migrations/{id}/reconcile` carry no Document 106 row --
    unsigned, RBAC-gated only.

Reconciliation tolerances (MIGV-FR-009/010/020) are **customer-authored per-plan data**
(`migration_validation_plan.reconciliation_rules`), never a platform constant: no approved baseline
gives WP-14 a numeric migration reconciliation tolerance, so the platform ships none and
`reconcile_migration_run()` fails closed (`VALIDATION_FAILED`) when a rule for a compared data class
is missing -- it never assumes "0 variance" or any default. See SG-171 in
`docs/generated/18_SPEC_GAPS.md`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models_wp14 import (
    MigrationReconciliation,
    MigrationRun,
    MigrationValidationPlan,
)
from app.modules.validation.shared import (
    finalize,
    receipt_from_existing,
    resolve_signature,
    verify_reauth_and_consume,
)
from app.mutation.errors import (
    InvalidTransitionError,
    LegacyTraceMissingError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_MIGRATION_PLAN = "migration_validation_plan"
RECORD_TYPE_MIGRATION_RUN = "migration_run"
RECORD_TYPE_MIGRATION_RECONCILIATION = "migration_reconciliation"


# =====================================================================================================
# createMigrationValidationPlan() -- FN-0841 (+ profileMigrationSource() FN-0842, folded in)
# =====================================================================================================

class CreateMigrationValidationPlanCommand(CommandEnvelope):
    plan_number: str
    source_system: str
    scope: str
    cutoff_at: datetime
    source_snapshot_ref: str
    source_snapshot_hash: str
    mapping_version: str
    transform_version: str
    acceptance_criteria: str
    regulated_history_strategy: str
    rollback_strategy: str
    legacy_access_strategy: str
    target_system: str = "eBMR/eDHR platform"
    source_timezone: str | None = None
    mappings: list[dict] = []
    reconciliation_rules: list[dict] = []   # [{data_class, count_tolerance, control_total_tolerance, critical_fields: [...]}]
    source_profile: dict | None = None      # {row_counts, duplicates, orphans, invalid_values} -- profileMigrationSource
    retention_class: str | None = None


async def create_migration_validation_plan(
    session: AsyncSession, cmd: CreateMigrationValidationPlanCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if not cmd.source_snapshot_hash.strip():
        raise ValidationFailedError("source_snapshot_hash is required -- the exact source export is frozen (MIGV-FR-002)")
    if not cmd.reconciliation_rules:
        raise ValidationFailedError(
            "reconciliation_rules is required (MIGV-FR-009/020) -- the platform ships no default tolerance (SG-171)"
        )
    for rule in cmd.reconciliation_rules:
        if not rule.get("data_class"):
            raise ValidationFailedError("each reconciliation rule needs a data_class")
    if not cmd.mappings:
        raise ValidationFailedError("mappings is required (MIGV-FR-004)")

    profiled = cmd.source_profile is not None
    row = MigrationValidationPlan(
        site_id=site_id, plan_number=cmd.plan_number, source_system=cmd.source_system,
        target_system=cmd.target_system, scope=cmd.scope, cutoff_at=cmd.cutoff_at,
        source_snapshot_ref=cmd.source_snapshot_ref, source_snapshot_hash=cmd.source_snapshot_hash,
        source_timezone=cmd.source_timezone, mappings=cmd.mappings, mapping_version=cmd.mapping_version,
        transform_version=cmd.transform_version, reconciliation_rules=cmd.reconciliation_rules,
        acceptance_criteria=cmd.acceptance_criteria, source_profile=cmd.source_profile,
        authored_by_user_id=actor_user_id,
        regulated_history_strategy=cmd.regulated_history_strategy, rollback_strategy=cmd.rollback_strategy,
        legacy_access_strategy=cmd.legacy_access_strategy, retention_class=cmd.retention_class,
        state="PROFILED" if profiled else "DRAFT", version=1,
    )
    session.add(row)
    await session.flush()

    # MIGV-FR-003: profiling the frozen source (completeness / duplicates / orphans / invalid values)
    # is an integral part of establishing the plan; when a profile is supplied its own event is
    # emitted against the plan aggregate (profileMigrationSource, FN-0842, has no dedicated §7 endpoint).
    if profiled:
        await write_outbox_event(
            session, event_type="MigrationSourceProfiled", aggregate_type=RECORD_TYPE_MIGRATION_PLAN,
            aggregate_id=row.id, aggregate_version=1,
            payload={"source_snapshot_hash": row.source_snapshot_hash,
                     "row_counts": cmd.source_profile.get("row_counts"),
                     "duplicates": cmd.source_profile.get("duplicates"),
                     "orphans": cmd.source_profile.get("orphans")},
            correlation_id=uuid.uuid4(),
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_MIGRATION_PLAN,
        aggregate_id=row.id, version=row.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_value=None,
        new_value={"plan_number": row.plan_number, "source_system": row.source_system,
                   "source_snapshot_hash": row.source_snapshot_hash, "profiled": profiled},
        event_type="MigrationValidationPlanCreated", expected_version=None,
        command_type="CreateMigrationValidationPlan", site_id=site_id,
    )


# =====================================================================================================
# executeMigrationDryRun() -- FN-0843 (also the production CUTOVER run)
# =====================================================================================================

class ExecuteMigrationRunCommand(CommandEnvelope):
    plan_id: uuid.UUID
    run_type: str                          # DRY_RUN | CUTOVER
    source_hash: str
    scripts_config: dict
    counts: dict = {}                      # {by_class: {read, transformed, loaded, rejected}}
    control_totals: dict = {}              # {by_class: {sum, hash}}
    identity_map: dict = {}                # {legacy_id: new_id}
    rejected_records: list[dict] = []      # [{legacy_id, reason, disposition}]
    attachments: dict = {}                 # {expected_count, loaded_count, hash_matches}
    legacy_signatures: dict = {}           # {preserved_count}
    legacy_audit: dict = {}                # {mode, ref}
    target_refs: dict = {}
    errors: list[dict] = []
    is_delta: bool = False
    sandbox: bool = True
    status: str = "COMPLETED"             # COMPLETED | FAILED | INTERRUPTED
    prior_run_id: uuid.UUID | None = None


async def execute_migration_dry_run(
    session: AsyncSession, cmd: ExecuteMigrationRunCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.run_type not in ("DRY_RUN", "CUTOVER"):
        raise ValidationFailedError("run_type must be DRY_RUN or CUTOVER")
    if cmd.status not in ("COMPLETED", "FAILED", "INTERRUPTED"):
        raise ValidationFailedError("status must be COMPLETED, FAILED or INTERRUPTED")

    plan = await session.get(MigrationValidationPlan, cmd.plan_id)
    if plan is None:
        raise NotFoundError("migration validation plan not found")
    if plan.state == "ROLLED_BACK":
        raise InvalidTransitionError("migration plan has been rolled back", current_state=plan.state)

    # MIGV-FR-002: a run's source_hash must match the plan's frozen snapshot -- unless it is an
    # explicit cutover delta run (MIGV-FR-017), which reconciles late changes on top of the baseline.
    if cmd.source_hash != plan.source_snapshot_hash and not cmd.is_delta:
        raise ValidationFailedError(
            "run source_hash does not match the plan's frozen source snapshot (MIGV-FR-002); "
            "set is_delta for a cutover delta run",
            plan_hash=plan.source_snapshot_hash, run_hash=cmd.source_hash,
        )
    # Document 87 §13 / MIGV-FR-012: legacy signature evidence is preserved as provenance, never
    # recreated as a new platform signing -- the mode is fixed here regardless of caller input.
    legacy_signatures = dict(cmd.legacy_signatures)
    legacy_signatures["mode"] = "PROVENANCE_MARKED"

    run_number = 1 + len(
        list((await session.execute(select(MigrationRun).where(MigrationRun.plan_id == plan.id))).scalars())
    )
    row = MigrationRun(
        plan_id=plan.id, plan_version=plan.version, run_type=cmd.run_type, run_number=run_number,
        prior_run_id=cmd.prior_run_id, source_hash=cmd.source_hash, is_delta=cmd.is_delta,
        sandbox=cmd.sandbox, scripts_config=cmd.scripts_config, counts=cmd.counts,
        control_totals=cmd.control_totals, identity_map=cmd.identity_map,
        rejected_records=cmd.rejected_records, attachments=cmd.attachments,
        legacy_signatures=legacy_signatures, legacy_audit=cmd.legacy_audit, target_refs=cmd.target_refs,
        errors=cmd.errors, status=cmd.status, state=cmd.status,
        retention_class=plan.retention_class, version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_MIGRATION_RUN,
        aggregate_id=row.id, version=row.version, action="Performed", actor_user_id=actor_user_id,
        reason=None, old_value=None,
        new_value={"plan_id": str(plan.id), "run_type": cmd.run_type, "run_number": run_number,
                   "is_delta": cmd.is_delta, "status": cmd.status,
                   "rejected_count": len(cmd.rejected_records)},
        event_type="MigrationDryRunCompleted", expected_version=None,
        command_type="ExecuteMigrationRun", site_id=site_id,
    )


# =====================================================================================================
# reconcileMigrationRun() -- FN-0844
# =====================================================================================================

class ReconcileMigrationRunCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int
    count_comparison: dict                 # {by_class: {source, target}}
    control_total_comparison: dict = {}    # {by_class: {source_sum, target_sum, source_hash, target_hash}}
    critical_field_comparison: dict = {}   # {method: FULL_AUTOMATED|SAMPLING, sample_size, mismatches: [...]}
    attachment_comparison: dict = {}       # {expected, loaded, hash_mismatches: [...]}
    reference_integrity: dict = {}         # {orphans_after_import: [...]}
    deviations: list[dict] = []            # [{ref, data_class, disposition}]


def _within(actual: int, tolerance) -> bool:
    try:
        return abs(int(actual)) <= int(tolerance)
    except (TypeError, ValueError):
        return False


async def reconcile_migration_run(
    session: AsyncSession, cmd: ReconcileMigrationRunCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    run = await session.get(MigrationRun, cmd.run_id)
    if run is None:
        raise NotFoundError("migration run not found")
    if run.status != "COMPLETED":
        raise InvalidTransitionError("only a COMPLETED migration run can be reconciled", current_state=run.status)
    if run.version != cmd.expected_version:
        raise StaleVersionError("migration run changed since this request was prepared", current_version=run.version)

    plan = await session.get(MigrationValidationPlan, run.plan_id)
    rules_by_class = {r["data_class"]: r for r in (plan.reconciliation_rules or [])}

    # MIGV-FR-010: never validate by count alone -- a reconciliation with no critical-field comparison
    # method recorded cannot PASS.
    method = cmd.critical_field_comparison.get("method")
    if method not in ("FULL_AUTOMATED", "SAMPLING"):
        raise ValidationFailedError(
            "critical_field_comparison.method must be FULL_AUTOMATED or SAMPLING (MIGV-FR-010)"
        )
    if method == "SAMPLING" and not cmd.critical_field_comparison.get("sample_size"):
        raise ValidationFailedError("a SAMPLING critical-field comparison must record its sample_size (MIGV-FR-010)")

    count_result: dict = {}
    for data_class, pair in cmd.count_comparison.items():
        rule = rules_by_class.get(data_class)
        if rule is None:
            # SG-171: fail closed -- the platform has no default tolerance for a class the plan did not rule on.
            raise ValidationFailedError(
                "no reconciliation rule for this data class -- cannot reconcile without a customer-authored "
                "tolerance (MIGV-FR-009, SG-171)",
                data_class=data_class,
            )
        delta = int(pair.get("source", 0)) - int(pair.get("target", 0))
        count_result[data_class] = {
            "source": pair.get("source"), "target": pair.get("target"), "delta": delta,
            "within_tolerance": _within(delta, rule.get("count_tolerance", 0)),
        }

    ct_result: dict = {}
    for data_class, pair in (cmd.control_total_comparison or {}).items():
        rule = rules_by_class.get(data_class, {})
        sum_delta = int(pair.get("source_sum", 0)) - int(pair.get("target_sum", 0))
        ct_result[data_class] = {
            "sum_delta": sum_delta,
            "within_tolerance": _within(sum_delta, rule.get("control_total_tolerance", 0)),
            "hash_match": pair.get("source_hash") == pair.get("target_hash"),
        }

    cf_mismatches = cmd.critical_field_comparison.get("mismatches") or []
    attach_mismatches = cmd.attachment_comparison.get("hash_mismatches") or []
    orphans = cmd.reference_integrity.get("orphans_after_import") or []
    undispositioned = [d for d in cmd.deviations if not d.get("disposition")]

    passed = (
        all(v["within_tolerance"] for v in count_result.values())
        and all(v["within_tolerance"] and v["hash_match"] for v in ct_result.values())
        and not cf_mismatches
        and not attach_mismatches
        and not orphans
        and not undispositioned
    )
    outcome = "PASS" if passed else "FAIL"

    row = MigrationReconciliation(
        run_id=run.id, run_version=run.version,
        reconciliation_profile={"rules": plan.reconciliation_rules, "critical_field_method": method},
        count_comparison=count_result, hash_comparison={"by_class": {k: v.get("hash_match") for k, v in ct_result.items()}},
        control_total_comparison=ct_result, critical_field_comparison=cmd.critical_field_comparison,
        attachment_comparison=cmd.attachment_comparison, reference_integrity=cmd.reference_integrity,
        deviations=cmd.deviations, outcome=outcome, state="COMPLETED", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_MIGRATION_RECONCILIATION,
        aggregate_id=row.id, version=row.version, action="Performed", actor_user_id=actor_user_id,
        reason=None, old_value=None,
        new_value={"run_id": str(run.id), "outcome": outcome,
                   "critical_field_mismatches": len(cf_mismatches), "orphans": len(orphans),
                   "undispositioned_deviations": len(undispositioned)},
        event_type="MigrationReconciled", expected_version=None, command_type="ReconcileMigrationRun",
        site_id=site_id,
    )


# =====================================================================================================
# approveMigrationCutover() -- FN-0845
# =====================================================================================================

class ApproveMigrationCutoverCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_migration_cutover(
    session: AsyncSession, cmd: ApproveMigrationCutoverCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to approve a migration cutover (Document 106 row 153)")

    run = await session.get(MigrationRun, cmd.run_id)
    if run is None:
        raise NotFoundError("migration run not found")
    if run.run_type != "CUTOVER":
        raise ValidationFailedError("only a CUTOVER run is approved for production cutover (MIGV-FR-020)")
    if run.status != "COMPLETED":
        raise InvalidTransitionError("migration run is not COMPLETED", current_state=run.status)
    if run.state == "ACCEPTED":
        raise InvalidTransitionError("migration run already accepted", current_state=run.state)
    if run.version != cmd.expected_version:
        raise StaleVersionError("migration run changed since this request was prepared", current_version=run.version)

    plan = await session.get(MigrationValidationPlan, run.plan_id)
    # Document 106 row 153 SoD: the cutover approver is independent of the migration plan author.
    if plan is not None and actor_user_id == plan.authored_by_user_id:
        raise ValidationFailedError(
            "the migration cutover approver must be independent of the plan author (Document 106 row 153)"
        )

    # MIGV-FR-020: final migration is accepted only after a PASSing reconciliation with every
    # deviation dispositioned.
    recs = list(
        (await session.execute(
            select(MigrationReconciliation).where(MigrationReconciliation.run_id == run.id)
        )).scalars()
    )
    if not recs:
        raise ValidationFailedError("cannot approve a cutover with no reconciliation (MIGV-FR-020)")
    latest = max(recs, key=lambda r: r.created_at)
    if latest.outcome != "PASS":
        raise ValidationFailedError(
            "the latest reconciliation for this run is not PASS (MIGV-FR-020)", reconciliation_id=str(latest.id)
        )
    if any(not d.get("disposition") for d in latest.deviations):
        raise ValidationFailedError("every reconciliation deviation must be dispositioned before approval (MIGV-FR-020)")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_MIGRATION_RUN, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=run.id, record_version=run.version,
        )

    run.state = "ACCEPTED"
    run.status = "ACCEPTED"
    run.approved_by_user_id = actor_user_id
    run.approved_at = datetime.now(timezone.utc)
    run.signature_id = signature_id
    run.version += 1
    if plan is not None:
        plan.state = "ACCEPTED"
        plan.version += 1

    # Document 06 (VLT-FR-001): an accepted migration cutover is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_MIGRATION_RUN, business_id=str(run.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "plan_number": plan.plan_number if plan else None, "source_hash": run.source_hash,
            "counts": run.counts, "control_totals": run.control_totals,
            "reconciliation_id": str(latest.id), "reconciliation_outcome": latest.outcome,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_MIGRATION_RUN,
        aggregate_id=run.id, version=run.version, action="Approved", actor_user_id=actor_user_id,
        reason=cmd.reason, old_value={"state": "COMPLETED"},
        new_value={"state": "ACCEPTED", "reconciliation_id": str(latest.id)},
        event_type="MigrationAccepted", expected_version=cmd.expected_version,
        command_type="ApproveMigrationCutover", site_id=site_id, signature_id=signature_id,
    )


# =====================================================================================================
# verifyLegacyRecordTrace() -- FN-0846 (inspection read; GET, no state change, no event)
# =====================================================================================================

async def verify_legacy_record_trace(session: AsyncSession, plan_id: uuid.UUID, legacy_id: str) -> dict:
    """MIGV-FR-007/021: given a legacy identifier, return the new-system id and provenance, or the
    controlled legacy-archive reference. Raises LEGACY_TRACE_MISSING (ValidationFailedError, per the
    Document 87 §4 error name) when neither is available.
    """
    plan = await session.get(MigrationValidationPlan, plan_id)
    if plan is None:
        raise NotFoundError("migration validation plan not found")

    runs = list(
        (await session.execute(select(MigrationRun).where(MigrationRun.plan_id == plan_id))).scalars()
    )
    for run in sorted(runs, key=lambda r: r.created_at, reverse=True):
        new_id = (run.identity_map or {}).get(legacy_id)
        if new_id:
            return {
                "legacy_id": legacy_id, "new_id": new_id, "migration_run_id": str(run.id),
                "run_type": run.run_type, "source_hash": run.source_hash,
                "legacy_audit": run.legacy_audit, "provenance": "IDENTITY_MAP",
            }
        for rejected in run.rejected_records or []:
            if str(rejected.get("legacy_id")) == str(legacy_id):
                return {
                    "legacy_id": legacy_id, "new_id": None, "migration_run_id": str(run.id),
                    "rejected": True, "reason": rejected.get("reason"),
                    "disposition": rejected.get("disposition"), "provenance": "REJECTED_RECORD",
                }

    if plan.legacy_access_strategy and plan.legacy_access_strategy.strip():
        return {
            "legacy_id": legacy_id, "new_id": None, "legacy_archive": plan.legacy_access_strategy,
            "provenance": "LEGACY_ARCHIVE",
        }
    raise LegacyTraceMissingError(
        "no trace for this legacy id in any run or legacy archive", legacy_id=legacy_id
    )
