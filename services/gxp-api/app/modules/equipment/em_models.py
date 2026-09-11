"""Document 41 (SPEC-EQP-004) — Environmental Monitoring & Cleanroom State Control. Same `equipment`
module/schema (AG-05). `em_location` is seed-only (no create endpoint in Document 41's own 8-op API list,
same precedent as `equipment_area`); `em_program_version` DOES have a real create endpoint
(`POST /em/v1/programs`), unlike Document 39's `cleaning_procedure_version`.

No separate `em_task` table exists (matches the spec's own 4-entity data model): a "task" is an
`em_sample_or_reading` row in state `SAMPLE_TASK`, matching Document 38's "plan+execution combined in one
row" precedent.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

EM_SAMPLE_STATES = ("SAMPLE_TASK", "COLLECTED", "RESULT_PENDING", "REVIEWED")
ALERT_ACTION_STATUSES = ("normal", "alert", "action_excursion")
AREA_READINESS_STATES = ("READY", "WARNING", "HOLD", "NOT_READY")
MONITORING_TYPES = (
    "viable_air", "surface_contact", "settle_plate", "personnel", "nonviable_particle",
    "temperature", "humidity", "differential_pressure",
)


class EmProgramVersion(Base):
    """EM-FR-001/003/004/011/017/018. Real create endpoint (`POST /em/v1/programs`) -- no Document 106
    row names a signature for it, so unsigned/RBAC-gated (same 'no row = unsigned' precedent as every
    prior document)."""

    __tablename__ = "em_program_versions"
    __table_args__ = (UniqueConstraint("program_number", "version_no"), {"schema": "equipment"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    program_number: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(nullable=False, default=1)
    monitoring_types: Mapped[dict | None] = mapped_column(JSONB)
    method_version: Mapped[str | None] = mapped_column(String(80))
    frequency: Mapped[dict | None] = mapped_column(JSONB)
    alert_limits: Mapped[dict | None] = mapped_column(JSONB)
    action_limits: Mapped[dict | None] = mapped_column(JSONB)
    operation_shift_coverage: Mapped[dict | None] = mapped_column(JSONB)
    review_trend_rules: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="RELEASED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EmLocation(Base):
    """EM-FR-002. Seed-only (no create endpoint) -- a monitoring *point* within an `equipment_area`, more
    granular than the area itself (multiple points per classified area)."""

    __tablename__ = "em_locations"
    __table_args__ = (UniqueConstraint("location_code"), {"schema": "equipment"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_areas.id"), nullable=False)
    location_code: Mapped[str] = mapped_column(String(120), nullable=False)
    criticality: Mapped[str | None] = mapped_column(String(20))
    sample_types: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EmSampleOrReading(Base):
    """EM-FR-005/006/007/008/009/010/013/014/016/019. `alert_action_status` is captured performer-
    attested input (same restraint as Document 38's calibration `result`) -- no automated numeric
    limit-vs-result evaluation across the many monitoring-type units this pass (SPEC_GAP). `aseptic_
    operation_id` is a forward, unenforced reference (Document 40 is built later in this pass).

    `media_reagent_ref` (EM-FR-007) and `incubation_conditions` (EM-FR-009) added on the SG-115 follow-up
    pass: both captured JSONB, not enumerated/enforced -- no controlled media/reagent or incubation
    vocabulary exists in any approved baseline, same "captured, not enumerated" precedent as
    `equipment_areas.area_type`. Split out from the pre-existing generic `instrument_or_media_ref` so the
    two concepts are at least distinguishable, not because either is validated.
    """

    __tablename__ = "em_samples_or_readings"
    __table_args__ = (
        Index("ix_em_samples_location", "location_id", "created_at"),
        {"schema": "equipment"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    program_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.em_program_versions.id"), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.em_locations.id"), nullable=False)
    monitoring_type: Mapped[str] = mapped_column(String(60), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    aseptic_operation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    instrument_or_media_ref: Mapped[dict | None] = mapped_column(JSONB)
    media_reagent_ref: Mapped[dict | None] = mapped_column(JSONB)
    incubation_conditions: Mapped[dict | None] = mapped_column(JSONB)
    scheduled_at: Mapped[datetime] = mapped_column(server_default=func.now())
    sampled_at: Mapped[datetime | None] = mapped_column()
    result: Mapped[dict | None] = mapped_column(JSONB)
    alert_action_status: Mapped[str | None] = mapped_column(String(20))
    operator_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="SAMPLE_TASK")
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deviation_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EmExcursion(Base):
    """EM-FR-012/021/022. Auto-created by `record_em_result` when `alert_action_status='action_excursion'`
    -- no separate create-excursion endpoint exists in Document 41's own API list; the only excursion
    operation declared is `POST /em/v1/excursions/{id}/impact`. Resampling (EM-FR-022) never overwrites
    this row -- a resample is a new `em_samples_or_readings` row referencing this excursion's area/window,
    never an edit."""

    __tablename__ = "em_excursions"
    __table_args__ = (
        Index("ix_em_excursions_area", "area_id"),
        {"schema": "equipment"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    sample_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.em_samples_or_readings.id"), nullable=False)
    area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_areas.id"), nullable=False)
    affected_time_start: Mapped[datetime | None] = mapped_column()
    affected_time_end: Mapped[datetime | None] = mapped_column()
    affected_batch_ids: Mapped[dict | None] = mapped_column(JSONB)
    organism_details: Mapped[dict | None] = mapped_column(JSONB)
    disposition: Mapped[str | None] = mapped_column(String(40))
    impact_assessed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    impact_assessed_at: Mapped[datetime | None] = mapped_column()
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deviation_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
