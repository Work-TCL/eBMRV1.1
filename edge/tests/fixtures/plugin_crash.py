"""Test-only connector plugin: emits one observation then hard-exits non-zero, simulating a driver
crash. Used by test_supervisor.py -- EDGE-FR-007 crash isolation.
"""

import argparse
import json
import os
import sys

from runtime.contracts import RawSourceObservation, SourceRef

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    json.loads(open(args.config).read())

    observation = RawSourceObservation(
        connector_id="crashy", connector_version="1.0", device_id="dev-crash", mapping_id="map-crash",
        source=SourceRef(protocol="MODBUS_TCP", address="1"), value=1,
    )
    sys.stdout.write(observation.model_dump_json() + "\n")
    sys.stdout.flush()
    os._exit(1)