"""Document 44 (SPEC-EDGE-002) section 3/4 -- the `EdgeDriver` common interface, its supporting
input/output types and the stable error taxonomy (section 9), transcribed field-for-field from the
spec's TypeScript `EdgeDriver` interface and function/driver contract catalogue.

This module is protocol-neutral. It never imports a protocol client library (asyncua, pymodbus,
aiomqtt, pysnmp) -- those live only inside their own `plugins/<protocol>/driver.py`.

"No driver receives database repository objects from the GxP application" (Document 44 section 4):
nothing here imports `runtime.forwarding`, `runtime.config`, `storage.db` or any GxP service client.
The only cross-import is `runtime.contracts.RawSourceObservation`/`SourceRef`, the fixed hand-off
shape a `ConnectorPlugin.poll()` already emits per Document 43.
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable

from runtime.contracts import Protocol, Quality, RawSourceObservation, SourceRef

# --------------------------------------------------------------------------------------------------
# Section 9 -- stable error taxonomy. Each driver raises one of these; the plugin wrapper (never the
# driver itself) is what turns a raised error into a BAD/COMM_ERROR RawSourceObservation so a single
# bad reading cannot kill the connector process (plugins/base.py's poll() contract).
# --------------------------------------------------------------------------------------------------


class DriverError(Exception):
    """Base class for the Document 44 section 9 stable error taxonomy. `raw_detail` retains the
    native protocol error/exception text for support (DRV-FR-024: "Native errors normalized to
    stable driver error taxonomy while raw diagnostic retained") without ever leaking a secret value
    (Security section 10: "no driver logs secret values") -- callers must not put credential material
    into `raw_detail`."""

    code: str = "PROTOCOL_EXCEPTION"

    def __init__(self, message: str, raw_detail: str | None = None) -> None:
        super().__init__(message)
        self.raw_detail = raw_detail


class EndpointUnreachable(DriverError):
    code = "ENDPOINT_UNREACHABLE"


class AuthFailed(DriverError):
    code = "AUTH_FAILED"


class CertUntrusted(DriverError):
    code = "CERT_UNTRUSTED"


class SessionExpired(DriverError):
    code = "SESSION_EXPIRED"


class ReadTimeout(DriverError):
    code = "READ_TIMEOUT"


class WriteDisabled(DriverError):
    code = "WRITE_DISABLED"


class ProtocolException(DriverError):
    code = "PROTOCOL_EXCEPTION"


class CrcError(DriverError):
    code = "CRC_ERROR"


class BadNativeQuality(DriverError):
    code = "BAD_NATIVE_QUALITY"


class PayloadSchemaInvalid(DriverError):
    code = "PAYLOAD_SCHEMA_INVALID"


class SourceMappingNotFound(DriverError):
    code = "SOURCE_MAPPING_NOT_FOUND"


class RateLimited(DriverError):
    code = "RATE_LIMITED"


class ReconnectFailed(DriverError):
    code = "RECONNECT_FAILED"


class BrowseDenied(DriverError):
    """Not in section 9's list verbatim, but named directly by the function catalogue's `browse()`
    row ("BROWSE_DENIED/BROWSE_FAILED") -- engineering-mode browse is authorization-gated separately
    from the general read/write error taxonomy."""

    code = "BROWSE_DENIED"


class BrowseFailed(DriverError):
    code = "BROWSE_FAILED"


class SubscribeFailed(DriverError):
    code = "SUBSCRIBE_FAILED"


class MappingTestFailed(DriverError):
    code = "MAPPING_TEST_FAILED"


class QualityMappingUnknown(DriverError):
    code = "QUALITY_MAPPING_UNKNOWN"


# --------------------------------------------------------------------------------------------------
# Section 4/6/7 input & output types
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceAddress:
    """Protocol-neutral pointer to one source tag/register/topic/OID. `extra` carries the
    protocol-specific mapping fields from Document 44 sections 5-8 (e.g. Modbus `function`/`length`/
    `data_type`/`byte_order`/`scale`; MQTT `topic`/`qos`/`decoder`/`schema_version`; SNMP `oid`) --
    each driver documents and validates only the keys it actually reads."""

    address: str
    protocol: Protocol
    data_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadOptions:
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class ConnectionResult:
    session_id: str
    capabilities: dict[str, bool]  # {"read": bool, "write": bool, "subscribe": bool, "browse": bool}


@dataclass(frozen=True)
class SubscriptionOptions:
    sampling_interval_ms: int = 1000
    publishing_interval_ms: int = 1000
    queue_size: int = 10
    keepalive_count: int = 10


@dataclass(frozen=True)
class SubscriptionHandle:
    subscription_id: str


@dataclass(frozen=True)
class BrowseRequest:
    root: str
    filters: dict[str, Any] = field(default_factory=dict)
    continuation: str | None = None
    engineering_mode_authorized: bool = False


@dataclass(frozen=True)
class BrowseResult:
    nodes: list[dict[str, Any]]
    continuation: str | None = None


@dataclass(frozen=True)
class DriverWriteRequest:
    address: SourceAddress
    value: object
    command_context: dict[str, Any] = field(default_factory=dict)
    verify_readback: bool = False


@dataclass(frozen=True)
class DriverWriteReceipt:
    accepted: bool
    read_back_value: object | None = None
    verified: bool | None = None


@dataclass
class DriverHealth:
    connected: bool
    last_success_at: datetime | None
    error_count: int
    latency_ms: float | None
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MappingPreview:
    """`testMapping()`'s output -- DRV-FR-018: "Engineering test reads source and displays raw/
    normalized preview without committing regulated result." Nothing built from this type may reach
    `runtime.ingestion`/`runtime.forwarding` -- it is a one-shot commissioning preview only."""

    raw_value: object
    normalized_value: object
    quality: Quality
    native_diagnostic: str | None = None


ObservationCallback = Callable[[RawSourceObservation], Awaitable[None]]


# --------------------------------------------------------------------------------------------------
# Section 4 -- the common `EdgeDriver` interface. `subscribe`/`unsubscribe`/`browse`/`write` are
# optional in the spec's TypeScript type (`?` suffix); the default implementations here raise
# `NotImplementedError`/`WriteDisabled` so a driver that does not support a capability need not
# override it, exactly like the TypeScript `?` marks it absent rather than a required no-op.
# --------------------------------------------------------------------------------------------------


class EdgeDriver(ABC):
    @abstractmethod
    async def connect(self, config: dict[str, Any]) -> ConnectionResult:
        ...

    @abstractmethod
    async def disconnect(self, reason: str) -> None:
        ...

    @abstractmethod
    async def read_once(self, address: SourceAddress, opts: ReadOptions | None = None) -> RawSourceObservation:
        ...

    async def subscribe(
        self, addresses: list[SourceAddress], opts: SubscriptionOptions, callback: ObservationCallback
    ) -> SubscriptionHandle:
        raise NotImplementedError("this driver does not support subscribe()")

    async def unsubscribe(self, subscription_id: str) -> None:
        raise NotImplementedError("this driver does not support unsubscribe()")

    async def browse(self, request: BrowseRequest) -> BrowseResult:
        raise NotImplementedError("this driver does not support browse()")

    async def write(self, request: DriverWriteRequest) -> DriverWriteReceipt:
        """Architectural Principles: "Commands to machines are disabled by default in V1 unless a
        specifically validated command profile authorizes them." This reference build has no
        validated command-profile authorization mechanism wired to the edge gateway yet, so every
        driver's `write()` fails closed with `WriteDisabled` unless a subclass deliberately overrides
        this method AND the caller supplies `command_context["validated_command_profile_id"]` --
        DRV-FR-017's "runtime blocks write unless explicit command profile" is satisfied by never
        enabling the bypass, not by inventing what a validated profile means (AG-15)."""
        raise WriteDisabled(
            "machine write is disabled by default in this reference build; no validated command "
            "profile authorization mechanism exists in this codebase (Document 44 Architectural "
            "Principles, DRV-FR-017)"
        )

    @abstractmethod
    async def health_check(self) -> DriverHealth:
        ...


def to_raw_observation(
    *,
    connector_id: str,
    connector_version: str,
    device_id: str,
    mapping_id: str,
    source: SourceRef,
    value: object,
    unit: str | None = None,
    source_timestamp: datetime | None = None,
    quality_hint: Quality | None = None,
) -> RawSourceObservation:
    """Every driver's `read_once()`/subscription callback builds its result through this one
    function so every protocol produces the identical `RawSourceObservation` shape (Document 44
    section 13's acceptance criterion: "The same downstream EdgeObservationEnvelope is produced for
    equivalent logical parameters regardless of ... source")."""

    return RawSourceObservation(
        connector_id=connector_id,
        connector_version=connector_version,
        device_id=device_id,
        mapping_id=mapping_id,
        source=source,
        value=value,
        unit=unit,
        source_timestamp=source_timestamp,
        quality_hint=quality_hint,
    )


# --------------------------------------------------------------------------------------------------
# DRV-FR-015 (connection retry) / DRV-FR-016 (source rate limits)
# --------------------------------------------------------------------------------------------------


def backoff_delay_seconds(
    attempt: int, *, base_seconds: float = 1.0, max_seconds: float = 60.0, jitter_fraction: float = 0.2
) -> float:
    """Exponential backoff with jitter (DRV-FR-015: "Exponential backoff/jitter with configured max
    and health state; avoid network storms"). `attempt` is 0 for the first retry."""

    delay = min(base_seconds * (2**attempt), max_seconds)
    jitter = delay * jitter_fraction
    return max(0.0, delay + random.uniform(-jitter, jitter))


class PollRateLimiter:
    """Per-device poll/subscription rate limit (DRV-FR-016: "prevent overloading PLC/instrument").
    Raises `RateLimited` rather than silently dropping or silently slowing down -- the caller (plugin
    `poll()`) decides how to surface that as an observation."""

    def __init__(self, min_interval_seconds: float) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be >= 0")
        self._min_interval = min_interval_seconds
        self._last_call_monotonic: float | None = None

    def check(self) -> None:
        now = time.monotonic()
        if self._last_call_monotonic is not None and self._min_interval > 0:
            elapsed = now - self._last_call_monotonic
            if elapsed < self._min_interval:
                raise RateLimited(
                    f"poll rate exceeds configured minimum interval of {self._min_interval}s "
                    f"(elapsed={elapsed:.3f}s)"
                )
        self._last_call_monotonic = now