"""Balance/scale connector plugin -- Document 46 (SPEC-EDGE-004) section 7 ("Balance Strategy": use
decimal strings; stable reading only; preserve device UOM and canonical UOM; check equipment eligibility;
fallback is explicit; readings associated with weighing session/order").

Protocol: a simple ASCII continuous-output line format modeled on the common industrial-balance
convention of comma-separated status/gross/net/unit fields (e.g. A&D/Mettler-Toledo-style continuous
output) --

    <STATUS>,<GROSS>,<TARE>,<NET>,<UOM>\\n     e.g.  ST,GS,+00123.45,+00000.00,+00123.45,g

STATUS is `ST` (stable) or `US` (unstable). No real balance hardware is available in this build
environment; `edge/tests/fixtures/balance_sim.py` is a real local TCP server emitting this exact line
format, so the socket I/O, line parsing and decimal handling below are exercised for real, not mocked --
only the physical weighing cell is simulated.

PER-FR-007: every observation carries value/unit/stable-flag/device status/`calibration_ref` (from this
connector's own config -- the plugin repeats the calibration identity it was configured with; it does not
itself decide the balance is *eligible* to use, since equipment-qualification status is a domain/Equipment
module concern this plugin has no access to, per EDGE-FR-008's sandbox and Document 46 PER-FR-018).
PER-FR-008: `stable` is taken only from the device's own STATUS field -- an unstable (`US`) line is still
forwarded (so a live-weight UI has something to show), but always carries `stable: false`; nothing in this
plugin ever promotes a transient/unstable value to `stable: true`.
PER-FR-009: gross/tare/net are three distinct decimal-string fields, never collapsed into one number.
`send_command({"action": "tare"})` sends the device's own tare instruction over the same TCP connection
this connector already owns -- see `plugins.base.ConnectorPlugin.send_command` for why this is not
Document 43's EDGE-FR-023 remote machine-command channel.
"""

from __future__ import annotations

import argparse
import json
import socket
from decimal import Decimal, InvalidOperation
from typing import Iterable

from plugins.base import ConnectorPlugin, PeripheralCommandNotSupportedError, run_plugin_main
from runtime.contracts import RawSourceObservation, SourceRef

MAPPING_ID = "doc46-balance-continuous-ascii-v1"
_RECV_BUFFER = 4096


class BalanceCommError(Exception):
    pass


class BalanceReadingMalformedError(Exception):
    pass


def _decimal_str(token: str) -> str:
    """Canonical decimal string per Document 46's `StableWeightReading.value: string` contract and this
    project's DATA-FR-019 ("Regulated numeric values/calculations use exact decimal representation") --
    parsed through `Decimal`, never `float`, and re-serialized as a string so no binary-float rounding
    ever touches the value on its way through this plugin."""
    try:
        return str(Decimal(token.strip()))
    except InvalidOperation as exc:
        raise BalanceReadingMalformedError(f"not a decimal quantity: {token!r}") from exc


