"""MQTT 5 client driver -- Document 44 (SPEC-EDGE-002) section 7.

DRV-FR-010 ("Support broker TLS/auth, topic filters, QoS policy, retained flag handling, payload
schema/version and client session policy") and DRV-FR-011 ("JSON/binary/custom payload decoded only
through versioned decoder plugin/schema" -- see `plugins/mqtt/decoders.py`).

Scope decision (not a SPEC_GAP -- an ordinary, spec-faithful engineering choice): Document 44 section 7's
own reference config shows exactly one `topic` per connector, unlike the Modbus/OPC UA sections which show
a `mappings:` list of several registers/nodes per connector. This driver follows the spec's own shape --
one MQTT connector subscribes to one topic filter. An operator needing several logical MQTT parameters
runs several connector instances (the supervisor already isolates connectors from each other per
EDGE-FR-007), rather than this driver inventing a multi-topic-per-connector fan-out Document 44 never
describes. This also sidesteps a real correctness hazard: `aiomqtt`'s `client.messages` is one interleaved
stream across every topic a client subscribes to, so a single shared iterator cannot be safely "read for
address A" vs "read for address B" without message-topic routing logic the spec does not ask for.

Uses `aiomqtt` (MIT; Document 104 justification recorded in `edge/pyproject.toml`). Tests run against a
real local `mosquitto` broker subprocess (`edge/tests/test_plugin_mqtt.py`).
"""

from __future__ import annotations

import ssl
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import aiomqtt

from plugins.common.driver_contracts import (
    ConnectionResult,
    DriverHealth,
    EdgeDriver,
    EndpointUnreachable,
    ReadOptions,
    ReadTimeout,
    SourceAddress,
    to_raw_observation,
)
from plugins.mqtt.decoders import get_decoder
from runtime.contracts import RawSourceObservation, SourceRef, utcnow


def _parse_broker_url(broker: str) -> tuple[str, int, bool]:
    parsed = urlsplit(broker)
    if parsed.scheme not in ("mqtt", "mqtts"):
        raise ValueError(f"unsupported MQTT broker scheme: {parsed.scheme!r} (expected mqtt:// or mqtts://)")
    use_tls = parsed.scheme == "mqtts"
    if not parsed.hostname:
        raise ValueError(f"MQTT broker URL missing hostname: {broker!r}")
    port = parsed.port or (8883 if use_tls else 1883)
    return parsed.hostname, port, use_tls


