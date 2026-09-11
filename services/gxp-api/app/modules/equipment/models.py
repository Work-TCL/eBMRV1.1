"""Document 38 (SPEC-EQP-001) — Equipment, Calibration, Qualification & Maintenance. First document in
WP-06; no equipment module existed before this pass. Exactly 4 authoritative entities per the spec's own
§5 Data Model and `docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md` -- no 5th table is added. Fields the
spec names with no dedicated entity (equipment class, calibration standards, PM plan, spare parts,
edge/CMMS identity) are captured as unenforced columns, same precedent as
`material.MaterialLot.material_spec_version_id`. `tenant_id` is dropped throughout (single-organization
platform, ADR-0006), matching every migration since 0002.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# EQP-FR-003 §4 state model, transcribed literally (VERIFICATION added as the explicit "post
# calibration/maintenance verification pending" substate the workflow diagram names but doesn't list
# alongside the others).
EQUIPMENT_STATES = (
    "PLANNED",
    "INSTALLED",
    "QUALIFICATION_PENDING",
    "QUALIFIED_AVAILABLE",
    "CALIBRATION_DUE",
    "MAINTENANCE_DUE",
    "OUT_OF_SERVICE",
    "SUSPENDED",
    "VERIFICATION",
    "RETIRED",
)

CALIBRATION_RESULTS = ("pass", "fail", "oot")
CALIBRATION_STATES = ("due", "in_progress", "completed")
MAINTENANCE_TYPES = ("planned", "corrective")
MAINTENANCE_STATES = ("open", "in_progress", "completed", "verified")
# EQP-FR-013 (use) / EQP-FR-016 (reservation, no dedicated reservation entity in the frozen 4-entity
# model) / and a trace row from every other mutating command, so the use log stays this module's one
# complete chronological history (EQP-FR-029) without inventing a 5th table.
USE_LOG_TYPES = ("use", "reservation", "calibration", "maintenance", "hold")


class EquipmentAsset(Base):
    """EQP-FR-001/002/003/004/009/014/017/018/019/022/023/025/030. `equipment_class_id` and
    `location_id` are captured, unenforced references -- no `equipment_class`/location-master entity
    exists in this module's frozen 4-entity data model (same treatment as
    `material.MaterialLot.material_spec_version_id`). `change_control_id` is a real FK: `qms.ChangeControl`
    already exists and is the owning entity EQP-FR-022 links to (called via
    `qms.change_commands.create_change`, never written directly -- AG-05/AG-06).
    """

    __tablename__ = "equipment_assets"
    __table_args__ = (
        UniqueConstraint("equipment_code"),
        Index("ix_equipment_assets_site_state", "site_id", "state"),
        {"schema": "equipment"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    equipment_code: Mapped[str] = mapped_column(String(120), nullable=False)
    equipment_class_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(160))
    serial_no: Mapped[str | None] = mapped_column(String(160))
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="PLANNED")

    qualification_status: Mapped[str | None] = mapped_column(String(40))
    qualification_effective_date: Mapped[date | None] = mapped_column()
    qualification_expiry_date: Mapped[date | None] = mapped_column()
    qualification_scope: Mapped[dict | None] = mapped_column(JSONB)

    calibration_status: Mapped[str | None] = mapped_column(String(40))
    next_calibration_due_date: Mapped[date | None] = mapped_column()

    maintenance_status: Mapped[str | None] = mapped_column(String(40))
    next_maintenance_due_date: Mapped[date | None] = mapped_column()

    # EQP-FR-025: Document 39 (cleaning/sanitization/line clearance) is not built in this codebase --
    # captured, unenforced field, same treatment as every other not-yet-built-dependency field in this
    # module (see SPEC_GAP).
    cleanliness_status: Mapped[str | None] = mapped_column(String(40))

    dedicated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    firmware_version: Mapped[str | None] = mapped_column(String(80))
    # EQP-FR-017: manual entry only -- no Edge/device source exists in this codebase (SPEC_GAP).
    runtime_hours: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    runtime_cycles: Mapped[int | None] = mapped_column(Integer())

    hold_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hold_reason: Mapped[str | None] = mapped_column(String(2000))
    # "manual" (hold_equipment) | "calibration" (OOT) | "maintenance" (breakdown) -- lets a resolving
    # passing calibration / verified work order clear its own hold automatically, while a manual hold
    # stays blocking until a human return_to_service call clears it (see commands.py
    # `_ineligibility_reasons`).
    hold_source: Mapped[str | None] = mapped_column(String(20))

    change_control_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("qms.change_control.id")
    )

    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EquipmentCalibration(Base):
    """EQP-FR-005/006/007/008. One row combines plan and execution -- the spec declares a single
    `POST /equipment/v1/{id}/calibrations` operation, not separate plan/execution endpoints, so a row is
    created `due` (plan fields populated) and later completed in place (execution fields populated) rather
    than modeled as two linked tables. `standard_reference`/`standard_calibration_status`/
    `standard_expiry_date` are captured, unenforced fields -- no calibration-standard master entity exists
    (EQP-FR-008, same precedent as `equipment_class_id` above). `deviation_reference_id` is a captured,
    unenforced reference a human populates after separately calling `qms.commands.create_deviation` --
    EQP-FR-007 says OOT "may trigger deviation/CAPA" (not "shall"); this module does not auto-create one
    (same restraint precedent as SG-108's effectiveness-check escalation).
    """

    __tablename__ = "equipment_calibrations"
    __table_args__ = (
        Index("ix_equipment_calibrations_asset", "equipment_asset_id"),
        {"schema": "equipment"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)

    calibration_plan_ref: Mapped[str | None] = mapped_column(String(160))
    procedure_version: Mapped[str | None] = mapped_column(String(80))
    frequency_days: Mapped[int | None] = mapped_column(Integer())
    tolerance: Mapped[dict | None] = mapped_column(JSONB)
    due_date: Mapped[date] = mapped_column(nullable=False)

    performed_date: Mapped[date | None] = mapped_column()
    as_found: Mapped[dict | None] = mapped_column(JSONB)
    adjustments: Mapped[dict | None] = mapped_column(JSONB)
    as_left: Mapped[dict | None] = mapped_column(JSONB)

    standard_reference: Mapped[str | None] = mapped_column(String(160))
    standard_calibration_status: Mapped[str | None] = mapped_column(String(40))
    standard_expiry_date: Mapped[date | None] = mapped_column()

    performer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    result: Mapped[str | None] = mapped_column(String(20))
    impact_assessment_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deviation_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    state: Mapped[str] = mapped_column(String(20), nullable=False, default="due")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaintenanceWorkOrder(Base):
    """EQP-FR-009/010/011/012/021. `parts_used` is captured JSONB (EQP-FR-021 spare parts) -- no parts
    master entity exists. `type=corrective` is the breakdown path (EQP-FR-012): the owning command puts
    the asset into OUT_OF_SERVICE immediately on creation, matching the acceptance intent "unexpected
    failure marks equipment unavailable"; the spec's "evaluates affected in-process/recent batches" half
    is a cross-module analysis this table doesn't attempt (no equipment reference exists on
    `batch_execution.BatchStep` yet -- SPEC_GAP, referencing SG-048).
    """

    __tablename__ = "maintenance_work_orders"
    __table_args__ = (
        Index("ix_maintenance_work_orders_asset", "equipment_asset_id"),
        {"schema": "equipment"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)

    type: Mapped[str] = mapped_column(String(20), nullable=False)
    fault_description: Mapped[str | None] = mapped_column(Text())
    diagnosis: Mapped[str | None] = mapped_column(Text())
    work_performed: Mapped[str | None] = mapped_column(Text())
    parts_used: Mapped[dict | None] = mapped_column(JSONB)
    # EQP-FR-009: preventive-maintenance-plan fields on the same row a `planned` work order uses -- plan
    # and execution combined for maintenance the same way EquipmentCalibration combines calibration plan
    # and execution (the spec declares one `POST /equipment/v1/{id}/maintenance` operation, not a separate
    # plan-authoring endpoint).
    procedure_version: Mapped[str | None] = mapped_column(String(80))
    frequency_days: Mapped[int | None] = mapped_column(Integer())
    next_due_date: Mapped[date | None] = mapped_column()
    expected_downtime_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    technician_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    post_maintenance_verification_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    verified_at: Mapped[datetime | None] = mapped_column()
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))

    state: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()

    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EquipmentUseLog(Base):
    """EQP-FR-013/016/025. Append-only (AG-08): no command in this module ever UPDATEs or DELETEs a row
    here. `batch_id`/`step_id` are real FKs into the existing `ebmr` schema when supplied; `product_id` is
    a captured, unenforced reference (ambiguous which of this codebase's several product tables a caller
    means -- same "captured, not enforced" treatment used throughout). `cleaning_context` is a captured
    JSONB placeholder for EQP-FR-025 (Document 39 not built).
    """

    __tablename__ = "equipment_use_logs"
    __table_args__ = (
        Index("ix_equipment_use_logs_asset", "equipment_asset_id", "occurred_at"),
        {"schema": "equipment"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)

    log_type: Mapped[str] = mapped_column(String(20), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch_step.id"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    operation: Mapped[str | None] = mapped_column(String(200))

    operator_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    cleaning_context: Mapped[dict | None] = mapped_column(JSONB)
    event_reference: Mapped[str | None] = mapped_column(String(200))

    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
