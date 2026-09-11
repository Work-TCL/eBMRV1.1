"""Document 14 (SPEC-EBMR-005) — Review-by-Exception & QA Review. New module. See migration
<pending>_0015_qa_review_schema for the schema deviations from docs/generated/04_DATA_MODEL_CATALOGUE.md.

Only 1 of Document 14's 3 owned entities (`qa_review_package`) is DDL-ready; `qa_review_item` and
`qa_review_comment` are prose-only field-name lists -- deferred as SG-053. Since almost every itemised
review behaviour (exception severity/disposition/assignment, changed-value/override lists as rows,
reviewer comments, return-for-action) is modelled as a `qa_review_item`/`qa_review_comment` row, this pass
builds only what's genuinely possible at the package level: create a package against a batch, an inline
completeness computation drawing on real existing signals (batch hold state, Vault integrity
verification, audit-trail corrections) instead of a persisted itemised index, package-level completion
gated on that computed completeness plus a Document 106 signature, reindexing/staleness detection, and a
site-scoped dashboard. `GET .../exceptions` is a computed, non-persisted view over real audit events and
Vault integrity checks -- not backed by qa_review_item rows. See SG-053/SG-054.

State model (real Document 14 §5): `CREATED -> INDEXING -> READY_FOR_REVIEW -> IN_REVIEW ->
ACTION_REQUIRED -> IN_REVIEW -> REVIEW_COMPLETE`, `REVIEW_COMPLETE -> INVALIDATED/REOPENED` on source
change. IN_REVIEW/ACTION_REQUIRED are entered and left through work on individual qa_review_item rows,
which don't exist this pass, and have no dedicated API endpoint of their own in Document 14's own 9-API
list either (no "start review" operation). QA_REVIEW_STATES below is the reduced, honestly-reachable
subset: CREATED and INDEXING are folded into one atomic create-and-index step (matching how the real
"exception indexing" and "completeness engine" are already computed inline, not as separate persisted
phases, since no itemised index exists to progress through); the package then reaches READY_FOR_REVIEW,
REVIEW_COMPLETE, or REOPENED.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

QA_REVIEW_STATES = ("READY_FOR_REVIEW", "REVIEW_COMPLETE", "REOPENED")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "READY_FOR_REVIEW": {"REVIEW_COMPLETE"},
    "REVIEW_COMPLETE": {"REOPENED"},
    "REOPENED": {"READY_FOR_REVIEW"},
}

# RBE-FR-005/028: real, if partial, completeness signals -- "complete" only when neither a blocker nor an
# exception was found; "blocked" whenever a genuine release blocker (hold, integrity failure) exists.
COMPLETENESS_STATUSES = ("complete", "has_exceptions", "blocked")


class QaReviewPackage(Base):
    __tablename__ = "qa_review_package"
    __table_args__ = (UniqueConstraint("batch_id"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"), nullable=False)
    batch_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    checklist_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    exception_index_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    completeness_status: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="READY_FOR_REVIEW")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()
