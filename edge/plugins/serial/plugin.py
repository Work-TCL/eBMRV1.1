"""Generic serial/TCP proprietary-adapter `ConnectorPlugin`. Config shape:

```yaml
protocol: SERIAL
transport: tcp          # or "serial"
host: 10.0.0.30          # tcp only
port: 9000                # tcp: TCP port; serial: device path when transport=serial
baudrate: 9600             # serial only
mapping_id: TANK_TEMP
unit: C
```

Streaming/message-driven like MQTT (each incoming frame is one reading), not fixed-address-polling like
Modbus/OPC UA -- one connector drains its one incoming line stream for up to `poll_interval_seconds` per
`poll()` call.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Iterable

from plugins.base import ConnectorPlugin
from plugins.common.driver_contracts import DriverError, ProtocolException, ReadOptions, ReadTimeout, SourceAddress, backoff_delay_seconds, to_raw_observation
from plugins.serial.driver import GenericSerialDriver
from runtime.contracts import RawSourceObservation, SourceRef

logger = logging.getLogger("edge.plugins.serial")

_MIN_SLICE_TIMEOUT_SECONDS = 0.05


class GenericSerialPlugin(ConnectorPlugin):
    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._driver = GenericSerialDriver(
            connector_id=connector_config.get("connector_id", "serial"),
            connector_version=connector_config.get("connector_version", "1.0.0"),
            device_id=connector_config.get("device_id", "serial-device"),
        )
        self._address = SourceAddress(
            address=connector_config.get("mapping_id", "SERIAL_STREAM"), protocol="SERIAL",
            extra={"mapping_id": connector_config.get("mapping_id", "SERIAL_STREAM"), "unit": connector_config.get("unit")},
        )
        self._loop = asyncio.new_event_loop()
        self._connected = False
        self._connect_attempt = 0
        self._next_connect_attempt_monotonic = 0.0

    def _error_observation(self, quality: str) -> RawSourceObservation:
        return to_raw_observation(
            connector_id=self.connector_config.get("connector_id", "unknown"),
            connector_version=self.connector_config.get("connector_version", "0.0.0"),
            device_id=self.connector_config.get("device_id", "unknown"),
            mapping_id=self._address.extra.get("mapping_id"),
            source=SourceRef(protocol="SERIAL", address=self._address.address),
            value=None, unit=self._address.extra.get("unit"), quality_hint=quality,
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
                logger.info("connector=%s SERIAL CONNECTED", self.connector_config.get("connector_id"))
            except DriverError as exc:
                self._connect_attempt += 1
                delay = backoff_delay_seconds(self._connect_attempt - 1)
                self._next_connect_attempt_monotonic = time.monotonic() + delay
                observations.append(self._error_observation("COMM_ERROR"))
                return observations

        deadline = time.monotonic() + self.poll_interval_seconds()
        while time.monotonic() < deadline:
            remaining = max(_MIN_SLICE_TIMEOUT_SECONDS, deadline - time.monotonic())
            try:
                observations.append(await self._driver.read_once(self._address, ReadOptions(timeout_seconds=remaining)))
            except ReadTimeout:
                break
            except ProtocolException as exc:
                logger.warning("connector=%s malformed/corrupt frame: %s", self.connector_config.get("connector_id"), exc)
                observations.append(self._error_observation("BAD"))
                continue
            except DriverError as exc:
                logger.warning("connector=%s connection lost: %s", self.connector_config.get("connector_id"), exc)
                self._connected = False
                try:
                    await self._driver.disconnect(reason=f"read failure: {exc.code}")
                except Exception:  # noqa: BLE001
                    pass
                observations.append(self._error_observation("COMM_ERROR"))
                break
        return observations
