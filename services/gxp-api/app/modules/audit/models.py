import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class AuditEvent(Base):
    """Append-only. The app DB role has INSERT/SELECT only — no UPDATE/DELETE (locked down in migration
    0002_privileges). Never write to this table outside the mutation gateway's transaction.
    """

    __tablename__ = "audit_events"
    __table_args__ = {"schema": "audit"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # human | service
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reason: Mapped[str | None] = mapped_column(String(1000))
    old_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    prev_event_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
