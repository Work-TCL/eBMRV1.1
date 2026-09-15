"""Document 46 (SPEC-EDGE-004) functional tester plugin tests. No real tester hardware is available in
this environment; a real result file is written to a real temp directory and the plugin's real filesystem
polling/hashing/parsing runs against it -- only the physical test fixture producing the file is simulated.
"""

from __future__ import annotations

import json

from plugins.tester.tester import TesterPlugin


def _make_plugin(drop_dir) -> TesterPlugin:
    return TesterPlugin({"connector_id": "tester-01", "device_id": "TST-400", "drop_dir": str(drop_dir)})


def test_valid_result_file_is_ingested_with_checksum_and_forwarded_verbatim(tmp_path):
    result = {
        "test_id": "FT-0099", "unit_serial": "UNIT-555", "method": "IEC-60601-leakage",
        "program_version": "3.2.1", "result": "PASS", "values": {"leakage_ua": "1.2"},
    }
    (tmp_path / "ft0099.json").write_text(json.dumps(result))

    plugin = _make_plugin(tmp_path)
    observations = list(plugin.poll())
    assert len(observations) == 1
    obs = observations[0]
    assert obs.device_id == "TST-400"
    assert obs.value["test_id"] == "FT-0099"
    assert obs.value["unit_serial"] == "UNIT-555"
    assert obs.value["program_version"] == "3.2.1"
    assert obs.value["result"] == "PASS"  # forwarded verbatim -- plugin never evaluates it
    assert obs.value["values"] == {"leakage_ua": "1.2"}
    assert len(obs.value["checksum_sha256"]) == 64
    assert obs.quality_hint == "GOOD"


def test_processed_file_is_not_reingested_on_next_poll(tmp_path):
    result = {
        "test_id": "FT-0100", "unit_serial": "UNIT-556", "method": "m", "program_version": "1.0",
        "result": "PASS", "values": {},
    }
    (tmp_path / "ft0100.json").write_text(json.dumps(result))
    plugin = _make_plugin(tmp_path)

    first = list(plugin.poll())
    assert len(first) == 1
    second = list(plugin.poll())
    assert second == []
    assert (tmp_path / "processed" / "ft0100.json").exists()
    assert not (tmp_path / "ft0100.json").exists()


def test_malformed_result_file_is_reported_bad_and_moved_to_rejected_not_deleted(tmp_path):
    (tmp_path / "bad.json").write_text(json.dumps({"test_id": "FT-0101"}))  # missing required fields
    plugin = _make_plugin(tmp_path)

    observations = list(plugin.poll())
    assert len(observations) == 1
    assert observations[0].quality_hint == "BAD"
    assert "missing required field" in observations[0].value["error"]
    assert (tmp_path / "rejected" / "bad.json").exists()
    assert not (tmp_path / "bad.json").exists()


def test_tester_never_evaluates_or_overrides_the_reported_result(tmp_path):
    """Prohibitions section 13: "Never accept tester 'PASS' without expected unit/program/method
    validation" -- this plugin does not accept/reject anything; it forwards the field untouched and lets
    the domain/QC layer do the validation. A FAIL result is forwarded exactly like a PASS result."""
    result = {
        "test_id": "FT-0102", "unit_serial": "UNIT-557", "method": "m", "program_version": "1.0",
        "result": "FAIL", "values": {"reading": "9.9"},
    }
    (tmp_path / "ft0102.json").write_text(json.dumps(result))
    plugin = _make_plugin(tmp_path)

    observations = list(plugin.poll())
    assert observations[0].value["result"] == "FAIL"
    assert observations[0].quality_hint == "GOOD"  # acquisition succeeded; "FAIL" is not a plugin error