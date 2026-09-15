"""SNMP driver/plugin tests -- Document 44 DRV-FR-012 ("Support v3 preferred with scoped credentials,
OID mapping and polling/trap profile where appropriate").

Protocol-simulator-backed: a real local SNMPv3 agent (`pysnmp.entity`'s own `GetCommandResponder` command
responder, the same library used for the client side) is started on an ephemeral UDP port with a real USM
user (auth+priv), and `SnmpDriver`/`SnmpPlugin` perform real SNMPv3 GET requests against it -- real BER
encoding, real USM authentication and real AES privacy encryption cross a real UDP socket. Queries target
the agent's own default SNMPv2-MIB instrumentation (`sysDescr.0`, `sysUpTime.0`, `sysContact.0`) rather
than invented custom OIDs, since a real SNMP agent responds to those out of the box -- no fixture data is
fabricated.
"""

from __future__ import annotations

import socket
import threading

import pytest

from plugins.common.driver_contracts import AuthFailed, EndpointUnreachable, ReadOptions, SourceAddress, SourceMappingNotFound
from plugins.snmp.driver import SnmpDriver
from plugins.snmp.plugin import SnmpPlugin

AUTH_KEY = "authpassword123"
PRIV_KEY = "privpassword123"
USERNAME = "testuser"

SYS_DESCR_OID = "1.3.6.1.2.1.1.1.0"
SYS_UPTIME_OID = "1.3.6.1.2.1.1.3.0"
UNREACHABLE_OID = "1.3.6.1.2.1.99.99.0"  # not covered by the test agent's VACM view


def _free_udp_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _SnmpAgentThread:
    """Runs the real local SNMPv3 agent on its own persistent background asyncio event loop in its own
    thread -- exactly the same "always-on, independent of whatever loop the test/driver happens to use"
    role `tests/support/tcp_line_server.py`'s thread and the `mosquitto`/`socat` subprocesses play for the
    other protocol tests. This matters concretely here: `SnmpPlugin`'s sync `poll()` drives its own
    throwaway `asyncio.new_event_loop()` per Document 43's polling-plugin pattern, which is a *different*
    loop than an `async def` test function's. An agent set up via a plain async pytest fixture only
    services requests while pytest-asyncio's own loop is actively being awaited -- a synchronous
    `plugin.poll()` call goes silent from that loop's perspective and every request times out, which is
    exactly the failure this class was written after observing for real, not a hypothetical."""

    def __init__(self, port: int) -> None:
        self.port = port
        self._loop: "asyncio.AbstractEventLoop | None" = None
        self._engine = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            raise RuntimeError("SNMP agent thread did not start in time")

    def _run(self) -> None:
        import asyncio

        from pysnmp.carrier.asyncio.dgram import udp
        from pysnmp.entity import config, engine
        from pysnmp.entity.rfc3413 import cmdrsp, context

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._engine = engine.SnmpEngine()
        config.add_transport(self._engine, udp.DOMAIN_NAME, udp.UdpTransport().open_server_mode(("127.0.0.1", self.port)))
        config.add_v3_user(self._engine, USERNAME, config.USM_AUTH_HMAC96_SHA, AUTH_KEY, config.USM_PRIV_CFB128_AES, PRIV_KEY)
        # VACM view intentionally limited to the standard system subtree (1.3.6.1.2.1.1) -- proves both a
        # real "in view" read and a real "out of view" SourceMappingNotFound-style rejection.
        config.add_vacm_user(self._engine, 3, USERNAME, "authPriv", (1, 3, 6, 1, 2, 1, 1), (1, 3, 6, 1, 2, 1, 1))
        snmp_context = context.SnmpContext(self._engine)
        cmdrsp.GetCommandResponder(self._engine, snmp_context)

        self._ready.set()
        self._loop.run_forever()

    def stop(self) -> None:
        assert self._loop is not None
        self._loop.call_soon_threadsafe(self._engine.close_dispatcher)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=3)


@pytest.fixture
def snmp_agent():
    port = _free_udp_port()
    agent = _SnmpAgentThread(port)
    try:
        yield {"port": port}
    finally:
        agent.stop()


@pytest.fixture
def driver():
    return SnmpDriver(connector_id="snmp-test", connector_version="1.0.0", device_id="dev-snmp")


