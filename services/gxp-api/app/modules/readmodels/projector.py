"""Document 75 (SPEC-DATA-007) live search projector -- WP-11 Stage 3 (ADR-0011, SG-183).

The first real at-least-once consumer wired end to end (`consumer.py::run_pull_consumer`) onto anything
in this codebase: applies `material_lot` domain events into the Postgres-backed search index
(`readmodels.search.index_authoritative_projection`) incrementally, instead of requiring an operator to
call `POST /search/v1/indexes/material_lot:rebuild` (a full audit-ledger rescan) for every update.

Chosen as the first live-wired index deliberately for what it does NOT need to invent: `material_lot` is
already both the real `aggregate_type` `material/commands.py` publishes under (`gxp.v1.material_lot.*`,
verified against the actual `write_outbox_event(aggregate_type="material_lot", ...)` call sites) and the
`index_type` `router.py`'s own `_ALLOWED_FILTERS`/`_ALLOWED_SORT` already carries a field allowlist for
-- no new aggregate_type-to-index_type mapping and no new field-exposure decision is made here, both are
reused exactly as already committed. `gxp_batch` was considered and set aside: its outbox events publish
as `aggregate_type="batch"`, not `"gxp_batch"` -- wiring it would mean inventing that mapping, which SG-183
did not ask this pass to decide (see PHASE_4_WP11_STAGE3.md).

AG-11: this index stays non-authoritative and rebuildable regardless of this consumer existing --
`rebuild_search_index()` (the full audit-ledger rescan) is untouched and remains the recovery path if this
consumer is ever behind, down, or its checkpoint needs to be thrown away and rebuilt from scratch.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eventbus.consumer import run_pull_consumer
from app.modules.readmodels.search import index_authoritative_projection
from app.modules.audit.models import AuditEvent

CONSUMER_NAME = "readmodels-material-lot-projector"
SUBJECT = "gxp.v1.material_lot.>"
INDEX_TYPE = "material_lot"
ENTITY_TYPE = "material_lot"

# Mirrors app/modules/readmodels/router.py::_ALLOWED_FILTERS["material_lot"] -- READ-FR-009's already
# code-reviewed allowlist for this index_type. Deliberately not re-derived or widened here; if the two
# ever need to diverge that is its own reviewed change, not something this file should decide alone.
ALLOWED_FIELDS = {"state"}


async def handle_material_lot_event(session: AsyncSession, envelope: dict) -> dict:
    """`run_pull_consumer`'s per-message handler, invoked inside `consume_event_idempotently()`'s own
    transaction (same `session`) so the `consumer_inbox` dedupe row and this projection update commit or
    roll back together. Reads the audit ledger's own `new_value` for this exact
    (aggregate_id, aggregate_version) -- the same authoritative source `rebuild_search_index()` reads --
    rather than the outbox envelope's own payload, which is deliberately minimal per event type
    (EVT-FR-013) and does not always carry a full `state` snapshot. A version this cannot find in the
    audit ledger is treated as a handler failure (nak/redeliver, then dead-letter) rather than silently
    skipped: it would mean an event was published for a transaction that never committed an audit row,
    which AG-09's one-transaction guarantee says should never happen."""
    aggregate_id = uuid.UUID(envelope["aggregate_id"])
    aggregate_version = envelope["aggregate_version"]

    new_value = (
        await session.execute(
            select(AuditEvent.new_value).where(
                AuditEvent.aggregate_id == aggregate_id,
                AuditEvent.aggregate_version == aggregate_version,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if new_value is None:
        raise ValueError(
            f"no audit event found for material_lot {aggregate_id} version {aggregate_version} "
            "-- cannot project a state this consumer cannot verify against the authoritative ledger"
        )

    row = await index_authoritative_projection(
        session, index_type=INDEX_TYPE, entity_type=ENTITY_TYPE, entity_id=aggregate_id,
        source_version=aggregate_version, allowed_fields=ALLOWED_FIELDS, source_payload=new_value,
    )
    return {"entity_id": str(aggregate_id), "source_version": row.source_version, "state": row.state}


async def run(*, stop_event: asyncio.Event) -> None:
    """Embedded background task, started from `app/main.py`'s lifespan next to the outbox publisher and
    the Temporal worker."""
    await run_pull_consumer(
        subject=SUBJECT, durable_name=CONSUMER_NAME, handler=handle_material_lot_event,
        consumer_name=CONSUMER_NAME, stop_event=stop_event,
    )