class BalancePlugin(ConnectorPlugin):
    """`connector_config` keys: `connector_id`, `device_id`, `station_id`, `calibration_ref`, `host`,
    `port`."""

    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._sock: socket.socket | None = None
        self._buffer = b""
        self._session_seq = 0

    def _device_id(self) -> str:
        return self.connector_config.get("device_id", "unknown-balance")

    def _connect(self) -> None:
        host = self.connector_config["host"]
        port = int(self.connector_config["port"])
        sock = socket.create_connection((host, port), timeout=2.0)
        sock.settimeout(0.2)
        self._sock = sock
        self._session_seq += 1

    def _reconnect(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._connect()

    def _read_lines(self) -> list[str]:
        assert self._sock is not None
        try:
            chunk = self._sock.recv(_RECV_BUFFER)
        except socket.timeout:
            return []
        except OSError as exc:
            raise BalanceCommError(str(exc)) from exc
        if chunk == b"":
            raise BalanceCommError("balance connection closed by peer")
        self._buffer += chunk
        lines: list[str] = []
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            text = line.decode("ascii", errors="replace").rstrip("\r")
            if text:
                lines.append(text)
        return lines

    def _parse_reading(self, line: str) -> dict:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 5:
            raise BalanceReadingMalformedError(f"expected 5 comma-separated fields, got {len(parts)}: {line!r}")
        status, gross, tare, net, uom = parts
        if status not in ("ST", "US"):
            raise BalanceReadingMalformedError(f"unknown status code {status!r}")
        return {
            "stable": status == "ST",
            "gross": _decimal_str(gross),
            "tare": _decimal_str(tare),
            "net": _decimal_str(net),
            "uom": uom,
        }

    def poll(self) -> Iterable[RawSourceObservation]:
        if self._sock is None:
            try:
                self._connect()
            except OSError as exc:
                yield self._comm_error_observation(str(exc))
                return

        try:
            raw_lines = self._read_lines()
        except BalanceCommError as exc:
            yield self._comm_error_observation(str(exc))
            try:
                self._reconnect()
            except OSError:
                self._sock = None
            return

        for raw in raw_lines:
            try:
                reading = self._parse_reading(raw)
            except BalanceReadingMalformedError as exc:
                yield RawSourceObservation(
                    connector_id=self.connector_config.get("connector_id", "balance"),
                    connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
                    source=SourceRef(protocol="SERIAL", address=self._device_id(), native_data_type="weight_line"),
                    value={"raw": raw, "error": str(exc)}, quality_hint="BAD",
                )
                continue

            yield RawSourceObservation(
                connector_id=self.connector_config.get("connector_id", "balance"),
                connector_version="1.0",
                device_id=self._device_id(),
                mapping_id=MAPPING_ID,
                source=SourceRef(protocol="SERIAL", address=self._device_id(), native_data_type="weight_line"),
                unit=reading["uom"],
                value={
                    "raw": raw,
                    "session_seq": self._session_seq,
                    "stable": reading["stable"],
                    "gross": reading["gross"],
                    "tare": reading["tare"],
                    "net": reading["net"],
                    "uom": reading["uom"],
                    "calibration_ref": self.connector_config.get("calibration_ref"),
                    "device_status": "STABLE" if reading["stable"] else "UNSTABLE",
                },
                quality_hint="GOOD" if reading["stable"] else "UNCERTAIN",
            )

    def _comm_error_observation(self, detail: str) -> RawSourceObservation:
        return RawSourceObservation(
            connector_id=self.connector_config.get("connector_id", "balance"),
            connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
            source=SourceRef(protocol="SERIAL", address=self._device_id(), native_data_type="weight_line"),
            value={"error": detail, "session_seq": self._session_seq}, quality_hint="COMM_ERROR",
        )

    def send_command(self, command: dict) -> RawSourceObservation:
        """Only `{"action": "tare"}` is supported -- see module docstring and `ConnectorPlugin.
        send_command` for why this is a locally-owned peripheral action, not Document 43's EDGE-FR-023
        remote machine-command channel. Any other action is refused rather than guessed."""
        action = command.get("action")
        if action != "tare":
            raise PeripheralCommandNotSupportedError(f"BalancePlugin does not support command action {action!r}")
        if self._sock is None:
            self._connect()
        assert self._sock is not None
        self._sock.sendall(b"T\r\n")
        try:
            ack_lines = self._read_lines()
        except BalanceCommError as exc:
            return self._comm_error_observation(f"tare send failed: {exc}")
        return RawSourceObservation(
            connector_id=self.connector_config.get("connector_id", "balance"),
            connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
            source=SourceRef(protocol="SERIAL", address=self._device_id(), native_data_type="tare_ack"),
            value={"action": "tare", "ack_lines": ack_lines, "session_seq": self._session_seq},
            quality_hint="GOOD",
        )


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--config", required=True)
    args = arg_parser.parse_args()
    cfg = json.loads(open(args.config).read())
    run_plugin_main(BalancePlugin(cfg))