def _connect_config(port: int, **overrides) -> dict:
    config = {
        "host": "127.0.0.1", "port": port, "username": USERNAME,
        "auth_protocol": "SHA", "auth_key": AUTH_KEY, "priv_protocol": "AES128", "priv_key": PRIV_KEY,
        "connect_timeout_seconds": 3.0, "health_check_oid": SYS_DESCR_OID,
    }
    config.update(overrides)
    return config


async def test_connect_and_read_sys_descr(snmp_agent, driver):
    await driver.connect(_connect_config(snmp_agent["port"]))
    address = SourceAddress(address=SYS_DESCR_OID, protocol="SNMP", extra={"mapping_id": "SYS_DESCR"})
    observation = await driver.read_once(address)
    assert isinstance(observation.value, str) and len(observation.value) > 0
    assert observation.quality_hint == "GOOD"
    assert observation.source.protocol == "SNMP"
    await driver.disconnect("test complete")


async def test_read_sys_uptime_decodes_as_numeric(snmp_agent, driver):
    await driver.connect(_connect_config(snmp_agent["port"]))
    address = SourceAddress(address=SYS_UPTIME_OID, protocol="SNMP", extra={"mapping_id": "SYS_UPTIME", "unit": "ticks"})
    observation = await driver.read_once(address)
    assert isinstance(observation.value, int)
    assert observation.value >= 0
    assert observation.unit == "ticks"
    await driver.disconnect("test complete")


async def test_connect_with_unknown_username_raises_auth_failed(snmp_agent, driver):
    """The one USM failure that *is* distinguishable from a timeout without a shared secret: the
    engine-discovery/report exchange for a username the agent has never heard of. Confirmed for real
    against the local agent in this pass -- see `classify_snmp_error`'s docstring."""
    with pytest.raises(AuthFailed):
        await driver.connect(_connect_config(snmp_agent["port"], username="totally-unregistered-user"))


async def test_connect_with_wrong_priv_key_raises_endpoint_unreachable(snmp_agent, driver):
    """A *known* username with a wrong privacy key is -- by USM's own anti-enumeration design -- silently
    dropped by a compliant agent rather than answered with a distinguishing error, so it surfaces exactly
    like an unreachable/non-responding endpoint. Confirmed for real against the local agent in this pass,
    not assumed: this is not a limitation of this driver's error classification, it is what the wire
    protocol actually returns (nothing)."""
    with pytest.raises(EndpointUnreachable):
        await driver.connect(_connect_config(snmp_agent["port"], priv_key="wrong-priv-key-xxxxx", connect_timeout_seconds=1.0))


async def test_connect_to_unreachable_host_raises_endpoint_unreachable(driver):
    with pytest.raises(EndpointUnreachable):
        await driver.connect(_connect_config(_free_udp_port(), connect_timeout_seconds=1.0))


async def test_read_oid_outside_vacm_view_raises_source_mapping_not_found(snmp_agent, driver):
    await driver.connect(_connect_config(snmp_agent["port"]))
    address = SourceAddress(address=UNREACHABLE_OID, protocol="SNMP", extra={"mapping_id": "OUT_OF_VIEW"})
    with pytest.raises(SourceMappingNotFound):
        await driver.read_once(address)
    await driver.disconnect("test complete")


async def test_health_check(snmp_agent, driver):
    await driver.connect(_connect_config(snmp_agent["port"]))
    health = await driver.health_check()
    assert health.connected is True
    await driver.disconnect("test complete")
    health_after = await driver.health_check()
    assert health_after.connected is False


def test_plugin_poll_returns_decoded_observation(snmp_agent):
    plugin = SnmpPlugin({
        "connector_id": "snmp-plugin-test", "connector_version": "1.0.0", "device_id": "dev-snmp-plugin",
        "host": "127.0.0.1", "port": snmp_agent["port"], "username": USERNAME,
        "auth_protocol": "SHA", "auth_key": AUTH_KEY, "priv_protocol": "AES128", "priv_key": PRIV_KEY,
        "mappings": [{"oid": SYS_DESCR_OID, "mapping_id": "SYS_DESCR"}],
        "poll_interval_seconds": 1.0,
    })
    try:
        observations = list(plugin.poll())
        assert len(observations) == 1
        assert observations[0].quality_hint == "GOOD"
        assert observations[0].mapping_id == "SYS_DESCR"
    finally:
        plugin._loop.run_until_complete(plugin._driver.disconnect("test teardown"))
