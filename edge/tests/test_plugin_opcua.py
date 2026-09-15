"""OPC UA driver tests -- Document 44 DRV-FR-002..006, section 12's mandatory contract tests.

Protocol-simulator-backed: every test that exercises the network path runs a real `asyncua.Server`
in-process on localhost (not a mock) and a real `asyncua.Client` inside `OpcUaDriver` -- this is the
actual OPC UA 1.05.x wire protocol (hello/OpenSecureChannel/CreateSession/Read/CreateSubscription),
the same reference stack Document 44's "Current Protocol Baseline" names. The certificate-trust-store
guard test (`test_security_mode_none_refused_without_allow_insecure`,
`test_secure_mode_without_trust_store_raises_cert_untrusted`) is a pure config-validation unit test
and never opens a socket -- driver code refuses before any connection attempt, so no server is needed.
"""

from __future__ import annotations

import asyncio

import pytest
from asyncua import Server, ua

from plugins.common.driver_contracts import (
    BrowseDenied,
    BrowseRequest,
    CertUntrusted,
    EndpointUnreachable,
    ReadOptions,
    SourceAddress,
    SubscriptionOptions,
)
from plugins.opcua.driver import OpcUaDriver, map_status_code


@pytest.fixture
async def opcua_server():
    port = 48400
    server = Server()
    await server.init()
    server.set_endpoint(f"opc.tcp://127.0.0.1:{port}/freeopcua/server/")
    idx = await server.register_namespace("http://ebmr.test/edge-driver-tests")
    objects = server.get_objects_node()
    pressure = await objects.add_variable(
        ua.NodeId("Line1.Filler.Pressure", idx, ua.NodeIdType.String), "Pressure", 1.0
    )
    await pressure.set_writable()
    await server.start()
    try:
        yield {"url": f"opc.tcp://127.0.0.1:{port}/freeopcua/server/", "idx": idx, "pressure": pressure}
    finally:
        await server.stop()


@pytest.fixture
def driver():
    return OpcUaDriver(connector_id="opcua-test", connector_version="1.0.0", device_id="dev-opcua")


async def test_connect_and_read_once_returns_good_quality(opcua_server, driver):
    result = await driver.connect({
        "endpoint_url": opcua_server["url"], "security_mode": "None", "allow_insecure": True,
    })
    assert result.capabilities["read"] is True

    address = SourceAddress(address="ns=%d;s=Line1.Filler.Pressure" % opcua_server["idx"], protocol="OPCUA")
    observation = await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert observation.value == 1.0
    assert observation.quality_hint == "GOOD"
    await driver.disconnect("test complete")


async def test_value_change_is_observed_on_next_read(opcua_server, driver):
    await driver.connect({"endpoint_url": opcua_server["url"], "security_mode": "None", "allow_insecure": True})
    address = SourceAddress(address="ns=%d;s=Line1.Filler.Pressure" % opcua_server["idx"], protocol="OPCUA")

    await opcua_server["pressure"].write_value(2.75)
    observation = await driver.read_once(address)
    assert observation.value == 2.75
    await driver.disconnect("test complete")


async def test_read_timeout_on_bad_node_id(opcua_server, driver):
    await driver.connect({"endpoint_url": opcua_server["url"], "security_mode": "None", "allow_insecure": True})
    bad_address = SourceAddress(address="ns=99;s=DoesNotExist", protocol="OPCUA")
    from plugins.common.driver_contracts import ProtocolException

    with pytest.raises(ProtocolException):
        await driver.read_once(bad_address, ReadOptions(timeout_seconds=2.0))
    await driver.disconnect("test complete")


async def test_endpoint_unreachable_raised_for_dead_port(driver):
    with pytest.raises(EndpointUnreachable):
        await driver.connect({
            "endpoint_url": "opc.tcp://127.0.0.1:1/nowhere", "security_mode": "None",
            "allow_insecure": True, "connect_timeout_seconds": 1.0,
        })


