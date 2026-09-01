"""WP-14 Document 87 (SPEC-VAL-009) -- Data Migration, Conversion, Cutover & Reconciliation
Validation. Executable evidence for plan -> run -> reconcile -> approve, the SG-171 fail-closed
"no reconciliation rule" behaviour, MIGV-FR-010 "never validate by count alone", MIGV-FR-012 legacy
signatures preserved-as-provenance, the Document 106 row 153 signature + SoD on cutover approval, the
legacy-trace inspection read and its LEGACY_TRACE_MISSING error, and the mandatory negatives.
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.core.db import SessionLocal
from app.modules.signature import service as signature_service
from app.modules.validation import commands_migration as mig
from app.modules.validation.models_wp14 import MigrationReconciliation, MigrationRun, MigrationValidationPlan
from app.modules.validation.shared import record_hash
from app.mutation.errors import (
    InvalidTransitionError,
    LegacyTraceMissingError,
    StaleVersionError,
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


_HASH = "a" * 64


def _plan_cmd(**over):
    base = dict(
        idempotency_key=idem(), plan_number=f"MIG-{uuid.uuid4().hex[:8]}", source_system="LegacyMES",
        scope="batch records + material lots", cutoff_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        source_snapshot_ref="s3://exports/legacy-2026-08-01.dump", source_snapshot_hash=_HASH,
        mapping_version="m-1.0", transform_version="t-1.0",
        acceptance_criteria="counts within tolerance, no undispositioned deviation",
        regulated_history_strategy="import provenance-marked history", rollback_strategy="restore snapshot + replay delta",
        legacy_access_strategy="read-only legacy archive at archive://legacy-mes",
        mappings=[{"source_entity": "BATCH", "target_entity": "batch", "field_map": {}}],
        reconciliation_rules=[
            {"data_class": "batch", "count_tolerance": 0, "control_total_tolerance": 0, "critical_fields": ["batch_number"]},
            {"data_class": "material_lot", "count_tolerance": 2, "control_total_tolerance": 0},
        ],
        source_profile={"row_counts": {"batch": 100}, "duplicates": [], "orphans": []},
    )
    base.update(over)
    return mig.CreateMigrationValidationPlanCommand(**base)


def _run_cmd(plan_id, **over):
    base = dict(
        idempotency_key=idem(), plan_id=plan_id, run_type="CUTOVER", source_hash=_HASH,
        scripts_config={"script": "convert.py@t-1.0"},
        counts={"batch": {"read": 100, "transformed": 100, "loaded": 100, "rejected": 0}},
        control_totals={"batch": {"sum": 5000, "hash": "h1"}},
        identity_map={"LEG-1": "NEW-1", "LEG-2": "NEW-2"},
        rejected_records=[{"legacy_id": "LEG-9", "reason": "invalid date", "disposition": "excluded per DEV-1"}],
        attachments={"expected_count": 10, "loaded_count": 10, "hash_matches": True},
        legacy_signatures={"preserved_count": 42},
        legacy_audit={"mode": "IMPORTED_PROVENANCE", "ref": "archive://legacy-mes/audit"},
        status="COMPLETED",
    )
    base.update(over)
    return mig.ExecuteMigrationRunCommand(**base)


def _recon_cmd(run_id, version, **over):
    base = dict(
        idempotency_key=idem(), run_id=run_id, expected_version=version,
        count_comparison={"batch": {"source": 100, "target": 100}},
        control_total_comparison={"batch": {"source_sum": 5000, "target_sum": 5000, "source_hash": "h1", "target_hash": "h1"}},
        critical_field_comparison={"method": "FULL_AUTOMATED", "mismatches": []},
        attachment_comparison={"hash_mismatches": []},
        reference_integrity={"orphans_after_import": []},
        deviations=[],
    )
    base.update(over)
    return mig.ReconcileMigrationRunCommand(**base)


# -------------------------------------------------------------------------------------------------

async def test_migration_full_flow_plan_run_reconcile_approve(db, seeded):
    author = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            run = await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            assert run_row.legacy_signatures["mode"] == "PROVENANCE_MARKED"  # MIGV-FR-012
            recon = await mig.reconcile_migration_run(s, _recon_cmd(run.aggregate_id, run_row.version), author, None)
        async with s.begin():
            rec_row = await s.get(MigrationReconciliation, recon.aggregate_id)
            assert rec_row.outcome == "PASS"
            run_row = await s.get(MigrationRun, run.aggregate_id)
            ver = run_row.version
            ch = await _challenge(s, releaser, "migration_run", "approve", run_row.id, ver)
        async with s.begin():
            receipt = await mig.approve_migration_cutover(
                s, mig.ApproveMigrationCutoverCommand(
                    idempotency_key=idem(), run_id=run.aggregate_id, expected_version=ver,
                    reason="reconciliation PASS, cutover accepted", challenge_id=ch, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
            assert receipt.signature_id is not None
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            assert run_row.state == "ACCEPTED"
            plan_row = await s.get(MigrationValidationPlan, plan.aggregate_id)
            assert plan_row.state == "ACCEPTED"


async def test_migration_reconcile_fails_closed_without_rule_for_class(db, seeded):
    """SG-171 / MIGV-FR-009: a compared data class with no reconciliation rule cannot be reconciled."""
    author = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            run = await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            with pytest.raises(ValidationFailedError):
                await mig.reconcile_migration_run(
                    s, _recon_cmd(run.aggregate_id, run_row.version,
                                  count_comparison={"equipment": {"source": 5, "target": 5}}),
                    author, None,
                )


async def test_migration_reconcile_requires_critical_field_method(db, seeded):
    """MIGV-FR-010: never validate by count alone -- a missing critical-field method fails."""
    author = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            run = await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            with pytest.raises(ValidationFailedError):
                await mig.reconcile_migration_run(
                    s, _recon_cmd(run.aggregate_id, run_row.version, critical_field_comparison={}),
                    author, None,
                )


async def test_migration_reconcile_fail_outcome_on_count_delta(db, seeded):
    author = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            run = await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            recon = await mig.reconcile_migration_run(
                s, _recon_cmd(run.aggregate_id, run_row.version,
                              count_comparison={"batch": {"source": 100, "target": 97}}),
                author, None,
            )
        async with s.begin():
            rec_row = await s.get(MigrationReconciliation, recon.aggregate_id)
            assert rec_row.outcome == "FAIL"


async def test_migration_approve_blocked_when_reconciliation_not_pass(db, seeded):
    author = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            run = await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            await mig.reconcile_migration_run(
                s, _recon_cmd(run.aggregate_id, run_row.version,
                              count_comparison={"batch": {"source": 100, "target": 90}}),
                author, None,
            )
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            ver = run_row.version
            ch = await _challenge(s, releaser, "migration_run", "approve", run_row.id, ver)
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await mig.approve_migration_cutover(
                    s, mig.ApproveMigrationCutoverCommand(
                        idempotency_key=idem(), run_id=run.aggregate_id, expected_version=ver,
                        reason="try", challenge_id=ch, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )


async def test_migration_approve_sod_author_cannot_approve(db, seeded):
    """Document 106 row 153: the cutover approver is independent of the plan author."""
    author = seeded["users"]["qa.releaser"].id  # same person authors and tries to approve
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            run = await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            await mig.reconcile_migration_run(s, _recon_cmd(run.aggregate_id, run_row.version), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            with pytest.raises(ValidationFailedError):
                await mig.approve_migration_cutover(
                    s, mig.ApproveMigrationCutoverCommand(
                        idempotency_key=idem(), run_id=run.aggregate_id, expected_version=run_row.version,
                        reason="self approve", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), author, None,
                )


async def test_migration_run_source_hash_mismatch_without_delta(db, seeded):
    """MIGV-FR-002: a run's source_hash must match the frozen snapshot unless is_delta."""
    author = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await mig.execute_migration_dry_run(
                    s, _run_cmd(plan.aggregate_id, source_hash="b" * 64, is_delta=False), author, None
                )
        async with s.begin():
            # is_delta=True is allowed (cutover delta run, MIGV-FR-017)
            run = await mig.execute_migration_dry_run(
                s, _run_cmd(plan.aggregate_id, source_hash="b" * 64, is_delta=True), author, None
            )
            assert run.aggregate_id is not None


