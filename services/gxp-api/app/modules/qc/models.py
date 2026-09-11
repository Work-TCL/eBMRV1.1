import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# Document 23 (SPEC-QC-001) §5 state models.
SPEC_STATES = ("draft", "review", "released", "superseded", "obsolete", "suspended")
SAMPLE_STATES = ("planned", "collected", "received", "in_testing", "testing_complete", "hold", "disposed", "retained")
TEST_ORDER_STATES = (
    "created", "assigned", "in_progress", "analyst_complete", "review_pending", "reviewed",
    "oos_pending", "oot_pending", "invalid_under_investigation",
)
RESULT_OUTCOMES = ("pending", "pass", "oos", "oot", "invalid")

# QC-FR-001: scope_type="material" is rejected at the command layer -- see SG-057/SG-063. Only these
# three are actually accepted this pass.
BUILDABLE_SCOPE_TYPES = ("product", "in_process", "device")


class QcTestSpecification(Base):
    """Document 23 §6 `qc_test_specification` -- DDL-ready. `scope_version_id` is a polymorphic
    reference (product/device -> gxp_product_version, in_process -> gxp_recipe_version) validated in
    application code, not a DB FK -- no single FK target can cover three tables."""

    __tablename__ = "qc_test_specification"
    __table_args__ = (UniqueConstraint("spec_code", "version_no"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spec_code: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    sampling_plan: Mapped[dict | None] = mapped_column(JSONB)
    released_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QcTestDefinition(Base):
    """Document 23 §6 `qc_test_definition` -- prose-only field list, typed here as an ordinary
    engineering decision (SG-045's precedent). `method_version` is a plain field, not a FK to a Method
    master -- no such entity exists anywhere in this codebase or in Document 23's own data model
    (SG-063). `acceptance_rule_business_id`/`trend_rule_business_id` are the `rules.gxp_rule_definition
    .rule_id` business keys resolved at evaluation time via `rules_service.get_effective_released_rule`
    -- same convention `f"batch-release-eligibility:{product_id}"` already uses; no rule reference is
    persisted here until a result is actually evaluated against one (see `QcResult.acceptance_rule_id`).
    """

    __tablename__ = "qc_test_definition"
    __table_args__ = (
        Index("ix_qc_test_definition_spec", "specification_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.qc_test_specification.id"), nullable=False
    )
    test_code: Mapped[str] = mapped_column(String(80), nullable=False)
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    method_version: Mapped[str | None] = mapped_column(String(80))
    result_data_type: Mapped[str] = mapped_column(String(40), nullable=False)
    uom: Mapped[str | None] = mapped_column(String(40))
    # SG-146 (remainder), MIG-FR-004 expand step: dual-written best-effort at spec-authoring time
    # (app.modules.qc.commands._resolve_uom_id). No backfill is possible for pre-existing rows -- this
    # table has no UPDATE grant (append-only once written, AG-08, see migration 0021's comment) -- so a
    # row created before this column existed keeps uom_id NULL forever, same as `qc_result` below.
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    acceptance_rule_business_id: Mapped[str | None] = mapped_column(String(160))
    trend_rule_business_id: Mapped[str | None] = mapped_column(String(160))
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    release_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    review_policy: Mapped[str | None] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QcSample(Base):
    """Document 23 §6 `qc_sample` -- DDL-ready. `source_id` is a polymorphic reference validated in
    application code for the 4 source_types that map to an already-built entity (material_lot/batch/
    batch_step/device_unit); reserve/environmental/investigation have no owning module yet and stay
    unvalidated free references."""

    __tablename__ = "qc_sample"
    __table_args__ = (UniqueConstraint("sample_number"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_number: Mapped[str] = mapped_column(String(160), nullable=False)
    sample_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_location_ref: Mapped[str | None] = mapped_column(String(200))
    lot_batch_serial_ref: Mapped[str | None] = mapped_column(String(200))
    sample_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    sample_uom: Mapped[str | None] = mapped_column(String(40))
    # SG-146 (remainder), MIG-FR-004 expand step: dual-written at creation and backfillable for
    # pre-existing rows (qc_sample is mutable -- UPDATE granted, unlike qc_test_definition/qc_result).
    sample_uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    sampled_at: Mapped[datetime | None] = mapped_column()
    received_at: Mapped[datetime | None] = mapped_column()
    sampler_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="planned")
    stability_study_ref: Mapped[str | None] = mapped_column(String(160))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QcTestOrder(Base):
    """Document 23 §6 `qc_test_order` -- prose-only, typed as an ordinary engineering decision."""

    __tablename__ = "qc_test_order"
    __table_args__ = (
        Index("ix_qc_test_order_sample", "sample_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_sample.id"), nullable=False)
    test_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.qc_test_definition.id"), nullable=False
    )
    assigned_analyst_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="created")
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    reviewed_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QcTestRun(Base):
    """Document 23 §6 `qc_test_run` -- prose-only, typed as an ordinary engineering decision.
    `instrument_ref` is an unenforced logical reference -- no equipment/instrument entity exists
    anywhere in this codebase (WP-06 Equipment, not built -- SG-063)."""

    __tablename__ = "qc_test_run"
    __table_args__ = (
        Index("ix_qc_test_run_order", "test_order_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.qc_test_order.id"), nullable=False
    )
    method_version: Mapped[str | None] = mapped_column(String(80))
    instrument_ref: Mapped[str | None] = mapped_column(String(160))
    analyst_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    sample_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    reference_standards: Mapped[dict | None] = mapped_column(JSONB)
    system_suitability: Mapped[dict | None] = mapped_column(JSONB)
    raw_evidence_vault_ids: Mapped[dict | None] = mapped_column(JSONB)
    calculation_rule_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.gxp_rule_definition.rule_object_id")
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QcResult(Base):
    """Document 23 §6 `qc_result` -- DDL-ready. `oos_record_id`/`oot_record_id` now carry a real FK
    constraint into Document 25's `oos_record`/`oot_record` (added by the Document 25 migration), but
    stay unpopulated by any command: `qc_result` is append-only (no UPDATE grant, AG-08), so an OOS/OOT
    opened from an already-committed result can never backfill this column onto it. The queryable
    relationship is the reverse FK -- `oos_record.source_result_id` / `oot_record.source_result_id`. A
    correction never edits this row either; it creates a new one with `supersedes_result_id` set
    (QC-FR-024, VLT-FR-010-style)."""

    __tablename__ = "qc_result"
    __table_args__ = (
        Index("ix_qc_result_order", "test_order_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.qc_test_order.id"), nullable=False
    )
    test_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_test_run.id"), nullable=False)
    result_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    result_type: Mapped[str] = mapped_column(String(40), nullable=False)
    value_decimal: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    value_text: Mapped[str | None] = mapped_column(Text())
    value_json: Mapped[dict | None] = mapped_column(JSONB)
    uom: Mapped[str | None] = mapped_column(String(40))
    # SG-146 (remainder) -- same no-backfill-possible note as QcTestDefinition.uom_id above: qc_result
    # has no UPDATE grant (append-only, AG-08), so this is dual-written at creation only.
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    acceptance_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.gxp_rule_definition.rule_object_id")
    )
    outcome: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    oos_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.oos_record.id"))
    oot_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.oot_record.id"))
    supersedes_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.qc_result.id")
    )
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OosRecord(Base):
    """Document 25 (SPEC-QC-003) §7 `oos_record` -- DDL-ready, exact 17-column list. Owner service is
    `qc` per docs/generated/04_DATA_MODEL_CATALOGUE.md. CAPA/Change Control links (OOS-FR-020/021) have
    no column here -- Document 25 declares no such field on this DDL-ready table and no dedicated link
    entity either; deferred (SG-074), not guessed onto this table."""

    __tablename__ = "oos_record"
    __table_args__ = (UniqueConstraint("oos_number"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    oos_number: Mapped[str] = mapped_column(String(120), nullable=False)
    source_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_result.id"), nullable=False)
    sample_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_sample.id"))
    test_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_test_order.id"))
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    material_lot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.material_lots.id"))
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    severity: Mapped[str | None] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    hold_status: Mapped[str | None] = mapped_column(String(40))
    final_classification: Mapped[str | None] = mapped_column(String(60))
    root_cause_code: Mapped[str | None] = mapped_column(String(100))
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class OosInvestigationActivity(Base):
    """Document 25 §7 `oos_investigation_activity` -- prose-only field list, typed as an ordinary
    engineering decision (SG-045 precedent). Append-only (no UPDATE grant, AG-08) -- an investigation
    entry is never edited, only added to."""

    __tablename__ = "oos_investigation_activity"
    __table_args__ = (
        Index("ix_oos_investigation_activity_oos", "oos_record_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oos_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.oos_record.id"), nullable=False)
    phase: Mapped[str] = mapped_column(String(40), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    checklist_item: Mapped[str | None] = mapped_column(String(200))
    response_text: Mapped[str | None] = mapped_column(Text())
    evidence_refs: Mapped[dict | None] = mapped_column(JSON)
    investigator_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class OosRetestPlan(Base):
    """Document 25 §7 `oos_retest_plan` -- prose-only field list, typed as an ordinary engineering
    decision. `status` is mutable (draft -> authorized -> executed/rejected) -- unlike the checklist
    activity above, this row IS updated in place as the plan progresses."""

    __tablename__ = "oos_retest_plan"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oos_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.oos_record.id"), nullable=False)
    justification: Mapped[str] = mapped_column(Text(), nullable=False)
    number_of_retests: Mapped[int] = mapped_column(nullable=False)
    method_ref: Mapped[str | None] = mapped_column(String(160))
    analyst_criteria: Mapped[str | None] = mapped_column(String(300))
    instrument_criteria: Mapped[str | None] = mapped_column(String(300))
    interpretation_rule: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="authorized")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OosResamplePlan(Base):
    """Document 25 §7 `oos_resample_plan` -- prose-only field list, typed as an ordinary engineering
    decision. Mutable, same reasoning as `OosRetestPlan`."""

    __tablename__ = "oos_resample_plan"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oos_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.oos_record.id"), nullable=False)
    scientific_rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    sampling_plan_ref: Mapped[str | None] = mapped_column(String(160))
    sampling_plan_version: Mapped[str | None] = mapped_column(String(40))
    source_ref: Mapped[str | None] = mapped_column(String(200))
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    resulting_sample_ids: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="authorized")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OotRecord(Base):
    """Document 25 §7 `oot_record` -- prose-only field list, typed as an ordinary engineering decision.
    `investigation_owner_user_id` is not in the source prose list but is added here (this entity is
    prose-only, not DDL-fixed like `OosRecord`) to support the Doc 106 row 69 independence check on
    `oot/{id}/close` without inventing a separate activity table Document 25 never describes."""

    __tablename__ = "oot_record"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_result.id"), nullable=False)
    trend_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_rule_definition.rule_object_id"))
    trend_rule_version: Mapped[str | None] = mapped_column(String(40))
    baseline_ref: Mapped[str | None] = mapped_column(String(200))
    trigger_details: Mapped[dict | None] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    investigation_notes: Mapped[str | None] = mapped_column(Text())
    impact_assessment: Mapped[str | None] = mapped_column(Text())
    investigation_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    hold_status: Mapped[str | None] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class QcResultCorrection(Base):
    """Not one of Document 23's 6 catalogued entities -- the pending state between the 2-signature
    `POST /qc/v1/results/{id}/correct` ceremony's two steps (Document 106 row 57: corrector signs the
    request, an independent approver signs completion). Same 2-step shape as
    `vault.gxp_record_correction`, extended with a second signature slot for the request step."""

    __tablename__ = "qc_result_correction"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_result.id"), nullable=False)
    reason_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    corrected_value_decimal: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    corrected_value_text: Mapped[str | None] = mapped_column(Text())
    corrected_value_json: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="requested")
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    requested_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approved_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resulting_result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_result.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()
