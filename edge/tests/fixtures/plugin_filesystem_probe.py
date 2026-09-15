"""Test-only connector plugin: attempts to read an absolute path outside its own scratch directory and
reports whether the read succeeded. Used by test_plugin_sandbox.py to measure the *actual* enforcement
boundary of EDGE-FR-008, honestly, rather than assuming the OS-process isolation implies filesystem
denial it does not implement (see the test's own docstring and SG-187's addendum).
"""

import argparse
import json
import sys

from plugins.base import ConnectorPlugin, run_plugin_main
from runtime.contracts import RawSourceObservation, SourceRef


class FilesystemProbePlugin(ConnectorPlugin):
    def poll(self):
        target = self.connector_config["probe_path"]
        try:
            with open(target) as fh:
                content_len = len(fh.read())
            outcome = {"read_succeeded": True, "bytes_read": content_len}
        except OSError as exc:
            outcome = {"read_succeeded": False, "error": str(exc)}
        yield RawSourceObservation(
            connector_id="fs-probe", connector_version="1.0", device_id="dev", mapping_id="map",
            source=SourceRef(protocol="MODBUS_TCP", address="1"), value=outcome,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(open(args.config).read())
    run_plugin_main(FilesystemProbePlugin(config), max_iterations=1)