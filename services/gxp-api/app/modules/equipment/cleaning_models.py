"""Document 39 (SPEC-EQP-002) — Cleaning, Sanitization & Line Clearance. Same `equipment` module/schema as
Document 38 (AG-05, one owner per Document 04/05's catalogue). `EquipmentArea` is a new shared master this
document introduces (no area/room/building entity exists anywhere in this codebase before this pass) --
deliberately a narrow "classified area" master scoped to what Documents 39/40/41 actually consume, not the
full Document 01/02 C-003 Building/Area/Room/Line hierarchy (SPEC_GAP).

`cleaning_procedure_version` has no CRUD operation anywhere in Document 39's own 7-op API list (§6) --
seed-only master data, same precedent as `material.WarehouseLocation` ("no CRUD API exists ... seed-only,
like Organization/Site").
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# CLN-FR-027 (also driving equipment_asset.cleanliness_status / EquipmentArea.cleanliness_status).
CLEANLINESS_STATES = ("DIRTY", "CLEANING", "CLEANING_VERIFICATION", "CLEAN", "READY_FOR_USE", "CLEAN_EXPIRED", "HOLD")
LINE_CLEARANCE_STATES = ("NOT_STARTED", "IN_PROGRESS", "VERIFICATION_PENDING", "CLEARED", "EXPIRED", "USED")
CLEANING_TYPES = ("routine", "product_changeover", "campaign_end", "deep_clean", "sanitization", "manual", "CIP", "COP")


class EquipmentArea(Base):
    """New shared master (see module docstring): a classified/monitored physical area. Referenced by
    `cleaning_execution`/`line_clearance` (this document), `em_location` (Document 41) and
    `aseptic_operation` (Document 40). `area_type`/`classification`/`criticality` are captured free text --
    no controlled code list exists in any of the source specs beyond prose (same "captured, not enumerated"
    precedent as `MaterialReceipt.discrepancy_type`).
    """

    __tablename__ = "equipment_areas"
    __table_args__ = (UniqueConstraint("area_code"), {"schema": "equipment"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    area_code: Mapped[str] = mapped_column(String(120), nullable=False)
    area_type: Mapped[str | None] = mapped_column(String(60))
    classification: Mapped[str | None] = mapped_column(String(40))
    criticality: Mapped[str | None] = mapped_column(String(20))
    cleanliness_status: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CleaningProcedureVersion(Base):
    """CLN-FR-001/002/026. Seed-only master (see module docstring) -- no create/release endpoint exists in
    Document 39's own API list. `scope_equipment_id`/`scope_area_id` are alternatives, not both set."""

    __tablename__ = "cleaning_procedure_versions"
    __table_args__ = (UniqueConstraint("procedure_number", "version_no"), {"schema": "equipment"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    procedure_number: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    scope_equipment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"))
    scope_area_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_areas.id"))
    cleaning_type: Mapped[str] = mapped_column(String(40), nullable=False)
    agents: Mapped[dict | None] = mapped_column(JSONB)
    steps: Mapped[dict | None] = mapped_column(JSONB)
    disassembly_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sample_inspection_requirements: Mapped[dict | None] = mapped_column(JSONB)
    dirty_hold_limit_minutes: Mapped[int | None] = mapped_column(Integer())
    clean_hold_limit_minutes: Mapped[int | None] = mapped_column(Integer())
    validation_reference: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="RELEASED")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CleaningExecution(Base):
    """CLN-FR-003/004/005/006/007/008/009/010/011/012/013/014/015/022/023/024/025. `steps_log` is an
    append-only JSONB array (`record_cleaning_step`) -- matches the spec's single
    `POST /cleaning/v1/executions/{id}/steps` operation rather than a 5th table. `critical` gates the
    Document 106 rows 109/111 conditional reason requirement ("required unless flagged critical") at the
    application level, since `SignaturePolicy.reason_required` is a flat boolean, not per-record
    conditional.

    `protection_state` (CLN-FR-014) and `sterilization_cycle_id` (CLN-FR-025) added on the SG-114
    follow-up pass: `protection_state` is captured free-form JSONB (cover/closure/storage state as
    recorded by the procedure/performer), not an enforced/gated enum -- no controlled vocabulary for it
    exists in Document 39 or any approved baseline (same "captured, not enumerated" precedent as
    `EquipmentArea.area_type` above). `sterilization_cycle_id` links to Document 42's `process_cycles`
    (now built, unlike when this table was first created) so a CIP/SIP cycle can evidence part of a
    cleaning record "through a validated interface" per CLN-FR-025 -- it is a reference only; the normal
    `verify_cleaning()` signature step still independently governs this record's own completion, so linking
    a cycle never substitutes for "and verification".
    """

    __tablename__ = "cleaning_executions"
    __table_args__ = {"schema": "equipment"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"))
    area_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_areas.id"))
    procedure_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.cleaning_procedure_versions.id"), nullable=False)
    batch_context: Mapped[dict | None] = mapped_column(JSONB)
    critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="CLEANING")
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()
    dirty_since: Mapped[datetime] = mapped_column(nullable=False)
    clean_until: Mapped[datetime | None] = mapped_column()
    agents_used: Mapped[dict | None] = mapped_column(JSONB)
    steps_log: Mapped[dict | None] = mapped_column(JSONB)
    previous_batch_identity_removed: Mapped[bool | None] = mapped_column(Boolean)
    disassembly_verified: Mapped[bool | None] = mapped_column(Boolean)
    inspection_result: Mapped[dict | None] = mapped_column(JSONB)
    swab_sample_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    protection_state: Mapped[dict | None] = mapped_column(JSONB)
    sterilization_cycle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.process_cycles.id"))
    performer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    verification_result: Mapped[str | None] = mapped_column(String(20))
    dirty_hold_exceeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deviation_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LineClearance(Base):
    """CLN-FR-016/017/018/019/020/021/022/023. `items` is captured JSONB (material/label/equipment
    checklist items, CLN-FR-018/019) -- no packaging-label-reconciliation integration this pass (SPEC_GAP,
    same class as every "no consuming integration yet" gap)."""

    __tablename__ = "line_clearances"
    __table_args__ = {"schema": "equipment"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    area_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_areas.id"))
    previous_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    next_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    checklist_version: Mapped[str | None] = mapped_column(String(80))
    items: Mapped[dict | list | None] = mapped_column(JSONB)
    critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    performer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    verifier_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_STARTED")
    expiry_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
