"""Entrypoint the supervisor launches as a subprocess (`python -m plugins.mqtt --config <path>`)."""

import argparse
import json

from plugins.base import run_plugin_main
from plugins.mqtt.plugin import MqttPlugin

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(open(args.config).read())
    run_plugin_main(MqttPlugin(config))
