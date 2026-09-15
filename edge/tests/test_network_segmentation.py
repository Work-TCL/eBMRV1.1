"""EDGE-FR-022 (Document 43 section 3/10) -- "Gateway supports industrial-side and enterprise/cloud-side
network interfaces with outbound-only preferred architecture." Verifies the checkable half of this
requirement: every connector config must declare which network zone it belongs to, and only the two
approved zone values are accepted. TLS/certificate/firewall controls (the rest of section 10's list) are
deployment-layer and are not asserted by this codebase -- see docs/generated/18_SPEC_GAPS.md if that ever
needs to change.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from runtime.config.loader import ConfigRejectedError, validate_config_payload
from runtime.config.schema import ConnectorConfig

VALID_PAYLOAD = {
    "config_version": "v1",
    "supported_plugin_api_version": "1.0",
    "connectors": [],
    "mappings": [],
}


def test_connector_config_requires_a_network_zone():
    with pytest.raises(ValidationError):
        ConnectorConfig(connector_id="c1", plugin="plugins.demo", plugin_version="1.0")


def test_connector_config_rejects_an_unknown_network_zone():
    with pytest.raises(ValidationError):
        ConnectorConfig(connector_id="c1", plugin="plugins.demo", plugin_version="1.0", network_zone="DMZ")


@pytest.mark.parametrize("zone", ["INDUSTRIAL_OT", "ENTERPRISE_CLOUD"])
def test_connector_config_accepts_both_declared_network_zones(zone):
    connector = ConnectorConfig(connector_id="c1", plugin="plugins.demo", plugin_version="1.0", network_zone=zone)
    assert connector.network_zone == zone


def test_validate_config_payload_rejects_connector_missing_network_zone():
    payload = {
        **VALID_PAYLOAD,
        "connectors": [{"connector_id": "c1", "plugin": "plugins.demo", "plugin_version": "1.0"}],
    }
    with pytest.raises(ConfigRejectedError) as exc_info:
        validate_config_payload(payload)
    assert exc_info.value.code == "CONFIG_SCHEMA_INVALID"


def test_validate_config_payload_accepts_both_zones_side_by_side():
    payload = {
        **VALID_PAYLOAD,
        "connectors": [
            {"connector_id": "plc-1", "plugin": "plugins.modbus.tcp_main", "plugin_version": "1.0", "network_zone": "INDUSTRIAL_OT"},
            {"connector_id": "cloud-uplink-probe", "plugin": "plugins.rest.main", "plugin_version": "1.0", "network_zone": "ENTERPRISE_CLOUD"},
        ],
    }
    validated = validate_config_payload(payload)
    zones = {c.connector_id: c.network_zone for c in validated.config.connectors}
    assert zones == {"plc-1": "INDUSTRIAL_OT", "cloud-uplink-probe": "ENTERPRISE_CLOUD"}
