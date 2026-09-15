"""Generic file-import adapter tests -- Document 44 DRV-FR-014's file-import half ("...or controlled file
import for instruments producing reports"). Real local filesystem drop directory, exactly like
`test_tester.py`/`test_vision.py` exercise the same underlying `FileEvidenceWatcher` for their own
bespoke schemas -- no physical instrument hardware is available in this environment, so a written-then-
discovered file is the realistic stand-in Document 46 itself names for this device class.
"""

from __future__ import annotations

import json
from pathlib import Path

from plugins.file.plugin import FileImportPlugin


def test_poll_picks_up_well_formed_report(tmp_path: Path):
    drop_dir = tmp_path / "dropbox"
    drop_dir.mkdir()
    (drop_dir / "reading1.json").write_text(json.dumps({"reading": 18.4, "reading_unit": "C"}))

    plugin = FileImportPlugin({
        "connector_id": "file-test", "connector_version": "1.0.0", "device_id": "dev-file",
        "drop_dir": str(drop_dir), "mapping_id": "ROOM_TEMP", "value_field": "reading", "unit_field": "reading_unit",
    })
    observations = list(plugin.poll())
    assert len(observations) == 1
    assert observations[0].value == 18.4
    assert observations[0].unit == "C"
    assert observations[0].quality_hint == "GOOD"
    assert observations[0].mapping_id == "ROOM_TEMP"
    assert observations[0].source.protocol == "FILE"
    # Processed file is moved out of the drop dir so it is not re-ingested on the next poll.
    assert not (drop_dir / "reading1.json").exists()
    assert (drop_dir / "processed" / "reading1.json").exists()


def test_poll_rejects_file_missing_required_field(tmp_path: Path):
    drop_dir = tmp_path / "dropbox"
    drop_dir.mkdir()
    (drop_dir / "bad.json").write_text(json.dumps({"unrelated_field": 1}))

    plugin = FileImportPlugin({
        "connector_id": "file-test", "connector_version": "1.0.0", "device_id": "dev-file",
        "drop_dir": str(drop_dir), "mapping_id": "ROOM_TEMP", "value_field": "reading",
    })
    observations = list(plugin.poll())
    assert len(observations) == 1
    assert observations[0].quality_hint == "BAD"
    assert observations[0].value["error"]
    assert (drop_dir / "rejected" / "bad.json").exists()


def test_poll_rejects_malformed_json(tmp_path: Path):
    drop_dir = tmp_path / "dropbox"
    drop_dir.mkdir()
    (drop_dir / "corrupt.json").write_text("not json at all")

    plugin = FileImportPlugin({
        "connector_id": "file-test", "connector_version": "1.0.0", "device_id": "dev-file",
        "drop_dir": str(drop_dir), "mapping_id": "ROOM_TEMP", "value_field": "reading",
    })
    observations = list(plugin.poll())
    assert len(observations) == 1
    assert observations[0].quality_hint == "BAD"
    assert (drop_dir / "rejected" / "corrupt.json").exists()


def test_poll_is_idempotent_across_restarts(tmp_path: Path):
    """A file already moved to processed/ is not re-ingested by a fresh plugin instance (simulating a
    connector restart) -- DRV-FR-014/Document 45's "never lose or duplicate" spirit for file evidence."""
    drop_dir = tmp_path / "dropbox"
    drop_dir.mkdir()
    (drop_dir / "reading1.json").write_text(json.dumps({"reading": 5.0}))

    plugin1 = FileImportPlugin({
        "connector_id": "file-test", "connector_version": "1.0.0", "device_id": "dev-file",
        "drop_dir": str(drop_dir), "mapping_id": "X", "value_field": "reading",
    })
    first_pass = list(plugin1.poll())
    assert len(first_pass) == 1

    plugin2 = FileImportPlugin({
        "connector_id": "file-test", "connector_version": "1.0.0", "device_id": "dev-file",
        "drop_dir": str(drop_dir), "mapping_id": "X", "value_field": "reading",
    })
    second_pass = list(plugin2.poll())
    assert second_pass == []
