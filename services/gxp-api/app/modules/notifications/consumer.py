"""The notification consumer(s) -- reuses `eventbus/consumer.py::run_pull_consumer` +
`consume_event_idempotently()` exactly as `readmodels/projector.py` and `erp/consumer.py` already do
(same durable-pull-consumer, same `consumer_inbox` dedupe row committed in the same transaction as this
module's own write). One durable consumer per registered aggregate type (four today, `registry.py`
governs how many), all running the same generic `handle_workflow_event` handler -- adding a fifth
aggregate type to `registry.py` is enough for it to get its own consumer here with no code change in this
file.

`handle_workflow_event` deliberately never branches on `envelope["event_type"]`. Every event for a
registered aggregate type re-syncs by re-reading that aggregate's *current* authoritative state
(`registry.py`'s loader) rather than trying to interpret which transition this particular event
represents -- partly because that is simply the more robust design (idempotent regardless of delivery
order/duplicates, see `service.py`'s own docstring), and partly because it sidesteps a real pre-existing
quirk found while building this: `qms/document_commands.py` publishes `event_type="DocumentVersionReleased"`
for three different transitions (create/submit/release) on `controlled_document_version` -- state-driven
sync makes that quirk irrelevant here rather than something this module needs to work around or fix.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eventbus.consumer import run_pull_consumer
from app.modules.notifications import service as notifications_service
from app.modules.notifications.registry import WORKFLOW_SPECS

_CONSUMER_NAME_PREFIX = "workflow-notifications"


async def handle_workflow_event(session: AsyncSession, envelope: dict) -> dict:
    aggregate_type = envelope["aggregate_type"]
    spec = WORKFLOW_SPECS.get(aggregate_type)
    if spec is None:
        # Bound only by the wildcard subject actually subscribed (gxp.v1.<aggregate_type>.>); every
        # subject this consumer binds to already matches a registered aggregate_type, so this is
        # defensive, not an expected path.
        return {"skipped": True, "reason": f"unregistered aggregate_type={aggregate_type}"}

    aggregate_id = uuid.UUID(envelope["aggregate_id"])
    source_event_id = uuid.UUID(envelope["event_id"])
    return await notifications_service.sync_notification(
        session, spec=spec, aggregate_id=aggregate_id, source_event_id=source_event_id,
    )


async def run(*, stop_event: asyncio.Event) -> None:
    """Embedded background task, started from `app/main.py`'s lifespan next to the other WP-11 consumers.
    Fans out one `run_pull_consumer` per registered aggregate type, all sharing this process's one
    `stop_event` -- `app/main.py` only needs one task handle for this module, same shape as every other
    consumer entry there."""
    tasks = [
        asyncio.create_task(
            run_pull_consumer(
                subject=spec.nats_subject,
                durable_name=f"{_CONSUMER_NAME_PREFIX}-{aggregate_type}",
                handler=handle_workflow_event,
                consumer_name=f"{_CONSUMER_NAME_PREFIX}-{aggregate_type}",
                stop_event=stop_event,
            )
        )
        for aggregate_type, spec in WORKFLOW_SPECS.items()
    ]
    await asyncio.gather(*tasks)
