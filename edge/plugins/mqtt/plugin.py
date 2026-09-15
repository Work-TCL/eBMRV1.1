"""MQTT `ConnectorPlugin`. Config shape follows Document 44 section 7's reference YAML:

```yaml
protocol: MQTT
broker: mqtts://broker.local:8883
client_id: edge-site-a
topic: plant/line1/filler/telemetry
qos: 1
decoder: generic-json-v1
schema_version: "2.1"
mapping_id: FILL_TELEMETRY
unit: bar
```

Message-driven, not poll-driven (see `plugins/common/polling_plugin.py`'s module docstring) -- this
class owns its own persistent asyncio loop and drains the subscribed topic for up to
`poll_interval_seconds` per `poll()` call rather than reusing `PollingConnectorPlugin`'s
"read N fixed addresses once per cycle" shape, which does not fit a single continuously-streaming
subscription.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Iterable

from plugins.base import ConnectorPlugin
from plugins.common.driver_contracts import (
    DriverError,
    PayloadSchemaInvalid,
    ReadOptions,
    ReadTimeout,
    SourceAddress,
    backoff_delay_seconds,
    to_raw_observation,
)
from plugins.mqtt.driver import MqttDriver
from runtime.contracts import RawSourceObservation, SourceRef

logger = logging.getLogger("edge.plugins.mqtt")

_MIN_SLICE_TIMEOUT_SECONDS = 0.05


class MqttPlugin(ConnectorPlugin):
    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._driver = MqttDriver(
            connector_id=connector_config.get("connector_id", "mqtt"),
            connector_version=connector_config.get("connector_version", "1.0.0"),
            device_id=connector_config.get("device_id", "mqtt-device"),
        )
        self._address = self._build_address()
        self._loop = asyncio.new_event_loop()
        self._connected = False
        self._connect_attempt = 0
        self._next_connect_attempt_monotonic = 0.0

    def _build_address(self) -> SourceAddress:
        return SourceAddress(
            address=self.connector_config["topic"], protocol="MQTT",
            extra={
                "qos": self.connector_config.get("qos", 0),
                "decoder": self.connector_config["decoder"],
                "schema_version": self.connector_config["schema_version"],
                "mapping_id": self.connector_config.get("mapping_id", self.connector_config["topic"]),
                "unit": self.connector_config.get("unit"),
            },
        )

    def _comm_error_observation(self, error: DriverError) -> RawSourceObservation:
        return to_raw_observation(
            connector_id=self.connector_config.get("connector_id", "unknown"),
            connector_version=self.connector_config.get("connector_version", "0.0.0"),
            device_id=self.connector_config.get("device_id", "unknown"),
            mapping_id=self._address.extra.get("mapping_id", self._address.address),
            source=SourceRef(protocol="MQTT", address=self._address.address),
            value=None,
            unit=self._address.extra.get("unit"),
            quality_hint="COMM_ERROR",
        )

    def _bad_payload_observation(self, error: PayloadSchemaInvalid) -> RawSourceObservation:
        """A single malformed/mismatched-schema message is a data-quality problem with that one
        message, not a connection failure -- the subscription stays up (DRV-FR-009's sibling principle
        for MQTT: never let one bad message kill the whole connector)."""
        return to_raw_observation(
            connector_id=self.connector_config.get("connector_id", "unknown"),
            connector_version=self.connector_config.get("connector_version", "0.0.0"),
            device_id=self.connector_config.get("device_id", "unknown"),
            mapping_id=self._address.extra.get("mapping_id", self._address.address),
            source=SourceRef(protocol="MQTT", address=self._address.address),
            value=None,
            unit=self._address.extra.get("unit"),
            quality_hint="BAD",
        )

    def poll(self) -> Iterable[RawSourceObservation]:
        return self._loop.run_until_complete(self._poll_async())

    async def _poll_async(self) -> list[RawSourceObservation]:
        observations: list[RawSourceObservation] = []

        if not self._connected:
            if time.monotonic() < self._next_connect_attempt_monotonic:
                return observations
            try:
                await self._driver.connect(self.connector_config)
                self._connected = True
                self._connect_attempt = 0
                logger.info("connector=%s MQTT CONNECTED topic=%s", self.connector_config.get("connector_id"), self._address.address)
            except DriverError as exc:
                self._connect_attempt += 1
                delay = backoff_delay_seconds(self._connect_attempt - 1)
                self._next_connect_attempt_monotonic = time.monotonic() + delay
                logger.warning(
                    "connector=%s MQTT connect failed (attempt=%d, retry_in=%.1fs): %s",
                    self.connector_config.get("connector_id"), self._connect_attempt, delay, exc,
                )
                observations.append(self._comm_error_observation(exc))
                return observations

        deadline = time.monotonic() + self.poll_interval_seconds()
        while time.monotonic() < deadline:
            remaining = max(_MIN_SLICE_TIMEOUT_SECONDS, deadline - time.monotonic())
            try:
                observations.append(await self._driver.read_once(self._address, ReadOptions(timeout_seconds=remaining)))
            except ReadTimeout:
                break  # nothing new arrived this cycle -- not an error for a message-driven source
            except PayloadSchemaInvalid as exc:
                logger.warning("connector=%s MQTT payload rejected: %s", self.connector_config.get("connector_id"), exc)
                observations.append(self._bad_payload_observation(exc))
                continue  # keep draining -- one bad message does not drop the subscription
            except DriverError as exc:
                logger.warning("connector=%s MQTT connection lost: %s", self.connector_config.get("connector_id"), exc)
                self._connected = False
                try:
                    await self._driver.disconnect(reason=f"read failure: {exc.code}")
                except Exception:  # noqa: BLE001 -- best-effort cleanup only
                    pass
                observations.append(self._comm_error_observation(exc))
                break
        return observations
