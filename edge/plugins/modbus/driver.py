"""Modbus TCP/RTU client driver -- Document 44 (SPEC-EDGE-002) section 6.

DRV-FR-007 (Modbus TCP: host/unit ID/function/register/type/endianness/scaling with bounded
polling), DRV-FR-008 (Modbus RTU: serial port/baud/parity/stop bits/slave ID/register mapping and
bus serialization), DRV-FR-009 (invalid value: timeout/CRC/exception/out-of-range marks
BAD/COMM_ERROR; never substitute last good as current without STALE quality -- enforced one layer up
in `plugins/common/polling_plugin.py`, which never re-emits a cached value on a read failure).

One `ModbusDriver` class serves both transports (`variant="MODBUS_TCP"` or `"MODBUS_RTU"`) since the
register-mapping/decode semantics (DRV-FR-009's error handling, `codec.py`'s data_type/byte_order/
scale) are identical once a `pymodbus` client is connected -- only connection setup differs.

Uses `pymodbus` (BSD-3-Clause; Document 104 justification recorded in `edge/pyproject.toml`).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Literal

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException, ModbusIOException

from plugins.common.driver_contracts import (
    ConnectionResult,
    DriverHealth,
    EdgeDriver,
    EndpointUnreachable,
    ProtocolException,
    ReadOptions,
    ReadTimeout,
    SourceAddress,
    SourceMappingNotFound,
    to_raw_observation,
)
from plugins.modbus.codec import decode_registers
from runtime.contracts import RawSourceObservation, SourceRef, utcnow

ModbusVariant = Literal["MODBUS_TCP", "MODBUS_RTU"]

_REGISTER_FUNCTIONS = {"HOLDING", "INPUT"}
_BIT_FUNCTIONS = {"COIL", "DISCRETE"}


def classify_modbus_exception(exc: Exception) -> Exception:
    """DRV-FR-024: normalize pymodbus's native exception hierarchy into the stable Document 44
    taxonomy while retaining the raw diagnostic text. `ModbusIOException` covers both "no valid
    response decoded" and, for the RTU framer specifically, a failed CRC check -- pymodbus does not
    expose a distinct CRC-specific exception class, so the raw message text is inspected (a technical
    classification detail, not a regulated-behavior decision)."""

    from plugins.common.driver_contracts import CrcError

    if isinstance(exc, ConnectionException):
        return EndpointUnreachable(str(exc), raw_detail=str(exc))
    if isinstance(exc, ModbusIOException):
        if "crc" in str(exc).lower():
            return CrcError(str(exc), raw_detail=str(exc))
        return ReadTimeout(str(exc), raw_detail=str(exc))
    if isinstance(exc, ModbusException):
        return ProtocolException(str(exc), raw_detail=str(exc))
    return ProtocolException(str(exc), raw_detail=str(exc))


class ModbusDriver(EdgeDriver):
    def __init__(self, connector_id: str, connector_version: str, device_id: str, variant: ModbusVariant) -> None:
        self.connector_id = connector_id
        self.connector_version = connector_version
        self.device_id = device_id
        self.variant = variant
        self._client: AsyncModbusTcpClient | AsyncModbusSerialClient | None = None
        self._default_unit_id = 1
        self._error_count = 0
        self._last_success_at = None
        self._session_id: str | None = None

    async def connect(self, config: dict[str, Any]) -> ConnectionResult:
        timeout = float(config.get("connect_timeout_seconds", 3.0))
        self._default_unit_id = int(config.get("unit_id", 1))

        if self.variant == "MODBUS_TCP":
            client = AsyncModbusTcpClient(config["host"], port=int(config.get("port", 502)), timeout=timeout)
        else:
            client = AsyncModbusSerialClient(
                config["port"],
                baudrate=int(config.get("baudrate", 19200)),
                bytesize=int(config.get("bytesize", 8)),
                parity=config.get("parity", "N"),
                stopbits=int(config.get("stopbits", 1)),
                timeout=timeout,
            )

        try:
            connected = await asyncio.wait_for(client.connect(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise EndpointUnreachable(f"Modbus {self.variant} connect timed out", raw_detail=str(exc)) from exc
        except OSError as exc:
            raise EndpointUnreachable(f"Modbus {self.variant} connect failed", raw_detail=str(exc)) from exc

        if not connected:
            raise EndpointUnreachable(f"Modbus {self.variant} connect returned failure (no exception raised)")

        self._client = client
        self._session_id = str(uuid.uuid4())
        self._last_success_at = utcnow()
        return ConnectionResult(
            session_id=self._session_id,
            capabilities={"read": True, "write": False, "subscribe": False, "browse": False},
        )

    async def disconnect(self, reason: str) -> None:
        if self._client is None:
            return
        self._client.close()
        self._client = None
        self._session_id = None

    def _require_client(self):
        if self._client is None:
            raise ProtocolException("Modbus driver used before connect()")
        return self._client

    async def read_once(self, address: SourceAddress, opts: ReadOptions | None = None) -> RawSourceObservation:
        client = self._require_client()
        extra = address.extra
        function = extra.get("function", "HOLDING")
        length = int(extra.get("length", 1))
        unit_id = int(extra.get("unit_id") or self._default_unit_id)
        register_address = int(address.address)
        timeout = opts.timeout_seconds if opts else 5.0

        try:
            if function == "HOLDING":
                response = await asyncio.wait_for(
                    client.read_holding_registers(register_address, count=length, device_id=unit_id), timeout=timeout
                )
            elif function == "INPUT":
                response = await asyncio.wait_for(
                    client.read_input_registers(register_address, count=length, device_id=unit_id), timeout=timeout
                )
            elif function == "COIL":
                response = await asyncio.wait_for(
                    client.read_coils(register_address, count=length, device_id=unit_id), timeout=timeout
                )
            elif function == "DISCRETE":
                response = await asyncio.wait_for(
                    client.read_discrete_inputs(register_address, count=length, device_id=unit_id), timeout=timeout
                )
            else:
                raise SourceMappingNotFound(f"unsupported Modbus function: {function!r}")
        except asyncio.TimeoutError as exc:
            self._error_count += 1
            raise ReadTimeout(f"Modbus read timed out at address={register_address}", raw_detail=str(exc)) from exc
        except (ConnectionException, ModbusIOException, ModbusException) as exc:
            self._error_count += 1
            raise classify_modbus_exception(exc) from exc

        if response.isError():
            self._error_count += 1
            raise ProtocolException(f"Modbus exception response for address={register_address}: {response}")

        if function in _REGISTER_FUNCTIONS:
            data_type = extra.get("data_type", "UINT16")
            byte_order = extra.get("byte_order", "ABCD")
            scale = float(extra.get("scale", 1.0))
            value = decode_registers(response.registers, data_type, byte_order, scale)
        else:
            bits = getattr(response, "bits", None)
            value = bool(bits[0]) if bits else None

        self._last_success_at = utcnow()
        return to_raw_observation(
            connector_id=self.connector_id,
            connector_version=self.connector_version,
            device_id=self.device_id,
            mapping_id=extra.get("mapping_id", address.address),
            source=SourceRef(protocol=self.variant, address=address.address, native_data_type=extra.get("data_type")),
            value=value,
            unit=extra.get("unit"),
            quality_hint="GOOD",
        )

    async def health_check(self) -> DriverHealth:
        connected = self._client is not None and bool(self._client.connected)
        return DriverHealth(
            connected=connected, last_success_at=self._last_success_at, error_count=self._error_count,
            latency_ms=None, diagnostics={"session_id": self._session_id, "variant": self.variant},
        )