async def test_security_mode_none_refused_without_allow_insecure(driver):
    """Security section 10 / Prohibitions section 14: "no accept all certs in production" -- the
    conservative reading applied here is that an explicitly insecure channel also needs an explicit
    opt-in, not a silent default. No socket is opened; the driver refuses before connecting."""

    with pytest.raises(CertUntrusted):
        await driver.connect({"endpoint_url": "opc.tcp://127.0.0.1:1/nowhere", "security_mode": "None"})


async def test_secure_mode_without_trust_store_raises_cert_untrusted(driver):
    with pytest.raises(CertUntrusted):
        await driver.connect({
            "endpoint_url": "opc.tcp://127.0.0.1:1/nowhere", "security_mode": "SignAndEncrypt",
            "security_policy": "Basic256Sha256",
        })


async def test_browse_denied_without_engineering_mode(opcua_server, driver):
    await driver.connect({"endpoint_url": opcua_server["url"], "security_mode": "None", "allow_insecure": True})
    with pytest.raises(BrowseDenied):
        await driver.browse(BrowseRequest(root="", engineering_mode_authorized=False))
    await driver.disconnect("test complete")


async def test_browse_with_engineering_mode_returns_nodes(opcua_server, driver):
    await driver.connect({"endpoint_url": opcua_server["url"], "security_mode": "None", "allow_insecure": True})
    result = await driver.browse(BrowseRequest(root="", engineering_mode_authorized=True))
    names = {n["browse_name"] for n in result.nodes}
    assert "Pressure" in names
    await driver.disconnect("test complete")


async def test_subscribe_delivers_datachange_observation(opcua_server, driver):
    await driver.connect({"endpoint_url": opcua_server["url"], "security_mode": "None", "allow_insecure": True})
    address = SourceAddress(address="ns=%d;s=Line1.Filler.Pressure" % opcua_server["idx"], protocol="OPCUA")

    received = []

    async def on_observation(obs):
        received.append(obs)

    handle = await driver.subscribe([address], SubscriptionOptions(publishing_interval_ms=100), on_observation)
    await opcua_server["pressure"].write_value(9.5)

    for _ in range(50):
        if received:
            break
        await asyncio.sleep(0.1)

    assert received, "expected at least one subscription data-change observation"
    assert any(o.value == 9.5 for o in received)
    await driver.unsubscribe(handle.subscription_id)
    await driver.disconnect("test complete")


async def test_health_check_reports_connected(opcua_server, driver):
    await driver.connect({"endpoint_url": opcua_server["url"], "security_mode": "None", "allow_insecure": True})
    health = await driver.health_check()
    assert health.connected is True
    await driver.disconnect("test complete")
    health_after = await driver.health_check()
    assert health_after.connected is False


async def test_write_is_disabled_by_default(opcua_server, driver):
    """DRV-FR-017: driver advertises write capability separately, and the runtime blocks write unless
    an explicit command profile authorizes it -- this reference build never implements the bypass."""
    from plugins.common.driver_contracts import DriverWriteRequest, WriteDisabled

    await driver.connect({"endpoint_url": opcua_server["url"], "security_mode": "None", "allow_insecure": True})
    address = SourceAddress(address="ns=%d;s=Line1.Filler.Pressure" % opcua_server["idx"], protocol="OPCUA")
    with pytest.raises(WriteDisabled):
        await driver.write(DriverWriteRequest(address=address, value=5.0))
    await driver.disconnect("test complete")


@pytest.mark.parametrize(
    "status_code,expected",
    [
        (ua.StatusCodes.Good, "GOOD"),
        (ua.StatusCodes.UncertainLastUsableValue, "UNCERTAIN"),
        (ua.StatusCodes.BadCommunicationError, "BAD"),
        (ua.StatusCodes.BadNodeIdUnknown, "BAD"),
    ],
)
def test_map_status_code_quality_mapping(status_code, expected):
    """DRV-FR-006 mapping-conversion unit test (section 12's mandatory "mapping conversion" case) --
    deterministic, no server needed."""
    assert map_status_code(ua.StatusCode(status_code)) == expected