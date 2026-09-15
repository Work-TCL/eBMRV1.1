"""Generic file-import `ConnectorPlugin` -- Document 44 (SPEC-EDGE-002) DRV-FR-014's file-import half
("Support authenticated REST polling/webhook or **controlled file import** for instruments producing
reports"), for instruments that need nothing more than "does this JSON report contain field X" rather
than a bespoke schema.

This reuses `plugins.common.file_ingest.FileEvidenceWatcher` -- the same real, already-tested
(`test_tester.py`, `test_vision.py`) checksum/move-to-processed/never-lose-an-unconfirmed-file mechanism
Document 46's tester/vision plugins already build on for their own bespoke result schemas. This module is
the protocol-neutral, generically-configurable version DRV-FR-014 itself asks for at the driver layer,
distinct from those two business-specific consumers.

Config shape:

```yaml
protocol: FILE
drop_dir: /var/lib/edge/instruments/xyz/dropbox
mapping_id: INSTRUMENT_REPORT
value_field: reading          # required key expected in each dropped JSON file
unit_field: reading_unit       # optional
```
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from plugins.base import ConnectorPlugin
from plugins.common.file_ingest import FileEvidenceParseError, FileEvidenceWatcher
from runtime.contracts import RawSourceObservation, SourceRef


class FileImportPlugin(ConnectorPlugin):
    """`connector_config` keys: `connector_id`, `connector_version`, `device_id`, `drop_dir`,
    `mapping_id`, `value_field`, `unit_field` (optional)."""

    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._value_field = connector_config["value_field"]
        self._unit_field = connector_config.get("unit_field")
        self._mapping_id = connector_config.get("mapping_id", "FILE_IMPORT")
        self._watcher = FileEvidenceWatcher(Path(connector_config["drop_dir"]), self._parse)

    def _parse(self, raw_obj: dict) -> dict:
        if self._value_field not in raw_obj:
            raise FileEvidenceParseError(f"file report missing required field: {self._value_field!r}")
        parsed = {"value": raw_obj[self._value_field]}
        if self._unit_field:
            parsed["unit"] = raw_obj.get(self._unit_field)
        return parsed

    def poll(self) -> Iterable[RawSourceObservation]:
        connector_id = self.connector_config.get("connector_id", "file")
        connector_version = self.connector_config.get("connector_version", "1.0.0")
        device_id = self.connector_config.get("device_id", "unknown-file-source")

        for item in self._watcher.poll_new_files():
            if "parse_error" in item:
                yield RawSourceObservation(
                    connector_id=connector_id, connector_version=connector_version, device_id=device_id,
                    mapping_id=self._mapping_id,
                    source=SourceRef(protocol="FILE", address=item["file_name"], native_data_type="json"),
                    value={
                        "file_name": item["file_name"], "checksum_sha256": item["checksum_sha256"],
                        "adapter_version": item["adapter_version"], "error": item["parse_error"],
                    },
                    quality_hint="BAD",
                )
                continue

            parsed = item["parsed"]
            yield RawSourceObservation(
                connector_id=connector_id, connector_version=connector_version, device_id=device_id,
                mapping_id=self._mapping_id,
                source=SourceRef(protocol="FILE", address=item["file_name"], native_data_type="json"),
                value=parsed["value"],
                unit=parsed.get("unit"),
                quality_hint="GOOD",
            )


if __name__ == "__main__":
    from plugins.base import run_plugin_main

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--config", required=True)
    args = arg_parser.parse_args()
    cfg = json.loads(open(args.config).read())
    run_plugin_main(FileImportPlugin(cfg))
