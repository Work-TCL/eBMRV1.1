"""Canonical Edge Observation Contract -- Document 43 (SPEC-EDGE-001) section 5, transcribed field-for-
field from the TypeScript type in the spec. EDGE-FR-009 (envelope), EDGE-FR-010 (provenance), EDGE-FR-011
(timestamp model), EDGE-FR-012 (data quality).

This is the *only* shape that crosses from a protocol plugin into the outbox (EDGE-FR-009: "All
readings/events normalize into canonical EdgeObservationEnvelope before buffering/forwarding") -- no
plugin may append a raw/protocol-specific record directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Protocol = Literal["OPCUA", "MODBUS_TCP", "MODBUS_RTU", "MQTT", "SNMP", "SERIAL", "REST", "FILE"]
Quality = Literal["GOOD", "UNCERTAIN", "BAD", "STALE", "COMM_ERROR", "CLOCK_UNCERTAIN"]
ClockStatus = Literal["GOOD", "UNCERTAIN", "BAD"]


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: Protocol
    address: str
    native_data_type: str | None = None


class ClockQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ClockStatus
    offset_ms: float | None = None
    source: str | None = None


class RawValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: object
    unit: str | None = None
    hash: str | None = None


class NormalizedValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | float | bool | None = None
    unit: str | None = None


class BatchContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str | None = None
    step_id: str | None = None
    operation_id: str | None = None


class EdgeObservationEnvelope(BaseModel):
    """`schema_version` is pinned to "1.0" -- a future breaking change to this shape is a new schema
    version per CTR-FR-020, not a silent field change, exactly like every other contract in this repo."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)  # gateway-assigned; UUIDv7 recommended by spec,
    # uuid4 accepted here (stdlib has no uuid7 before 3.14; identity/uniqueness is what EDGE-FR-016 needs)
    gateway_id: uuid.UUID
    tenant_id: str
    site_id: uuid.UUID
    connector_id: str
    connector_version: str
    device_id: str
    mapping_id: str
    mapping_version: str
    source: SourceRef
    source_timestamp: datetime | None = None
    gateway_received_at: datetime
    gateway_sequence: int
    clock_quality: ClockQuality
    quality: Quality
    raw: RawValue
    normalized: NormalizedValue | None = None
    correlation_id: uuid.UUID | None = None
    batch_context: BatchContext | None = None


class RawSourceObservation(BaseModel):
    """What a protocol plugin hands to `ingestSourceObservation()` -- protocol-specific, never itself
    persisted or forwarded (Prohibitions section 16: "Do not put protocol-specific logic in GxP domain
    services" -- this type is the sandbox boundary between plugin output and the canonical envelope)."""

    model_config = ConfigDict(extra="allow")  # plugin-specific fields pass through into `raw.value` only

    connector_id: str
    connector_version: str
    device_id: str
    mapping_id: str
    source: SourceRef
    value: object
    unit: str | None = None
    source_timestamp: datetime | None = None
    quality_hint: Quality | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)