import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class SignaturePolicy(Base):
    """Policy data, not code conditionals — AG-07 / SIG-FR-004 equivalent."""

    __tablename__ = "signature_policies"
    __table_args__ = (
        UniqueConstraint("record_type", "action"),
        {"schema": "signature"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    meaning: Mapped[str] = mapped_column(String(50), nullable=False)
    required_role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.roles.id"))
    requires_independent_signer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SignatureChallenge(Base):
    __tablename__ = "signature_challenges"
    __table_args__ = (UniqueConstraint("nonce"), {"schema": "signature"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_version: Mapped[int] = mapped_column(nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    meaning: Mapped[str] = mapped_column(String(50), nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Signature(Base):
    """Immutable once written — no update path exposed anywhere in the app layer."""

    __tablename__ = "signatures"
    __table_args__ = {"schema": "signature"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signature.signature_challenges.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    meaning: Mapped[str] = mapped_column(String(50), nullable=False)
    record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_version: Mapped[int] = mapped_column(nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_context: Mapped[dict | None] = mapped_column(JSONB)
