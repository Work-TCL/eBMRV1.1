"""Tests for the `ConnectorPlugin.send_command()` extension point added for Document 46 (SPEC-EDGE-004).
See `plugins/base.py`'s docstring for why this exists and why it is deliberately not Document 43's
EDGE-FR-023 command channel."""

from __future__ import annotations

import pytest

from plugins.base import ConnectorPlugin, PeripheralCommandNotSupportedError
from runtime.contracts import RawSourceObservation, SourceRef


class _PollOnlyPlugin(ConnectorPlugin):
    """A plugin that only implements the required abstract `poll()` -- proves the default `send_command`
    behavior (poll-only connectors, e.g. the barcode scanner and tester/vision plugins in this pass,
    need not implement anything to correctly refuse an outbound command)."""

    def poll(self):
        yield RawSourceObservation(
            connector_id="poll-only", connector_version="1.0", device_id="dev", mapping_id="map",
            source=SourceRef(protocol="FILE", address="x"), value=1,
        )


def test_default_send_command_raises_not_supported():
    plugin = _PollOnlyPlugin({})
    with pytest.raises(PeripheralCommandNotSupportedError):
        plugin.send_command({"action": "anything"})


def test_default_send_command_error_names_the_plugin_class():
    plugin = _PollOnlyPlugin({})
    with pytest.raises(PeripheralCommandNotSupportedError, match="_PollOnlyPlugin"):
        plugin.send_command({"action": "anything"})
