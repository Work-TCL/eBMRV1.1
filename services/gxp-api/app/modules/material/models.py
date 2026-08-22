import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# MAT-009: automatic quarantine at receipt. MAT-011: QC disposition states.
LOT_STATES = ("quarantine", "released", "rejected", "consumed", "expired")


class Material(Base):
    """Raw material / component master (MAT-001-adjacent — the regulated identity a lot is received
    against). Mirrors ebmr.products in shape deliberately: same kind of master-data aggregate."""

    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("site_id", "code"), {"schema": "materials"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialLot(Base):
    """One received lot/container. Authoritative quality-status aggregate for MAT-009/011/013."""

    __tablename__ = "material_lots"
    __table_args__ = (UniqueConstraint("internal_lot"), {"schema": "materials"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.materials.id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    supplier_lot: Mapped[str | None] = mapped_column(String(100))
    manufacturer_lot: Mapped[str | None] = mapped_column(String(100))
    internal_lot: Mapped[str] = mapped_column(String(100), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="quarantine")
    expiry_date: Mapped[date | None] = mapped_column()
    retest_date: Mapped[date | None] = mapped_column()
    received_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    version: Mapped[int] = mapped_column(nullable=False, default=1)


class MaterialLotDisposition(Base):
    """QC release/reject decision on a lot (MAT-011). Signed — same pattern as batch_reviews."""

    __tablename__ = "material_lot_dispositions"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # released | rejected
    reason: Mapped[str | None] = mapped_column(String(1000))
    signature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    disposed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    disposed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialIssue(Base):
    """Lot -> batch genealogy link (MAT-015/MAT-021 minimal form): which lot, how much, into which
    batch/step. This table *is* the batch's material genealogy trace for Phase 1."""

    __tablename__ = "material_issues"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    batch_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.batch_steps.id")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    issued_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now())
