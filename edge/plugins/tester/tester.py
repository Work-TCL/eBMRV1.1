"""Functional/device tester connector plugin -- Document 46 (SPEC-EDGE-004) PER-FR-014 ("Functional/
device testers return test ID, unit/serial, method/program version, values, result, raw evidence and
tester identity") and section 9 ("Tester/Vision Boundary": "Tester/vision system output is external
evidence. eDHR/QC module determines whether the result fulfills an acceptance requirement.").

This plugin is purely inbound (`poll()` only) -- Document 46's own function catalogue lists
`ingestTesterResult()`'s caller/trigger as "Tester adapter", i.e. the tester reports results as it
produces them, not on gateway request; this matches Document 43's baseline "file/SFTP/REST integration
for instruments that export evidence rather than live values." It uses `plugins.common.file_ingest.
FileEvidenceWatcher` against a drop directory a real tester would be configured to export result files
into -- no real tester hardware is available in this environment, so writing a well-formed/malformed
result file into that directory in a test is the direct real exercise of this ingestion path (only the
physical test fixture is simulated).

Prohibitions section 13: "Never accept tester 'PASS' without expected unit/program/method validation" --
this plugin does not decide acceptance either way; it forwards the tester's own reported `result` field
completely unaltered alongside `program_version`/`unit_serial`, and it is the domain/QC layer (not built
here) that is required to check those against what was expected before treating a "PASS" as meaningful.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from plugins.base import ConnectorPlugin
from plugins.common.file_ingest import ADAPTER_VERSION, FileEvidenceParseError, FileEvidenceWatcher
from runtime.contracts import RawSourceObservation, SourceRef

MAPPING_ID = "doc46-tester-result-file-v1"

_REQUIRED_FIELDS = ("test_id", "unit_serial", "method", "program_version", "result", "values")


def _parse_tester_payload(raw_obj: dict) -> dict:
    missing = [f for f in _REQUIRED_FIELDS if f not in raw_obj]
    if missing:
        raise FileEvidenceParseError(f"tester result missing required field(s): {missing}")
    return {field: raw_obj[field] for field in _REQUIRED_FIELDS}


class TesterPlugin(ConnectorPlugin):
    """`connector_config` keys: `connector_id`, `device_id` (tester identity), `drop_dir`."""

    __test__ = False  # not a pytest test class -- name coincidentally starts with "Tester"

    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._watcher = FileEvidenceWatcher(Path(connector_config["drop_dir"]), _parse_tester_payload)

    def _device_id(self) -> str:
        return self.connector_config.get("device_id", "unknown-tester")

    def poll(self) -> Iterable[RawSourceObservation]:
        for item in self._watcher.poll_new_files():
            if "parse_error" in item:
                yield RawSourceObservation(
                    connector_id=self.connector_config.get("connector_id", "tester"),
                    connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
                    source=SourceRef(protocol="FILE", address=item["file_name"], native_data_type="tester_result_json"),
                    value={
                        "file_name": item["file_name"], "checksum_sha256": item["checksum_sha256"],
                        "adapter_version": item["adapter_version"], "error": item["parse_error"],
                    },
                    quality_hint="BAD",
                )
                continue

            parsed = item["parsed"]
            yield RawSourceObservation(
                connector_id=self.connector_config.get("connector_id", "tester"),
                connector_version="1.0", device_id=self._device_id(), mapping_id=MAPPING_ID,
                source=SourceRef(protocol="FILE", address=item["file_name"], native_data_type="tester_result_json"),
                value={
                    "file_name": item["file_name"],
                    "checksum_sha256": item["checksum_sha256"],
                    "adapter_version": item["adapter_version"],
                    "tester_identity": self._device_id(),
                    "test_id": parsed["test_id"],
                    "unit_serial": parsed["unit_serial"],
                    "method": parsed["method"],
                    "program_version": parsed["program_version"],
                    "result": parsed["result"],  # forwarded verbatim -- never evaluated/overridden here
                    "values": parsed["values"],
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
    run_plugin_main(TesterPlugin(cfg))