"""MQTT driver/plugin tests -- Document 44 DRV-FR-010 (MQTT 5: broker TLS/auth, topic filters, QoS,
retained flag, payload schema/version, client session) and DRV-FR-011 (payload validated only through a
versioned decoder).

Protocol-simulator-backed: a real local `mosquitto` broker subprocess (already an OS package in this
environment -- Document 104 does not need to justify it because it is test-only tooling, never imported
or shelled out to by `edge/plugins/mqtt/`) is started with `allow_anonymous true` on an ephemeral port,
and `MqttDriver`/`MqttPlugin` connect a real `aiomqtt.Client` to it. A second `aiomqtt.Client` in the test
acts as the publisher, exactly like a real instrument/PLC MQTT publisher would.
"""

from __future__ import annotations

import asyncio
import shutil
import socket
import subprocess
import time
from pathlib import Path

import aiomqtt
import pytest

from plugins.common.driver_contracts import EndpointUnreachable, PayloadSchemaInvalid, ReadOptions, ReadTimeout, SourceAddress
from plugins.mqtt.driver import MqttDriver
from plugins.mqtt.plugin import MqttPlugin

MOSQUITTO_AVAILABLE = shutil.which("mosquitto") is not None
pytestmark = pytest.mark.skipif(not MOSQUITTO_AVAILABLE, reason="mosquitto not installed -- see module docstring")


