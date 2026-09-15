"""Shared poll-loop plumbing reused by every "read a fixed set of source addresses" driver (OPC UA,
Modbus TCP/RTU, SNMP, REST, file). MQTT is message-driven rather than poll-driven and implements its
own `ConnectorPlugin` in `plugins/mqtt/plugin.py`.

Document 43's `ConnectorPlugin.poll()` is a *synchronous* generator (`plugins/base.py`) called from a
plain `while True: ... time.sleep(...)` loop (`run_plugin_main`). Every real protocol client used here
(asyncua, pymodbus, aiomqtt, pysnmp) is async-native, so this base class owns one persistent asyncio
event loop per plugin process and drives one `run_until_complete()` per `poll()` call rather than
starting/stopping a loop every time (which would drop an OPC UA subscription/Modbus TCP connection on
every single poll tick).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Iterable

from plugins.base import ConnectorPlugin
from plugins.common.driver_contracts import (
    ConnectionResult,
    DriverError,
    EdgeDriver,
    ReadOptions,
    SourceAddress,
    backoff_delay_seconds,
)
from runtime.contracts import RawSourceObservation, SourceRef

logger = logging.getLogger("edge.plugins.polling")

# Connection-level failures (DRV-FR-009: "Timeout/CRC/exception/out-of-range marks BAD/COMM_ERROR")
_CONNECTION_LEVEL_ERROR_CODES = {
    "ENDPOINT_UNREACHABLE", "SESSION_EXPIRED", "READ_TIMEOUT", "CRC_ERROR", "RECONNECT_FAILED",
    "AUTH_FAILED", "CERT_UNTRUSTED",
}


class PollingConnectorPlugin(ConnectorPlugin):
    """Subclasses provide `_build_driver()` and `_build_addresses()`; this base class owns connect/
    reconnect-with-backoff (DRV-FR-015, DRV-FR-021) and the read-error-to-quality mapping
    (DRV-FR-009, DRV-FR-024)."""

    def __init__(self, connector_config: dict) -> None:
        super().__init__(connector_config)
        self._driver: EdgeDriver = self._build_driver()
        self._addresses: list[SourceAddress] = self._build_addresses()
        self._connection: ConnectionResult | None = None
        self._connect_attempt = 0
        self._next_connect_attempt_monotonic = 0.0
        self._loop = asyncio.new_event_loop()
        rate_limit = float(self.connector_config.get("min_poll_interval_seconds", 0.0))
        from plugins.common.driver_contracts import PollRateLimiter

        self._rate_limiter = PollRateLimiter(rate_limit) if rate_limit > 0 else None
        self._was_connected = False

    def _build_driver(self) -> EdgeDriver:  # pragma: no cover - overridden by every subclass
        raise NotImplementedError

    def _build_addresses(self) -> list[SourceAddress]:  # pragma: no cover - overridden by every subclass
        raise NotImplementedError

    def _comm_error_observation(self, address: SourceAddress, error: DriverError) -> RawSourceObservation:
        from plugins.common.driver_contracts import to_raw_observation

        quality = "COMM_ERROR" if error.code in _CONNECTION_LEVEL_ERROR_CODES else "BAD"
        return to_raw_observation(
            connector_id=self.connector_config.get("connector_id", "unknown"),
            connector_version=self.connector_config.get("connector_version", "0.0.0"),
            device_id=self.connector_config.get("device_id", "unknown"),
            mapping_id=address.extra.get("mapping_id", address.address),
            source=SourceRef(protocol=address.protocol, address=address.address, native_data_type=address.data_type),
            value=None,  # DRV-FR-009: never substitute a last-good value as current without STALE quality
            unit=address.extra.get("unit"),
            quality_hint=quality,
        )

    def poll(self) -> Iterable[RawSourceObservation]:
        return self._loop.run_until_complete(self._poll_async())

    async def _poll_async(self) -> list[RawSourceObservation]:
        observations: list[RawSourceObservation] = []

        if self._connection is None:
            if time.monotonic() < self._next_connect_attempt_monotonic:
                return observations  # backoff window not elapsed yet -- avoid a network storm
            try:
                self._connection = await self._driver.connect(self.connector_config)
                if self._was_connected:
                    logger.info(
                        "connector=%s RECONNECTED after %d attempt(s) -- gap boundary at this point "
                        "in the source stream (DRV-FR-021); see SG-189 for why this is a log line, "
                        "not an observation-stream event",
                        self.connector_config.get("connector_id"), self._connect_attempt,
                    )
                else:
                    logger.info("connector=%s CONNECTED", self.connector_config.get("connector_id"))
                self._was_connected = True
                self._connect_attempt = 0
            except DriverError as exc:
                self._connect_attempt += 1
                delay = backoff_delay_seconds(self._connect_attempt - 1)
                self._next_connect_attempt_monotonic = time.monotonic() + delay
                logger.warning(
                    "connector=%s connect failed (attempt=%d, code=%s, retry_in=%.1fs): %s",
                    self.connector_config.get("connector_id"), self._connect_attempt, exc.code, delay, exc,
                )
                for address in self._addresses:
                    observations.append(self._comm_error_observation(address, exc))
                return observations

        if self._rate_limiter is not None:
            try:
                self._rate_limiter.check()
            except DriverError as exc:
                logger.debug("connector=%s poll rate limited: %s", self.connector_config.get("connector_id"), exc)
                return observations

        opts = ReadOptions(timeout_seconds=float(self.connector_config.get("read_timeout_seconds", 5.0)))
        for address in self._addresses:
            try:
                observations.append(await self._driver.read_once(address, opts))
            except DriverError as exc:
                logger.warning(
                    "connector=%s read failed for address=%s (code=%s): %s",
                    self.connector_config.get("connector_id"), address.address, exc.code, exc,
                )
                observations.append(self._comm_error_observation(address, exc))
                if exc.code in _CONNECTION_LEVEL_ERROR_CODES:
                    # A connection-level failure invalidates the whole session, not just this one
                    # address -- drop it so the next poll() reconnects rather than re-using a dead
                    # session for the remaining addresses in this same cycle.
                    try:
                        await self._driver.disconnect(reason=f"read failure: {exc.code}")
                    except Exception:  # noqa: BLE001 -- best-effort cleanup only
                        pass
                    self._connection = None
                    break
        return observations