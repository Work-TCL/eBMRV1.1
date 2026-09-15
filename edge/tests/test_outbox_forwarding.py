import uuid

import httpx
import pytest

from runtime.contracts import ClockQuality, EdgeObservationEnvelope, RawValue, SourceRef
from runtime.forwarding.forwarder import UpstreamUnavailableError, disk_pressure_status, forward_pending_batch
from runtime.forwarding.outbox import append_delivery_envelope, next_gateway_sequence, oldest_unacked_age_seconds, pending_depth

GATEWAY_ID = uuid.uuid4()
SITE_ID = uuid.uuid4()


def _envelope(seq: int) -> EdgeObservationEnvelope:
    return EdgeObservationEnvelope(
        gateway_id=GATEWAY_ID, tenant_id="t1", site_id=SITE_ID, connector_id="c1", connector_version="1.0",
        device_id="d1", mapping_id="m1", mapping_version="m1", source=SourceRef(protocol="MQTT", address="a/b"),
        gateway_received_at="2026-09-14T00:00:00Z", gateway_sequence=seq,
        clock_quality=ClockQuality(status="GOOD"), quality="GOOD", raw=RawValue(value=seq),
    )


def test_append_delivery_envelope_is_idempotent_on_duplicate_event_id(conn):
    envelope = _envelope(1)
    ref1 = append_delivery_envelope(conn, envelope)
    ref2 = append_delivery_envelope(conn, envelope)  # exact same event_id resubmitted
    assert ref1.event_id == ref2.event_id

    count = conn.execute("SELECT COUNT(*) AS n FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()["n"]
    assert count == 1


def test_pending_depth_and_sequence_tracking(conn):
    for i in range(1, 4):
        append_delivery_envelope(conn, _envelope(i))
    assert pending_depth(conn) == 3
    assert next_gateway_sequence(conn) == 4
    assert oldest_unacked_age_seconds(conn) is not None


@pytest.mark.asyncio
async def test_forward_pending_batch_acks_exactly_the_returned_event_ids(conn):
    e1, e2 = _envelope(1), _envelope(2)
    append_delivery_envelope(conn, e1)
    append_delivery_envelope(conn, e2)

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        import json

        payload = json.loads(body)
        sent_ids = [o["event_id"] for o in payload["observations"]]
        # server acknowledges only the first of the two -- EDGE-FR-015 exact-range ack
        return httpx.Response(200, json={"accepted_event_ids": [sent_ids[0]], "duplicate_event_ids": [], "rejected": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://server")
    result = await forward_pending_batch(conn, client, gateway_id=str(GATEWAY_ID), expected_version=1, idempotency_key="k1")

    assert len(result.server_ack_event_ids) == 1
    acked = conn.execute("SELECT event_id FROM edge_outbox WHERE state = 'acked'").fetchall()
    assert len(acked) == 1
    assert pending_depth(conn) == 1  # the un-acked one is still pending, not purged


@pytest.mark.asyncio
async def test_forward_pending_batch_leaves_rows_untouched_on_upstream_failure(conn):
    append_delivery_envelope(conn, _envelope(1))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://server")

    with pytest.raises(UpstreamUnavailableError):
        await forward_pending_batch(conn, client, gateway_id=str(GATEWAY_ID), expected_version=1, idempotency_key="k1")

    # local continuity (EDGE-FR-024): the row is neither lost nor marked sent/acked
    row = conn.execute("SELECT state FROM edge_outbox").fetchone()
    assert row["state"] == "pending"


@pytest.mark.asyncio
async def test_forward_pending_batch_noop_when_outbox_empty(conn):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})), base_url="http://server")
    result = await forward_pending_batch(conn, client, gateway_id=str(GATEWAY_ID), expected_version=1, idempotency_key="k1")
    assert result.sent_event_ids == []


def test_disk_pressure_status_thresholds(tmp_path, monkeypatch):
    import shutil

    Usage = type(shutil.disk_usage(tmp_path))

    monkeypatch.setattr(shutil, "disk_usage", lambda p: Usage(total=10**12, used=0, free=10**12))
    assert disk_pressure_status(tmp_path / "edge.db") == "GOOD"

    monkeypatch.setattr(shutil, "disk_usage", lambda p: Usage(total=10**12, used=0, free=200 * 1024 * 1024))
    assert disk_pressure_status(tmp_path / "edge.db") == "WARNING"

    monkeypatch.setattr(shutil, "disk_usage", lambda p: Usage(total=10**12, used=0, free=50 * 1024 * 1024))
    assert disk_pressure_status(tmp_path / "edge.db") == "CRITICAL"