"""Document 16 (SPEC-EBMR-007) — Packaging, Labeling & Reconciliation. New module. See migration
<pending>_0017_packaging_schema for the schema deviations from docs/generated/04_DATA_MODEL_CATALOGUE.md.

`label_issue` is DDL-ready. `packaging_run`, `label_reconciliation` and `package_node` are prose-only
field-name lists in the catalogue, but -- like Document 15's release_evaluation/release_decision -- all
three are genuinely unambiguous (mostly bigint counters, a state/version pair, self-referential hierarchy
fields); typed here directly as an ordinary engineering decision, the same latitude SG-045/SG-055 already
used. No `label_version`/artwork-master or `print_job` entity exists anywhere in this codebase's data
model catalogue (not even in Document 16's own 4-entity list, despite `print_job_id` being referenced on
`label_issue` and a `POST /packaging/v1/print-jobs` endpoint being listed) -- `label_version_id` and
`print_job_id` are therefore unenforced logical-reference columns, and `POST /packaging/v1/print-jobs`,
`POST /packaging/v1/labels/{id}/reprint`, `POST .../label-application` and `POST .../inspection` are not
built this pass (no entity to persist their results against) -- see SG-056.

None of Document 16's 10 API operations require a Document 106 signature (every row in its own API table
lists "—" for Signature). None of the 10 are a GET, either -- Document 16's own API section (§6) defines
zero read operations, even though its UI Surfaces section (§8) lists read-oriented screens (Packaging Run,
Line Clearance, Packaging Materials, ...) that would need one. This looks like a real authoring gap in the
source document rather than an intentional "no independent read API" boundary; consistent with the "don't
invent an endpoint outside the document's own list" discipline used throughout this build, no GET is added
this pass either -- see SG-056.

State model (real Document 16 §4): `NOT_READY -> LINE_CLEARANCE -> READY -> IN_PROGRESS ->
RECONCILIATION_PENDING -> COMPLETE`, alternates `HOLD, EXCEPTION, ABORTED`. There is exactly one
line-clearance endpoint (not a separate start/complete pair), so LINE_CLEARANCE is folded into a single
`not_ready -> ready` transition rather than modelled as its own reachable pending state. EXCEPTION/
ABORTED have no driving endpoint in Document 16's own 10-API list and are not reachable this pass.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

PACKAGING_STATES = ("not_ready", "ready", "in_progress", "reconciliation_pending", "complete", "hold")

# PKG-FR-024 (packaging hold) has no driving endpoint anywhere in Document 16's own 10-API list -- unlike
# Documents 11/12/15's hold actions, there is no POST .../hold operation. "hold" stays a named state (the
# source's own catalogue includes it) but is unreachable this pass rather than inventing an endpoint the
# document doesn't define -- see SG-056.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "not_ready": {"ready"},
    "ready": {"in_progress"},
    "in_progress": {"in_progress", "reconciliation_pending"},
    "reconciliation_pending": {"reconciliation_pending", "complete"},
    "complete": set(),
    "hold": set(),
}

RECONCILIATION_RESULTS = ("balanced", "discrepancy")
PACKAGE_LEVELS = ("unit", "carton", "shipper", "pallet")


class PackagingRun(Base):
    __tablename__ = "packaging_run"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"), nullable=False)
    # "product/package configuration version" -- no dedicated packaging-configuration entity exists
    # anywhere in this codebase; reuses product_version_id generically, same latitude device_unit already
    # used for "production specification snapshot" (Document 12).
    product_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False)
    line_ref: Mapped[str | None] = mapped_column(String(120))  # no equipment master to FK to yet (SG-050/055)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="not_ready")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    line_clearance_completed: Mapped[bool] = mapped_column(nullable=False, default=False)
    reconciliation_state: Mapped[str] = mapped_column(String(40), nullable=False, default="not_started")
    started_at: Mapped[datetime | None] = mapped_column()
    ended_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LabelIssue(Base):
    __tablename__ = "label_issue"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    packaging_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.packaging_run.id"), nullable=False)
    label_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # no label-master entity exists yet (SG-056)
    quantity_issued: Mapped[int] = mapped_column(nullable=False)
    serial_range: Mapped[dict | None] = mapped_column(JSONB)
    print_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # no print_job entity exists yet (SG-056)
    issued_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now())
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="issued")


class LabelReconciliation(Base):
    __tablename__ = "label_reconciliation"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    packaging_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.packaging_run.id"), nullable=False)
    issued: Mapped[int] = mapped_column(nullable=False)
    applied: Mapped[int] = mapped_column(nullable=False, default=0)
    returned: Mapped[int] = mapped_column(nullable=False, default=0)
    destroyed: Mapped[int] = mapped_column(nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(nullable=False, default=0)
    samples: Mapped[int] = mapped_column(nullable=False, default=0)
    calculated_variance: Mapped[int] = mapped_column(nullable=False)
    tolerance_rule: Mapped[str | None] = mapped_column(String(120))  # no released tolerance rule exists yet (SG-056)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    investigation_link: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PackageNode(Base):
    """No public write API exists for this entity (not in Document 16's own 10-API list) -- built and
    exercised as an internal service function only, the same pattern genealogy's node/edge creation
    already uses."""

    __tablename__ = "package_node"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_level: Mapped[str] = mapped_column(String(20), nullable=False)
    business_ref: Mapped[str | None] = mapped_column(String(120))
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"), nullable=False)
    parent_package_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.package_node.id"))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
