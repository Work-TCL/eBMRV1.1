"""Document 46 (SPEC-EDGE-004) vision inspection plugin tests. No real camera/vision system is available
in this environment; a real result file is written to a real temp directory and the plugin's real
filesystem polling/hashing/parsing runs against it -- only the physical inspection is simulated."""

from __future__ import annotations

import json

from plugins.vision.vision import VisionPlugin


def _make_plugin(drop_dir) -> VisionPlugin:
    return VisionPlugin({"connector_id": "vision-01", "device_id": "VIS-500", "drop_dir": str(drop_dir)})


def test_valid_inspection_result_is_ingested_with_evidence_refs(tmp_path):
    result = {
        "unit_id": "UNIT-900", "lot": "L-42", "model_version": "defect-net-v3.1",
        "defects": ["scratch", "misalignment"], "image_ref": "obj://evidence/img-900.png",
        "confidence": 0.87, "final_result": "PASS",
    }
    (tmp_path / "insp900.json").write_text(json.dumps(result))

    plugin = _make_plugin(tmp_path)
    observations = list(plugin.poll())
    assert len(observations) == 1
    obs = observations[0]
    assert obs.value["unit_id"] == "UNIT-900"
    assert obs.value["lot"] == "L-42"
    assert obs.value["model_version"] == "defect-net-v3.1"
    assert obs.value["defects"] == ["scratch", "misalignment"]
    assert obs.value["image_ref"] == "obj://evidence/img-900.png"
    assert obs.value["confidence"] == 0.87
    assert obs.value["reported_final_result"] == "PASS"


def test_ai_decision_status_is_always_advisory_even_when_system_reports_pass():
    """PER-FR-016 / AG-14: automated pass/fail is only authoritative behind a validated approved model
    this plugin has no way to check -- so every observation is unconditionally marked ADVISORY regardless
    of what the vision system itself reported."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        drop_dir = Path(d)
        (drop_dir / "insp901.json").write_text(json.dumps({
            "unit_id": "UNIT-901", "lot": "L-43", "model_version": "v9", "defects": [],
            "image_ref": "obj://x", "final_result": "PASS",
        }))
        plugin = _make_plugin(drop_dir)
        obs = list(plugin.poll())[0]
        assert obs.value["ai_decision_status"] == "ADVISORY"
        assert obs.value["reported_final_result"] == "PASS"  # forwarded, but never authoritative


def test_malformed_inspection_file_is_rejected_not_deleted(tmp_path):
    (tmp_path / "bad.json").write_text(json.dumps({"unit_id": "UNIT-902"}))  # missing required fields
    plugin = _make_plugin(tmp_path)

    observations = list(plugin.poll())
    assert observations[0].quality_hint == "BAD"
    assert (tmp_path / "rejected" / "bad.json").exists()
