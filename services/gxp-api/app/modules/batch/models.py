import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# Authoritative batch lifecycle — UI state is never authoritative (mirrors MUT-FR-008 intent).
BATCH_STATES = (
    "planned",
    "issued",
    "in_execution",
    "on_hold",
    "production_complete",
    "qa_review",
    "released",
    "rejected",
    "closed",
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "planned": {"issued"},
    "issued": {"in_execution", "on_hold"},
    "in_execution": {"on_hold", "production_complete"},
    "on_hold": {"in_execution"},
    "production_complete": {"qa_review"},
    "qa_review": {"released", "rejected"},
    "released": {"closed"},
    "rejected": {"closed"},
    "closed": set(),
}

BATCH_STEP_STATES = ("pending", "ready", "in_progress", "completed", "skipped")


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (UniqueConstraint("batch_number"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.products.id"), nullable=False
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.recipes.id"), nullable=False)
    recipe_version: Mapped[int] = mapped_column(nullable=False)
    batch_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned")
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class BatchStep(Base):
    __tablename__ = "batch_steps"
    __table_args__ = (UniqueConstraint("batch_id", "recipe_step_id"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    recipe_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.recipe_steps.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    data: Mapped[dict | None] = mapped_column(JSONB)


class BatchReview(Base):
    __tablename__ = "batch_reviews"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000))
    signature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class BatchRelease(Base):
    __tablename__ = "batch_releases"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    released_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    signature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    released_at: Mapped[datetime] = mapped_column(server_default=func.now())
