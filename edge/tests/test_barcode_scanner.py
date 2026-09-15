"""Document 46 (SPEC-EDGE-004) barcode scanner plugin tests.

`parse_scan()` tests are pure unit tests (no I/O). `BarcodeScannerPlugin` tests are simulator-backed: they
run a real `TCPLineServer` (tests/support/tcp_line_server.py) on localhost and have the plugin connect to
it over a real socket exactly as it would a real serial/TCP scanner -- only the physical scanner hardware
is simulated; the socket connect/recv/reconnect and line-framing code in `scanner.py` all run for real.
"""

from __future__ import annotations

import time

import pytest

from plugins.barcode.parser import PARSER_ID, PARSER_VERSION, parse_scan
from plugins.barcode.scanner import BarcodeScannerPlugin
from tests.support.tcp_line_server import TCPLineServer


def _drain(plugin, attempts: int = 40, delay: float = 0.05) -> list:
    observations: list = []
    for _ in range(attempts):
        observations.extend(list(plugin.poll()))
        if observations:
            break
        time.sleep(delay)
    return observations


# ---------------------------------------------------------------------------
# parser.py -- pure unit tests (PER-FR-004: deterministic, versioned, GS1/UDI/custom)
# ---------------------------------------------------------------------------

def test_parse_gs1_element_string_extracts_gtin_lot_expiry_serial():
    raw = (
        "01" + "00360002914521"  # AI(01) GTIN, fixed 14 digits
        + "17" + "260228"  # AI(17) expiry, fixed 6 digits
        + "10" + "ABC123"  # AI(10) lot, variable-length, FNC1-terminated
        + "\x1d"
        + "21" + "SN000777"  # AI(21) serial, variable-length (end of string)
    )
    parsed = parse_scan(raw)
    assert parsed.entity_type == "gs1_element_string"
    assert parsed.product_code == "00360002914521"
    assert parsed.expiry == "260228"
    assert parsed.lot == "ABC123"
    assert parsed.serial == "SN000777"
    assert parsed.udi == "(01)00360002914521"


def test_parse_scan_is_deterministic_for_same_raw_and_version():
    raw = "0100360002914521172602281234"
    assert parse_scan(raw) == parse_scan(raw)


def test_parse_aim_symbology_prefixed_gs1_barcode():
    raw = "]C1" + "0100360002914521"
    parsed = parse_scan(raw)
    assert parsed.entity_type == "gs1_element_string"
    assert parsed.product_code == "00360002914521"


def test_parse_custom_internal_label_format():
    parsed = parse_scan("PRODUCT:PN-42|LOT:L9|SN:S7|SITE:BUF01")
    assert parsed.entity_type == "custom_internal"
    assert parsed.product_code == "PN-42"
    assert parsed.lot == "L9"
    assert parsed.serial == "S7"
    assert parsed.custom == {"site": "BUF01"}


def test_parse_unstructured_text_is_preserved_verbatim_not_dropped():
    parsed = parse_scan("totally-unrecognized-scan-text")
    assert parsed.entity_type == "custom_unstructured"
    assert parsed.custom["raw"] == "totally-unrecognized-scan-text"


# ---------------------------------------------------------------------------
# BarcodeScannerPlugin -- simulator-backed
# ---------------------------------------------------------------------------

@pytest.fixture()
def scanner_server():
    server = TCPLineServer()
    yield server
    server.stop()


def _wait_connected(server, attempts=40):
    for _ in range(attempts):
        if server.has_client():
            return
        time.sleep(0.05)
    raise AssertionError("scanner plugin never connected to the simulator")


def test_scan_observation_carries_raw_parsed_and_source_identity(scanner_server):
    plugin = BarcodeScannerPlugin({
        "connector_id": "scanner-01", "device_id": "SCN-100", "station_id": "DISP-1",
        "host": "127.0.0.1", "port": scanner_server.port,
    })
    list(plugin.poll())  # triggers connect
    _wait_connected(scanner_server)
    scanner_server.push_line("PRODUCT:PN-1|LOT:L1|SN:S1")

    observations = _drain(plugin)
    assert len(observations) == 1
    obs = observations[0]
    assert obs.device_id == "SCN-100"
    assert obs.mapping_id == PARSER_ID
    assert obs.value["raw"] == "PRODUCT:PN-1|LOT:L1|SN:S1"
    assert obs.value["parser_version"] == PARSER_VERSION
    assert obs.value["station_id"] == "DISP-1"
    assert obs.value["parsed"]["product_code"] == "PN-1"
    assert obs.quality_hint == "GOOD"


def test_duplicate_scan_is_never_suppressed(scanner_server):
    """PER-FR-006: "Debounce/duplicate handling does not suppress legitimate repeated actions" -- two
    identical raw scans must both be forwarded, unmodified, as two separate observations."""
    plugin = BarcodeScannerPlugin({
        "connector_id": "scanner-01", "device_id": "SCN-100", "station_id": "DISP-1",
        "host": "127.0.0.1", "port": scanner_server.port,
    })
    list(plugin.poll())
    _wait_connected(scanner_server)
    scanner_server.push_line("PRODUCT:PN-1|LOT:L1|SN:S1")
    scanner_server.push_line("PRODUCT:PN-1|LOT:L1|SN:S1")

    observations = _drain(plugin)
    assert len(observations) == 2
    assert observations[0].value["raw"] == observations[1].value["raw"]


def test_reconnect_preserves_device_identity_and_bumps_session(scanner_server):
    """PER-FR-020: hot-plug/reconnect preserves device identity and generates a session boundary."""
    plugin = BarcodeScannerPlugin({
        "connector_id": "scanner-01", "device_id": "SCN-100", "station_id": "DISP-1",
        "host": "127.0.0.1", "port": scanner_server.port,
    })
    list(plugin.poll())
    _wait_connected(scanner_server)
    scanner_server.push_line("PRODUCT:PN-1|LOT:L1|SN:S1")
    first = _drain(plugin)
    assert first[0].value["session_seq"] == 1

    scanner_server.drop_client_connection()
    comm_error_obs = _drain(plugin)
    assert comm_error_obs[0].quality_hint == "COMM_ERROR"
    assert comm_error_obs[0].device_id == "SCN-100"  # identity preserved across the drop

    _wait_connected(scanner_server)
    scanner_server.push_line("PRODUCT:PN-2|LOT:L2|SN:S2")
    second = _drain(plugin)
    assert second[0].value["session_seq"] == 2
    assert second[0].device_id == "SCN-100"