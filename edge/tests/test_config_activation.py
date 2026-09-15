import hashlib
import json

import pytest

from runtime.config.activation import activate_runtime_config
from runtime.config.loader import ConfigRejectedError, validate_config_payload
from runtime.ingestion.pipeline import MappingRegistry
from runtime.supervisor.supervisor import ConnectorSupervisor

VALID_PAYLOAD = {
    "config_version": "v1",
    "supported_plugin_api_version": "1.0",
    "connectors": [],
    "mappings": [],
}


def _checksum(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def test_validate_accepts_matching_checksum():
    validated = validate_config_payload(VALID_PAYLOAD, expected_checksum=_checksum(VALID_PAYLOAD))
    assert validated.config_version == "v1"


def test_validate_rejects_checksum_mismatch():
    with pytest.raises(ConfigRejectedError) as exc_info:
        validate_config_payload(VALID_PAYLOAD, expected_checksum="deadbeef")
    assert exc_info.value.code == "CONFIG_SIGNATURE_INVALID"


def test_validate_rejects_unsupported_plugin_api_version():
    payload = {**VALID_PAYLOAD, "supported_plugin_api_version": "99.0"}
    with pytest.raises(ConfigRejectedError) as exc_info:
        validate_config_payload(payload)
    assert exc_info.value.code == "PLUGIN_UNSUPPORTED"


def test_validate_rejects_malformed_schema():
    with pytest.raises(ConfigRejectedError) as exc_info:
        validate_config_payload({"config_version": "v1", "connectors": [{"connector_id": "c1"}]})  # missing required fields
    assert exc_info.value.code == "CONFIG_SCHEMA_INVALID"


def test_validate_rejects_contradictory_duplicate_connector_ids():
    payload = {
        **VALID_PAYLOAD,
        "connectors": [
            {"connector_id": "c1", "plugin": "plugins.demo", "plugin_version": "1.0", "network_zone": "INDUSTRIAL_OT"},
            {"connector_id": "c1", "plugin": "plugins.demo", "plugin_version": "1.0", "network_zone": "INDUSTRIAL_OT"},
        ],
    }
    with pytest.raises(ConfigRejectedError) as exc_info:
        validate_config_payload(payload)
    assert exc_info.value.code == "CONFIG_CONTRADICTORY"


def test_validate_rejects_connector_referencing_undeclared_mapping():
    payload = {
        **VALID_PAYLOAD,
        "connectors": [
            {"connector_id": "c1", "plugin": "plugins.demo", "plugin_version": "1.0", "network_zone": "INDUSTRIAL_OT", "settings": {"mapping_id": "missing-map"}},
        ],
    }
    with pytest.raises(ConfigRejectedError) as exc_info:
        validate_config_payload(payload)
    assert exc_info.value.code == "CONFIG_CONTRADICTORY"


async def _noop_sink(connector_id, observation):
    pass


@pytest.mark.asyncio
async def test_activation_is_atomic_and_retains_prior_config_on_failure(conn):
    good = validate_config_payload(VALID_PAYLOAD)
    supervisor = ConnectorSupervisor(conn, _noop_sink)
    result = await activate_runtime_config(conn, supervisor, MappingRegistry(), good)
    assert result.active_version == "v1"

    row = conn.execute("SELECT status FROM edge_config_snapshot WHERE config_version = 'v1'").fetchone()
    assert row["status"] == "active"

    class ExplodingSupervisor(ConnectorSupervisor):
        async def start_connector(self, *args, **kwargs):
            raise RuntimeError("simulated connector start failure")

    bad_payload = {
        **VALID_PAYLOAD,
        "config_version": "v2",
        "connectors": [{"connector_id": "c1", "plugin": "plugins.demo", "plugin_version": "1.0", "network_zone": "INDUSTRIAL_OT"}],
    }
    bad = validate_config_payload(bad_payload)
    exploding = ExplodingSupervisor(conn, _noop_sink)

    from runtime.config.activation import ActivationFailedError

    with pytest.raises(ActivationFailedError):
        await activate_runtime_config(conn, exploding, MappingRegistry(), bad)

    # prior valid configuration (v1) must still be the active one -- EDGE-FR-006
    active_row = conn.execute("SELECT config_version FROM edge_config_snapshot WHERE status = 'active'").fetchone()
    assert active_row["config_version"] == "v1"

    rejected_row = conn.execute("SELECT status FROM edge_config_snapshot WHERE config_version = 'v2'").fetchone()
    assert rejected_row["status"] == "rejected"


@pytest.mark.asyncio
async def test_activation_skips_restart_for_unchanged_connector(conn):
    payload = {
        **VALID_PAYLOAD,
        "config_version": "v1",
        "connectors": [{"connector_id": "c1", "plugin": "plugins.demo", "plugin_version": "1.0", "network_zone": "INDUSTRIAL_OT", "settings": {}}],
    }
    validated_v1 = validate_config_payload(payload)

    started = []

    class RecordingSupervisor(ConnectorSupervisor):
        async def start_connector(self, connector_id, *args, **kwargs):
            started.append(connector_id)
            return None

        async def stop_connector(self, *args, **kwargs):
            return None

    supervisor = RecordingSupervisor(conn, _noop_sink)
    await activate_runtime_config(conn, supervisor, MappingRegistry(), validated_v1)
    assert started == ["c1"]

    payload_v2 = {**payload, "config_version": "v2"}  # identical connector config, new version
    validated_v2 = validate_config_payload(payload_v2)
    await activate_runtime_config(conn, supervisor, MappingRegistry(), validated_v2)
    assert started == ["c1"]  # not restarted again -- connector config itself did not change