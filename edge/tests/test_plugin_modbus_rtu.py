"""Modbus RTU driver tests -- Document 44 DRV-FR-008 ("Support serial port/baud/parity/stop bits/slave
ID/register mapping and bus serialization").

Protocol-simulator-backed exactly like `test_plugin_modbus_tcp.py`: a real `pymodbus.server.
ModbusSerialServer` (RTU framer, the pymodbus default for that class) is bound to one end of a real
virtual serial-port pair created by `socat` (`pty,raw,echo=0` on both ends -- a genuine kernel pty pair
linked by a real byte stream, the standard way to exercise serial-port client/server code without
physical RS-485/RS-232 hardware), and `ModbusDriver(variant="MODBUS_RTU")` connects a real
`AsyncModbusSerialClient` to the other end. Real RTU framing (address byte + PDU + CRC16) crosses the
wire exactly as it would on a physical bus.

`socat` is a test-only tool (already an OS package in this environment, like `mosquitto` for the MQTT
tests) -- it is not an `edge/pyproject.toml` runtime dependency and nothing under `runtime/`/`plugins/`
imports or shells out to it. If `socat` is not on PATH the tests are skipped rather than failing, so this
suite degrades gracefully in an environment without it while still running for real here.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from pymodbus.server import ModbusSerialServer
from pymodbus.simulator import DataType, SimData, SimDevice

from plugins.common.driver_contracts import EndpointUnreachable, ProtocolException, ReadOptions, SourceAddress
from plugins.modbus.codec import encode_value_to_registers
from plugins.modbus.driver import ModbusDriver

SOCAT_AVAILABLE = shutil.which("socat") is not None
pytestmark = pytest.mark.skipif(not SOCAT_AVAILABLE, reason="socat not installed -- see module docstring")


@pytest.fixture
def serial_pair(tmp_path: Path):
    """Real linked pty pair standing in for an RS-232/RS-485 cable -- one path is the server's serial
    port, the other is the client's."""
    port_a = tmp_path / "ttyA"
    port_b = tmp_path / "ttyB"
    proc = subprocess.Popen(
        ["socat", "-d", "-d", f"pty,raw,echo=0,link={port_a}", f"pty,raw,echo=0,link={port_b}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if port_a.exists() and port_b.exists():
            break
        time.sleep(0.05)
    else:
        proc.terminate()
        pytest.fail("socat did not create the virtual serial pair in time")
    try:
        yield {"server_port": str(port_a), "client_port": str(port_b)}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture
async def modbus_rtu_server(serial_pair):
    di = [SimData(address=0, count=50, values=0, datatype=DataType.BITS)]
    co = [SimData(address=0, count=50, values=0, datatype=DataType.BITS)]
    ir = [SimData(address=0, count=50, values=0, datatype=DataType.REGISTERS)]
    hr = [SimData(address=0, count=50, values=0, datatype=DataType.REGISTERS)]
    device = SimDevice(id=3, simdata=(di, co, ir, hr))
    server = ModbusSerialServer(device, port=serial_pair["server_port"], baudrate=19200, parity="N", stopbits=1, bytesize=8)
    task = asyncio.create_task(server.serve_forever())
    await asyncio.sleep(0.3)  # let the server open/listen on its end of the pty before the client dials
    try:
        yield {"server": server, "client_port": serial_pair["client_port"]}
    finally:
        await server.shutdown()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.fixture
def driver():
    return ModbusDriver(connector_id="modbus-rtu-test", connector_version="1.0.0", device_id="dev-rtu", variant="MODBUS_RTU")


async def test_connect_and_read_holding_register_float32(modbus_rtu_server, driver):
    registers = encode_value_to_registers(77.25, "FLOAT32", "ABCD")
    await modbus_rtu_server["server"].async_setValues(3, 3, 10, registers)  # function code 3 = holding registers

    await driver.connect({
        "port": modbus_rtu_server["client_port"], "baudrate": 19200, "parity": "N", "stopbits": 1,
        "bytesize": 8, "unit_id": 3, "connect_timeout_seconds": 3.0,
    })
    address = SourceAddress(
        address="10", protocol="MODBUS_RTU",
        extra={"function": "HOLDING", "length": 2, "data_type": "FLOAT32", "byte_order": "ABCD"},
    )
    observation = await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert observation.value == pytest.approx(77.25)
    assert observation.quality_hint == "GOOD"
    assert observation.source.protocol == "MODBUS_RTU"
    await driver.disconnect("test complete")


async def test_read_coil(modbus_rtu_server, driver):
    await modbus_rtu_server["server"].async_setValues(3, 1, 4, [True])  # function code 1 = read coils
    await driver.connect({
        "port": modbus_rtu_server["client_port"], "baudrate": 19200, "unit_id": 3, "connect_timeout_seconds": 3.0,
    })
    address = SourceAddress(address="4", protocol="MODBUS_RTU", extra={"function": "COIL", "length": 1})
    observation = await driver.read_once(address)
    assert observation.value is True
    await driver.disconnect("test complete")


async def test_wrong_unit_id_is_endpoint_or_protocol_error(modbus_rtu_server, driver):
    """DRV-FR-009: bus serialization means a request addressed to a slave ID that never answers must
    surface as a driver error, never a silently-returned value."""
    await driver.connect({
        "port": modbus_rtu_server["client_port"], "baudrate": 19200, "unit_id": 9, "connect_timeout_seconds": 1.0,
    })
    address = SourceAddress(address="10", protocol="MODBUS_RTU", extra={"function": "HOLDING", "length": 1})
    with pytest.raises((ProtocolException, EndpointUnreachable)):
        await driver.read_once(address, ReadOptions(timeout_seconds=1.5))
    await driver.disconnect("test complete")


async def test_out_of_range_register_raises_protocol_exception(modbus_rtu_server, driver):
    await driver.connect({
        "port": modbus_rtu_server["client_port"], "baudrate": 19200, "unit_id": 3, "connect_timeout_seconds": 3.0,
    })
    address = SourceAddress(address="9999", protocol="MODBUS_RTU", extra={"function": "HOLDING", "length": 1})
    with pytest.raises(ProtocolException):
        await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    await driver.disconnect("test complete")


async def test_health_check(modbus_rtu_server, driver):
    await driver.connect({"port": modbus_rtu_server["client_port"], "baudrate": 19200, "unit_id": 3, "connect_timeout_seconds": 3.0})
    health = await driver.health_check()
    assert health.connected is True
    assert health.diagnostics["variant"] == "MODBUS_RTU"
    await driver.disconnect("test complete")
    health_after = await driver.health_check()
    assert health_after.connected is False


async def test_connect_to_nonexistent_serial_port_is_endpoint_unreachable(driver):
    with pytest.raises(EndpointUnreachable):
        await driver.connect({"port": "/dev/ttyUSB_does_not_exist_99", "connect_timeout_seconds": 1.0})
