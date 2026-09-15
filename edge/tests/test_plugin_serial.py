"""Generic serial/TCP proprietary adapter tests -- Document 44 DRV-FR-013 ("Custom proprietary protocol
lives in isolated adapter with framing/checksum/test vectors") and section 12's mandatory
"duplicate/replayed source event where detectable" test.

`test_known_test_vector` and `test_encode_decode_roundtrip` are the pure codec unit tests (framing/
checksum test vectors, mirroring `test_plugin_modbus_tcp.py::test_decode_registers_matches_test_vectors`'s
role for Modbus). The TCP-transport tests run against a real local TCP server
(`edge/tests/support/tcp_line_server.py`); the serial-transport test runs against a real `socat`-created
virtual serial pty pair, exactly like `test_plugin_modbus_rtu.py`.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from plugins.common.driver_contracts import CrcError, EndpointUnreachable, ProtocolException, ReadOptions, ReadTimeout, SourceAddress
from plugins.serial.driver import GenericSerialDriver
from plugins.serial.framing import decode_frame, encode_frame
from plugins.serial.plugin import GenericSerialPlugin
from tests.support.tcp_line_server import TCPLineServer

SOCAT_AVAILABLE = shutil.which("socat") is not None


# --------------------------------------------------------------------------------------------------
# Pure codec test vectors
# --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sequence,payload",
    [(0, b"TEMP=23.5"), (1, b""), (0xFFFF, b"A"), (0x1234, b"STATUS=OK;LEVEL=87.2")],
)
def test_encode_decode_roundtrip(sequence, payload):
    frame = encode_frame(sequence, payload)
    decoded = decode_frame(frame)
    assert decoded.sequence == sequence
    assert decoded.payload == payload


def test_known_test_vector():
    """A hand-computed test vector: sequence=0x0001, payload=b"OK" -> body=b"0001OK",
    XOR of bytes '0'(0x30) ^ '0'(0x30) ^ '0'(0x30) ^ '1'(0x31) ^ 'O'(0x4F) ^ 'K'(0x4B) = 0x05."""
    body = b"0001OK"
    expected_checksum = 0
    for b in body:
        expected_checksum ^= b
    assert expected_checksum == 0x05
    frame = encode_frame(1, b"OK")
    assert frame == b"$0001OK*05"
    decoded = decode_frame(frame)
    assert decoded.sequence == 1
    assert decoded.payload == b"OK"


def test_decode_frame_rejects_bad_checksum():
    frame = bytearray(encode_frame(5, b"X"))
    # Flip the last checksum hex digit to something definitely wrong.
    frame[-1] = ord("0") if frame[-1:] != b"0" else ord("1")
    with pytest.raises(CrcError):
        decode_frame(bytes(frame))


def test_decode_frame_rejects_missing_start_delimiter():
    with pytest.raises(ProtocolException):
        decode_frame(b"0001OK*6E")


def test_decode_frame_rejects_missing_checksum_delimiter():
    with pytest.raises(ProtocolException):
        decode_frame(b"$0001OK")


# --------------------------------------------------------------------------------------------------
# TCP transport -- real local socket server
# --------------------------------------------------------------------------------------------------

@pytest.fixture
def tcp_server():
    server = TCPLineServer()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def tcp_driver():
    return GenericSerialDriver(connector_id="serial-tcp-test", connector_version="1.0.0", device_id="dev-serial-tcp")


async def _wait_for_client(server: TCPLineServer, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.has_client():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("TCP server never saw a client connection")


async def test_tcp_transport_reads_valid_frame(tcp_server, tcp_driver):
    await tcp_driver.connect({"transport": "tcp", "host": "127.0.0.1", "port": tcp_server.port, "connect_timeout_seconds": 3.0})
    await _wait_for_client(tcp_server)
    tcp_server.push_line(encode_frame(1, b"TEMP=23.5").decode("ascii"))

    address = SourceAddress(address="TANK_TEMP", protocol="SERIAL", extra={"mapping_id": "TANK_TEMP", "unit": "C"})
    observation = await tcp_driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert observation.value == "TEMP=23.5"
    assert observation.quality_hint == "GOOD"
    assert observation.source.protocol == "SERIAL"
    await tcp_driver.disconnect("test complete")


async def test_tcp_transport_bad_checksum_raises_crc_error(tcp_server, tcp_driver):
    await tcp_driver.connect({"transport": "tcp", "host": "127.0.0.1", "port": tcp_server.port, "connect_timeout_seconds": 3.0})
    await _wait_for_client(tcp_server)
    corrupted = bytearray(encode_frame(2, b"BAD"))
    corrupted[-1] = ord("0") if corrupted[-1:] != b"0" else ord("1")
    tcp_server.push_line(corrupted.decode("ascii"))

    address = SourceAddress(address="TANK_TEMP", protocol="SERIAL", extra={"mapping_id": "TANK_TEMP"})
    with pytest.raises(CrcError):
        await tcp_driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    await tcp_driver.disconnect("test complete")


async def test_replayed_sequence_is_marked_uncertain(tcp_server, tcp_driver):
    """Document 44 section 12: "duplicate/replayed source event where detectable" -- a frame whose
    sequence number was already seen is not treated as fresh evidence."""
    await tcp_driver.connect({"transport": "tcp", "host": "127.0.0.1", "port": tcp_server.port, "connect_timeout_seconds": 3.0})
    await _wait_for_client(tcp_server)
    address = SourceAddress(address="TANK_TEMP", protocol="SERIAL", extra={"mapping_id": "TANK_TEMP"})

    tcp_server.push_line(encode_frame(10, b"V1").decode("ascii"))
    first = await tcp_driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert first.quality_hint == "GOOD"

    # Same sequence number replayed (e.g. a retransmit from a flaky serial line).
    tcp_server.push_line(encode_frame(10, b"V1").decode("ascii"))
    replay = await tcp_driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert replay.quality_hint == "UNCERTAIN"

    # A genuinely new, higher sequence number is fresh evidence again.
    tcp_server.push_line(encode_frame(11, b"V2").decode("ascii"))
    fresh = await tcp_driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert fresh.quality_hint == "GOOD"
    await tcp_driver.disconnect("test complete")


async def test_read_timeout_then_fresh_read_never_fabricates_a_value(tcp_server, tcp_driver):
    """Analogous to DRV-FR-009's "never substitute last good as current" -- after a timeout (no frame
    arrived), the driver raises rather than returning a cached/fabricated value, and the next genuine
    read returns the real, new value, not something invented during the timeout window."""
    await tcp_driver.connect({"transport": "tcp", "host": "127.0.0.1", "port": tcp_server.port, "connect_timeout_seconds": 3.0})
    await _wait_for_client(tcp_server)
    address = SourceAddress(address="TANK_TEMP", protocol="SERIAL", extra={"mapping_id": "TANK_TEMP"})

    with pytest.raises(ReadTimeout):
        await tcp_driver.read_once(address, ReadOptions(timeout_seconds=0.3))

    tcp_server.push_line(encode_frame(20, b"REAL_VALUE").decode("ascii"))
    observation = await tcp_driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert observation.value == "REAL_VALUE"
    assert observation.quality_hint == "GOOD"
    await tcp_driver.disconnect("test complete")


async def test_connect_to_unreachable_tcp_host_raises_endpoint_unreachable(tcp_driver):
    with pytest.raises(EndpointUnreachable):
        await tcp_driver.connect({"transport": "tcp", "host": "127.0.0.1", "port": 1, "connect_timeout_seconds": 1.0})


async def test_health_check(tcp_server, tcp_driver):
    await tcp_driver.connect({"transport": "tcp", "host": "127.0.0.1", "port": tcp_server.port, "connect_timeout_seconds": 3.0})
    health = await tcp_driver.health_check()
    assert health.connected is True
    assert health.diagnostics["transport"] == "tcp"
    await tcp_driver.disconnect("test complete")
    health_after = await tcp_driver.health_check()
    assert health_after.connected is False


def test_plugin_poll_returns_decoded_observation(tcp_server):
    """End-to-end through `GenericSerialPlugin.poll()`, the actual supervisor-facing contract."""
    plugin = GenericSerialPlugin({
        "connector_id": "serial-plugin-test", "connector_version": "1.0.0", "device_id": "dev-serial-plugin",
        "transport": "tcp", "host": "127.0.0.1", "port": tcp_server.port, "mapping_id": "TANK_TEMP", "unit": "C",
        "poll_interval_seconds": 1.0,
    })
    try:
        first = list(plugin.poll())  # connects
        assert first == []
        plugin._loop.run_until_complete(_wait_for_client(tcp_server))
        tcp_server.push_line(encode_frame(1, b"TEMP=41.0").decode("ascii"))
        second = list(plugin.poll())
        assert len(second) == 1
        assert second[0].value == "TEMP=41.0"
    finally:
        plugin._loop.run_until_complete(plugin._driver.disconnect("test teardown"))


# --------------------------------------------------------------------------------------------------
# Serial transport smoke test -- real socat virtual serial pty pair
# --------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not SOCAT_AVAILABLE, reason="socat not installed")
async def test_serial_transport_reads_valid_frame(tmp_path: Path):
    port_a = tmp_path / "ttyA"
    port_b = tmp_path / "ttyB"
    proc = subprocess.Popen(
        ["socat", "-d", "-d", f"pty,raw,echo=0,link={port_a}", f"pty,raw,echo=0,link={port_b}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not (port_a.exists() and port_b.exists()):
        time.sleep(0.05)
    assert port_a.exists() and port_b.exists(), "socat did not create the virtual serial pair in time"

    try:
        driver = GenericSerialDriver(connector_id="serial-rtu-test", connector_version="1.0.0", device_id="dev-serial-serial")
        await driver.connect({"transport": "serial", "port": str(port_b), "baudrate": 9600, "connect_timeout_seconds": 3.0})

        import serial as pyserial

        def _write_frame():
            with pyserial.Serial(str(port_a), baudrate=9600, timeout=3.0) as instrument_end:
                instrument_end.write(encode_frame(1, b"PRESSURE=101.3") + b"\r\n")

        await asyncio.get_event_loop().run_in_executor(None, _write_frame)

        address = SourceAddress(address="PRESSURE", protocol="SERIAL", extra={"mapping_id": "PRESSURE"})
        observation = await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
        assert observation.value == "PRESSURE=101.3"
        assert observation.quality_hint == "GOOD"
        await driver.disconnect("test complete")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
