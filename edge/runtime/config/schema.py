"""Gateway configuration schema -- Document 43 EDGE-FR-004 (connector, mapping, certificate, buffering
and forwarding configuration, immutable/versioned). `additionalProperties: false` throughout (CTR-FR-005
strict-input discipline, applied here even though this is a local config file, not a wire API, because a
silently-ignored typo'd field is exactly the "contradictory settings" EDGE-FR-005 must catch).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# EDGE-FR-022 (Document 43 section 3/10): "Gateway supports industrial-side and enterprise/cloud-side
# network interfaces with outbound-only preferred architecture." INDUSTRIAL_OT is the plant-network side
# a connector polls (PLC/SCADA/instrument/peripheral) -- every shipped driver in plugins/ (modbus, opcua,
# mqtt, snmp, serial, rest, file, barcode, balance, printer, tester, vision) is a poll()-based client that
# only ever initiates outbound connections to its own configured device, matching the on-industrial-side
# half of this requirement. ENTERPRISE_CLOUD is the gateway's own uplink side (runtime/forwarding's outbox
# publisher, which only ever makes outbound HTTPS calls to the GxP API -- it never opens a listening
# socket). Declaring the zone per connector is what makes "supports industrial-side and enterprise/
# cloud-side interfaces" a checkable config fact rather than an implicit assumption; TLS version, gateway
# workload certificates and firewall rules (the rest of section 10's list) are deployment/infrastructure
# controls outside this Python codebase and are not asserted here.
NetworkZone = Literal["INDUSTRIAL_OT", "ENTERPRISE_CLOUD"]


class ConnectorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_id: str
    plugin: str  # importable module path the supervisor launches as `python -m <plugin>`
    plugin_version: str
    network_zone: NetworkZone
    poll_interval_seconds: float = Field(gt=0, default=1.0)
    settings: dict = Field(default_factory=dict)


class UnitConversionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_unit: str
    to_unit: str
    factor: float = 1.0
    offset: float = 0.0


class MappingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_id: str
    mapping_version: str
    target_unit: str | None = None
    conversions: list[UnitConversionConfig] = Field(default_factory=list)


class BufferingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disk_pressure_warning_bytes: int = Field(gt=0, default=500 * 1024 * 1024)
    disk_pressure_critical_bytes: int = Field(gt=0, default=100 * 1024 * 1024)


class ForwardingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_batch_items: int = Field(gt=0, le=1000, default=200)
    base_retry_backoff_seconds: float = Field(gt=0, default=5.0)
    max_retry_backoff_seconds: float = Field(gt=0, default=300.0)


class CommandChannelConfig(BaseModel):
    """EDGE-FR-023: disabled by default; a config cannot silently enable it without an explicit
    `approved_command_profile_ids` allowlist naming which validated profiles are permitted."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    approved_command_profile_ids: list[str] = Field(default_factory=list)


class GatewayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_version: str
    supported_plugin_api_version: str = "1.0"
    connectors: list[ConnectorConfig] = Field(default_factory=list)
    mappings: list[MappingConfig] = Field(default_factory=list)
    buffering: BufferingConfig = Field(default_factory=BufferingConfig)
    forwarding: ForwardingConfig = Field(default_factory=ForwardingConfig)
    command_channel: CommandChannelConfig = Field(default_factory=CommandChannelConfig)


PLUGIN_API_VERSION = "1.0"  # this gateway build's own supported plugin adapter interface version