def _free_tcp_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def mosquitto_broker(tmp_path: Path):
    port = _free_tcp_port()
    conf_path = tmp_path / "mosquitto.conf"
    conf_path.write_text(f"listener {port} 127.0.0.1\nallow_anonymous true\n")
    proc = subprocess.Popen(
        ["mosquitto", "-c", str(conf_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 5.0
    connected = False
    while time.monotonic() < deadline:
        try:
            probe = socket.create_connection(("127.0.0.1", port), timeout=0.2)
            probe.close()
            connected = True
            break
        except OSError:
            time.sleep(0.1)
    if not connected:
        proc.terminate()
        pytest.fail("local mosquitto broker did not start listening in time")
    try:
        yield {"port": port, "broker_url": f"mqtt://127.0.0.1:{port}"}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


async def _publish(broker_url: str, topic: str, payload: bytes, *, qos: int = 0, retain: bool = False) -> None:
    from urllib.parse import urlsplit

    parsed = urlsplit(broker_url)
    async with aiomqtt.Client(hostname=parsed.hostname, port=parsed.port) as client:
        await client.publish(topic, payload=payload, qos=qos, retain=retain)


@pytest.fixture
def driver():
    return MqttDriver(connector_id="mqtt-test", connector_version="1.0.0", device_id="dev-mqtt")


async def test_connect_and_receive_decoded_message(mosquitto_broker, driver):
    await driver.connect({
        "broker": mosquitto_broker["broker_url"], "client_id": "edge-test-subscriber",
        "topic": "plant/line1/filler/telemetry", "qos": 1, "connect_timeout_seconds": 3.0,
    })

    # Publish concurrently with the read -- the subscription (driver.connect()) is already established
    # above, so the message is queued for us as soon as it is published.
    publish_task = asyncio.create_task(_publish(
        mosquitto_broker["broker_url"], "plant/line1/filler/telemetry",
        b'{"schema_version":"2.1","value":123.5,"unit":"bar","parameter_code":"FILL_PRESSURE"}', qos=1,
    ))

    address = SourceAddress(
        address="plant/line1/filler/telemetry", protocol="MQTT",
        extra={"decoder": "generic-json-v1", "schema_version": "2.1", "mapping_id": "FILL_PRESSURE", "unit": "bar"},
    )
    observation = await driver.read_once(address, ReadOptions(timeout_seconds=5.0))
    await publish_task

    assert observation.value == 123.5
    assert observation.unit == "bar"
    assert observation.quality_hint == "GOOD"
    assert observation.source.protocol == "MQTT"
    assert observation.mapping_id == "FILL_PRESSURE"
    await driver.disconnect("test complete")


async def test_retained_message_is_marked_stale_not_good(mosquitto_broker, driver):
    """Section 7: "a retained historical value cannot silently masquerade as a new live observation."""
    await _publish(
        mosquitto_broker["broker_url"], "plant/line1/filler/retained",
        b'{"schema_version":"2.1","value":99.0}', qos=1, retain=True,
    )
    await driver.connect({
        "broker": mosquitto_broker["broker_url"], "client_id": "edge-test-retained",
        "topic": "plant/line1/filler/retained", "qos": 1, "connect_timeout_seconds": 3.0,
    })
    address = SourceAddress(
        address="plant/line1/filler/retained", protocol="MQTT",
        extra={"decoder": "generic-json-v1", "schema_version": "2.1", "mapping_id": "RETAINED_PARAM"},
    )
    # The broker delivers the retained message immediately on subscribe.
    observation = await driver.read_once(address, ReadOptions(timeout_seconds=5.0))
    assert observation.value == 99.0
    assert observation.quality_hint == "STALE"
    await driver.disconnect("test complete")


async def test_schema_version_mismatch_raises_payload_schema_invalid(mosquitto_broker, driver):
    await driver.connect({
        "broker": mosquitto_broker["broker_url"], "client_id": "edge-test-badschema",
        "topic": "plant/line1/badschema", "qos": 0, "connect_timeout_seconds": 3.0,
    })
    publish_task = asyncio.create_task(_publish(
        mosquitto_broker["broker_url"], "plant/line1/badschema", b'{"schema_version":"1.0","value":1}',
    ))
    address = SourceAddress(
        address="plant/line1/badschema", protocol="MQTT",
        extra={"decoder": "generic-json-v1", "schema_version": "2.1", "mapping_id": "X"},
    )
    with pytest.raises(PayloadSchemaInvalid):
        await driver.read_once(address, ReadOptions(timeout_seconds=5.0))
    await publish_task
    await driver.disconnect("test complete")


async def test_malformed_json_raises_payload_schema_invalid(mosquitto_broker, driver):
    await driver.connect({
        "broker": mosquitto_broker["broker_url"], "client_id": "edge-test-malformed",
        "topic": "plant/line1/malformed", "qos": 0, "connect_timeout_seconds": 3.0,
    })
    publish_task = asyncio.create_task(_publish(mosquitto_broker["broker_url"], "plant/line1/malformed", b"not json at all"))
    address = SourceAddress(
        address="plant/line1/malformed", protocol="MQTT",
        extra={"decoder": "generic-json-v1", "schema_version": "2.1", "mapping_id": "X"},
    )
    with pytest.raises(PayloadSchemaInvalid):
        await driver.read_once(address, ReadOptions(timeout_seconds=5.0))
    await publish_task
    await driver.disconnect("test complete")


async def test_unknown_decoder_raises_payload_schema_invalid(mosquitto_broker, driver):
    await driver.connect({
        "broker": mosquitto_broker["broker_url"], "client_id": "edge-test-unknown-decoder",
        "topic": "plant/line1/unknown", "qos": 0, "connect_timeout_seconds": 3.0,
    })
    publish_task = asyncio.create_task(_publish(mosquitto_broker["broker_url"], "plant/line1/unknown", b'{"value":1}'))
    address = SourceAddress(
        address="plant/line1/unknown", protocol="MQTT",
        extra={"decoder": "not-a-registered-decoder", "schema_version": "2.1", "mapping_id": "X"},
    )
    with pytest.raises(PayloadSchemaInvalid):
        await driver.read_once(address, ReadOptions(timeout_seconds=5.0))
    await publish_task
    await driver.disconnect("test complete")


async def test_read_timeout_on_quiet_topic(mosquitto_broker, driver):
    await driver.connect({
        "broker": mosquitto_broker["broker_url"], "client_id": "edge-test-quiet",
        "topic": "plant/line1/nobody-publishes-here", "qos": 0, "connect_timeout_seconds": 3.0,
    })
    address = SourceAddress(
        address="plant/line1/nobody-publishes-here", protocol="MQTT",
        extra={"decoder": "generic-json-v1", "schema_version": "2.1", "mapping_id": "X"},
    )
    with pytest.raises(ReadTimeout):
        await driver.read_once(address, ReadOptions(timeout_seconds=0.5))
    await driver.disconnect("test complete")


async def test_connect_to_unreachable_broker_raises_endpoint_unreachable(driver):
    with pytest.raises(EndpointUnreachable):
        await driver.connect({"broker": "mqtt://127.0.0.1:1", "connect_timeout_seconds": 1.0})


async def test_health_check(mosquitto_broker, driver):
    await driver.connect({
        "broker": mosquitto_broker["broker_url"], "client_id": "edge-test-health",
        "topic": "plant/line1/health", "qos": 0, "connect_timeout_seconds": 3.0,
    })
    health = await driver.health_check()
    assert health.connected is True
    assert health.diagnostics["subscribed_topic"] == "plant/line1/health"
    await driver.disconnect("test complete")
    health_after = await driver.health_check()
    assert health_after.connected is False


def test_plugin_poll_returns_decoded_observation(mosquitto_broker):
    """End-to-end through `MqttPlugin.poll()` (the actual supervisor-facing `ConnectorPlugin` contract),
    not just the driver -- exercises the plugin's own connect/backoff/drain loop for real."""

    plugin = MqttPlugin({
        "connector_id": "mqtt-plugin-test", "connector_version": "1.0.0", "device_id": "dev-mqtt-plugin",
        "broker": mosquitto_broker["broker_url"], "client_id": "edge-plugin-test",
        "topic": "plant/line1/plugin-topic", "qos": 1, "decoder": "generic-json-v1", "schema_version": "2.1",
        "mapping_id": "PLUGIN_PARAM", "unit": "kg", "poll_interval_seconds": 1.5,
    })
    try:
        # First poll() connects and subscribes; publish happens after so the message is fresh, not retained.
        first = list(plugin.poll())
        assert first == []

        async def publish_after_delay():
            await asyncio.sleep(0.2)
            await _publish(
                mosquitto_broker["broker_url"], "plant/line1/plugin-topic",
                b'{"schema_version":"2.1","value":42.0,"unit":"kg"}', qos=1,
            )

        plugin._loop.run_until_complete(publish_after_delay())
        second = list(plugin.poll())
        assert len(second) == 1
        assert second[0].value == 42.0
        assert second[0].quality_hint == "GOOD"
    finally:
        plugin._loop.run_until_complete(plugin._driver.disconnect("test teardown"))
