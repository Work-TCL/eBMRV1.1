"""Document 30 (SPEC-QMS-005) — Document Control. Same owner service as Documents 26-29
(`services/gxp-api/src/modules/qms`), so these three entities live in the same `qms` schema
(migration 0025_document_control_schema). Unlike Documents 26-29, this module's own API prefix is
`/documents/v1` (not `/qms/v1`), matching Document 30 section 6 exactly.

`controlled_document`'s 8-field list and `controlled_document_version`'s 11-field list in
docs/generated/04_DATA_MODEL_CATALOGUE.md are both DDL-ready as given -- the master+version split mirrors
Document 09/10's `ProductFamily`/`ProductVersion` and `RecipeFamily`/`RecipeVersion` pattern exactly
(app/modules/product_master/models.py), including reusing `vault_service.release_master()` for the same
canonical-snapshot-plus-digest release mechanism. `controlled_copy` is a prose field-name list but --
like ncr_disposition (SG-045's precedent) -- genuinely unambiguous, typed directly.

`change_control_id` gets a **real enforced FK** to `qms.change_control` (not an unenforced logical
reference) -- Document 29, built in this same pass, makes that possible for the first time; this is the
"other direction" SG-072 already anticipated (change_control -> other modules, versus other modules ->
change_control).

Extra columns beyond the catalogue's literal field list are each traced directly to requirement text:
  - `rendition_hash` (DOC-FR-004: "differentiate editable source from released rendition")
  - `review_workflow` (DOC-FR-005: reviewer roles/completion), `training_impact` (DOC-FR-013, same
    flag+data pattern as SG-060/SG-063's precedent -- real assignment wiring is out of scope, SG-079),
    `acknowledgment_required` (DOC-FR-014 -- the flag is captured; per-user acknowledgment capture has no
    operation, SG-079)
  - `superseded_by_version_id` (DOC-FR-008: self-referential, set on the *old* version when a new one
    becomes effective)
  - `source_relationships` (DOC-FR-016: parent/child/reference links)
  - `is_external`/`external_source`/`external_revision` (DOC-FR-018: external standards/guidance tracking)
  - `retirement_reason`/`retired_at` (DOC-FR-021, folded into obsolete() -- see below)

State model (real Document 30 section 4: DRAFT -> REVIEW -> APPROVED/RELEASED -> EFFECTIVE ->
SUPERSEDED -> OBSOLETE/ARCHIVED, plus DRAFT/REVIEW -> CANCELLED). Document 30's own 7-op API list has no
operation to drive APPROVED as separate from RELEASED (the same fold-in pattern this module family always
uses: release() itself, being the signed act, both approves and releases in one step) and no operation
anywhere for CANCELLED either -- unlike Documents 26-29, no DOC-FR requirement actually names
"cancellation" (the diagram names the state but the requirements table never does), so nothing is gapped
for it; it is simply not reachable. DOC-FR-021 (retirement, "reason/effective date/impact") is folded into
obsolete() -- the same endpoint reuse pattern CAPA-FR-016/CHG-FR-021 used, since Document 30 has no
separate retire operation either.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# DOC-FR-001: the document types Document 30 itself enumerates ("SOPs, policies, specifications, work
# instructions, forms and other regulated documents"). DOC-FR-017/018 fold into this same enum ("form" /
# "external").
DOCUMENT_TYPES = ("sop", "policy", "specification", "work_instruction", "form", "external", "other")

VERSION_STATES = ("DRAFT", "REVIEW", "RELEASED", "EFFECTIVE", "SUPERSEDED", "OBSOLETE")

VERSION_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"REVIEW"},
    "REVIEW": {"RELEASED"},
    "RELEASED": {"EFFECTIVE"},
    "EFFECTIVE": {"OBSOLETE"},
    "SUPERSEDED": {"OBSOLETE"},
    "OBSOLETE": set(),
}

COPY_STATES = ("issued", "returned", "destroyed")


class ControlledDocument(Base):
    __tablename__ = "controlled_document"
    __table_args__ = (UniqueConstraint("document_code"), {"schema": "qms"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    document_code: Mapped[str] = mapped_column(String(120), nullable=False)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    site_scope: Mapped[list | None] = mapped_column(JSONB)
    is_external: Mapped[bool] = mapped_column(nullable=False, default=False)
    external_source: Mapped[str | None] = mapped_column(String(200))
    external_revision: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ControlledDocumentVersion(Base):
    __tablename__ = "controlled_document_version"
    __table_args__ = (
        Index("ix_controlled_document_version_document", "document_id"),
        Index("ix_controlled_document_version_state", "document_id", "state"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.controlled_document.id"), nullable=False)
    version_label: Mapped[str] = mapped_column(String(60), nullable=False)
    vault_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rendition_hash: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    review_workflow: Mapped[dict | None] = mapped_column(JSONB)
    training_impact: Mapped[dict | None] = mapped_column(JSONB)
    acknowledgment_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    source_relationships: Mapped[list | None] = mapped_column(JSONB)
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    change_control_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.change_control.id"))
    periodic_review_due: Mapped[datetime | None] = mapped_column()
    superseded_by_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.controlled_document_version.id"))
    retirement_reason: Mapped[str | None] = mapped_column(Text)
    retired_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ControlledCopy(Base):
    __tablename__ = "controlled_copy"
    __table_args__ = (UniqueConstraint("document_version_id", "copy_number"), {"schema": "qms"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.controlled_document_version.id"), nullable=False)
    copy_number: Mapped[str] = mapped_column(String(60), nullable=False)
    recipient: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="issued")
    issued_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now())
    returned_at: Mapped[datetime | None] = mapped_column()
    destroyed_at: Mapped[datetime | None] = mapped_column()
