"""Document 75 (SPEC-DATA-007) -- Caching, Search, Read Models, Reporting Projections & Analytics Data
Access. New `readmodels` PostgreSQL schema. Two owned entities per `04_DATA_MODEL_CATALOGUE.md`:
`projection_document_metadata` and `read_model_checkpoint`. Both are, by the catalogue's own
"authoritative store" column, "Redis / search / read models (rebuildable, NON-AUTHORITATIVE)" --
governed metadata *about* a non-authoritative tier, tracked in PostgreSQL so it survives a cache/search
restart and is itself auditable, same shape as Document 69's `dataops.projection_checkpoint` but at a
different granularity:

- `projection_document_metadata` -- **per indexed document** (READ-FR-012): one row per entity
  actually placed in a search index, carrying the allowlisted (READ-FR-009) fields that were indexed,
  its source version and when it was projected. This is the Postgres-backed default search provider
  (READ-FR-008: "pluggable... not hard-dependent on one commercial engine") -- Phase 1 has no live
  OpenSearch/Elasticsearch, so `readmodels/search.py` indexes into this table and queries it with
  `ILIKE`/JSONB containment instead of a real search engine. Swapping in OpenSearch changes only
  `search.py`'s body.
- `read_model_checkpoint` -- **per index-type / read-model / export definition** (READ-FR-016/017): the
  refresh cursor + frozen `source_cutoff` a rebuild/refresh/export advances. Distinct from Document 69's
  `projection_checkpoint` (which tracks *any* projection's cross-cutting ownership/version cursor at
  platform-governance granularity) -- this one is scoped to this module's own read/search/report tier
  and additionally carries the reproducibility cutoff READ-FR-017 requires for frozen report snapshots.

No `tenant_id` (ADR-0006); no `site_id` (both are platform/product-level tracking, same as the
`security.*` and `dataops.*` precedent). No signature (Document 106 has no SPEC-DATA-007 row). No float
columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

DOCUMENT_STATES = ("LIVE", "STALE")
CHECKPOINT_STATES = ("FRESH", "REFRESHING", "STALE", "ERROR")


class ProjectionDocumentMetadata(Base):
    __tablename__ = "projection_document_metadata"
    __table_args__ = (
        UniqueConstraint("index_type", "entity_type", "entity_id", name="uq_projection_document_identity"),
        Index("ix_projection_document_metadata_index_type", "index_type"),
        {"schema": "readmodels"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    index_type: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. "search.batches"
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Only the READ-FR-009 allowlisted fields for this index_type -- never the full domain payload.
    indexed_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="LIVE")
    projected_at: Mapped[datetime] = mapped_column(server_default=func.now())
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class ReadModelCheckpoint(Base):
    __tablename__ = "read_model_checkpoint"
    __table_args__ = (UniqueConstraint("model_name"), {"schema": "readmodels"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)  # "search.batches" | "export.yield_report"
    source_stream: Mapped[str] = mapped_column(String(160), nullable=False)
    # READ-FR-017: the frozen cutoff a report/export/rebuild used, independent of live dashboard state.
    source_cutoff: Mapped[datetime | None] = mapped_column()
    refreshed_at: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="STALE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
