"""Document 73 (SPEC-DATA-005) -- NATS/JetStream Event Bus, Transactional Outbox & Async Contracts.

**`gxp_outbox` already exists.** Document 73 # 6 lists it as one of this module's 2 owned entities, but
it is the same table `app/modules/mutation/models.py::OutboxEvent` (`mutation.outbox_events`) built in
WP-01 and used by every domain command handler through `app/mutation/gateway.py::write_outbox_event` --
that IS the transactional outbox EVT-FR-002/003/004 require. This module does not create a second one
(AG-05 / DATA-FR-001); it adds the one field EVT-FR-001's canonical envelope needs that the WP-01 table
didn't yet carry (`schema_version`, additive migration 0072) and the *new* entity Document 73 actually
needs: `consumer_inbox`.

**`consumer_inbox`** (Document 73 # 6, 5 fields) -- EVT-FR-005/006: the dedupe/idempotency record for
an at-least-once consumer. One row per `(consumer_name, event_id)`; `result` and `aggregate_version`
let `consume_event_idempotently()` return the prior outcome instead of re-running a non-idempotent
business effect on redelivery.

New `eventbus` schema (only `consumer_inbox` lives here -- the outbox stays owned by `mutation`).
No `tenant_id` (ADR-0006); no `site_id` (a consumer's dedupe record is not itself site-scoped -- the
event payload it processed may be). No signature (Document 106 has no SPEC-DATA-005 row).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

CONSUMER_RESULTS = ("PROCESSED", "DEAD_LETTERED")


class ConsumerInbox(Base):
    __tablename__ = "consumer_inbox"
    __table_args__ = (
        UniqueConstraint("consumer_name", "event_id", name="uq_consumer_inbox_identity"),
        {"schema": "eventbus"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consumer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    aggregate_version: Mapped[int | None] = mapped_column()
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="PROCESSED")
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=1)
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime] = mapped_column(server_default=func.now())
