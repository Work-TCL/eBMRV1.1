"""Document 46 (SPEC-EDGE-004) printer plugin tests -- simulator-backed against a real `TCPLineServer`
standing in for a network label printer's raw socket protocol (e.g. Zebra-style port 9100 print + status
query); only the physical printer/label media is simulated."""

from __future__ import annotations

import base64

import pytest

from plugins.base import PeripheralCommandNotSupportedError
from plugins.printer.printer import PrinterPlugin
from tests.support.tcp_line_server import TCPLineServer


class _FakePrinterProtocol:
    """Mimics a real network printer: accepts PRINT, replies ACK/NACK; accepts STATUS, replies with the
    job's currently configured state. `job_states` is mutated by the test to drive status transitions."""

    def __init__(self) -> None:
        self.job_states: dict[str, str] = {}
        self.received_payloads: dict[str, bytes] = {}
        self.reject_job_ids: set[str] = set()

    def handle(self, line: str):
        parts = line.split(" ", 2)
        if parts[0] == "PRINT":
            job_id, encoded = parts[1], parts[2]
            if job_id in self.reject_job_ids:
                return f"NACK {job_id} OUT_OF_LABELS"
            self.received_payloads[job_id] = base64.b64decode(encoded)
            self.job_states.setdefault(job_id, "QUEUED")
            return f"ACK {job_id}"
        if parts[0] == "STATUS":
            job_id = parts[1]
            state = self.job_states.get(job_id, "UNKNOWN")
            return f"STATUS {job_id} {state}"
        return None


@pytest.fixture()
def printer_protocol():
    return _FakePrinterProtocol()


@pytest.fixture()
def printer_server(printer_protocol):
    server = TCPLineServer(handler=printer_protocol.handle)
    yield server
    server.stop()


def _make_plugin(port: int) -> PrinterPlugin:
    return PrinterPlugin({"connector_id": "printer-01", "device_id": "PRN-300", "host": "127.0.0.1", "port": port})


def test_send_command_print_relays_exact_payload_bytes(printer_server, printer_protocol):
    """Document 46 section 8: "Adapter only renders/sends exact approved payload." -- the plugin must not
    alter the bytes it was given."""
    plugin = _make_plugin(printer_server.port)
    payload = b"^XA^FDLOT:L1 SN:S1^FS^XZ"  # a stand-in for an already-rendered ZPL label
    result = plugin.send_command({"action": "print", "print_job_id": "JOB-1", "payload": payload})
    assert result.value["status"] == "ACCEPTED"
    assert result.device_id == "PRN-300"
    assert printer_protocol.received_payloads["JOB-1"] == payload


def test_send_command_rejects_unsupported_action(printer_server):
    plugin = _make_plugin(printer_server.port)
    with pytest.raises(PeripheralCommandNotSupportedError):
        plugin.send_command({"action": "cancel"})


def test_printer_rejection_is_reported_not_fabricated_success(printer_server, printer_protocol):
    printer_protocol.reject_job_ids.add("JOB-2")
    plugin = _make_plugin(printer_server.port)
    result = plugin.send_command({"action": "print", "print_job_id": "JOB-2", "payload": b"x"})
    assert result.value["status"] == "REJECTED"


def test_reprint_command_is_not_special_cased_by_the_adapter(printer_server, printer_protocol):
    """PER-FR-013: reprint is a *domain* controlled action (new print job, reason, counter); this adapter
    must treat it identically to any other print -- it only echoes `reprint_of` as received evidence."""
    plugin = _make_plugin(printer_server.port)
    normal = plugin.send_command({"action": "print", "print_job_id": "JOB-3", "payload": b"label-bytes"})
    reprint = plugin.send_command({
        "action": "print", "print_job_id": "JOB-4", "payload": b"label-bytes", "reprint_of": "JOB-3", "reason": "smudged label",
    })
    assert normal.value["status"] == reprint.value["status"] == "ACCEPTED"
    assert reprint.value["reprint_of"] == "JOB-3"
    assert printer_protocol.received_payloads["JOB-3"] == printer_protocol.received_payloads["JOB-4"] == b"label-bytes"


def test_poll_reports_job_status_and_stops_polling_once_terminal(printer_server, printer_protocol):
    """PER-FR-012: capture job/print status via polling; lack of status must never be reported as
    COMPLETED -- only what the printer itself says."""
    plugin = _make_plugin(printer_server.port)
    plugin.send_command({"action": "print", "print_job_id": "JOB-5", "payload": b"x"})

    printer_protocol.job_states["JOB-5"] = "PRINTING"
    mid = list(plugin.poll())
    assert mid[0].value["status"] == "PRINTING"

    printer_protocol.job_states["JOB-5"] = "COMPLETED"
    done = list(plugin.poll())
    assert done[0].value["status"] == "COMPLETED"

    # Job is no longer pending -- a further poll yields nothing for it, proving the adapter does not
    # keep re-asserting a stale terminal status.
    after = list(plugin.poll())
    assert after == []


def test_poll_never_fabricates_completed_status_on_comm_failure(printer_server):
    plugin = _make_plugin(printer_server.port)
    plugin.send_command({"action": "print", "print_job_id": "JOB-6", "payload": b"x"})
    printer_server.stop()  # simulator goes away entirely -- printer unreachable for status query

    observations = list(plugin.poll())
    assert observations[0].value["status"] == "UNKNOWN"
    assert observations[0].quality_hint == "COMM_ERROR"