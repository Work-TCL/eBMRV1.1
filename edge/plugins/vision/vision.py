"""Vision inspection system connector plugin -- Document 46 (SPEC-EDGE-004) PER-FR-015 ("Capture
inspected unit/lot, recipe/model version, defect classification, image/evidence ref and system confidence
if used") and PER-FR-016 ("Automated pass/fail only if validated approved model/rule; otherwise advisory
result requiring operator/QA decision").

Same file-drop transport as `plugins.tester` (Document 46 groups vision under the same "file-producing
instrument" baseline, PER-FR-017) via `plugins.common.file_ingest.FileEvidenceWatcher` -- no real camera/
vision system is available in this build environment, so a written-then-discovered result file is the
direct real exercise of the ingestion path.

PER-FR-016 / AG-14 (AI is advisory only): this plugin has no way to know whether a given `model_version`
is a "validated approved model" -- that is a model-registry/approval decision that belongs to the domain/
QA layer, not to a peripheral connector running in an EDGE-FR-008 sandbox with no access to that registry.
So `ai_decision_status` is unconditionally hard-coded to `"ADVISORY"` on every single observation this
plugin ever emits, regardless of what the vision system itself may have labeled its own output (a vision
system reporting `"final_result": "PASS"` in its export file does not become an authoritative disposition
here -- that field is still forwarded, verbatim and unevaluated, exactly like `plugins.tester`, but always
alongside the fixed advisory marker). This is a hand-coded invariant, not a per-file heuristic, precisely
because AG-15 forbids this plugin from guessing when a model would count as "validated approved."
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from plugins.base import ConnectorPlugin
from plugins.common.file_ingest import FileEvidenceParseError, FileEvidenceWatcher
from runtime.contracts import RawSourceObservation, SourceRef

MAPPING_ID = "doc46-vision-result-file-v1"

_REQUIRED_FIELDS = ("unit_id", "lot", "model_version", "defects", "image_ref")


def _parse_vision_payload(raw_obj: dict) -> dict:
    missing = [f for f in _REQUIRED_FIELDS if f not in raw_obj]
    if missing:
        raise FileEvidenceParseError(f"vision result missing required field(s): {missing}")
    out = {field: raw_obj[field] for field in _REQUIRED_FIELDS}
    out["confidence"] = raw_obj.get("confidence")
    out["final_result"] = raw_obj.get("final_result")  # forwarded verbatim, never treated as authoritative
    return out


class VisionPlugin(ConnectorPlugin):
    """`connector_config` keys: `connector_id`, `device_id` (vision system identity), `drop_dir`."""

    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._watcher = FileEvidenceWatcher(Path(connector_config["drop_dir"]), _parse_vision_payload)

    def _device_id(self) -> str:
        return self.connector_config.get("device_id", "unknown-vision")

    def poll(self) -> Iterable[RawSourceObservation]:
        for item in self._watcher.poll_new_files():
            if "parse_error" in item:
                yield RawSourceObservation(
                    connector_id=self.connector_config.get("connector_id", "vision"),
                    connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
                    source=SourceRef(protocol="FILE", address=item["file_name"], native_data_type="vision_result_json"),
                    value={
                        "file_name": item["file_name"], "checksum_sha256": item["checksum_sha256"],
                        "adapter_version": item["adapter_version"], "error": item["parse_error"],
                    },
                    quality_hint="BAD",
                )
                continue

            parsed = item["parsed"]
            yield RawSourceObservation(
                connector_id=self.connector_config.get("connector_id", "vision"),
                connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
                source=SourceRef(protocol="FILE", address=item["file_name"], native_data_type="vision_result_json"),
                value={
                    "file_name": item["file_name"],
                    "checksum_sha256": item["checksum_sha256"],
                    "adapter_version": item["adapter_version"],
                    "vision_system_identity": self._device_id(),
                    "unit_id": parsed["unit_id"],
                    "lot": parsed["lot"],
                    "model_version": parsed["model_version"],
                    "defects": parsed["defects"],
                    "image_ref": parsed["image_ref"],
                    "confidence": parsed["confidence"],
                    "reported_final_result": parsed["final_result"],
                    "ai_decision_status": "ADVISORY",  # fixed invariant -- see module docstring
                    "raw_evidence_ref": item["file_name"],
                },
                quality_hint="GOOD",
            )


if __name__ == "__main__":
    from plugins.base import run_plugin_main

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--config", required=True)
    args = arg_parser.parse_args()
    cfg = json.loads(open(args.config).read())
    run_plugin_main(VisionPlugin(cfg))
