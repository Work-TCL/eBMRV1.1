"""Document 69 (SPEC-DATA-001) -- Enterprise Data Ownership, Persistence Topology & Data Lineage.

New `dataops` PostgreSQL schema. Adds exactly the 3 owned entities the approved
`04_DATA_MODEL_CATALOGUE.md` lists for Document 69: `data_ownership_registry`, `projection_checkpoint`,
`migration_batch`.

**What this module is.** Document 69 is a *governance / registry* specification, not a new regulated
domain. Its job is to declare -- machine-readably -- the single authoritative owner/store of every data
class already built in Documents 01-68, and to give the platform the read APIs and lint helpers that
enforce "no dual master" (AG-05). It is closest in shape to Document 66 (`app/modules/security/netzero`):
mostly a seeded catalogue plus a pure-library of checks, with one genuinely state-changing operation
(`POST /platform/v1/projections/{type}:rebuild`).

**No signature anywhere.** Document 106 has no SPEC-DATA-001 row, and Document 106 # 10 *explicitly*
lists "Projection rebuilds and cache invalidation" and "Search, export and read operations" as
operations that do not require a signature. So `rebuild_projection()` / `register_data_class()` /
`record_migration_provenance()` are RBAC-gated and audit-only -- no challenge, no `SIGNATURE_*` path.

**No `tenant_id` / `site_id`.** ADR-0006 (single-tenant-per-deployment; no `tenant_id` column anywhere)
plus: this registry is platform/product-wide governance metadata. `tenant_scoped` / `site_scoped` are
*attributes describing an entity* on `data_ownership_registry`, not scoping of the registry row itself
-- same treatment as every `security.*` table.

**Retention numbers stay unresolved (SG-005).** `data_ownership_registry.retention_policy_id` is a
*reference* to a retention policy, never a duration. Document 108's numeric retention periods are the
existing open gap SG-005; this module records the reference and does not invent a number (DATA-FR-022).

**No binary float.** Every count / size / version column is `BigInteger` (DATA-FR-019).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# data_ownership_registry.authoritative_store -- the storage tier that holds regulated truth for an
# entity. Mirrors Document 69 # 6 (POSTGRES|MARIADB|OBJECT|EXTERNAL) plus HISTORIAN for DATA-FR-010.
AUTHORITATIVE_STORES = ("POSTGRES", "MARIADB", "OBJECT", "HISTORIAN", "EXTERNAL")
# Non-authoritative projection tiers an entity's regulated truth is allowed to be *copied* into.
PROJECTION_TIERS = ("FRAPPE_MARIADB", "SEARCH", "CACHE", "ANALYTICS", "INTEGRATION")
# data_ownership_registry.classification -- DATA-FR-021 sensitive-data classes.
DATA_CLASSIFICATIONS = ("GXP", "PII", "SECURITY", "CONFIG", "OPERATIONAL", "PUBLIC")
REGISTRY_STATES = ("EFFECTIVE", "SUPERSEDED")

# projection_checkpoint.state
CHECKPOINT_STATES = ("IDLE", "REBUILDING", "LIVE", "STALE", "ERROR")

# migration_batch.reconciliation_status -- DATA-FR-024
RECONCILIATION_STATUSES = ("PENDING", "RECONCILED", "MISMATCH")
MIGRATION_BATCH_STATES = ("RECORDED", "SUPERSEDED")


class DataOwnershipRegistry(Base):
    """Document 69 # 6 `data_ownership_registry` -- one row per entity/data class, declaring its single
    authoritative service + store and the projection tiers it may legitimately be copied into.
    `resolve_data_owner()` reads this; `assert_authoritative_write_allowed()` rejects a write by any
    service that is not `authoritative_service`. Seeded from `05_DATABASE_OWNERSHIP_MATRIX.md`
    (`scripts/seed.py` / `tests/conftest.py`), superseded, never edited through a generic CRUD API
    (AG-06 / Document 113 §6); `register_data_class()` is the only writer and it goes through the
    Mutation Gateway (audit + outbox)."""

    __tablename__ = "data_ownership_registry"
    __table_args__ = (UniqueConstraint("entity_type"), {"schema": "dataops"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(160), nullable=False)
    authoritative_service: Mapped[str] = mapped_column(String(120), nullable=False)
    authoritative_store: Mapped[str] = mapped_column(String(20), nullable=False)
    # list[str] from PROJECTION_TIERS -- the tiers this entity may be projected into (DATA-FR-004).
    projection_targets: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tenant_scoped: Mapped[bool] = mapped_column(nullable=False, default=False)
    site_scoped: Mapped[bool] = mapped_column(nullable=False, default=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False, default="GXP")
    # Reference to a Document 108 retention policy -- NOT a duration (numeric periods unresolved, SG-005).
    retention_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    encryption_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # Provenance of this row (e.g. "05_DATABASE_OWNERSHIP_MATRIX.md", "Document 69").
    source_reference: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ProjectionCheckpoint(Base):
    """Document 69 # 6 `projection_checkpoint` -- the operational cursor for one rebuildable projection
    (a Frappe read model, a search index, an analytics export). Records how far the projection has been
    advanced from its authoritative source stream, when, and whether it is currently stale/rebuilding.
    `get_projection_freshness()` compares `last_source_version` against the authoritative aggregate;
    `rebuild_projection()` is the state-changing command that advances this row through the Mutation
    Gateway (version++ + audit + outbox + receipt)."""

    __tablename__ = "projection_checkpoint"
    __table_args__ = (UniqueConstraint("projection_type"), {"schema": "dataops"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # e.g. "frappe.batch_list", "search.batches", "analytics.yield_export"
    projection_type: Mapped[str] = mapped_column(String(120), nullable=False)
    # The authoritative entity/stream this projection is derived from (an `entity_type` in the registry).
    source_stream: Mapped[str] = mapped_column(String(160), nullable=False)
    last_source_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    last_source_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    projected_at: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="IDLE")
    error: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class MigrationBatch(Base):
    """Document 69 # 6 `migration_batch` -- DATA-FR-024 provenance for one imported/migrated data set:
    source system + artifact + hash, transform version, row-count / hash reconciliation and the
    approver/evidence reference. Written by `record_migration_provenance()` through the Mutation
    Gateway; it is migration provenance, not a user action (MIG-FR-013). Append-only / superseding
    (AG-08) -- a correction is a new row referencing the prior `batch_ref`."""

    __tablename__ = "migration_batch"
    __table_args__ = (UniqueConstraint("batch_ref"), {"schema": "dataops"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    source_system: Mapped[str] = mapped_column(String(160), nullable=False)
    source_artifact: Mapped[str] = mapped_column(String(300), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(160), nullable=False)
    transform_version: Mapped[str] = mapped_column(String(80), nullable=False)
    destination_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()
    source_row_count: Mapped[int | None] = mapped_column(BigInteger)
    loaded_row_count: Mapped[int | None] = mapped_column(BigInteger)
    reconciliation_hash: Mapped[str | None] = mapped_column(String(160))
    reconciliation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    approver: Mapped[str] = mapped_column(String(120), nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(300))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="RECORDED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
