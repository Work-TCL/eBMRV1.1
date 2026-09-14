"""Document 53 (SPEC-ERP-006) / Document 22 (SPEC-MAT-002D) live ERP posting consumer -- WP-11 Stage 4
(ADR-0011, SG-183 / SG-098 CON-FR-025/026).

The second real at-least-once consumer wired end to end (`eventbus/consumer.py::run_pull_consumer`),
after WP-11 Stage 3's readmodels projector. Subscribes to `MaterialConsumed` events and calls the
already-built, already-tested outbound ERP command machinery (`erp/commands.py::queue_erp_command`,
`erp/adapters/*.py`) automatically instead of requiring an operator to `POST /integration/v1/commands`
by hand for every consumption. `dispatch_erp_command()` itself -- the actual outbound HTTP call, retry
policy, dead-lettering -- is untouched; this module only ever queues, exactly like every other
`queue_erp_command()` caller.

**Deliberately scoped to ERPNext only.** Every adapter (`erpnext.py`, `sap.py`, `oracle_fusion.py`,
`dynamics365.py`) forwards `IntegrationCommand.payload` to its vendor verbatim -- there is no
vendor-neutral transformation layer anywhere in this codebase, so a single generic payload cannot be
correct for more than one vendor's native API shape at once. Building a real, vendor-neutral mapping for
all four (SAP OData composition, Oracle `inventoryTransactions`, Dynamics `InventJournalTrans` +
`dataAreaId`) without ever verifying against a live tenant would be exactly the kind of un-owned guess
AG-15 exists to stop. This module builds only ERPNext's real Stock Entry shape
(`items: [{item_code, qty, uom}]`, `purpose` is auto-injected by the adapter); a site whose only ACTIVE
`ErpInstance` is a different vendor is treated the same as a site with no ERP integration configured at
all (skip, not a failure) -- SAP/Oracle/Dynamics posting is future scope, not attempted here, same
disclosed-caveat class the adapters' own module docstrings already use for their own unverified mappings
(e.g. `erpnext.py`'s Reservation/Release-Availability doctype choices, `SG-125`).

**Warehouse is deliberately omitted from the payload.** No warehouse-mapping layer (GxP warehouse/location
-> ERPNext `s_warehouse`) exists anywhere in this codebase either -- inventing one here would be the same
class of guess. A real deployment would need ERPNext's own default-warehouse-per-item configuration to
carry this, or a future stage adds an explicit mapping; documented here as a known limitation, not
blocking (same non-blocking-caveat precedent as the adapters' own unverified operations).

**First-deploy backlog is deliberate, confirmed behaviour, not an oversight.** `jetstream.pull_subscribe()`
always binds a new durable with `deliver_policy=ALL` (EVT-FR-009: a durable never silently skips events
published before it first bound). For this consumer specifically that means: the very first time it is
ever deployed, it will replay every `MaterialConsumed` event already retained on `GXP_EVENTS` and queue a
`POST_CONSUMPTION` command for each one that has a mapped material and an eligible ERPNext instance --
including real historical consumption from before this consumer existed, if the outbox publisher has
already been running. Confirmed with the project owner before shipping (not silently decided): every one
of those events really did happen and should reach ERP eventually, and no live ERPNext tenant is
integrated yet in this environment, so there is no near-term risk of actually double-posting into a real
system. A future stage may want an explicit one-time "mark backlog as already reconciled" step before
pointing this consumer at a real production ERPNext tenant for the first time -- not built here.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp import commands as erp_commands
from app.modules.erp.models import ErpExternalMapping, ErpInstance
from app.modules.eventbus.consumer import run_pull_consumer
from app.modules.material.models import MaterialConsumption, MaterialLot

CONSUMER_NAME = "erp-material-consumption-poster"
SUBJECT = "gxp.v1.material_consumption.MaterialConsumed"

# The one vendor this consumer knows how to build a correct payload for -- see module docstring.
_SUPPORTED_VENDOR = "ERPNEXT"


async def handle_material_consumed_event(session: AsyncSession, envelope: dict) -> dict:
    """`run_pull_consumer`'s per-message handler, invoked inside `consume_event_idempotently()`'s own
    transaction (same `session`) -- the `consumer_inbox` dedupe row and `queue_erp_command()`'s own
    `IntegrationCommand`/audit/outbox writes commit or roll back together.

    Reads the full `MaterialConsumption` row by id (the outbox envelope's own payload is deliberately
    minimal, EVT-FR-013) rather than trusting anything beyond the id out of the envelope itself."""
    consumption_id = uuid.UUID(envelope["aggregate_id"])
    consumption = await session.get(MaterialConsumption, consumption_id)
    if consumption is None:
        raise ValueError(f"no material_consumption row found for {consumption_id}")
    if consumption.material_lot_id is None:
        # record_consumption() always resolves exactly one lot before creating this row (DSP-FR-017's
        # _resolve_consumption_lot never returns None) -- reaching this means the event was published for
        # a row that violates that invariant, a real defect, not a silent skip.
        raise ValueError(f"material_consumption {consumption_id} has no material_lot_id to post against")

    material_lot = await session.get(MaterialLot, consumption.material_lot_id)
    if material_lot is None:
        raise ValueError(f"material_lot {consumption.material_lot_id} not found for consumption {consumption_id}")

    instance = (
        await session.execute(
            select(ErpInstance)
            .where(
                ErpInstance.site_id == consumption.site_id,
                ErpInstance.status == "ACTIVE",
                ErpInstance.vendor == _SUPPORTED_VENDOR,
                ErpInstance.service_actor_user_id.is_not(None),
            )
            .order_by(ErpInstance.id)
        )
    ).scalars().first()
    if instance is None:
        # No ERPNext instance configured for this site (or none provisioned for automated posting yet,
        # migration 0103) -- ERP integration is optional per AG-13/Document 48, this is the expected
        # common case for most sites, not an error.
        return {
            "skipped": True, "reason": "no ACTIVE ERPNext instance with service_actor_user_id for this site",
            "site_id": str(consumption.site_id),
        }

    mapping = (
        await session.execute(
            select(ErpExternalMapping).where(
                ErpExternalMapping.erp_instance_id == instance.id,
                ErpExternalMapping.entity_type == "MATERIAL",
                ErpExternalMapping.internal_id == material_lot.material_id,
                ErpExternalMapping.mapping_status == "ACTIVE",
            )
        )
    ).scalars().first()
    if mapping is None:
        # A real, actionable gap (someone needs to approve a MATERIAL mapping for this material on this
        # instance) -- surfaced through the existing dead-letter mechanism (Stage 3), not silently dropped.
        raise ValueError(
            f"no ACTIVE MATERIAL ErpExternalMapping for material {material_lot.material_id} "
            f"on ERP instance {instance.id}"
        )

    payload = {
        "items": [{"item_code": mapping.external_id, "qty": str(consumption.quantity), "uom": consumption.uom}],
    }
    receipt = await erp_commands.queue_erp_command(
        session,
        erp_commands.QueueERPCommandCommand(
            idempotency_key=f"material-consumed:{envelope['event_id']}",
            erp_instance_id=instance.id,
            command_type="POST_CONSUMPTION",
            source_event_id=uuid.UUID(envelope["event_id"]),
            source_aggregate_type="material_consumption",
            source_aggregate_id=consumption.id,
            payload=payload,
        ),
        instance.service_actor_user_id,
    )
    return {"queued_command_id": str(receipt.aggregate_id), "erp_instance_id": str(instance.id)}


async def run(*, stop_event: asyncio.Event) -> None:
    """Embedded background task, started from `app/main.py`'s lifespan next to the outbox publisher, the
    Temporal worker and the readmodels projector."""
    await run_pull_consumer(
        subject=SUBJECT, durable_name=CONSUMER_NAME, handler=handle_material_consumed_event,
        consumer_name=CONSUMER_NAME, stop_event=stop_event,
    )