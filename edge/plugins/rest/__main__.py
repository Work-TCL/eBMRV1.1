"""Entrypoint the supervisor launches as a subprocess (`python -m plugins.rest --config <path>`)."""

import argparse
import json

from plugins.base import run_plugin_main
from plugins.rest.plugin import RestPlugin

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(open(args.config).read())
    run_plugin_main(RestPlugin(config))
