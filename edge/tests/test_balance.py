"""Document 46 (SPEC-EDGE-004) balance plugin tests -- simulator-backed against a real `TCPLineServer`
(only the physical weighing cell is simulated; socket connect/recv/reconnect and decimal parsing all run
for real)."""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

from plugins.balance.balance import BalancePlugin
from plugins.base import PeripheralCommandNotSupportedError
from tests.support.tcp_line_server import TCPLineServer


def _drain(plugin, attempts: int = 40, delay: float = 0.05) -> list:
    observations: list = []
    for _ in range(attempts):
        observations.extend(list(plugin.poll()))
        if observations:
            break
        time.sleep(delay)
    return observations


def _wait_connected(server, attempts=40):
    for _ in range(attempts):
        if server.has_client():
            return
        time.sleep(0.05)
    raise AssertionError("balance plugin never connected to the simulator")


@pytest.fixture()
def balance_server():
    def handler(line: str):
        if line.strip() == "T":
            return "TARE_OK"
        return None

    server = TCPLineServer(handler=handler)
    yield server
    server.stop()


def _make_plugin(port: int) -> BalancePlugin:
    return BalancePlugin({
        "connector_id": "balance-01", "device_id": "BAL-200", "calibration_ref": "CAL-2026-004",
        "host": "127.0.0.1", "port": port,
    })


def test_stable_reading_carries_decimal_strings_unit_and_calibration_ref(balance_server):
    plugin = _make_plugin(balance_server.port)
    list(plugin.poll())
    _wait_connected(balance_server)
    balance_server.push_line("ST,+00123.450,+00000.000,+00123.450,g")

    observations = _drain(plugin)
    obs = observations[0]
    assert obs.device_id == "BAL-200"
    assert obs.unit == "g"
    assert obs.value["stable"] is True
    assert obs.value["gross"] == "123.450"
    assert obs.value["tare"] == "0.000"
    assert obs.value["net"] == "123.450"
    assert obs.value["calibration_ref"] == "CAL-2026-004"
    assert obs.quality_hint == "GOOD"
    # DATA-FR-019: exact decimal representation -- Decimal round-trips without binary-float drift.
    assert Decimal(obs.value["net"]) == Decimal("123.450")


def test_unstable_reading_is_forwarded_but_never_marked_stable(balance_server):
    """PER-FR-008: "UI cannot accept transient value as stable" -- an unstable line must still be
    forwarded (so a live-weight display has something to show) but must never be labeled stable."""
    plugin = _make_plugin(balance_server.port)
    list(plugin.poll())
    _wait_connected(balance_server)
    balance_server.push_line("US,+00050.010,+00000.000,+00050.010,g")

    observations = _drain(plugin)
    obs = observations[0]
    assert obs.value["stable"] is False
    assert obs.value["device_status"] == "UNSTABLE"
    assert obs.quality_hint == "UNCERTAIN"


def test_malformed_reading_line_is_quarantined_as_bad_quality_not_dropped(balance_server):
    plugin = _make_plugin(balance_server.port)
    list(plugin.poll())
    _wait_connected(balance_server)
    balance_server.push_line("GARBAGE-NOT-A-READING")

    observations = _drain(plugin)
    obs = observations[0]
    assert obs.quality_hint == "BAD"
    assert obs.value["raw"] == "GARBAGE-NOT-A-READING"


def test_send_command_tare_writes_device_instruction_and_returns_ack(balance_server):
    """PER-FR-009: recordTare() -- the plugin sends the balance's own tare instruction over the
    connection it already owns and returns the device's acknowledgement."""
    plugin = _make_plugin(balance_server.port)
    result = plugin.send_command({"action": "tare"})
    assert result.value["action"] == "tare"
    assert "TARE_OK" in result.value["ack_lines"]
    assert result.quality_hint == "GOOD"


def test_send_command_rejects_unsupported_action(balance_server):
    plugin = _make_plugin(balance_server.port)
    with pytest.raises(PeripheralCommandNotSupportedError):
        plugin.send_command({"action": "zero_calibrate"})


def test_reconnect_after_drop_preserves_device_identity(balance_server):
    plugin = _make_plugin(balance_server.port)
    list(plugin.poll())
    _wait_connected(balance_server)
    balance_server.push_line("ST,+00010.000,+00000.000,+00010.000,g")
    first = _drain(plugin)
    assert first[0].value["session_seq"] == 1

    balance_server.drop_client_connection()
    comm_error = _drain(plugin)
    assert comm_error[0].quality_hint == "COMM_ERROR"
    assert comm_error[0].device_id == "BAL-200"

    _wait_connected(balance_server)
    balance_server.push_line("ST,+00020.000,+00000.000,+00020.000,g")
    second = _drain(plugin)
    assert second[0].value["session_seq"] == 2