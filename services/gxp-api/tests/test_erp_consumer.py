"""Document 53 (SPEC-ERP-006) / Document 22 (SPEC-MAT-002D), WP-11 Stage 4 (ADR-0011, SG-183 / SG-098
CON-FR-025/026): the second real at-least-once consumer wired end to end -- automated ERPNext consumption
posting (`app/modules/erp/consumer.py`).

Every test runs a genuinely real chain: the real `POST /materials/v1/consumptions` command (through the
full dispense -> consume flow `tests/test_material_consumption_flow.py` already establishes), the real
`MaterialConsumed` outbox row it writes, published for real to the live local NATS JetStream broker via
`outbox.publish_outbox_event()` (not a hand-built envelope), fetched back for real by a real durable pull
consumer, and processed through the real `consume_event_idempotently()` / `queue_erp_command()` path. No
live ERPNext/SAP/Oracle/Dynamics tenant exists anywhere in this environment or is claimed here -- this
consumer only ever queues an `IntegrationCommand`; the actual outbound HTTP dispatch is
`dispatch_erp_command()`'s own job, already covered by `tests/test_erp_flow.py`.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.eventbus import consumer as eventbus_consumer
from app.modules.eventbus import jetstream
from app.modules.eventbus.models import ConsumerInbox
from app.modules.erp import consumer as erp_consumer
from app.modules.erp.models import ErpExternalMapping, ErpInstance, IntegrationCommand
from app.modules.material.models import DispensedContainer, MaterialConsumption
from app.modules.mutation.models import OutboxEvent
from app.modules.eventbus.outbox import publish_outbox_event
from tests.conftest import auth_headers, idem, login
from tests.test_material_consumption_flow import _build_dispensed_container


async def _nats_reachable() -> bool:
    try:
        await jetstream.connect()
        return jetstream.is_connected()
    except Exception:  # noqa: BLE001 - genuinely "not reachable", not a test failure
        return False


@pytest.fixture(scope="module", autouse=True)
async def _jetstream_connection():
    if not await _nats_reachable():
        pytest.skip(f"No live NATS JetStream broker reachable at {settings.nats_url} -- skipping, not faking")
    yield
    await jetstream.close()


async def _record_real_consumption(client, db, seeded, code: str, lot_code: str) -> tuple[str, str, MaterialConsumption]:
    """Real dispense -> consume chain. Returns (material_id, dispensed_container_id, the resulting real
    MaterialConsumption row)."""
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, code, lot_code
    )
    # _build_dispensed_container's own bare db.execute() left an implicit (autobegin) transaction open on
    # this session -- close it out before using an explicit `async with db.begin()` block below.
    await db.commit()
    resp = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "30.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    async with db.begin():
        consumption = (
            await db.execute(select(MaterialConsumption).where(MaterialConsumption.dispensed_container_id == uuid.UUID(dc_id)))
        ).scalar_one()
    return material_id, dc_id, consumption


async def _fetch_matching_message(sub, consumption_id: uuid.UUID, *, timeout: float = 5, max_tries: int = 20):
    """`erp_consumer.SUBJECT` is a fixed, real production subject (not a per-test-unique one like
    `test_eventbus_consumer.py` uses) -- a durable consumer created here replays every `MaterialConsumed`
    event still retained on the shared, long-lived `GXP_EVENTS` stream, including ones this session's own
    earlier test runs published. Acks away anything that isn't this test's own event (harmless leftover
    test traffic, not a real message this consumer should ever act on) until the expected one arrives."""
    import json

    for _ in range(max_tries):
        msgs = await sub.fetch(1, timeout=timeout)
        msg = msgs[0]
        envelope = json.loads(msg.data)
        if envelope["aggregate_id"] == str(consumption_id):
            return msg
        await msg.ack()
    raise AssertionError(f"expected event for consumption {consumption_id} not seen within {max_tries} messages")


async def _publish_real_consumption_event(consumption_id: uuid.UUID) -> None:
    async with SessionLocal() as s:
        event = (
            await s.execute(
                select(OutboxEvent).where(OutboxEvent.event_type == "MaterialConsumed", OutboxEvent.aggregate_id == consumption_id)
            )
        ).scalar_one()
        await publish_outbox_event(event)


async def test_mapped_erpnext_consumption_is_queued_end_to_end(client, db, seeded):
    material_id, _dc_id, consumption = await _record_real_consumption(client, db, seeded, "MAT-ERPC1", "LOT-ERPC1")

    async with db.begin():
        db.add(
            ErpExternalMapping(
                erp_instance_id=seeded["erp_instance"].id, entity_type="MATERIAL", internal_id=uuid.UUID(material_id),
                external_id="ITEM-ERPC1", external_code="ITEM-ERPC1", field_ownership="ERP",
                mapping_status="ACTIVE", match_method="MANUAL", version=1,
            )
        )

    await _publish_real_consumption_event(consumption.id)

    durable = f"test-erp-consumer-{uuid.uuid4().hex[:10]}"
    sub = await jetstream.pull_subscribe(erp_consumer.SUBJECT, durable_name=durable)
    msg = await _fetch_matching_message(sub, consumption.id)
    await eventbus_consumer._process_one_message(
        msg, consumer_name=erp_consumer.CONSUMER_NAME, handler=erp_consumer.handle_material_consumed_event, max_deliver=6,
    )

    async with SessionLocal() as s:
        command = (
            await s.execute(
                select(IntegrationCommand).where(
                    IntegrationCommand.source_aggregate_type == "material_consumption",
                    IntegrationCommand.source_aggregate_id == consumption.id,
                )
            )
        ).scalar_one()
        assert command.command_type == "POST_CONSUMPTION"
        assert command.erp_instance_id == seeded["erp_instance"].id
        reloaded_consumption = await s.get(MaterialConsumption, consumption.id)
        assert command.payload == {
            "items": [{"item_code": "ITEM-ERPC1", "qty": str(reloaded_consumption.quantity), "uom": reloaded_consumption.uom}]
        }
        assert command.state == "PENDING"

        inbox = (
            await s.execute(
                select(ConsumerInbox).where(ConsumerInbox.consumer_name == erp_consumer.CONSUMER_NAME)
            )
        ).scalars().all()
        assert any(row.result == "PROCESSED" for row in inbox)

    # acked -- nothing left to redeliver
    with pytest.raises(TimeoutError):
        await sub.fetch(1, timeout=2)


async def test_site_with_no_active_erpnext_instance_is_skipped_not_dead_lettered(client, db, seeded):
    _material_id, _dc_id, consumption = await _record_real_consumption(client, db, seeded, "MAT-ERPC2", "LOT-ERPC2")

    async with db.begin():
        instance = await db.get(ErpInstance, seeded["erp_instance"].id)
        instance.status = "INACTIVE"

    await _publish_real_consumption_event(consumption.id)

    durable = f"test-erp-consumer-{uuid.uuid4().hex[:10]}"
    sub = await jetstream.pull_subscribe(erp_consumer.SUBJECT, durable_name=durable)
    msg = await _fetch_matching_message(sub, consumption.id)
    await eventbus_consumer._process_one_message(
        msg, consumer_name=erp_consumer.CONSUMER_NAME, handler=erp_consumer.handle_material_consumed_event, max_deliver=6,
    )

    async with SessionLocal() as s:
        commands = (
            await s.execute(
                select(IntegrationCommand).where(
                    IntegrationCommand.source_aggregate_type == "material_consumption",
                    IntegrationCommand.source_aggregate_id == consumption.id,
                )
            )
        ).scalars().all()
        assert commands == []  # nothing queued -- correctly skipped, not an error

        inbox = (
            await s.execute(
                select(ConsumerInbox).where(ConsumerInbox.consumer_name == erp_consumer.CONSUMER_NAME)
            )
        ).scalars().all()
        assert any(row.result == "PROCESSED" for row in inbox)  # acked as a successful no-op, not dead-lettered

    async with db.begin():
        instance = await db.get(ErpInstance, seeded["erp_instance"].id)
        instance.status = "ACTIVE"


async def test_unmapped_material_naks_then_dead_letters(client, db, seeded):
    """No ErpExternalMapping exists for this material -- a real, actionable gap that must surface through
    the dead-letter mechanism, not be silently dropped (confirmed design choice, distinct from the "no
    ERP instance configured" case above)."""
    _material_id, _dc_id, consumption = await _record_real_consumption(client, db, seeded, "MAT-ERPC3", "LOT-ERPC3")
    await _publish_real_consumption_event(consumption.id)

    durable = f"test-erp-consumer-{uuid.uuid4().hex[:10]}"
    max_deliver = 2
    sub = await jetstream.pull_subscribe(erp_consumer.SUBJECT, durable_name=durable, max_deliver=max_deliver, ack_wait_seconds=5)
    for _ in range(max_deliver):
        msg = await _fetch_matching_message(sub, consumption.id)
        await eventbus_consumer._process_one_message(
            msg, consumer_name=durable, handler=erp_consumer.handle_material_consumed_event, max_deliver=max_deliver,
        )

    # dead-lettered -- confirm this specific message is never redelivered again (other, unrelated
    # leftover test traffic on this shared subject may still exist and is drained/ignored here).
    import json

    for _ in range(5):
        try:
            msgs = await sub.fetch(1, timeout=2)
        except TimeoutError:
            break
        envelope = json.loads(msgs[0].data)
        assert envelope["aggregate_id"] != str(consumption.id), "dead-lettered message must not be redelivered"
        await msgs[0].ack()

    async with SessionLocal() as s:
        inbox = (
            await s.execute(
                select(ConsumerInbox).where(ConsumerInbox.consumer_name == durable)
            )
        ).scalar_one()
        assert inbox.result == "DEAD_LETTERED"

        commands = (
            await s.execute(
                select(IntegrationCommand).where(
                    IntegrationCommand.source_aggregate_type == "material_consumption",
                    IntegrationCommand.source_aggregate_id == consumption.id,
                )
            )
        ).scalars().all()
        assert commands == []  # never queued -- the mapping gap blocked it, correctly