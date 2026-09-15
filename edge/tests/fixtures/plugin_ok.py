"""Test-only connector plugin: emits one synthetic observation per poll and never crashes on its own.
Used by test_supervisor.py to prove a healthy connector is unaffected by a sibling connector crashing.
"""

import argparse
import json

from plugins.base import ConnectorPlugin, run_plugin_main
from runtime.contracts import RawSourceObservation, SourceRef


class OkPlugin(ConnectorPlugin):
    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._n = 0

    def poll(self):
        self._n += 1
        yield RawSourceObservation(
            connector_id=self.connector_config.get("connector_id", "ok"),
            connector_version="1.0", device_id="dev-ok", mapping_id="map-ok",
            source=SourceRef(protocol="MODBUS_TCP", address="1"), value=self._n,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(open(args.config).read())
    config.setdefault("poll_interval_seconds", 0.05)
    run_plugin_main(OkPlugin(config), max_iterations=200)