"""Modbus TCP driver tests -- Document 44 DRV-FR-007, DRV-FR-009, section 6/12.

Protocol-simulator-backed: `pymodbus.server.ModbusTcpServer` runs a real Modbus TCP server on
localhost (real PDU/MBAP framing on the wire, the same server pymodbus's own conformance tests use),
and `ModbusDriver` connects a real `AsyncModbusTcpClient` to it. `test_decode_registers_matches_test_
vectors` is section 6's "each mapping has test vectors with raw registers -> expected engineering
value" requirement -- a pure codec unit test, no server needed.
"""

from __future__ import annotations

import asyncio

import pytest
from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

from plugins.common.driver_contracts import (
    EndpointUnreachable,
    ProtocolException,
    ReadOptions,
    SourceAddress,
)
from plugins.modbus.codec import decode_registers, encode_value_to_registers
from plugins.modbus.driver import ModbusDriver

TEST_PORT = 15020


@pytest.fixture
async def modbus_tcp_server():
    di = [SimData(address=0, count=200, values=0, datatype=DataType.BITS)]
    co = [SimData(address=0, count=200, values=0, datatype=DataType.BITS)]
    ir = [SimData(address=0, count=200, values=0, datatype=DataType.REGISTERS)]
    hr = [SimData(address=0, count=200, values=0, datatype=DataType.REGISTERS)]
    device = SimDevice(id=1, simdata=(di, co, ir, hr))
    server = ModbusTcpServer(device, address=("127.0.0.1", TEST_PORT))
    task = asyncio.create_task(server.serve_forever())
    await asyncio.sleep(0.2)  # let the listener bind before a client tries to connect
    try:
        yield {"server": server}
    finally:
        await server.shutdown()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.fixture
def driver():
    return ModbusDriver(connector_id="modbus-tcp-test", connector_version="1.0.0", device_id="dev-tcp", variant="MODBUS_TCP")


async def test_connect_and_read_holding_register_float32(modbus_tcp_server, driver):
    registers = encode_value_to_registers(123.5, "FLOAT32", "ABCD")
    await modbus_tcp_server["server"].async_setValues(1, 3, 10, registers)  # function code 3 = holding registers

    await driver.connect({"host": "127.0.0.1", "port": TEST_PORT, "unit_id": 1})
    address = SourceAddress(
        address="10", protocol="MODBUS_TCP",
        extra={"function": "HOLDING", "length": 2, "data_type": "FLOAT32", "byte_order": "ABCD"},
    )
    observation = await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    assert observation.value == pytest.approx(123.5)
    assert observation.quality_hint == "GOOD"
    await driver.disconnect("test complete")


async def test_read_coil(modbus_tcp_server, driver):
    await modbus_tcp_server["server"].async_setValues(1, 1, 5, [True])  # function code 1 = read coils
    await driver.connect({"host": "127.0.0.1", "port": TEST_PORT, "unit_id": 1})
    address = SourceAddress(address="5", protocol="MODBUS_TCP", extra={"function": "COIL", "length": 1})
    observation = await driver.read_once(address)
    assert observation.value is True
    await driver.disconnect("test complete")


async def test_endpoint_unreachable_for_dead_port(driver):
    with pytest.raises(EndpointUnreachable):
        await driver.connect({"host": "127.0.0.1", "port": 1, "connect_timeout_seconds": 1.0})


async def test_out_of_range_register_raises_protocol_exception(modbus_tcp_server, driver):
    """DRV-FR-009: an out-of-range register access is a Modbus exception response (illegal data
    address), classified as PROTOCOL_EXCEPTION -- never silently returned as a numeric value."""
    await driver.connect({"host": "127.0.0.1", "port": TEST_PORT, "unit_id": 1})
    address = SourceAddress(address="9999", protocol="MODBUS_TCP", extra={"function": "HOLDING", "length": 1})
    with pytest.raises(ProtocolException):
        await driver.read_once(address, ReadOptions(timeout_seconds=3.0))
    await driver.disconnect("test complete")


async def test_health_check(modbus_tcp_server, driver):
    await driver.connect({"host": "127.0.0.1", "port": TEST_PORT, "unit_id": 1})
    health = await driver.health_check()
    assert health.connected is True
    await driver.disconnect("test complete")
    health_after = await driver.health_check()
    assert health_after.connected is False


async def test_write_is_disabled_by_default(modbus_tcp_server, driver):
    from plugins.common.driver_contracts import DriverWriteRequest, WriteDisabled

    await driver.connect({"host": "127.0.0.1", "port": TEST_PORT, "unit_id": 1})
    address = SourceAddress(address="10", protocol="MODBUS_TCP", extra={"function": "HOLDING", "length": 2})
    with pytest.raises(WriteDisabled):
        await driver.write(DriverWriteRequest(address=address, value=1.0))
    await driver.disconnect("test complete")


@pytest.mark.parametrize(
    "registers,data_type,byte_order,scale,expected",
    [
        # Document 44 section 6's own example: 40010, FLOAT32, ABCD, scale 1.0
        ([0x42F6, 0x0000], "FLOAT32", "ABCD", 1.0, 123.0),
        ([0x0000, 0x42F6], "FLOAT32", "CDAB", 1.0, 123.0),  # word-swapped variant of the same value
        ([1234], "UINT16", "ABCD", 1.0, 1234),
        ([1234], "UINT16", "ABCD", 0.1, 123.4),
        ([0xFFFF], "INT16", "ABCD", 1.0, -1),
        ([0x0000, 0x0064], "UINT32", "ABCD", 1.0, 100),
    ],
)
def test_decode_registers_matches_test_vectors(registers, data_type, byte_order, scale, expected):
    """Section 6: "Each mapping has test vectors with raw registers -> expected engineering value."""
    assert decode_registers(registers, data_type, byte_order, scale) == pytest.approx(expected)