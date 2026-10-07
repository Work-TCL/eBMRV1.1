"""Workflow Handoff Notifications -- a net-new capability (project-owner-directed, no Document/SPEC-xxx
baseline id; not in the 01-115 specification set) built on WP-11's already-real event backbone
(`mutation.outbox_events` -> NATS JetStream -> `run_pull_consumer`/`consume_event_idempotently`, Document
73 SPEC-DATA-005) rather than a parallel notification/event mechanism (AG-09).

New `notifications` schema, same "Postgres-tracked, rebuildable, non-authoritative" tier as `readmodels.*`
(Document 75 SPEC-DATA-007) and `eventbus.consumer_inbox` (AG-11): every row here is a disposable
projection over regulated state that already lives authoritatively in `ebmr.release_scope`,
`qms.deviation_record`, `qms.capa_record` and `qms.controlled_document_version`. Losing this table loses
nothing regulated -- `service.py::rebuild_all()` recomputes it from those tables' current state.

`WorkflowNotification` is one row per (aggregate_type, aggregate_id, category) -- not one row per
recipient. "Who should see it" is resolved live, at read time, against the actor's *current*
`iam.user_site_roles`/`iam.role_permissions` grant of `required_permission_code` at `site_id` (the same
RBAC catalogue `policy.service.evaluate_policy()` already checks at the real Mutation Gateway for the next
command) -- never a hardcoded user id, and never itself an authorization decision (AG-14 analogue: this is
advisory routing, not a grant; the Gateway's own `evaluate_policy()`/signature-policy checks remain the
only real gate when someone actually acts). See `registry.py` for exactly which permission code each
category maps to, and `docs/generated/18_SPEC_GAPS.md` SG-214 for the one documented simplification (this
resolves the audience from the plain RBAC permission code checked at the router, not the possibly-narrower
`signature.signature_policy.required_role_id`/`signature_order` -- a safe over-inclusion for an advisory
nudge, never the actual write-time gate).

`WorkflowNotificationRead` is per-viewer "seen" state -- deliberately separate from the notification row
itself (many viewers may be able to see one open notification; each tracks their own read state
independently, and a stale/incorrect read row can never resolve or otherwise change the underlying
notification).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class WorkflowNotification(Base):
    __tablename__ = "workflow_notification"
    __table_args__ = (
        UniqueConstraint("aggregate_type", "aggregate_id", "category", name="uq_workflow_notification_identity"),
        Index("ix_workflow_notification_audience", "required_permission_code", "site_id", "resolved_at"),
        {"schema": "notifications"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # e.g. "batch_release_pending", "deviation_disposition_pending" -- registry.py's WORKFLOW_SPECS keys.
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    # The RBAC action code (iam.permissions.code) whose holders, at site_id, are this notification's
    # audience -- resolved live at read time, never denormalized into a per-user row.
    required_permission_code: Mapped[str] = mapped_column(String(100), nullable=False)
    # Nullable: a handful of aggregates this projection covers (oot_record, supplier_qualification, and
    # oos_record when its own site_id happens to be unset) are themselves not site-scoped in the real
    # authorization path either -- their own `evaluate_policy(..., site_id=None)` call sites already mean
    # "any site" (policy.service.effective_role_names's own documented site_id=None semantics). NULL here
    # means the same thing: audience resolution in service.py checks "holds the permission at ANY site"
    # instead of "at this site" -- never a guessed/invented site.
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    # SoD nudge only (not enforcement -- the Gateway's own independence check is what actually matters):
    # whoever last touched the aggregate into this pending state is excluded from its own audience.
    excluded_actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    entity_label: Mapped[str] = mapped_column(String(300), nullable=False)
    link_path: Mapped[str] = mapped_column(String(300), nullable=False)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class WorkflowNotificationRead(Base):
    __tablename__ = "workflow_notification_read"
    __table_args__ = (
        UniqueConstraint("notification_id", "user_id", name="uq_workflow_notification_read_identity"),
        {"schema": "notifications"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.workflow_notification.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    read_at: Mapped[datetime] = mapped_column(server_default=func.now())
