"""Controlled label printer connector plugin -- Document 46 (SPEC-EDGE-004) section 8 ("Printing
Boundary"): "The print service does not decide product correctness. Packaging/Dispensing domains create
the approved print request. Adapter only renders/sends exact approved payload." This plugin is that
adapter and nothing more: it never receives a template id or variable-data map, only bytes a domain
service already canonicalized and hashed (`createPrintJob()`'s "Canonicalizes variables; hashes request"
happens upstream, not here) -- Prohibitions section 13: "Never allow printer adapter to choose label
template."

PER-FR-011 (label printer): `send_command({"action": "print", ...})` sends the exact payload it is given,
tagged with this connector's own `device_id` (printer identity) and the caller-supplied `print_job_id`.
PER-FR-012 (print acknowledgement): `poll()` queries outstanding job ids for status and forwards exactly
what the printer reports. If the printer does not answer (no status support, or currently unreachable),
the observation's status is `UNKNOWN`, never `COMPLETED` -- Document 46's own acceptance intent: "lack of
status does not fabricate successful physical application."
PER-FR-013 (reprint): this adapter has no notion of "reprint" at all -- `send_command()` treats every
call identically regardless of any `reprint_of`/`reason` metadata riding along in the command dict (it is
accepted and echoed back for evidence purposes but never inspected/branched on). The reprint *policy*
(new controlled print action, reason required, counter incremented) is Document 46's domain-side
responsibility precisely because the adapter must not be trusted to enforce it -- section 8's boundary.

Transport: a TCP line protocol against `edge/tests/fixtures/printer_sim.py`, a real local TCP server
standing in for a real network label printer's raw socket protocol (e.g. Zebra-style port 9100 printing
plus a status query) -- no physical printer is available in this build environment.
"""

from __future__ import annotations

import argparse
import base64
import json
import socket
from typing import Iterable

from plugins.base import ConnectorPlugin, PeripheralCommandNotSupportedError, run_plugin_main
from runtime.contracts import RawSourceObservation, SourceRef

MAPPING_ID = "doc46-printer-status-v1"
_RECV_BUFFER = 4096


class PrinterCommError(Exception):
    pass


class PrinterPlugin(ConnectorPlugin):
    """`connector_config` keys: `connector_id`, `device_id` (printer identity), `host`, `port`."""

    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._sock: socket.socket | None = None
        self._pending_job_ids: set[str] = set()

    def _device_id(self) -> str:
        return self.connector_config.get("device_id", "unknown-printer")

    def _ensure_connected(self) -> None:
        if self._sock is not None:
            return
        host = self.connector_config["host"]
        port = int(self.connector_config["port"])
        sock = socket.create_connection((host, port), timeout=2.0)
        sock.settimeout(2.0)
        self._sock = sock

    def _send_line(self, line: str) -> str:
        assert self._sock is not None
        self._sock.sendall((line + "\n").encode("utf-8"))
        data = b""
        while not data.endswith(b"\n"):
            chunk = self._sock.recv(_RECV_BUFFER)
            if chunk == b"":
                raise PrinterCommError("printer connection closed by peer")
            data += chunk
        return data.decode("utf-8", errors="replace").strip()

    def send_command(self, command: dict) -> RawSourceObservation:
        action = command.get("action")
        if action != "print":
            raise PeripheralCommandNotSupportedError(f"PrinterPlugin does not support command action {action!r}")
        job_id = command["print_job_id"]
        payload: bytes = command["payload"] if isinstance(command["payload"], bytes) else str(command["payload"]).encode("utf-8")
        encoded = base64.b64encode(payload).decode("ascii")
        # `command` may carry `reprint_of`/`reason` -- deliberately not read past this point (see module
        # docstring): only echoed into the observation's `raw` field as received-evidence, never branched on.
        try:
            self._ensure_connected()
            reply = self._send_line(f"PRINT {job_id} {encoded}")
        except (OSError, PrinterCommError) as exc:
            self._sock = None
            return RawSourceObservation(
                connector_id=self.connector_config.get("connector_id", "printer"),
                connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
                source=SourceRef(protocol="SERIAL", address=self._device_id(), native_data_type="print_ack"),
                value={"print_job_id": job_id, "status": "UNKNOWN", "error": str(exc), "command_echo": command.get("reprint_of")},
                quality_hint="COMM_ERROR",
            )

        parts = reply.split()
        ack_word = parts[0] if parts else ""
        if ack_word == "ACK":
            status = "ACCEPTED"
            self._pending_job_ids.add(job_id)
        elif ack_word == "NACK":
            status = "REJECTED"
        else:
            status = "UNKNOWN"
        return RawSourceObservation(
            connector_id=self.connector_config.get("connector_id", "printer"),
            connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
            source=SourceRef(protocol="SERIAL", address=self._device_id(), native_data_type="print_ack"),
            value={"print_job_id": job_id, "status": status, "raw_reply": reply, "reprint_of": command.get("reprint_of")},
            quality_hint="GOOD",
        )

    def poll(self) -> Iterable[RawSourceObservation]:
        """PER-FR-012: only ever reports what the printer actually said. A job whose status query fails
        stays `UNKNOWN` and stays pending (never assumed COMPLETED) until the printer answers or is
        removed by an operator/domain-side timeout policy this plugin does not implement itself."""
        for job_id in list(self._pending_job_ids):
            try:
                self._ensure_connected()
                reply = self._send_line(f"STATUS {job_id}")
            except (OSError, PrinterCommError) as exc:
                self._sock = None
                yield RawSourceObservation(
                    connector_id=self.connector_config.get("connector_id", "printer"),
                    connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
                    source=SourceRef(protocol="SERIAL", address=self._device_id(), native_data_type="print_status"),
                    value={"print_job_id": job_id, "status": "UNKNOWN", "error": str(exc)},
                    quality_hint="COMM_ERROR",
                )
                continue

            parts = reply.split()
            state = parts[2] if len(parts) >= 3 and parts[0] == "STATUS" else "UNKNOWN"
            yield RawSourceObservation(
                connector_id=self.connector_config.get("connector_id", "printer"),
                connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
                source=SourceRef(protocol="SERIAL", address=self._device_id(), native_data_type="print_status"),
                value={"print_job_id": job_id, "status": state, "raw_reply": reply},
                quality_hint="GOOD",
            )
            if state in ("COMPLETED", "ERROR"):
                self._pending_job_ids.discard(job_id)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--config", required=True)
    args = arg_parser.parse_args()
    cfg = json.loads(open(args.config).read())
    run_plugin_main(PrinterPlugin(cfg))