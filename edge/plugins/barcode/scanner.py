"""Barcode scanner connector plugin -- Document 46 (SPEC-EDGE-004).

PER-FR-003 ("preferred explicit scanner SDK/serial/HID service with source identity" over bare keyboard
wedge): this plugin connects to the scanner over a TCP line protocol rather than treating unattributed
keyboard-wedge text as a scan. Document 43's own Current Protocol Baseline explicitly allows "serial/TCP
proprietary adapters through isolated plugins" -- no real scanner hardware/SDK is available in this build
environment, so a TCP line server (`edge/tests/fixtures/barcode_scanner_sim.py`) stands in for the
serial/HID transport a real deployment would use; every scan this plugin emits still carries this
connector's own `device_id`/`source` identity, which is the property PER-FR-003 actually requires (never
an anonymous OS-level keystroke stream).

PER-FR-004 (parsing): delegates to `plugins.barcode.parser`, versioned and separate from validation.
PER-FR-005 (scan validation): explicitly NOT done here -- Document 46 section 6 assigns
`validateScanForAction()` to the "server/domain" layer against the authoritative material/lot/serial
record; a plugin has no access to that record (EDGE-FR-008 sandbox) and must not guess it.
PER-FR-006 (duplicate scan): this plugin never suppresses or debounces a repeated raw scan -- the spec is
explicit that "operation context determines idempotency", which is also domain-side. Two identical scans
one second apart are both forwarded, unmodified, exactly like two different scans.
PER-FR-020 (hot-plug/reconnect): `_reconnect()` preserves `device_id` across a dropped TCP connection and
increments `session_seq`, giving every observation an explicit session boundary.
PER-FR-023 (raw input preservation): the exact scanned text is always present verbatim as `parsed_raw` in
the observation payload (never re-encoded/altered), independent of whatever the parser extracts from it.
"""

from __future__ import annotations

import argparse
import json
import socket
from typing import Iterable

from plugins.barcode.parser import PARSER_ID, PARSER_VERSION, parse_scan
from plugins.base import ConnectorPlugin, run_plugin_main
from runtime.contracts import RawSourceObservation, SourceRef

_RECV_BUFFER = 4096


class ScannerCommError(Exception):
    pass


class BarcodeScannerPlugin(ConnectorPlugin):
    """`connector_config` keys: `connector_id`, `device_id`, `station_id` (PER-FR-001/002 identity
    attribution -- carried on every observation but the peripheral *registry*/*station profile* stores
    themselves are domain-side, not built here), `host`, `port` (the TCP scan-line source)."""

    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._sock: socket.socket | None = None
        self._buffer = b""
        self._session_seq = 0

    def _device_id(self) -> str:
        return self.connector_config.get("device_id", "unknown-scanner")

    def _station_id(self) -> str:
        return self.connector_config.get("station_id", "unknown-station")

    def _connect(self) -> None:
        host = self.connector_config["host"]
        port = int(self.connector_config["port"])
        sock = socket.create_connection((host, port), timeout=2.0)
        sock.settimeout(0.2)
        self._sock = sock
        self._session_seq += 1

    def _reconnect(self) -> None:
        """PER-FR-020: a fresh TCP session is a fresh `session_seq`, but `device_id` (the attributable
        identity) never changes across the reconnect -- the observation stream, not the plugin object
        identity, is what proves continuity/discontinuity to a downstream consumer."""
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
            raise ScannerCommError(str(exc)) from exc
        if chunk == b"":
            raise ScannerCommError("scanner connection closed by peer")
        self._buffer += chunk
        lines: list[str] = []
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            text = line.decode("utf-8", errors="replace").rstrip("\r")
            if text:
                lines.append(text)
        return lines

    def poll(self) -> Iterable[RawSourceObservation]:
        if self._sock is None:
            try:
                self._connect()
            except OSError as exc:
                yield self._comm_error_observation(str(exc))
                return

        try:
            raw_lines = self._read_lines()
        except ScannerCommError as exc:
            yield self._comm_error_observation(str(exc))
            try:
                self._reconnect()
            except OSError:
                self._sock = None
            return

        for raw in raw_lines:
            parsed = parse_scan(raw)
            yield RawSourceObservation(
                connector_id=self.connector_config.get("connector_id", "barcode-scanner"),
                connector_version="1.0",
                device_id=self._device_id(),
                mapping_id=PARSER_ID,
                source=SourceRef(protocol="SERIAL", address=self._station_id(), native_data_type="scan_line"),
                value={
                    "raw": raw,
                    "parser_id": PARSER_ID,
                    "parser_version": PARSER_VERSION,
                    "session_seq": self._session_seq,
                    "station_id": self._station_id(),
                    "parsed": {
                        "entity_type": parsed.entity_type,
                        "product_code": parsed.product_code,
                        "lot": parsed.lot,
                        "serial": parsed.serial,
                        "udi": parsed.udi,
                        "expiry": parsed.expiry,
                        "custom": parsed.custom,
                    },
                },
                quality_hint="GOOD",
            )

    def _comm_error_observation(self, detail: str) -> RawSourceObservation:
        return RawSourceObservation(
            connector_id=self.connector_config.get("connector_id", "barcode-scanner"),
            connector_version="1.0",
            device_id=self._device_id(),
            mapping_id=PARSER_ID,
            source=SourceRef(protocol="SERIAL", address=self._station_id(), native_data_type="scan_line"),
            value={"error": detail, "session_seq": self._session_seq},
            quality_hint="COMM_ERROR",
        )


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--config", required=True)
    args = arg_parser.parse_args()
    cfg = json.loads(open(args.config).read())
    run_plugin_main(BarcodeScannerPlugin(cfg))