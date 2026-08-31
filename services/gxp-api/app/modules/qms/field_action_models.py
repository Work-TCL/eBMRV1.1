"""Document 36 (SPEC-QMS-011) — Recall / Field Action Management. Same owner service as Documents 26-35
(`services/gxp-api/src/modules/qms`), so `field_action`, `field_action_scope_item`,
`field_action_communication` and `field_action_reconciliation` are added to the existing `qms` schema.

All four entities' field lists in docs/generated/04_DATA_MODEL_CATALOGUE.md are prose-only, but -- like
every prior module in this family (SG-045's precedent) -- genuinely unambiguous: typed directly as an
ordinary engineering decision. `risk_assessment_ref` is a real nullable FK into the existing
`qms.risk_record` (Document 33) rather than a second risk store (AG-05, FAR-FR-005).

State model (Document 36 §4):
`ASSESSMENT -> SCOPE_DEFINITION -> REGULATORY_DECISION -> APPROVAL -> EXECUTION/NOTIFICATION ->
RECONCILIATION -> EFFECTIVENESS -> CLOSURE_REVIEW -> CLOSED`, plus `CLOSED -> EXPANDED/REOPENED
(controlled)`. Document 36's own 8-op API list is shorter than this text, so the same fold-in pattern used
throughout this module family applies:
  - `scope()` is the ONE endpoint that carries three distinct roles depending on current state: it moves
    ASSESSMENT -> SCOPE_DEFINITION on first call (FAR-FR-003/004/007/008 -- affected/constituent scope,
    distribution hold and consignee snapshot are all captured as `field_action_scope_item` rows in this
    single call); it can be called again while still SCOPE_DEFINITION to add more items (no transition);
    and it can be called while CLOSED to reopen the field action (FAR-FR-019 "scope expansion"), moving
    state back to SCOPE_DEFINITION, incrementing `revision`, and firing `FieldActionScopeExpanded` instead
    of `FieldActionScopeFrozen`.
  - `approve()` moves REGULATORY_DECISION -> APPROVAL -> immediately makes EXECUTION/NOTIFICATION
    reachable; APPROVAL is not a resting state a caller has to separately advance out of.
  - `communications()` is the EXECUTION/NOTIFICATION step (FAR-FR-009/010 folded together -- a
    communication package version IS the notification, tracked with recipient/delivery/ack status on the
    same row); its first call moves APPROVAL -> EXECUTION_NOTIFICATION.
  - CLOSURE_REVIEW is not a resting state: `close()` performs it in one step, checking reconciliation
    completeness (RECONCILIATION_INCOMPLETE) and a recorded effectiveness check (EFFECTIVENESS_REQUIRED)
    before allowing CLOSED.
  - FAR-FR-017 (status updates/milestones) has no dedicated field: every state transition already writes
    an append-only audit event (AG-06), which IS the tracked milestone history.
  - FAR-FR-015 ("maintain correction/removal records even if reporting decision is no") requires no
    special gating: `communications()`/`reconcile()`/`effectiveness()`/`close()` all proceed regardless of
    `reportability_assessment`'s content -- only the FAR-FR-006 decision itself is captured, it never
    blocks execution.

Deferred this pass (see docs/generated/18_SPEC_GAPS.md SG-105/SG-106, same discipline as SG-097/SG-103):
  - FAR-FR-008's ERP/WMS/CRM consignee resolution is caller-supplied `distribution_ref` JSONB, not a real
    cross-module/external-system query (no ERP/WMS integration exists yet, WP-07 territory).
  - FAR-FR-016 (CAPA link) is captured as `capa_required`/`capa_rationale` flag+rationale, matching every
    prior QMS module's precedent, without calling `capa_commands.create_capa()`.
  - FAR-FR-020 (export) has no operation in Document 36's own 8-op API list; served by the existing
    generic audit export path (AUD-FR-022).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# FAR-FR-002, verbatim from Document 36.
ACTION_TYPES = ("recall", "correction", "removal", "field_action", "customer_advisory", "stock_recovery")

# FAR-FR-001, verbatim from Document 36.
TRIGGER_TYPES = ("complaint", "deviation", "capa", "trend", "regulatory_request", "management_decision")

FIELD_ACTION_STATES = (
    "ASSESSMENT",
    "SCOPE_DEFINITION",
    "REGULATORY_DECISION",
    "APPROVAL",
    "EXECUTION_NOTIFICATION",
    "RECONCILIATION",
    "EFFECTIVENESS",
    "CLOSED",
)


class FieldAction(Base):
    __tablename__ = "field_action"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("action_number"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    action_number: Mapped[str] = mapped_column(String(120), nullable=False)
    action_type: Mapped[str] = mapped_column(String(60), nullable=False)
    trigger_ref: Mapped[dict] = mapped_column(JSONB, nullable=False)
    risk_assessment_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.risk_record.id"))
    reportability_assessment: Mapped[dict | None] = mapped_column(JSONB)
    effectiveness_check: Mapped[dict | None] = mapped_column(JSONB)
    # FAR-FR-016 -- deferred flag+rationale, see module docstring / SG-105.
    capa_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    capa_rationale: Mapped[str | None] = mapped_column(Text)
    scope_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # FAR-FR-019: bumped every time a CLOSED field action is reopened via scope() (scope expansion).
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="ASSESSMENT")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class FieldActionScopeItem(Base):
    __tablename__ = "field_action_scope_item"
    __table_args__ = {"schema": "qms"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    field_action_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.field_action.id"), nullable=False)
    product_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"))
    lot_batch_serial_refs: Mapped[dict | None] = mapped_column(JSONB)
    # FAR-FR-008: ERP/WMS/CRM consignee scope -- caller-supplied, not cross-system resolved (see SG-105).
    distribution_ref: Mapped[dict | None] = mapped_column(JSONB)
    # FAR-FR-007: block undistributed inventory when required.
    distribution_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="identified")
    action_required: Mapped[str | None] = mapped_column(String(40))
    action_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class FieldActionCommunication(Base):
    __tablename__ = "field_action_communication"
    __table_args__ = {"schema": "qms"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    field_action_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.field_action.id"), nullable=False)
    package_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recipient: Mapped[str] = mapped_column(String(200), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column()
    delivery_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    ack_status: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class FieldActionReconciliation(Base):
    __tablename__ = "field_action_reconciliation"
    __table_args__ = (UniqueConstraint("field_action_id"), {"schema": "qms"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    field_action_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.field_action.id"), nullable=False)
    affected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contacted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    returned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    corrected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    destroyed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unavailable_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outstanding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
