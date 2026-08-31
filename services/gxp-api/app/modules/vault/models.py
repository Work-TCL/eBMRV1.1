import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class VaultObject(Base):
    """Document 06 (SPEC-GXP-004) — `gxp_vault_object`. Append-only: a release or correction always
    creates a new row (`supersedes_object_id`/`corrected_from_object_id` link back to the prior one);
    nothing here is ever UPDATEd, so there is no optimistic-concurrency version column the way mutable
    aggregates have one — `internal_version` *is* the version (VLT-FR-001/009/023).
    """

    __tablename__ = "gxp_vault_object"
    __table_args__ = (
        UniqueConstraint("object_type", "business_id", "internal_version"),
        {"schema": "vault"},
    )

    object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    business_id: Mapped[str] = mapped_column(String(160), nullable=False)
    internal_version: Mapped[int] = mapped_column(Integer, nullable=False)
    business_version_label: Mapped[str | None] = mapped_column(String(80))
    schema_version: Mapped[str] = mapped_column(String(30), nullable=False, default="1")
    canonical_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    digest_algorithm: Mapped[str] = mapped_column(String(40), nullable=False, default="sha256")
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="released")
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    supersedes_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    corrected_from_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    retention_class: Mapped[str | None] = mapped_column(String(80))
    released_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by_subject: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))


class VaultEvidence(Base):
    """`gxp_vault_evidence` — evidence items linked to a released vault object (VLT-FR-005)."""

    __tablename__ = "gxp_vault_evidence"
    __table_args__ = {"schema": "vault"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    evidence_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(120))
    sequence: Mapped[int | None] = mapped_column(Integer)


class RecordCorrection(Base):
    """`gxp_record_correction` (VLT-FR-010/011) — the one vault entity that legitimately gets UPDATEd
    (its own status/completed_at/resulting_object_id) as a request moves requested -> completed; the
    vault objects it references are still never edited, only superseded."""

    __tablename__ = "gxp_record_correction"
    __table_args__ = {"schema": "vault"}

    correction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="requested")
    reason_code: Mapped[str | None] = mapped_column(String(80))
    reason_text: Mapped[str | None] = mapped_column(Text)
    impact_assessment: Mapped[dict | None] = mapped_column(JSONB)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approved_by_signatures: Mapped[dict | None] = mapped_column(JSONB)
    resulting_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()
