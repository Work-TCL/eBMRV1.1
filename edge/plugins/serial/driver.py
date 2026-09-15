"""Generic serial/TCP proprietary adapter driver -- Document 44 (SPEC-EDGE-002) DRV-FR-013 ("Custom
proprietary protocol lives in isolated adapter with framing/checksum/test vectors").

Supports two transports for the same framed-line protocol (`plugins/serial/framing.py`):
- `transport: tcp` -- a raw TCP socket to a device or a "serial device server" (a very common way real
  RS-232/RS-485 instruments get exposed on a plant network) -- tested against a real local TCP server
  (`edge/tests/support/tcp_line_server.py`, already built for exactly this "stand in for scanner/balance/
  printer serial-or-TCP hardware" role per Document 46 PER-FR-025).
- `transport: serial` -- a real local serial port via `pyserial` -- tested against a real `socat`-created
  virtual serial pty pair, the same technique `test_plugin_modbus_rtu.py` uses.

Uses `pyserial` (BSD-3-Clause; Document 104 justification already recorded in `edge/pyproject.toml` for
Modbus RTU's transport -- this driver is the second, not a new, consumer of that dependency).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from plugins.common.driver_contracts import (
    ConnectionResult,
    DriverHealth,
    EdgeDriver,
    EndpointUnreachable,
    ProtocolException,
    ReadOptions,
    ReadTimeout,
    SourceAddress,
    to_raw_observation,
)
from plugins.serial.framing import decode_frame
from runtime.contracts import RawSourceObservation, SourceRef, utcnow

_LINE_TERMINATOR = b"\n"


class GenericSerialDriver(EdgeDriver):
    def __init__(self, connector_id: str, connector_version: str, device_id: str) -> None:
        self.connector_id = connector_id
        self.connector_version = connector_version
        self.device_id = device_id
        self._transport: str | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._serial = None  # a pyserial Serial instance when transport == "serial"
        self._session_id: str | None = None
        self._error_count = 0
        self._last_success_at: datetime | None = None
        self._last_sequence: int | None = None

    async def connect(self, config: dict[str, Any]) -> ConnectionResult:
        transport = config.get("transport", "tcp")
        timeout = float(config.get("connect_timeout_seconds", 5.0))

        if transport == "tcp":
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(config["host"], int(config["port"])), timeout=timeout
                )
            except (OSError, asyncio.TimeoutError) as exc:
                raise EndpointUnreachable(f"TCP connect failed: {exc}", raw_detail=str(exc)) from exc
            self._reader, self._writer = reader, writer
        elif transport == "serial":
            import serial  # pyserial

            def _open() -> "serial.Serial":
                return serial.Serial(
                    config["port"], baudrate=int(config.get("baudrate", 9600)),
                    bytesize=int(config.get("bytesize", 8)), parity=config.get("parity", "N"),
                    stopbits=int(config.get("stopbits", 1)), timeout=timeout,
                )

            try:
                self._serial = await asyncio.get_event_loop().run_in_executor(None, _open)
            except serial.SerialException as exc:
                raise EndpointUnreachable(f"serial port open failed: {exc}", raw_detail=str(exc)) from exc
        else:
            raise ProtocolException(f"unsupported transport: {transport!r} (expected 'tcp' or 'serial')")

        self._transport = transport
        self._session_id = str(uuid.uuid4())
        self._last_success_at = utcnow()
        return ConnectionResult(
            session_id=self._session_id,
            capabilities={"read": True, "write": False, "subscribe": False, "browse": False},
        )

    async def disconnect(self, reason: str) -> None:
        if self._transport == "tcp" and self._writer is not None:
            self._writer.close()
        elif self._transport == "serial" and self._serial is not None:
            await asyncio.get_event_loop().run_in_executor(None, self._serial.close)
        self._transport = None
        self._reader = None
        self._writer = None
        self._serial = None
        self._session_id = None

    async def _read_line(self, timeout: float) -> bytes:
        if self._transport == "tcp":
            assert self._reader is not None
            try:
                return await asyncio.wait_for(self._reader.readuntil(_LINE_TERMINATOR), timeout=timeout)
            except asyncio.TimeoutError as exc:
                raise ReadTimeout(f"no frame received within {timeout}s (tcp)", raw_detail=str(exc)) from exc
            except asyncio.IncompleteReadError as exc:
                self._error_count += 1
                raise EndpointUnreachable("TCP connection closed by peer", raw_detail=str(exc)) from exc
        elif self._transport == "serial":
            assert self._serial is not None
            self._serial.timeout = timeout

            def _readline() -> bytes:
                return self._serial.readline()  # pyserial: b"" on its own timeout, never raises for that

            line = await asyncio.get_event_loop().run_in_executor(None, _readline)
            if not line:
                raise ReadTimeout(f"no frame received within {timeout}s (serial)")
            return line
        else:
            raise EndpointUnreachable("driver used before connect()")

    async def read_once(self, address: SourceAddress, opts: ReadOptions | None = None) -> RawSourceObservation:
        timeout = opts.timeout_seconds if opts else 5.0
        raw_line = (await self._read_line(timeout)).rstrip(b"\r\n")
        try:
            frame = decode_frame(raw_line)
        except ProtocolException:
            self._error_count += 1
            raise

        # DRV-FR-013's sibling mandatory test (Document 44 section 12: "duplicate/replayed source event
        # where detectable"). Document 44 section 9's stable error taxonomy has no REPLAY_DETECTED code
        # for a protocol driver (that vocabulary belongs to the GxP mutation layer, not this layer) --
        # UNCERTAIN is this codebase's existing quality category for "a value is present but its
        # trustworthiness is in doubt" (Document 43 section 5), which is exactly the honest description
        # of a sequence number the driver has already seen: the *value* is not necessarily wrong, but it
        # is not new evidence, and downstream must not treat it as such without review.
        is_replay = self._last_sequence is not None and frame.sequence <= self._last_sequence
        self._last_sequence = frame.sequence if self._last_sequence is None else max(self._last_sequence, frame.sequence)

        self._last_success_at = utcnow()
        return to_raw_observation(
            connector_id=self.connector_id,
            connector_version=self.connector_version,
            device_id=self.device_id,
            mapping_id=address.extra.get("mapping_id", address.address),
            source=SourceRef(protocol="SERIAL", address=address.address),
            value=frame.payload.decode("ascii", errors="replace"),
            unit=address.extra.get("unit"),
            quality_hint="UNCERTAIN" if is_replay else "GOOD",
        )

    async def health_check(self) -> DriverHealth:
        connected = self._transport is not None
        return DriverHealth(
            connected=connected, last_success_at=self._last_success_at, error_count=self._error_count,
            latency_ms=None, diagnostics={"session_id": self._session_id, "transport": self._transport, "last_sequence": self._last_sequence},
        )
