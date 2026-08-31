"""Document 72 (SPEC-DATA-004) -- Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle.

New `evidence` PostgreSQL schema. Two owned entities per `04_DATA_MODEL_CATALOGUE.md`:
`evidence_object` (16 fields) and `evidence_manifest` (5). The **authoritative store is split**: the
raw bytes live in object storage (S3 / Azure Blob / on-prem, or the Phase-1 `LocalEvidenceStore`) and
PostgreSQL holds the metadata / hash / ownership / retention / legal-hold record (OBJ-FR-005/009).

**Immutability (OBJ-FR-004/017).** A finalized object is never overwritten or edited: a correction is
a new `evidence_object` row + a `superseded_by` link. The app role has `SELECT/INSERT/UPDATE` (needed
for state transitions STAGED->FINALIZED->ARCHIVED and the legal-hold flag) but **no `DELETE`** -- a
purge is a controlled state change to `PURGED`, never a row delete.

**Signature.** Only `apply_evidence_legal_hold()` is signed -- Document 106 row 142 (`Performed`,
"Authorized holder (Production / QA)", 1 signature, independence None, reason required). That signer
class is a role *pair*, not one dedicated role, so the seeded policy row uses `required_role_id=None`
with the RBAC `evidence.legal_hold` permission defining "authorized holder" -- the exact precedent of
Document 106 row 108 (`equipment_asset/hold`). No SPEC_GAP.

**No `tenant_id`** (ADR-0006). `site_id` is kept nullable -- evidence attaches to a site-scoped owner
record (a batch, a QC result, a process cycle). All sizes are `BigInteger`; no float columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

EVIDENCE_PROVIDERS = ("LOCAL", "S3", "AZURE_BLOB")
# STAGED -> (QUARANTINE) -> FINALIZED -> ARCHIVED ; any -> MISSING (integrity) ; FINALIZED/ARCHIVED -> PURGED
EVIDENCE_STATES = ("STAGED", "QUARANTINE", "FINALIZED", "ARCHIVED", "MISSING", "PURGED")
HASH_ALGORITHMS = ("SHA-256",)
MANIFEST_TYPES = ("RELEASE", "EXPORT", "BATCH_ISSUE", "RENDITION")
MANIFEST_STATES = ("ACTIVE", "SUPERSEDED")


class EvidenceObject(Base):
    """Document 72 # 6 `evidence_object`. `content_hash` is NULL while STAGED and set at
    `finalize_evidence_upload()` after the stored object's digest is verified against `expected_hash`
    (OBJ-FR-002/016). `object_key` is content-addressed by the store; `provider_version_id` is the
    provider's own immutable version handle (e.g. S3 Object Lock version) where available."""

    # No location unique constraint: content addressing means two evidence rows may legitimately point
    # at the same content-addressed object (e.g. one PDF attached to two batches); `put()` is idempotent
    # for identical bytes and refuses a same-key overwrite with *different* bytes (OBJ-FR-004).
    __tablename__ = "evidence_object"
    __table_args__ = ({"schema": "evidence"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    owner_type: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_version: Mapped[int | None] = mapped_column(BigInteger)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="LOCAL")
    bucket: Mapped[str] = mapped_column(String(200), nullable=False)
    object_key: Mapped[str] = mapped_column(String(400), nullable=False)
    provider_version_id: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(400))  # metadata only (OBJ-FR-015)
    hash_algorithm: Mapped[str] = mapped_column(String(20), nullable=False, default="SHA-256")
    expected_hash: Mapped[str | None] = mapped_column(String(128))
    content_hash: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="STAGED")
    retention_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    retention_until: Mapped[datetime | None] = mapped_column()
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    legal_hold_ref: Mapped[str | None] = mapped_column(String(120))
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class EvidenceManifest(Base):
    """Document 72 # 6 `evidence_manifest` -- an immutable, ordered list of evidence IDs + hashes +
    versions that a regulated record / release package / inspection export references (OBJ-FR-008/027).
    `canonical_hash` is a digest over the canonicalized `items` so the manifest cannot be silently
    re-ordered or trimmed. A change is a new manifest row (`manifest_version` +1, prior `SUPERSEDED`)."""

    __tablename__ = "evidence_manifest"
    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", "manifest_type", "manifest_version",
                         name="uq_evidence_manifest_identity"),
        {"schema": "evidence"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_type: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_version: Mapped[int | None] = mapped_column(BigInteger)
    manifest_type: Mapped[str] = mapped_column(String(20), nullable=False)
    manifest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    canonical_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    renderer_version: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
