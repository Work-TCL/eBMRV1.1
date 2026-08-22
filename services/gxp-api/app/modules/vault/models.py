import uuid
from datetime import datetime

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class VaultVersion(Base):
    """Append-only canonical snapshot of a released/effective version of a regulated object."""

    __tablename__ = "vault_versions"
    __table_args__ = (
        UniqueConstraint("object_type", "business_id", "version"),
        {"schema": "vault"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    canonical_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(server_default=func.now())
    effective_to: Mapped[datetime | None] = mapped_column()
    released_by_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
