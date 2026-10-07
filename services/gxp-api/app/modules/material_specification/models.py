import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# Client gap-analysis Phase 5 (2026-10-05): how each test row on a draft specification will actually be
# satisfied once material is received -- decided at spec-authoring time, same distinction the client drew
# for Equipment/QC generally (In-House test method reference / an approved External Lab / relying on the
# Supplier's own COA without independent testing).
FULFILLMENT_PATHS = ("in_house", "external_lab", "supplier_coa")


class MaterialSpecificationVersion(Base):
    """`gxp_material_specification_version` (SG-057, architecture rule C-014). Mirrors
    `product_master.ProductVersion`'s master+immutable-version split exactly — `material_id` links the
    existing flat `Material` master (C-013, `app/modules/material/models.py`) to a separately versioned,
    separately released specification, the same relationship Product has to its own version history.

    `acceptance_criteria` is a captured, unenforced JSONB field, the same precedent as
    `yield_reconciliation.tolerance_rule`/`packaging.tolerance_rule` elsewhere in this codebase — no
    acceptance-range execution/evaluation engine exists yet (that is QC method master, a separate open
    item), so this pass stores declared criteria without interpreting or enforcing them.
    """

    __tablename__ = "gxp_material_specification_version"
    __table_args__ = (
        UniqueConstraint("material_spec_business_id", "version_no"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_spec_business_id: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.materials.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    # Client gap-analysis Phase 5 (2026-10-05): superseded by MaterialSpecificationCriterion below --
    # nothing writes this anymore (confirmed zero real usage at the time of that change: no UI ever
    # populated it, and the one existing released row in the live database has it null). Left in place
    # rather than dropped (MIG-FR-004 expand/contract discipline -- a column this clearly inert is still
    # not removed in the same release that stops writing it).
    acceptance_criteria: Mapped[dict | None] = mapped_column(JSONB)
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    released_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    version_hash: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialSpecificationCriterion(Base):
    """Client gap-analysis Phase 5 (2026-10-05): the structured Test Name / Specification / Acceptance
    Criteria row the client described repeatedly (matches a typical Certificate of Analysis table shape),
    replacing `MaterialSpecificationVersion.acceptance_criteria`'s unused JSONB blob. Mutable only while
    the parent version is still `draft` (enforced in commands.py, not a DB constraint -- the parent's own
    `lifecycle_state` is the single source of truth, same as every other draft/release split in this
    codebase) -- once released, the parent's Vault snapshot is the immutable record of what these rows
    said at release time, not this table directly."""

    __tablename__ = "gxp_material_specification_criterion"
    __table_args__ = (
        Index("ix_material_spec_criterion_version", "material_spec_version_id", "sequence"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_spec_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_material_specification_version.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specification_text: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Client gap-analysis Phase 5: decided per-test, at spec-authoring time -- drives which pathway
    # Material Receipt/QC testing follows for this test once material actually arrives (a later phase's
    # concern; this column is captured here, not yet read/enforced anywhere downstream).
    fulfillment_path: Mapped[str | None] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
