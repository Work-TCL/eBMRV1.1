"""REST-polling driver/plugin tests -- Document 44 DRV-FR-014 ("Support authenticated REST polling...").

Protocol-simulator-backed: a real local `http.server.ThreadingHTTPServer` (stdlib, no new dependency)
stands in for an instrument's REST API, and `RestPollingDriver`/`RestPlugin` connect a real `httpx.
AsyncClient` to it -- real HTTP request/response bytes cross a real localhost socket.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from plugins.common.driver_contracts import AuthFailed, EndpointUnreachable, PayloadSchemaInvalid, ProtocolException, ReadOptions, ReadTimeout, SourceAddress
from plugins.rest.driver import RestPollingDriver
from plugins.rest.plugin import RestPlugin

VALID_TOKEN = "secret-instrument-token"


class _InstrumentHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 -- silence test server logging
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 -- stdlib method name
        if self.path == "/api/v1/reading":
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {VALID_TOKEN}":
                self._send_json(401, {"error": "unauthorized"})
                return
            self._send_json(200, {"data": {"value": 42.5, "unit": "bar"}})
        elif self.path == "/api/v1/malformed":
            body = b"not json"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/v1/missing-field":
            self._send_json(200, {"data": {"other_field": 1}})
        elif self.path == "/api/v1/server-error":
            self._send_json(500, {"error": "internal"})
        elif self.path == "/api/v1/hang":
            import time

            time.sleep(5)
            self._send_json(200, {"data": {"value": 1}})
        else:
            self._send_json(404, {"error": "not found"})


@pytest.fixture
def instrument_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _InstrumentHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {"base_url": f"http://127.0.0.1:{server.server_port}"}
    finally:
        server.shutdown()
        thread.join(timeout=2)


@pytest.fixture
def driver():
    return RestPollingDriver(connector_id="rest-test", connector_version="1.0.0", device_id="dev-rest")


async def test_connect_and_read_valid_reading(instrument_server, driver):
    await driver.connect({
        "base_url": instrument_server["base_url"], "path": "/api/v1/reading",
        "auth": {"type": "bearer", "token": VALID_TOKEN}, "connect_timeout_seconds": 3.0,
    })
    address = SourceAddress(address="/api/v1/reading", protocol="REST", extra={"value_field": "data.value", "unit_field": "data.unit", "mapping_id": "TANK_LEVEL"})
    observation = await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert observation.value == 42.5
    assert observation.unit == "bar"
    assert observation.quality_hint == "GOOD"
    assert observation.source.protocol == "REST"
    await driver.disconnect("test complete")


async def test_connect_with_wrong_token_raises_auth_failed(instrument_server, driver):
    with pytest.raises(AuthFailed):
        await driver.connect({
            "base_url": instrument_server["base_url"], "path": "/api/v1/reading",
            "auth": {"type": "bearer", "token": "wrong-token"}, "connect_timeout_seconds": 3.0,
        })


async def test_connect_to_unreachable_host_raises_endpoint_unreachable(driver):
    with pytest.raises(EndpointUnreachable):
        await driver.connect({"base_url": "http://127.0.0.1:1", "path": "/x", "connect_timeout_seconds": 1.0})


async def test_read_malformed_json_raises_payload_schema_invalid(instrument_server, driver):
    await driver.connect({"base_url": instrument_server["base_url"], "auth": {"type": "bearer", "token": VALID_TOKEN}, "connect_timeout_seconds": 3.0})
    address = SourceAddress(address="/api/v1/malformed", protocol="REST", extra={"value_field": "data.value"})
    with pytest.raises(PayloadSchemaInvalid):
        await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    await driver.disconnect("test complete")


async def test_read_missing_field_raises_payload_schema_invalid(instrument_server, driver):
    await driver.connect({"base_url": instrument_server["base_url"], "auth": {"type": "bearer", "token": VALID_TOKEN}, "connect_timeout_seconds": 3.0})
    address = SourceAddress(address="/api/v1/missing-field", protocol="REST", extra={"value_field": "data.value"})
    with pytest.raises(PayloadSchemaInvalid):
        await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    await driver.disconnect("test complete")


async def test_read_server_error_raises_protocol_exception(instrument_server, driver):
    await driver.connect({"base_url": instrument_server["base_url"], "auth": {"type": "bearer", "token": VALID_TOKEN}, "connect_timeout_seconds": 3.0})
    address = SourceAddress(address="/api/v1/server-error", protocol="REST", extra={"value_field": "data.value"})
    with pytest.raises((ProtocolException, EndpointUnreachable)):
        await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    await driver.disconnect("test complete")


async def test_read_timeout(instrument_server, driver):
    await driver.connect({"base_url": instrument_server["base_url"], "auth": {"type": "bearer", "token": VALID_TOKEN}, "connect_timeout_seconds": 3.0})
    address = SourceAddress(address="/api/v1/hang", protocol="REST", extra={"value_field": "data.value"})
    with pytest.raises(ReadTimeout):
        await driver.read_once(address, ReadOptions(timeout_seconds=0.5))
    await driver.disconnect("test complete")


async def test_health_check(instrument_server, driver):
    await driver.connect({"base_url": instrument_server["base_url"], "auth": {"type": "bearer", "token": VALID_TOKEN}, "connect_timeout_seconds": 3.0})
    health = await driver.health_check()
    assert health.connected is True
    await driver.disconnect("test complete")
    health_after = await driver.health_check()
    assert health_after.connected is False


def test_plugin_poll_returns_decoded_observation(instrument_server):
    plugin = RestPlugin({
        "connector_id": "rest-plugin-test", "connector_version": "1.0.0", "device_id": "dev-rest-plugin",
        "base_url": instrument_server["base_url"], "path": "/api/v1/reading",
        "value_field": "data.value", "unit_field": "data.unit", "mapping_id": "TANK_LEVEL",
        "auth": {"type": "bearer", "token": VALID_TOKEN}, "poll_interval_seconds": 1.0,
    })
    try:
        observations = list(plugin.poll())
        assert len(observations) == 1
        assert observations[0].value == 42.5
        assert observations[0].mapping_id == "TANK_LEVEL"
    finally:
        plugin._loop.run_until_complete(plugin._driver.disconnect("test teardown"))
