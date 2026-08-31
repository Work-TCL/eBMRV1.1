import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# Document 18 (SPEC-MAT-001) §5. Supplier-level lifecycle.
SUPPLIER_STATES = ("draft", "under_qualification", "approved", "suspended", "disqualified")
# Qualification-record lifecycle driving the supplier-level transitions above.
QUALIFICATION_STATES = ("requested", "in_review", "approved", "conditional", "rejected")


class Supplier(Base):
    """Document 18 §6 `supplier` -- DDL-ready in docs/generated/04_DATA_MODEL_CATALOGUE.md. `role_type`
    carries SUP-FR-002's supplier-vs-manufacturer distinction; Document 18 defines no separate manufacturer
    table. No `tenant_id` (ADR-0006, single-organization platform -- same deviation as every other additive
    module). No `site_id`: a supplier is an org-wide legal identity; its sites are `SupplierSite` rows.
    """

    __tablename__ = "supplier"
    __table_args__ = (UniqueConstraint("supplier_code"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_code: Mapped[str] = mapped_column(String(120), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_type: Mapped[str] = mapped_column(String(40), nullable=False)  # supplier | manufacturer | both
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    country: Mapped[str | None] = mapped_column(String(80))
    external_mappings: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SupplierSite(Base):
    """Document 18 §6 `supplier_site` -- prose-only field list, typed here as an ordinary engineering
    decision (SG-045's precedent): supplier ID, site identity/address, manufacturer flag, regulatory/
    certification refs, status.
    """

    __tablename__ = "supplier_site"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.supplier.id"), nullable=False
    )
    site_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address_line1: Mapped[str | None] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    state_province: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(30))
    country: Mapped[str | None] = mapped_column(String(80))
    manufacturer_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    certification_refs: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SupplierQualification(Base):
    """Document 18 §6 `supplier_qualification` -- DDL-ready. `requested_by_user_id` is not in the
    published field list; added so the approval step can enforce SIG-FR-018/SUP-FR-007's independent-signer
    requirement (signer != requester), the same SoD pattern `batch.release` already uses against
    `BatchReview.reviewer_user_id`.
    """

    __tablename__ = "supplier_qualification"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.supplier_site.id"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    scope: Mapped[dict | None] = mapped_column(JSONB)
    risk_class: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="requested")
    justification: Mapped[str | None] = mapped_column(String(2000))
    effective_from: Mapped[datetime | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column()
    quality_agreement_vault_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    approval_signatures: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SupplierQualificationEvidence(Base):
    """SUP-FR-005 "versioned evidence" (questionnaire/certifications/licenses/audits/capability evidence/
    test history/attachments) -- implemented by reusing the existing Vault release pattern
    (`POST /vault/v1/masters/{type}/{businessId}/release`, `vault.gxp_vault_object`) rather than inventing a
    parallel evidence-storage mechanism. This table is the join between a qualification and the vault
    objects offered as its evidence; it does not write vault objects itself.
    """

    __tablename__ = "supplier_qualification_evidence"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_qualification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.supplier_qualification.id"), nullable=False
    )
    vault_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id"), nullable=False
    )
    evidence_category: Mapped[str] = mapped_column(String(60), nullable=False)
    added_at: Mapped[datetime] = mapped_column(server_default=func.now())
