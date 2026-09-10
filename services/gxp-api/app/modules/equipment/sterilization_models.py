"""Document 42 (SPEC-EQP-005) — Sterilization, CIP/SIP & Sterile Filtration Management. Same `equipment`
module/schema (AG-05). `process_cycle_profile_version` is seed-only (no create endpoint in Document 42's
own 9-op API list, same precedent as `cleaning_procedure_version`).

STR-FR-009 ("operator cannot manually mark pass") drives a real design split from Document 38's calibration
precedent: `record_cycle_data` never accepts a pass/fail result -- only the independent reviewer
(`review_cycle`, Document 106 row 117, MUST be independent) decides accept/reject. `complete_filter_use`
(row 116) has no independence requirement, so a performer-attested result there is consistent with
Document 106's own policy, not a guess.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

PROCESS_TYPES = (
    "steam_autoclave", "dry_heat", "depyrogenation", "gas", "radiation", "external_reference",
    "SIP", "CIP", "sterile_filtration",
)
CYCLE_STATES = ("DRAFT", "CYCLE_STARTED", "CYCLE_RUNNING", "CYCLE_COMPLETE", "REVIEW_PENDING", "ACCEPTED", "FAILED", "HOLD")
FILTER_STATES = ("RECEIVED_ELIGIBLE", "INSTALLED", "PRE_USE_TEST", "IN_USE", "POST_USE_TEST", "ACCEPTED", "FAILED")
INTEGRITY_TEST_PHASES = ("pre", "post")


class ProcessCycleProfileVersion(Base):
    """STR-FR-001/002/003/027. Seed-only (see module docstring)."""

    __tablename__ = "process_cycle_profile_versions"
    __table_args__ = (UniqueConstraint("profile_number", "version_no"), {"schema": "equipment"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    profile_number: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(nullable=False, default=1)
    process_type: Mapped[str] = mapped_column(String(40), nullable=False)
    equipment_class_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    load_pattern: Mapped[dict | None] = mapped_column(JSONB)
    controller_recipe_ref: Mapped[str | None] = mapped_column(String(160))
    critical_parameters: Mapped[dict | None] = mapped_column(JSONB)
    indicator_requirements: Mapped[dict | None] = mapped_column(JSONB)
    review_policy: Mapped[dict | None] = mapped_column(JSONB)
    validation_reference: Mapped[str | None] = mapped_column(String(200))
    sterile_status_validity_hours: Mapped[int | None] = mapped_column(Integer())
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="RELEASED")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ProcessCycle(Base):
    """STR-FR-004/005/006/007/008/009/010/014/026. Covers both `POST /sterilization/v1/cycles` and
    `POST /cip-sip/v1/cycles` (same table, distinguished by `process_type`) -- the spec's own two-endpoint
    surface maps onto one entity, matching the data model's single `process_cycle` declaration.
    `parameter_summary`/`alarm_summary` accumulate via `record_cycle_data` (append-only, never edited in
    place); no `result`/pass-fail field exists here -- see module docstring.

    `indicator_results` (STR-FR-011) and `reprocessing_authorization_ref` (STR-FR-026) added on the
    SG-116 follow-up pass. `indicator_results` is captured JSONB (biological/chemical indicator IDs/
    locations/lots/pass-fail as recorded) -- captured, not enumerated, same precedent as
    `equipment_areas.area_type`; it never substitutes for `critical_alarm`/`review_cycle`'s own
    accept/reject decision. `reprocessing_authorization_ref` is required (fail-closed, using the
    already-declared `REPROCESSING_AUTHORIZATION_REQUIRED`) whenever a new cycle's `load_items` share an
    `item_reference` with a previously `FAILED` cycle's load items -- structurally required, not
    validated against any specific QMS record shape (none exists to validate against yet)."""

    __tablename__ = "process_cycles"
    __table_args__ = {"schema": "equipment"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    process_type: Mapped[str] = mapped_column(String(40), nullable=False)
    equipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"), nullable=False)
    profile_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.process_cycle_profile_versions.id"), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    controller_cycle_id: Mapped[str | None] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    parameter_summary: Mapped[dict | None] = mapped_column(JSONB)
    alarm_summary: Mapped[dict | None] = mapped_column(JSONB)
    indicator_results: Mapped[dict | None] = mapped_column(JSONB)
    reprocessing_authorization_ref: Mapped[dict | None] = mapped_column(JSONB)
    critical_alarm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_evidence_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    review_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deviation_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SterilizationLoadItem(Base):
    """STR-FR-004/012/013/028. `item_reference` is a captured, unenforced polymorphic reference
    (equipment/component/lot/container id) -- same "captured, not enforced" precedent as
    `MaterialLot.material_spec_version_id`, since the referenced table varies by `item_type`."""

    __tablename__ = "sterilization_load_items"
    __table_args__ = {"schema": "equipment"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.process_cycles.id"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    item_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str | None] = mapped_column(String(80))
    sterile_status: Mapped[str | None] = mapped_column(String(20))
    sterile_status_expiry: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SterileFilterUse(Base):
    """STR-FR-016/017/018/019/020/021/022/023. `filter_lot`/`filter_serial` are captured identity fields
    -- no dedicated filter master entity exists (frozen 4-entity data model). `reuse_count` defaults to 0
    and this pass never increments it via a second `install_filter` call on the same filter identity --
    default single-use per STR-FR-022's "safe default", reuse tracking itself is a SPEC_GAP."""

    __tablename__ = "sterile_filter_uses"
    __table_args__ = {"schema": "equipment"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    filter_lot: Mapped[str | None] = mapped_column(String(120))
    filter_serial: Mapped[str] = mapped_column(String(120), nullable=False)
    filter_type: Mapped[str | None] = mapped_column(String(80))
    manufacturer: Mapped[str | None] = mapped_column(String(160))
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    sterilization_cycle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.process_cycles.id"))
    housing_location: Mapped[str | None] = mapped_column(String(160))
    direction: Mapped[str | None] = mapped_column(String(40))
    installed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    installed_at: Mapped[datetime | None] = mapped_column()
    pre_use_integrity_result: Mapped[str | None] = mapped_column(String(20))
    pre_use_integrity_ref: Mapped[dict | None] = mapped_column(JSONB)
    post_use_integrity_result: Mapped[str | None] = mapped_column(String(20))
    post_use_integrity_ref: Mapped[dict | None] = mapped_column(JSONB)
    process_parameters: Mapped[dict | None] = mapped_column(JSONB)
    reuse_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="RECEIVED_ELIGIBLE")
    performer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deviation_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
