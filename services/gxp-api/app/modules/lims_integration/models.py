import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# Document 24 (SPEC-QC-002) §5. Only GXP_MANAGED behavior is built this pass -- SG-067.
OWNERSHIP_MODES = ("gxp_managed", "lims_managed_with_sync", "hybrid")
BUILDABLE_OWNERSHIP_MODES = ("gxp_managed",)


class LimsInstance(Base):
    """Document 24 §6 `lims_instance` -- prose-only field list, typed as an ordinary engineering
    decision (SG-045's precedent). No API operation registers an instance (Document 24's own 6-operation
    §8 list has none) -- instances are provisioned as configuration data, same class of decision as
    Document 106's own signature-policy floor. `service_actor_user_id` stands in for a dedicated
    machine-identity model, which does not exist anywhere in this codebase (SG-067 / LIMS-FR-013)."""

    __tablename__ = "lims_instance"
    __table_args__ = (UniqueConstraint("instance_code"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_code: Mapped[str] = mapped_column(String(80), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    provider_type: Mapped[str] = mapped_column(String(60), nullable=False)
    provider_version: Mapped[str | None] = mapped_column(String(40))
    endpoint_url: Mapped[str | None] = mapped_column(String(300))
    auth_method: Mapped[str | None] = mapped_column(String(40))
    ownership_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="gxp_managed")
    service_actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LimsMapping(Base):
    """Document 24 §6 `lims_mapping` -- prose-only, typed directly. Also doubles as the LIMS-FR-011
    ordering ledger for accepted results: one row per (instance, external_entity_id) tracks the highest
    `mapping_version` (== external_result_version) accepted so far, `internal_object_id` pointing at the
    latest accepted `qc_result` row."""

    __tablename__ = "lims_mapping"
    __table_args__ = (
        UniqueConstraint("instance_id", "external_entity_type", "external_entity_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.lims_instance.id"), nullable=False)
    internal_object_type: Mapped[str] = mapped_column(String(60), nullable=False)
    internal_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    internal_object_version: Mapped[int | None] = mapped_column()
    external_entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    external_entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    mapping_version: Mapped[int] = mapped_column(nullable=False, default=1)
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LimsMessage(Base):
    """Document 24 §6 `lims_message` -- prose-only, typed directly. `external_event_id` is unique per
    instance -- the LIMS-FR-010 duplicate-protection key. Also the LIMS-FR-024 dead-letter record: a
    message that fails processing is retained here with `status='dead_letter'`, never deleted."""

    __tablename__ = "lims_message"
    __table_args__ = (
        UniqueConstraint("instance_id", "external_event_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.lims_instance.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # inbound | outbound
    external_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    internal_correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload_hash: Mapped[str | None] = mapped_column(String(64))
    schema_version: Mapped[str | None] = mapped_column(String(20))
    adapter_version: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    error_code: Mapped[str | None] = mapped_column(String(80))
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    sent_at: Mapped[datetime | None] = mapped_column()
    received_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
