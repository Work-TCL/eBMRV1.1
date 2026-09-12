import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


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
