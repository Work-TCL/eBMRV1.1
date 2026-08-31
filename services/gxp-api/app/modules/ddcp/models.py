"""Document 54 (SPEC-DDCP-001, PFS-FR-001..030) — Prefilled Syringe & Injectable DDCP Manufacturing
Profile. First WP-08 document; no `ddcp` module existed before this pass.

Exactly the 9 entities Document 112 (Entity Schema Completion & Migration Contract Addendum) approves for
this document (`ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`, `fill_operation`,
`production_count_ledger`, `device_assembly_record`, `device_functional_test_link`,
`ddcp_release_checkpoint`, `batch_evidence_manifest`) -- unlike WP-07's provisional ERP schema, Document
112 already has real, approved DDL for this module (§ "ddcp_profile_version" onward); this file transcribes
it, with two deliberate, documented deviations from the literal DDL:

1. `tenant_id` is dropped throughout (ADR-0006, single-organization platform) -- the same deviation every
   prior module in this codebase makes from its own source document.
2. `site_id` is added to every table, per Document 54's own §"Data model" text ("every regulated table
   carries id, tenant_id, site_id, state, version...") and every other master/transactional table in this
   codebase -- Document 112's raw DDL omits it for this module, which reads as an oversight relative to its
   own universal-aggregate baseline (Document 70) rather than a deliberate exclusion, so this fills it in
   the same way SG-121's ERP schema filled in the universal baseline fields the ERP source spec omitted.

`constituent_requirement` and `production_count_ledger` have no `version` column, matching Document 112's
own DDL exactly: the former is immutable child config created once with its parent profile draft and never
mutated independently; the latter is an append-only ledger (corrections insert a new `correction_of_id`-
linked row, never UPDATE) where a version column would imply in-place mutation that never happens.

Cross-module references are captured, not owned: `batch_id`/`filler_equipment_id` are real FKs into
`ebmr.batches`/`equipment.equipment_assets`; `source_batch_reference`/`qc_record_reference`/
`component_lot_reference` are JSONB (never a duplicated copy of the owning module's row -- "Do not
duplicate QC, Genealogy, Equipment or Audit tables", Document 54 §7).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# PFS-FR-001. Document 54's own profile-configuration TS type §6 -- this document's subtype set only;
# Documents 55/56/57 declare their own subtype vocabularies under the same shared `profile_code` axis
# (Document 112's comment: "e.g. PFS, AUTOINJECTOR, MDI, DPI").
INJECTABLE_SUBTYPES = ("PREFILLED_SYRINGE", "CARTRIDGE", "VIAL_DEVICE_COPACK", "OTHER_INJECTABLE")
# Document 55 (INJ-FR-001) §5 InjectorDDCPProfile.injectorType.
INJECTOR_SUBTYPES = ("AUTOINJECTOR", "PEN_SINGLE_USE", "PEN_REUSABLE", "CARTRIDGE_SYSTEM")
# Document 56 (INH-FR-001) §5 InhalationDDCPProfile.subtype. Document 57 names no subtype variant of its
# own (COAT-FR-001) -- `subtype` stays unset/free-text for coated-device profiles, no enum enforced.
INHALATION_SUBTYPES = ("MDI", "DPI")
PROFILE_STATES = ("DRAFT", "RELEASED", "SUPERSEDED")

# PFS-FR-002/004/005/016.
CONSTITUENT_TYPES = ("DRUG", "BIOLOGIC", "DEVICE", "PACKAGING", "LABEL")
REQUIRED_CONSTITUENT_STATES = ("RELEASED", "READY_TO_USE", "STERILIZED", "DEPYROGENATED")

# PFS-FR-003, §8.
HANDOFF_STATES = ("PENDING", "ACCEPTED", "REJECTED")

# PFS-FR-010/015/022. SG-150: ASSEMBLED/COATED added for Documents 55/57's own unit-count concepts
# (Document 56 reuses FILLED for inhaler fill counts, matching its own filling-route language).
COUNT_TYPES = ("FILLED", "REJECTED_VISUAL", "REJECTED_IPC", "SAMPLED", "LINE_LOSS", "PACKED", "ASSEMBLED", "COATED")
COUNT_SOURCES = ("MACHINE", "MANUAL", "RECONCILIATION")

# PFS-FR-013/018/021. SG-150: extended with Document 55's device-BOM steps (INJ-FR-003), Document 56's
# valve/crimp/actuator steps (INH-FR-009/010) and Document 57's surface-prep/coating steps (COAT-FR-004/
# 005) -- still validated at the command layer as a documented-not-enforced-by-DB-CHECK open set (same
# treatment DEVICE_TEST_TYPES below already uses): a released profile's own control strategy may name an
# assembly step this baseline doesn't anticipate.
ASSEMBLY_STEPS = (
    "NEEDLE_INSTALL", "SHIELD", "TIP_CAP", "SAFETY_DEVICE", "PLUNGER",
    "HOUSING_ASSEMBLY", "SPRING_DRIVE_INSTALL", "NEEDLE_SYSTEM_ASSEMBLY", "DOSE_MECHANISM_INSTALL",
    "CAP_ASSEMBLY", "ELECTRONICS_INSTALL",
    "VALVE_PLACEMENT", "CRIMP", "ACTUATOR_ASSEMBLY",
    "SURFACE_PREPARATION", "COATING_APPLICATION", "DRYING_CURING",
    # INJ-FR-021: recordUnitDisposition() is a final unit-level disposition, not a per-component assembly
    # step -- reuses device_assembly_record with this dedicated step value rather than a new table.
    "FINAL_DISPOSITION",
)
# INJ-FR-021: recordUnitDisposition()'s own PASS/REJECT/REWORK vocabulary -- REJECT added alongside the
# existing FAIL (Document 54's own vocabulary) rather than conflating the two; REJECT is a final-unit
# disposition decision, FAIL is a per-step assembly result, semantically distinct even though both block
# further use without a rework/rejection route.
ASSEMBLY_RESULTS = ("PASS", "FAIL", "REWORK", "REJECT")

# PFS-FR-014/017. Document 112's own comment set -- test_type carries no DB CHECK constraint (a released
# profile's control strategy may name a device test this baseline set doesn't anticipate), validated at
# the command layer as a documented-not-enforced set (same treatment as `component_role` below). SG-150:
# extended with Documents 55/56/57's own test vocabularies (INJ-FR-014/015/016/017, INH-FR-012..017,
# COAT-FR-011..016) -- no code change was needed to accept these, `test_type` was already unenforced.
DEVICE_TEST_TYPES = (
    "CCI", "LEAK", "SEAL", "BREAK_LOOSE", "GLIDE_FORCE", "DOSE_DELIVERY", "SHIELD_REMOVAL",
    "ACTIVATION_FORCE", "DOSE_ACCURACY", "DOSE_COUNTER", "AUDIBLE_INDICATOR",
    "NEEDLE_ACTIVATION", "DOSE_MECHANISM_CALIBRATION", "FINAL_COMBINATION_TEST",
    "DELIVERED_DOSE", "AERODYNAMIC_PARTICLE_SIZE", "SPRAY_PATTERN", "PRIMING",
    "DRUG_CONTENT_ASSAY", "COATING_INTEGRITY", "RELEASE_ELUTION", "DIMENSIONAL_FUNCTION",
)
TEST_RESULT_STATES = ("PENDING", "PASS", "FAIL", "OOS")

# PFS-FR-023/024.
RELEASE_CHECKPOINT_CODES = ("DRUG_CONSTITUENT", "DEVICE_CONSTITUENT", "COMBINED_PRODUCT")
RELEASE_CHECKPOINT_STATES = ("OPEN", "SATISFIED", "BLOCKED", "WAIVED_BY_APPROVAL")

FILL_OPERATION_STATES = ("SETUP", "EXECUTION", "HOLD", "COMPLETE")

# SG-150 (Documents 55/56/57, no Document 112 schema -- provisional, reuse-first per the DDCP Platform
# Rule). ddcp_process_operation generalizes fill_operation's shape for a non-fill process step.
PROCESS_OPERATION_TYPES = ("INJECTOR_ASSEMBLY", "INHALER_FILL", "COATING_RUN")
PROCESS_OPERATION_STATES = ("SETUP", "EXECUTION", "HOLD", "COMPLETE")

# SG-150. ddcp_unit_binding -- INJ-FR-008/009 (drug container -> injector unit) and COAT-FR-010 (device ->
# coating constituent) are structurally the same "primary unit bound to a constituent reference" operation.
UNIT_BINDING_TYPES = ("DRUG_CONTAINER_TO_INJECTOR_UNIT", "DEVICE_TO_COATING_CONSTITUENT", "DOSE_UNIT_TO_DEVICE")
UNIT_BINDING_STATES = ("BOUND", "RELEASED")

# SG-150. reusable_device_pairing (Document 55, INJ-FR-018).
PAIRING_COMPATIBILITY_STATES = ("COMPATIBLE", "INCOMPATIBLE", "PENDING_REVIEW")

# SG-150. drug_coating_usage_ledger (Document 57, COAT-FR-009) -- Document 57 §6's own "Drug/coating
# reconciliation" vocabulary: issued = applied + residual + samples + destroyed/waste + process loss + variance.
COATING_USAGE_TYPES = ("ISSUED", "APPLIED", "RESIDUAL", "SAMPLED", "REJECTED", "RECOVERED", "DISPOSED")
MANIFEST_STATES = ("DRAFT", "FROZEN")


class DdcpProfileVersion(Base):
    """PFS-FR-001/002/028/029. `constituent_architecture`/`required_controls`/`release_checkpoint_set`
    hold Document 54 §6's `InjectableDDCPProfile` TS shape verbatim (sterile process flags, fill control
    rule ids, required device tests, required CCI/visual-inspection profile ids) -- captured JSONB, not a
    proliferation of typed columns, matching Document 112's own DDL. Released profiles are immutable
    (enforced in commands.py, not a DB trigger -- same discipline as `recipe_master`/`product_master`
    release, neither of which writes to `vault.*` either at this pass's depth: `vault_object_id` stays
    NULL here until a future pass wires real Vault integration for master-data releases generally)."""

    __tablename__ = "ddcp_profile_version"
    __table_args__ = (UniqueConstraint("site_id", "profile_code", "version"), {"schema": "ddcp"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    profile_code: Mapped[str] = mapped_column(String(80), nullable=False)
    subtype: Mapped[str | None] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    dosage_form: Mapped[str | None] = mapped_column(String(80))
    presentation: Mapped[str | None] = mapped_column(String(80))
    constituent_architecture: Mapped[dict] = mapped_column(JSONB, nullable=False)
    required_controls: Mapped[dict] = mapped_column(JSONB, nullable=False)
    release_checkpoint_set: Mapped[dict] = mapped_column(JSONB, nullable=False)
    vault_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    released_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    release_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    effective_from: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ConstituentRequirement(Base):
    """PFS-FR-002/004/005/016. Immutable child config of a profile draft (no `version` column -- see
    module docstring); mutating a released profile's requirements means authoring a new profile version,
    never editing this row in place."""

    __tablename__ = "constituent_requirement"
    __table_args__ = (
        UniqueConstraint("ddcp_profile_version_id", "component_role", "sequence_no"),
        {"schema": "ddcp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    ddcp_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ddcp.ddcp_profile_version.id"), nullable=False
    )
    constituent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    component_role: Mapped[str] = mapped_column(String(80), nullable=False)
    required_state: Mapped[str] = mapped_column(String(60), nullable=False)
    material_spec_reference: Mapped[dict | None] = mapped_column(JSONB)
    attribute_requirements: Mapped[dict | None] = mapped_column(JSONB)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sequence_no: Mapped[int] = mapped_column(nullable=False)


class ConstituentHandoff(Base):
    """PFS-FR-003, §8. `source_batch_reference` carries the released upstream bulk/component batch id +
    version (a JSONB reference into `ebmr.batches` or `materials.material_lots`, never a duplicated copy).
    The exact-duplicate-handoff uniqueness Document 112 declares as a JSONB-expression UNIQUE index is
    enforced at the application layer in `commands.py` (a plain multi-column DB constraint here would
    either miss the JSONB key or over-block legitimately distinct handoffs for the same
    (batch, from, to) triple against different source batches)."""

    __tablename__ = "constituent_handoff"
    __table_args__ = {"schema": "ddcp"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    from_constituent: Mapped[str] = mapped_column(String(40), nullable=False)
    to_constituent: Mapped[str] = mapped_column(String(80), nullable=False)
    source_batch_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    acceptance_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    accepted_at: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    rejection_reason: Mapped[str | None] = mapped_column(Text())
    version: Mapped[int] = mapped_column(nullable=False, default=1)


class FillOperation(Base):
    """PFS-FR-006..011. `line_id` names an `equipment.equipment_areas` row (the readiness composition in
    `commands.py::_compute_fill_readiness` reuses Document 39-42's exact area-readiness/line-clearance/
    equipment-eligibility/sterile-item-status query functions the aseptic module already composes for the
    same purpose -- see `equipment.aseptic_commands._compute_readiness`) -- named `line_id`, not `area_id`,
    to match Document 112's DDL literally. `interventions`/`alarms` are append-in-place JSONB arrays
    (small, bounded per fill run); a high-volume future pass could split these into child tables without
    changing this column's meaning."""

    __tablename__ = "fill_operation"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_fill_operation_end_after_start"),
        CheckConstraint("target_fill > 0", name="ck_fill_operation_target_fill_positive"),
        {"schema": "ddcp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_areas.id"), nullable=False)
    filler_equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"), nullable=False
    )
    fill_program_id: Mapped[str] = mapped_column(String(120), nullable=False)
    fill_program_version: Mapped[str] = mapped_column(String(40), nullable=False)
    product_contact_path: Mapped[dict] = mapped_column(JSONB, nullable=False)
    target_fill: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    target_fill_uom: Mapped[str] = mapped_column(String(20), nullable=False)
    # SG-146 dual-write precedent (best-effort resolved, never blocks the write on an unknown UOM).
    target_fill_uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    cycle_group: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column()
    line_readiness_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    machine_count_start: Mapped[int | None] = mapped_column()
    machine_count_end: Mapped[int | None] = mapped_column()
    interventions: Mapped[dict | None] = mapped_column(JSONB)
    alarms: Mapped[dict | None] = mapped_column(JSONB)
    # PFS-FR-008: "bind filter lot/serial, pre/post integrity status ... and evidence." Not in Document
    # 112's literal DDL for this table -- added the same way SG-148 already added site_id: an additive,
    # non-destructive nullable column filling in a real requirement the approved DDL omitted, not a
    # reinterpretation of anything Document 112 does specify. `complete_filling_stage` already validated
    # this reference via Document 42's `get_item_status` before this column existed; this only adds
    # persistence of what was already being checked.
    filter_use_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.sterile_filter_uses.id"))
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="SETUP")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ProductionCountLedger(Base):
    """PFS-FR-010/015/022. Append-only (no `version` column -- see module docstring); a correction never
    UPDATEs an existing row, it inserts a new one with `correction_of_id` pointing at the row it
    supersedes, same discipline as `erp.integration_command_attempts`."""

    __tablename__ = "production_count_ledger"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_production_count_ledger_quantity_non_negative"),
        {"schema": "ddcp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    count_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False, default="EA")
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    device_reference: Mapped[dict | None] = mapped_column(JSONB)
    reason_code: Mapped[str | None] = mapped_column(String(80))
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    correction_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ddcp.production_count_ledger.id")
    )
    source_event_id: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DeviceAssemblyRecord(Base):
    """PFS-FR-013/018/021. `CHECK (verified_by IS NULL OR verified_by <> performed_by)` is Document 112's
    own IND-001 independence constraint, enforced at the database level (not just in commands.py) exactly
    as declared."""

    __tablename__ = "device_assembly_record"
    __table_args__ = (
        CheckConstraint("verified_by IS NULL OR verified_by <> performed_by", name="ck_device_assembly_independent_verify"),
        {"schema": "ddcp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    unit_identifier: Mapped[str | None] = mapped_column(String(120))
    assembly_step: Mapped[str] = mapped_column(String(80), nullable=False)
    component_lot_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"))
    process_parameters: Mapped[dict | None] = mapped_column(JSONB)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    performed_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    verified_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DeviceFunctionalTestLink(Base):
    """PFS-FR-014/017. `qc_record_reference` is the owning `qc.qc_result`/`qc.qc_test_order` id+version --
    "QC results are owned by Document 23/24, referenced only" (Document 112's own comment); this table
    never stores a raw test value. Document 112's `UNIQUE (batch_id, test_type, qc_record_reference->>
    'record_id')` is a JSONB-expression constraint, enforced at the application layer in `commands.py`
    (same treatment as `ConstituentHandoff`'s JSONB-key uniqueness, for the same reason)."""

    __tablename__ = "device_functional_test_link"
    __table_args__ = {"schema": "ddcp"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    test_type: Mapped[str] = mapped_column(String(80), nullable=False)
    qc_record_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sample_plan_reference: Mapped[dict | None] = mapped_column(JSONB)
    method_reference: Mapped[dict | None] = mapped_column(JSONB)
    result_state: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    blocks_release: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    linked_at: Mapped[datetime] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)


class DdcpReleaseCheckpoint(Base):
    """PFS-FR-023/024. One row per (batch, checkpoint_code); final combined-product release requires all
    three SATISFIED (`commands.py::evaluate_pfs_release_readiness` is the only writer)."""

    __tablename__ = "ddcp_release_checkpoint"
    __table_args__ = (UniqueConstraint("batch_id", "checkpoint_code"), {"schema": "ddcp"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    checkpoint_code: Mapped[str] = mapped_column(String(80), nullable=False)
    required_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    blocker_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    decision_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decided_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(nullable=False, default=1)


class BatchEvidenceManifest(Base):
    """PFS-FR-025/030; Document 72 (object evidence). A frozen manifest is immutable (enforced in
    commands.py: `create_pfs_batch_evidence_package` always inserts a new `manifest_version`, never
    updates a FROZEN row)."""

    __tablename__ = "batch_evidence_manifest"
    __table_args__ = (UniqueConstraint("batch_id", "manifest_version"), {"schema": "ddcp"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    manifest_version: Mapped[int] = mapped_column(nullable=False)
    evidence_set: Mapped[dict] = mapped_column(JSONB, nullable=False)
    digest: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(nullable=False)
    vault_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(nullable=False, default=1)


# =======================================================================================================
# SG-150 — Documents 55/56/57 (SPEC-DDCP-002/003/004). No Document 112 schema exists for any of these
# three documents; the four tables below are a provisional schema (same class of judgment as SG-121's WP-07
# ERP schema), designed from each document's own §5 profile-schema TS type and prose per the DDCP Platform
# Rule ("configure and extend the common engines... shall not fork core GxP services"). Document 54's own
# nine tables above (ddcp_profile_version, constituent_requirement, constituent_handoff,
# device_assembly_record, device_functional_test_link, production_count_ledger, ddcp_release_checkpoint,
# batch_evidence_manifest) are reused unchanged by Documents 55/56/57 -- only these four are new.
# =======================================================================================================


class DdcpProcessOperation(Base):
    """SG-150. Generalizes `fill_operation`'s shape for a non-fill process step -- injector assembly
    (INJ-FR-006/007), inhaler filling/valve-crimp (INH-FR-007/008/009) or a coating run (COAT-FR-005/006/
    007/008), distinguished by `operation_type`. `process_parameters` replaces `fill_operation`'s
    fill-specific `target_fill`/`target_fill_uom` columns (a NOT NULL "target fill volume" on an injector
    assembly run that never fills anything would be misleading -- same restraint Document 54's own
    module docstring already applies to its own columns). `environment_reference` captures INH-FR-018's
    humidity/environment readiness gate and COAT-FR-008's environment gate generically -- both documents
    describe environment dependencies as "product/validation-controlled, not generic constants"
    (Document 56 §7), so this stores a reference/snapshot, never a baked-in limit."""

    __tablename__ = "ddcp_process_operation"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_ddcp_process_operation_end_after_start"),
        {"schema": "ddcp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_areas.id"))
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"))
    program_id: Mapped[str | None] = mapped_column(String(120))
    program_version: Mapped[str | None] = mapped_column(String(40))
    process_parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    environment_reference: Mapped[dict | None] = mapped_column(JSONB)
    readiness_reference: Mapped[dict | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column()
    interventions: Mapped[dict | None] = mapped_column(JSONB)
    alarms: Mapped[dict | None] = mapped_column(JSONB)
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="SETUP")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DdcpUnitBinding(Base):
    """SG-150. `bindDrugContainerToInjectorUnit()` (INJ-FR-008/009 -- CONTAINER_ALREADY_USED/
    WRONG_CONTAINER_DEVICE_PAIRING) and `bindDeviceToCoatingConstituent()` (COAT-FR-010) are structurally
    the same "primary unit reference bound to a constituent reference" operation on different constituent
    types -- one shared table, distinguished by `binding_type`. Document 112's JSONB-expression-uniqueness-
    enforced-in-code discipline (see `ConstituentHandoff`) applies here too: application-level uniqueness
    on `(binding_type, bound_constituent_reference)` prevents duplicate/cross-use, enforced in
    injector_commands.py/coated_device_commands.py, not a DB constraint."""

    __tablename__ = "ddcp_unit_binding"
    __table_args__ = {"schema": "ddcp"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    binding_type: Mapped[str] = mapped_column(String(60), nullable=False)
    primary_unit_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    bound_constituent_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="BOUND")
    bound_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    bound_at: Mapped[datetime] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ReusableDevicePairing(Base):
    """SG-150 (Document 55 only, INJ-FR-018). "For reusable injector + cartridge, model compatibility/
    approved pairing... without assuming permanent single unit relationship" -- explicitly not a per-batch
    consumable handoff (a reusable pen is not "consumed" by one batch), so this does not fit
    `constituent_handoff`'s batch-scoped shape. `batch_id` is nullable: a pairing/compatibility decision
    can be authored independently of any specific batch (device-family-to-cartridge-family compatibility),
    while a pairing record produced during a specific batch's assembly still carries one."""

    __tablename__ = "reusable_device_pairing"
    __table_args__ = {"schema": "ddcp"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"))
    reusable_device_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    cartridge_lot_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    compatibility_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING_REVIEW")
    rationale: Mapped[str | None] = mapped_column(Text())
    paired_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    paired_at: Mapped[datetime] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DrugCoatingUsageLedger(Base):
    """SG-150 (Document 57 only, COAT-FR-009). Decimal mass-balance ledger (DATA-FR-019 -- no binary float
    for a regulated quantity), distinct from `production_count_ledger` (bigint unit counts, reused
    unchanged for Document 57's own *device*-unit reconciliation side). Append-only, no `version` column --
    same discipline as `production_count_ledger` itself: a correction inserts a new row referencing the one
    it supersedes via `correction_of_id`, never an UPDATE."""

    __tablename__ = "drug_coating_usage_ledger"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_drug_coating_usage_ledger_quantity_non_negative"),
        {"schema": "ddcp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    usage_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    reason_code: Mapped[str | None] = mapped_column(String(80))
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    correction_of_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ddcp.drug_coating_usage_ledger.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