async def test_migration_reconcile_stale_version(db, seeded):
    author = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            run = await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id), author, None)
        async with s.begin():
            with pytest.raises(StaleVersionError):
                await mig.reconcile_migration_run(s, _recon_cmd(run.aggregate_id, 999), author, None)


async def test_migration_dry_run_only_cannot_be_approved(db, seeded):
    author = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            run = await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id, run_type="DRY_RUN"), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            await mig.reconcile_migration_run(s, _recon_cmd(run.aggregate_id, run_row.version), author, None)
        async with s.begin():
            run_row = await s.get(MigrationRun, run.aggregate_id)
            with pytest.raises(ValidationFailedError):
                await mig.approve_migration_cutover(
                    s, mig.ApproveMigrationCutoverCommand(
                        idempotency_key=idem(), run_id=run.aggregate_id, expected_version=run_row.version,
                        reason="x", challenge_id=uuid.uuid4(), reauth_password="ChangeMe123!",
                    ), releaser, None,
                )


async def test_legacy_record_trace_hit_and_missing(db, seeded):
    author = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            plan = await mig.create_migration_validation_plan(s, _plan_cmd(), author, None)
        async with s.begin():
            await mig.execute_migration_dry_run(s, _run_cmd(plan.aggregate_id), author, None)
        async with s.begin():
            hit = await mig.verify_legacy_record_trace(s, plan.aggregate_id, "LEG-1")
            assert hit["new_id"] == "NEW-1" and hit["provenance"] == "IDENTITY_MAP"
            rejected = await mig.verify_legacy_record_trace(s, plan.aggregate_id, "LEG-9")
            assert rejected["provenance"] == "REJECTED_RECORD"
        async with s.begin():
            # a plan without a legacy_access_strategy and no map hit -> LEGACY_TRACE_MISSING
            plan2 = await mig.create_migration_validation_plan(
                s, _plan_cmd(legacy_access_strategy="  "), author, None
            )
        async with s.begin():
            with pytest.raises(LegacyTraceMissingError):
                await mig.verify_legacy_record_trace(s, plan2.aggregate_id, "NOPE-1")


async def test_migration_plan_requires_reconciliation_rules(db, seeded):
    author = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await mig.create_migration_validation_plan(s, _plan_cmd(reconciliation_rules=[]), author, None)
