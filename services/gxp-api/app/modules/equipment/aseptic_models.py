"""Document 40 (SPEC-EQP-003) — Sterile / Aseptic Manufacturing Operations. Same `equipment` module/schema
as Documents 38/39/41/42 (AG-05). Built last in the WP-06 pass (39 -> 41 -> 42 -> 40) so its readiness
composition can call the real functions those documents already built:
`em.commands.get_area_readiness()` (Document 41), `equipment.commands.get_eligibility()` (Document 38),
`sterilization.commands.get_item_status()` (Document 42) and the sibling
`cleaning.commands.get_area_line_clearance_status()` added this pass.

Two deliberate deviations from the spec's literal §5 data model, same restraint discipline as every prior
document's substitutions:
- `aseptic_operation.recipe_stage_id` -> `batch_step_id` (real FK to `ebmr.batch_steps`, the actual
  execution-time anchor `MaterialIssue` and other modules already use -- no "recipe stage" concept exists
  anywhere in `batch_execution`/`recipe_master`).
- `aseptic_operation.environment_snapshot_ref uuid` -> `readiness_snapshot JSONB` (the full computed
  readiness result captured at `start`, not a dangling FK to a table this document never declares).

`aseptic_profile_version` was seed-only through 2026-09-06 (no create/release endpoint in Document 40's
own 7-op API list), same precedent as `cleaning_procedure_version`/`process_cycle_profile_version`.
**2026-09-07, project-owner-directed** (see `aseptic_commands.py::create_profile_version`'s own docstring):
a `POST /aseptic/v1/profiles` create endpoint was added — still no *release* stage (rows go straight to
`state="RELEASED"`, same as the seed row), so this remains outside Document 40's declared API list, not a
literal implementation of it; logged in `18_SPEC_GAPS.md` (SG-176) as a deliberate deviation, same
treatment as SG-081's `warehouse_location.create`.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

OPERATION_STATES = ("PREPARATION", "EXECUTION", "ASEPTIC_COMPLETE", "HOLD")
INTERVENTION_TYPES = ("inherent", "routine", "corrective", "non_routine")
EVENT_SEVERITIES = ("info", "warning", "critical")


PROFILE_STATES = ("RELEASED", "SUPERSEDED")


class AsepticProfileVersion(Base):
    """ASP-FR-001/002/003/007/008/010/013/014/020. Seed-only through 2026-09-06 (see module docstring);
    create/supersede added 2026-09-07 (SG-176). `state` transitions RELEASED -> SUPERSEDED only, on the
    *old* row, when a new version supersedes it -- the row's own content columns are never rewritten after
    creation (AG-08/DATA-FR-017), only this lifecycle marker and `version` (optimistic concurrency)."""

    __tablename__ = "aseptic_profile_versions"
    __table_args__ = (UniqueConstraint("profile_number", "version_no"), {"schema": "equipment"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    profile_number: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(nullable=False, default=1)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.products.id"))
    required_area_classification: Mapped[str | None] = mapped_column(String(40))
    personnel_qualifications: Mapped[dict | None] = mapped_column(JSONB)
    sterile_input_requirements: Mapped[dict | None] = mapped_column(JSONB)
    intervention_catalogue: Mapped[dict | None] = mapped_column(JSONB)
    hold_time_rules: Mapped[dict | None] = mapped_column(JSONB)
    em_dependencies: Mapped[dict | None] = mapped_column(JSONB)
    filter_sterilization_requirements: Mapped[dict | None] = mapped_column(JSONB)
    release_blockers: Mapped[dict | None] = mapped_column(JSONB)
    validation_reference: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="RELEASED")
    supersedes_profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.aseptic_profile_versions.id")
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AsepticOperation(Base):
    """ASP-FR-004/005/006/007/008/009/013/014/025/026. `sterile_input_refs`/`equipment_ids` are captured
    JSONB lists of {item_id, item_kind} / equipment_asset ids -- the real inputs the readiness composition
    and `complete` iterate over. No dedicated API operation exists to manage these as separate rows (the
    spec's own 7-op list has no such endpoint), so they are set once at `create` and read thereafter, same
    "captured, not a separate CRUD surface" precedent as `SterilizationLoadItem`'s creation-time-only list.

    The spec's 4-state PREPARATION/AREA_READY/ASEPTIC_SETUP/EXECUTION progression collapses onto
    PREPARATION -> EXECUTION at `start` (there is no dedicated "area-ready"/"setup" transition endpoint,
    same restraint as Document 42 collapsing declared sub-states onto the transitions its own API actually
    exposes) -- `start` performs the full readiness check in one step and refuses to transition if not
    ready (ASP-FR-005/006/007/008, Codex rule "never let operator start with failed area readiness").

    `media_fill_reference` (ASP-FR-018) and `qc_test_order_id`/`qc_result_id` (ASP-FR-019) added on the
    SG-117 follow-up pass -- captured references only, same "captured, not a separate CRUD surface"
    precedent as `sterile_input_refs`/`equipment_ids` above. Neither is validated against the referenced
    record's own state/result (that cross-check, and any resulting release-blocker wiring, has no
    established precedent anywhere in this codebase yet -- see SG-117's remaining open items).
    """

    __tablename__ = "aseptic_operations"
    __table_args__ = {"schema": "equipment"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    batch_step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch_step.id"))
    area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_areas.id"), nullable=False)
    profile_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.aseptic_profile_versions.id"), nullable=False)
    sterile_input_refs: Mapped[dict | None] = mapped_column(JSONB)
    equipment_ids: Mapped[dict | None] = mapped_column(JSONB)
    media_fill_reference: Mapped[dict | None] = mapped_column(JSONB)
    qc_test_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_test_order.id"))
    qc_result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_result.id"))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="PREPARATION")
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    readiness_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    complete_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deviation_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AsepticIntervention(Base):
    """ASP-FR-010/011/012. `planned=False` (an unplanned intervention) always sets
    `requires_deviation=True` on both the intervention and its parent operation, and always holds the
    operation (ASP-FR-012 "no hidden intervention"; Codex rule "never let operator create arbitrary
    intervention category during production" -- `intervention_type` is constrained to
    `INTERVENTION_TYPES`, not free text)."""

    __tablename__ = "aseptic_interventions"
    __table_args__ = {"schema": "equipment"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.aseptic_operations.id"), nullable=False)
    intervention_type: Mapped[str] = mapped_column(String(40), nullable=False)
    planned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    operator_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    started_at: Mapped[datetime | None] = mapped_column()
    ended_at: Mapped[datetime | None] = mapped_column()
    location: Mapped[str | None] = mapped_column(String(160))
    reason: Mapped[str | None] = mapped_column(String(400))
    impacted_unit_scope: Mapped[dict | None] = mapped_column(JSONB)
    evidence_ref: Mapped[dict | None] = mapped_column(JSONB)
    requires_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deviation_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AsepticEventTimeline(Base):
    """ASP-FR-021/022/025. Append-only. `severity="critical"` (an EM/HVAC excursion or operator/gown
    breach, ASP-FR-021/022) holds the parent operation, same treatment as an unplanned intervention."""

    __tablename__ = "aseptic_event_timeline"
    __table_args__ = {"schema": "equipment"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.aseptic_operations.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str | None] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    payload: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
