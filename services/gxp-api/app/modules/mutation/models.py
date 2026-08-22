import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class CommandReceipt(Base):
    __tablename__ = "command_receipts"
    __table_args__ = {"schema": "mutation"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    command_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    expected_version: Mapped[int | None] = mapped_column()
    resulting_version: Mapped[int] = mapped_column(nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="committed")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = {"schema": "mutation"}

    idempotency_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    command_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mutation.command_receipts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = {"schema": "mutation"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column()
