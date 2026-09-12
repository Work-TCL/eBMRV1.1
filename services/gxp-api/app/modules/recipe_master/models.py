"""Document 10 (SPEC-EBMR-001) — Master Recipe / Master Manufacturing Record. New, additive module: does
not touch app/modules/recipe (the legacy Batch-facing stub) at all. See migration d0a1a1bdfaef's docstring
for the schema deviations from docs/generated/04_DATA_MODEL_CATALOGUE.md.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

LIFECYCLE_STATES = ("draft", "under_review", "released", "suspended", "obsolete", "superseded")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"under_review"},
    "under_review": {"draft", "released"},
    "released": {"suspended", "obsolete", "superseded"},
    "suspended": {"released"},
    "obsolete": set(),
    "superseded": set(),
}

# RCP-FR-006: the controlled step-type set. A common engine reusable across all recipe authoring.
STEP_TYPES = (
    "instruction",
    "data_entry",
    "scan",
    "weigh",
    "equipment_check",
    "calculation",
    "ipc_qc",
    "signature",
    "verification",
    "timer",
    "hold_point",
    "material_consume",
    "assembly",
    "test",
    "packaging",
    "custom_approved_type",
)


class RecipeFamily(Base):
    __tablename__ = "gxp_recipe_family"
    __table_args__ = (UniqueConstraint("recipe_code"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_business_id: Mapped[str] = mapped_column(String(120), nullable=False)
    recipe_code: Mapped[str] = mapped_column(String(120), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    manufacturing_profile_code: Mapped[str] = mapped_column(String(80), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeVersion(Base):
    __tablename__ = "gxp_recipe_version"
    __table_args__ = (UniqueConstraint("recipe_family_id", "version_no"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_family.id"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    product_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_size_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    batch_size_uom: Mapped[str | None] = mapped_column(String(40))
    # SG-146 (remainder, module 4 of 8), MIG-FR-004 expand step: dual-written best-effort, backfillable
    # (ebmr.gxp_recipe_version is mutable — UPDATE granted, migration d0a1a1bdfaef 0011).
    batch_size_uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    lifecycle_state: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    graph_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1")
    released_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    version_hash: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeSection(Base):
    __tablename__ = "gxp_recipe_section"
    __table_args__ = (UniqueConstraint("recipe_version_id", "stable_section_code"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_version.id"), nullable=False
    )
    stable_section_code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    area_requirement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    parallel_group: Mapped[str | None] = mapped_column(String(40))
    expected_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeStep(Base):
    __tablename__ = "gxp_recipe_step"
    __table_args__ = (UniqueConstraint("recipe_version_id", "stable_step_code"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_version.id"), nullable=False
    )
    stable_step_code: Mapped[str] = mapped_column(String(80), nullable=False)
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_section.id"), nullable=False
    )
    step_type: Mapped[str] = mapped_column(String(60), nullable=False)
    instruction_text: Mapped[str | None] = mapped_column(String(4000))
    sequence_hint: Mapped[int] = mapped_column(Integer, nullable=False)
    required_role_code: Mapped[str | None] = mapped_column(String(80))
    qualification_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    signature_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    exception_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeStepDependency(Base):
    __tablename__ = "gxp_recipe_step_dependency"
    __table_args__ = (UniqueConstraint("predecessor_step_id", "successor_step_id"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    predecessor_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_step.id"), nullable=False
    )
    successor_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_step.id"), nullable=False
    )
    condition_rule_id: Mapped[str | None] = mapped_column(String(160))
    condition_rule_version: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeParameter(Base):
    __tablename__ = "gxp_recipe_parameter"
    __table_args__ = (UniqueConstraint("step_id", "parameter_code"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_step.id"), nullable=False)
    parameter_code: Mapped[str] = mapped_column(String(80), nullable=False)
    data_type: Mapped[str] = mapped_column(String(40), nullable=False)
    uom: Mapped[str | None] = mapped_column(String(40))
    # SG-146 (remainder, module 4 of 8), MIG-FR-004 expand step: dual-written best-effort, backfillable
    # (ebmr.gxp_recipe_parameter is mutable — UPDATE/DELETE granted, migration d0a1a1bdfaef 0011).
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    min_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    max_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    precision_digits: Mapped[int | None] = mapped_column(Integer)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rule_id: Mapped[str | None] = mapped_column(String(160))
    rule_version: Mapped[str | None] = mapped_column(String(40))
    manual_fallback_policy: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeEvidenceRequirement(Base):
    __tablename__ = "gxp_recipe_evidence_requirement"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_step.id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    required_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    allowed_mime_types: Mapped[str | None] = mapped_column(String(255))
    retention_class: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeMaterialRequirement(Base):
    """SG-045 (equipment/material half) — `min_value`/`max_value`/`uom`/`uom_id` mirror
    `RecipeParameter`'s own already-DDL-ready tolerance shape exactly (same "no rule-execution engine
    exists" precedent SG-089 documents for dispensing tolerance) rather than inventing a new tolerance
    schema. `alternative_material_spec_version_id`/`substitution_allowed` are captured, unenforced --
    same class as `RecipeStep.required_role_code` before SG-178 wired enforcement, or `equipment_class_id`
    elsewhere: declared but not yet gated by a runtime check. `material_spec_version_id` FKs the new
    SG-057 entity (migration d2d738c7f191)."""

    __tablename__ = "gxp_recipe_material_requirement"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_step.id"), nullable=False)
    material_spec_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_material_specification_version.id"), nullable=False
    )
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    min_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    max_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    uom: Mapped[str | None] = mapped_column(String(40))
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    alternative_material_spec_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_material_specification_version.id")
    )
    substitution_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consume_mode: Mapped[str | None] = mapped_column(String(40))
    genealogy_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeEquipmentRequirement(Base):
    """SG-045 (equipment half) — `equipment_class` is a captured, unenforced reference, the same
    precedent `EquipmentAsset.equipment_class_id` already uses (no equipment-class-master entity exists).
    `require_current_calibration`/`require_current_qualification` declare the gate this recipe step needs
    (would compare against `EquipmentAsset.calibration_status`/`.qualification_status`, mirroring SG-178's
    `required_role_code` pattern) but are NOT enforced by this pass -- BAT-FR-012/013's batch_execution
    step-start wiring (SG-048 #012/#013, explicitly deferred pending this schema) is a separate build.
    `require_current_cleaning` is captured for the same reason and additionally has no persistent status
    field to check against yet (cleaning state lives in separate CleaningExecution/LineClearance event
    records, not on EquipmentAsset)."""

    __tablename__ = "gxp_recipe_equipment_requirement"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_step.id"), nullable=False)
    equipment_class: Mapped[str] = mapped_column(String(80), nullable=False)
    exact_equipment_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_current_calibration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_current_qualification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_current_cleaning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