def _parse_source_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class MqttDriver(EdgeDriver):
    """One `MqttDriver` instance owns one `aiomqtt.Client` and one subscribed topic filter (see module
    docstring for the single-topic-per-connector scope decision)."""

    def __init__(self, connector_id: str, connector_version: str, device_id: str) -> None:
        self.connector_id = connector_id
        self.connector_version = connector_version
        self.device_id = device_id
        self._client: aiomqtt.Client | None = None
        self._message_iter = None
        self._session_id: str | None = None
        self._error_count = 0
        self._last_success_at: datetime | None = None
        self._subscribed_topic: str | None = None

    async def connect(self, config: dict[str, Any]) -> ConnectionResult:
        try:
            hostname, port, use_tls = _parse_broker_url(config["broker"])
        except (KeyError, ValueError) as exc:
            raise EndpointUnreachable(f"invalid MQTT broker configuration: {exc}", raw_detail=str(exc)) from exc

        tls_context = ssl.create_default_context() if use_tls else None
        try:
            client = aiomqtt.Client(
                hostname=hostname,
                port=port,
                identifier=config.get("client_id"),
                username=config.get("username"),
                password=config.get("password"),
                tls_context=tls_context,
                keepalive=int(config.get("keepalive_seconds", 60)),
                timeout=float(config.get("connect_timeout_seconds", 5.0)),
            )
            await client.__aenter__()
        except aiomqtt.MqttError as exc:
            raise EndpointUnreachable(f"MQTT connect failed: {exc}", raw_detail=str(exc)) from exc
        except OSError as exc:
            raise EndpointUnreachable(f"MQTT connect failed: {exc}", raw_detail=str(exc)) from exc

        self._client = client
        self._message_iter = client.messages.__aiter__()
        self._session_id = str(uuid.uuid4())
        self._last_success_at = utcnow()

        topic = config.get("topic")
        if topic:
            qos = int(config.get("qos", 0))
            await self._subscribe(topic, qos)

        return ConnectionResult(
            session_id=self._session_id,
            capabilities={"read": True, "write": False, "subscribe": True, "browse": False},
        )

    async def _subscribe(self, topic: str, qos: int) -> None:
        assert self._client is not None
        try:
            await self._client.subscribe(topic, qos=qos)
        except aiomqtt.MqttError as exc:
            raise EndpointUnreachable(f"MQTT subscribe failed for topic={topic}: {exc}", raw_detail=str(exc)) from exc
        self._subscribed_topic = topic

    async def disconnect(self, reason: str) -> None:
        if self._client is None:
            return
        try:
            await self._client.__aexit__(None, None, None)
        finally:
            self._client = None
            self._message_iter = None
            self._subscribed_topic = None
            self._session_id = None

    def _require_client(self) -> aiomqtt.Client:
        if self._client is None or self._message_iter is None:
            raise EndpointUnreachable("MQTT driver used before connect()")
        return self._client

    async def read_once(self, address: SourceAddress, opts: ReadOptions | None = None) -> RawSourceObservation:
        """Waits for the next message on this connector's one subscribed topic and decodes it through
        the address's configured versioned decoder (DRV-FR-011). `ReadTimeout` on a quiet topic is a
        normal, expected outcome for a message-driven source -- the caller (plugin poll loop) treats it
        as "nothing new this cycle", not a connection failure."""
        import asyncio

        self._require_client()
        timeout = opts.timeout_seconds if opts else 5.0
        try:
            message = await asyncio.wait_for(self._message_iter.__anext__(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise ReadTimeout(f"no MQTT message on topic={address.address} within {timeout}s", raw_detail=str(exc)) from exc
        except StopAsyncIteration as exc:
            self._error_count += 1
            raise EndpointUnreachable("MQTT message stream ended (broker disconnected)", raw_detail=str(exc)) from exc
        except aiomqtt.MqttError as exc:
            self._error_count += 1
            raise EndpointUnreachable(f"MQTT connection error while reading: {exc}", raw_detail=str(exc)) from exc

        decoder = get_decoder(address.extra["decoder"])  # raises PayloadSchemaInvalid if unregistered
        decoded = decoder(message.payload, address.extra["schema_version"])  # raises PayloadSchemaInvalid

        # DRV-FR-010 "retained flag handling" / section 7: "a retained historical value cannot silently
        # masquerade as a new live observation" -- STALE is this codebase's already-defined quality
        # category for exactly this "value may be valid but is not current" case (Document 43 section 5's
        # Quality enum), not a new business rule invented for MQTT.
        quality = "STALE" if message.retain else "GOOD"
        self._last_success_at = utcnow()
        return to_raw_observation(
            connector_id=self.connector_id,
            connector_version=self.connector_version,
            device_id=self.device_id,
            mapping_id=address.extra.get("mapping_id", address.address),
            source=SourceRef(protocol="MQTT", address=str(message.topic)),
            value=decoded.value,
            unit=decoded.unit or address.extra.get("unit"),
            source_timestamp=_parse_source_timestamp(decoded.source_timestamp_iso),
            quality_hint=quality,
        )

    async def health_check(self) -> DriverHealth:
        connected = self._client is not None
        return DriverHealth(
            connected=connected, last_success_at=self._last_success_at, error_count=self._error_count,
            latency_ms=None, diagnostics={"session_id": self._session_id, "subscribed_topic": self._subscribed_topic},
        )
