"""Test-only connector plugin: reports its own environment/cwd back as the observation payload, so the
supervisor test can verify the sandbox boundary from the parent side (EDGE-FR-008).
"""

import argparse
import json
import os

from plugins.base import ConnectorPlugin, run_plugin_main
from runtime.contracts import RawSourceObservation, SourceRef


class IntrospectPlugin(ConnectorPlugin):
    def poll(self):
        yield RawSourceObservation(
            connector_id="introspect", connector_version="1.0", device_id="dev", mapping_id="map",
            source=SourceRef(protocol="MODBUS_TCP", address="1"),
            value={"env_keys": sorted(os.environ.keys()), "cwd": os.getcwd()},
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(open(args.config).read())
    run_plugin_main(IntrospectPlugin(config), max_iterations=1)
