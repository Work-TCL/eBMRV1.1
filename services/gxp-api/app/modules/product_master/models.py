"""Document 09 (SPEC-EBMR-000) — Product, Constituent & Regulatory Profile Master. New, additive module:
does not touch app/modules/product (the legacy Batch/Recipe-facing stub) at all. See migration
d5d48a66187f for the schema deviations from docs/generated/04_DATA_MODEL_CATALOGUE.md (tenant_id dropped,
FKs added, `version` added).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

LIFECYCLE_STATES = ("draft", "under_review", "released", "suspended", "obsolete", "superseded")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"under_review"},
    "under_review": {"draft", "released"},
    "released": {"suspended", "obsolete", "superseded"},
    "suspended": {"released"},
    "obsolete": set(),
    "superseded": set(),
}


class ProductFamily(Base):
    __tablename__ = "gxp_product_family"
    __table_args__ = (UniqueConstraint("family_code"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_code: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ProductVersion(Base):
    __tablename__ = "gxp_product_version"
    __table_args__ = (
        UniqueConstraint("product_business_id", "version_no"),
        UniqueConstraint("product_code", "version_no"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_business_id: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    product_code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_family_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_family.id")
    )
    lifecycle_state: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    manufacturing_profile_code: Mapped[str] = mapped_column(String(80), nullable=False)
    combination_product_type: Mapped[str | None] = mapped_column(String(40))
    pmoa_reference: Mapped[str | None] = mapped_column(String(255))
    part4_profile_code: Mapped[str | None] = mapped_column(String(80))
    sterile_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    finished_tracking_strategy: Mapped[str | None] = mapped_column(String(40))
    udi_applicable: Mapped[bool | None] = mapped_column(Boolean)
    strength_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    strength_uom: Mapped[str | None] = mapped_column(String(40))
    # SG-146 (remainder, module 4 of 8), MIG-FR-004 expand step: dual-written best-effort, backfillable
    # (ebmr.gxp_product_version is mutable — UPDATE granted, migration d5d48a66187f 0010).
    strength_uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    device_model_code: Mapped[str | None] = mapped_column(String(120))
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    released_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    version_hash: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


# PRD-FR-009: the controlled manufacturing-profile set that (per PRD-FR-010) requires a released sterile
# process profile before a draft can be released.
STERILE_REQUIRED_PROFILES = {"injectable_ddcp", "inhalation_ddcp"}


class ProductConstituent(Base):
    __tablename__ = "gxp_product_constituent"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False
    )
    constituent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    role_code: Mapped[str | None] = mapped_column(String(40))
    constituent_business_id: Mapped[str] = mapped_column(String(120), nullable=False)
    constituent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False
    )
    source_site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    tracking_strategy: Mapped[str | None] = mapped_column(String(40))
    sequence_no: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ConstituentCompatibilityVersion(Base):
    __tablename__ = "gxp_constituent_compatibility_version"
    __table_args__ = (UniqueConstraint("compatibility_code", "version_no"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    compatibility_code: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    drug_constituent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False
    )
    device_constituent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False
    )
    interface_constraints: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
