"""`loadRuntimeConfig()` -- Document 43 section 4. EDGE-FR-005: "Gateway validates schema,
signatures/checksum, supported plugin versions and contradictory settings before activation."

Checksum here is a plain SHA-256 integrity check the server returns alongside the payload (matching the
server's `GET /edge/v1/gateways/{id}/configuration` response shape in services/gxp-api/app/modules/edge/
commands.py::get_gateway_configuration -- it returns `checksum` computed server-side). True cryptographic
config-signing (a detached signature verified against a trusted key, not just a checksum) is not attempted
here: no signing-key distribution/rotation mechanism is defined anywhere in Document 43 or Document 106,
which is exactly the class of decision this project raises as a SPEC_GAP rather than inventing (see
SG-118/SG-120's "no real PKI issuance exists in this codebase" precedent, same limitation class).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from runtime.config.schema import PLUGIN_API_VERSION, GatewayConfig


class ConfigRejectedError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass
class ValidatedGatewayConfig:
    config_version: str
    config: GatewayConfig
    checksum: str
    raw_payload: dict


def validate_config_payload(payload: dict, *, expected_checksum: str | None = None) -> ValidatedGatewayConfig:
    """Pure validation, no I/O -- kept separate from the HTTP fetch so config-rejection tests do not need
    a real or mocked server."""
    computed_checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if expected_checksum is not None and computed_checksum != expected_checksum:
        raise ConfigRejectedError("CONFIG_SIGNATURE_INVALID", f"checksum mismatch: expected {expected_checksum}, computed {computed_checksum}")

    try:
        config = GatewayConfig.model_validate(payload)
    except ValidationError as exc:
        raise ConfigRejectedError("CONFIG_SCHEMA_INVALID", str(exc)) from exc

    if config.supported_plugin_api_version != PLUGIN_API_VERSION:
        raise ConfigRejectedError(
            "PLUGIN_UNSUPPORTED",
            f"config requires plugin API version {config.supported_plugin_api_version!r}, this build supports {PLUGIN_API_VERSION!r}",
        )

    connector_ids = [c.connector_id for c in config.connectors]
    if len(connector_ids) != len(set(connector_ids)):
        raise ConfigRejectedError("CONFIG_CONTRADICTORY", "duplicate connector_id values in configuration")

    mapping_ids = {m.mapping_id for m in config.mappings}
    for connector in config.connectors:
        # A connector's `settings.mapping_id`, if present, must resolve to a declared mapping -- an
        # undeclared reference is exactly the "contradictory settings" EDGE-FR-005 requires catching
        # before activation rather than discovering it later as a runtime UOM_INCOMPATIBLE failure.
        referenced = connector.settings.get("mapping_id")
        if referenced is not None and referenced not in mapping_ids:
            raise ConfigRejectedError("CONFIG_CONTRADICTORY", f"connector {connector.connector_id!r} references undeclared mapping_id {referenced!r}")

    return ValidatedGatewayConfig(config_version=config.config_version, config=config, checksum=computed_checksum, raw_payload=payload)


async def load_runtime_config(client: httpx.AsyncClient, gateway_id: str) -> ValidatedGatewayConfig:
    response = await client.get(f"/edge/v1/gateways/{gateway_id}/configuration")
    response.raise_for_status()
    body = response.json()
    return validate_config_payload(body["payload"], expected_checksum=body.get("checksum"))