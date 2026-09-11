"""Document 28 (SPEC-QMS-003) — Nonconformance Management. Same owner service as Documents 26/27
(`services/gxp-api/src/modules/qms`), so these two entities live in the same `qms` schema
(migration 0021_ncr_schema).

`nonconformance_record`'s 10-field list in docs/generated/04_DATA_MODEL_CATALOGUE.md is DDL-ready as
given. `ncr_disposition` is a prose field-name list but -- like capa_action (SG-045's precedent) --
genuinely unambiguous, typed directly as an ordinary engineering decision.

Extra columns beyond the catalogue's literal field list are each traced directly to requirement text:
  - `source_type/source_id/source_version` (NCR-FR-002: "Failed QC/test/inspection can create NCR
    candidate")
  - `segregation` (NCR-FR-003: "Hold/segregate exact lots/serials/quantities")
  - `requirement_ref` is in the catalogue already; `evaluation` (NCR-FR-005: "severity, usability,
    quality/safety/performance and investigation need")
  - `supplier_link` (NCR-FR-010), `capa_required`/`capa_rationale` (NCR-FR-012), `release_blocker_active`
    (NCR-FR-011, a local flag only -- see SG-059's precedent, wiring it into the release module is
    cross-module work out of scope), `verification` (NCR-FR-009, recorded directly on the parent record
    since Document 28 doesn't declare a third entity for it)

State model (real Document 28 §4: OPEN -> SEGREGATED -> EVALUATION -> DISPOSITION_PENDING -> REWORK/
RETURN/SCRAP/CONDITIONAL_DISPOSITION -> VERIFICATION -> QA_CLOSURE -> CLOSED). Document 28's own 6-op API
list has no operation to drive DISPOSITION_PENDING or QA_CLOSURE as separately reachable phases -- the same
fold-in pattern used throughout this module family (SG-055's original reasoning): DISPOSITION_PENDING is
inherent in reaching EVALUATION (the record IS pending disposition once evaluated, with no distinct
"pending" transition of its own); QA_CLOSURE is folded into close()'s own gate + signature ceremony.
CONDITIONAL_DISPOSITION is named USE_AS_IS here, matching NCR-FR-007's own vocabulary, and REPAIR is added
alongside REWORK per NCR-FR-006's own text ("Rework, repair where allowed...").

NCR-FR-016 ("Reopen: New evidence can reopen") has **no operation** in Document 28's own 6-op API list --
unlike Documents 26/27, which both had a `reopen` endpoint, this document's own API section simply omits
one despite naming the capability in its requirements table. No reopen operation is built this pass --
see docs/generated/18_SPEC_GAPS.md SG-069 (same "don't invent an endpoint" discipline as everywhere else
in this codebase) -- so CLOSED is a genuine terminal state here.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# NCR-FR-001: the scope types Document 28 itself enumerates.
NCR_SCOPE_TYPES = ("material", "component", "subassembly", "device", "packaging", "finished_output")

# NCR-FR-002: the automatic-source types Document 28 itself enumerates ("Failed QC/test/inspection").
NCR_SOURCE_TYPES = ("qc_result", "test", "inspection")

# NCR-FR-006: the disposition outcomes Document 28 itself enumerates ("Rework, repair where allowed,
# return, scrap/destroy, concession/use-as-is").
NCR_DISPOSITION_TYPES = ("REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS")

REWORK_LIKE_DISPOSITIONS = ("REWORK", "REPAIR")

NCR_STATES = (
    "OPEN", "SEGREGATED", "EVALUATION", "REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS",
    "VERIFICATION", "CLOSED",
)

NCR_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"SEGREGATED"},
    "SEGREGATED": {"EVALUATION"},
    "EVALUATION": {"EVALUATION", *NCR_DISPOSITION_TYPES},
    "REWORK": {"REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS", "VERIFICATION"},
    "REPAIR": {"REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS", "VERIFICATION"},
    "RETURN": {"REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS", "VERIFICATION"},
    "SCRAP": {"REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS", "VERIFICATION"},
    "USE_AS_IS": {"REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS", "VERIFICATION"},
    "VERIFICATION": {"CLOSED"},
    "CLOSED": set(),
}


class NonconformanceRecord(Base):
    __tablename__ = "nonconformance_record"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("ncr_number"),
        Index("ix_nonconformance_record_state", "site_id", "state", "severity"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    ncr_number: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(40))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_version: Mapped[int | None] = mapped_column()
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_records: Mapped[list] = mapped_column(JSONB, nullable=False)
    requirement_ref: Mapped[dict] = mapped_column(JSONB, nullable=False)
    defect_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    segregation: Mapped[dict | None] = mapped_column(JSONB)
    evaluation: Mapped[dict | None] = mapped_column(JSONB)
    supplier_link: Mapped[dict | None] = mapped_column(JSONB)
    capa_required: Mapped[bool | None] = mapped_column()
    capa_rationale: Mapped[str | None] = mapped_column(Text)
    release_blocker_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    verification: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    closure_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class NcrDisposition(Base):
    """Insert-only history: NCR-FR-013's partial scope means multiple dispositions can exist for one
    NCR (e.g. part of a lot reworked, part scrapped). Full cross-row quantity-coverage reconciliation
    (proving every unit in scope_records has been dispositioned) is not built this pass -- closure only
    requires at least one disposition to exist; see the module docstring's "genuinely buildable subset"
    discipline used throughout this codebase for reconciliation-shaped problems.
    """

    __tablename__ = "ncr_disposition"
    __table_args__ = (
        Index("ix_ncr_disposition_ncr", "ncr_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ncr_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.nonconformance_record.id"), nullable=False)
    affected_scope: Mapped[list] = mapped_column(JSONB, nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    serials: Mapped[list | None] = mapped_column(JSONB)
    disposition_type: Mapped[str] = mapped_column(String(20), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    rework_route: Mapped[dict | None] = mapped_column(JSONB)
    follow_up_test_requirements: Mapped[dict | None] = mapped_column(JSONB)
    # NCR-FR-007: use-as-is requires an identified authorizing subject distinct from the general
    # `justification` narrative -- only populated for disposition_type == "USE_AS_IS".
    use_as_is_authorized_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
