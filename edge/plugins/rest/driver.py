"""Authenticated REST-polling driver -- Document 44 (SPEC-EDGE-002) DRV-FR-014 ("Support authenticated
REST polling/webhook or controlled file import for instruments producing reports").

Polls a fixed REST endpoint per configured address (path) and extracts a value from the JSON response
body through a configured dotted field path (e.g. `data.value`) -- the "versioned decoder" discipline for
REST here is simply that the field path is part of the released connector config (Document 44 section 2's
"no arbitrary parsing" spirit already codified for MQTT applies just as much to a REST body: the caller
must say exactly which field is the value, not have the driver guess).

Uses `httpx` (already an approved dependency for this repo -- Document 104 justification recorded in
`edge/pyproject.toml`; no new dependency). Tested against a real local HTTP server (`edge/tests/
test_plugin_rest.py` starts a real `http.server`-based instrument stand-in).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import httpx

from plugins.common.driver_contracts import (
    AuthFailed,
    ConnectionResult,
    DriverHealth,
    EdgeDriver,
    EndpointUnreachable,
    PayloadSchemaInvalid,
    ProtocolException,
    ReadOptions,
    ReadTimeout,
    SourceAddress,
    to_raw_observation,
)
from runtime.contracts import RawSourceObservation, SourceRef, utcnow


def _get_dotted(obj: Any, dotted_path: str) -> Any:
    current = obj
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise PayloadSchemaInvalid(f"REST response missing field path {dotted_path!r} at segment {part!r}")
        current = current[part]
    return current


def _build_auth(auth_config: dict | None) -> tuple[dict[str, str], httpx.Auth | None]:
    if not auth_config:
        return {}, None
    auth_type = auth_config.get("type")
    if auth_type == "bearer":
        return {"Authorization": f"Bearer {auth_config['token']}"}, None
    if auth_type == "basic":
        return {}, httpx.BasicAuth(auth_config["username"], auth_config["password"])
    if auth_type in (None, "none"):
        return {}, None
    raise ValueError(f"unsupported REST auth type: {auth_type!r}")


class RestPollingDriver(EdgeDriver):
    def __init__(self, connector_id: str, connector_version: str, device_id: str) -> None:
        self.connector_id = connector_id
        self.connector_version = connector_version
        self.device_id = device_id
        self._client: httpx.AsyncClient | None = None
        self._session_id: str | None = None
        self._error_count = 0
        self._last_success_at: datetime | None = None

    async def connect(self, config: dict[str, Any]) -> ConnectionResult:
        try:
            headers, httpx_auth = _build_auth(config.get("auth"))
        except (KeyError, ValueError) as exc:
            raise EndpointUnreachable(f"invalid REST auth configuration: {exc}", raw_detail=str(exc)) from exc

        timeout = float(config.get("connect_timeout_seconds", 5.0))
        client = httpx.AsyncClient(base_url=config["base_url"], headers=headers, auth=httpx_auth, timeout=timeout)

        # Preflight the configured path (or the first mapping's path) so connect/auth failures surface
        # at connect() time -- Document 44 section 12's mandatory "connect/auth failure" contract test.
        probe_path = config.get("path") or (config.get("mappings") or [{}])[0].get("path")
        if probe_path:
            try:
                response = await client.get(probe_path)
            except httpx.ConnectError as exc:
                await client.aclose()
                raise EndpointUnreachable(f"REST connect failed: {exc}", raw_detail=str(exc)) from exc
            except httpx.TimeoutException as exc:
                await client.aclose()
                raise EndpointUnreachable(f"REST connect timed out: {exc}", raw_detail=str(exc)) from exc
            if response.status_code in (401, 403):
                await client.aclose()
                raise AuthFailed(f"REST auth failed: HTTP {response.status_code}", raw_detail=response.text[:200])
            if response.status_code >= 500:
                await client.aclose()
                raise EndpointUnreachable(f"REST endpoint returned HTTP {response.status_code}", raw_detail=response.text[:200])

        self._client = client
        self._session_id = str(uuid.uuid4())
        self._last_success_at = utcnow()
        return ConnectionResult(
            session_id=self._session_id,
            capabilities={"read": True, "write": False, "subscribe": False, "browse": False},
        )

    async def disconnect(self, reason: str) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None
        self._session_id = None

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise EndpointUnreachable("REST driver used before connect()")
        return self._client

    async def read_once(self, address: SourceAddress, opts: ReadOptions | None = None) -> RawSourceObservation:
        client = self._require_client()
        timeout = opts.timeout_seconds if opts else 5.0
        try:
            response = await client.get(address.address, timeout=timeout)
        except httpx.TimeoutException as exc:
            self._error_count += 1
            raise ReadTimeout(f"REST GET {address.address} timed out after {timeout}s", raw_detail=str(exc)) from exc
        except httpx.ConnectError as exc:
            self._error_count += 1
            raise EndpointUnreachable(f"REST GET {address.address} connection failed: {exc}", raw_detail=str(exc)) from exc

        if response.status_code in (401, 403):
            self._error_count += 1
            raise AuthFailed(f"REST auth failed: HTTP {response.status_code}", raw_detail=response.text[:200])
        if response.status_code >= 400:
            self._error_count += 1
            raise ProtocolException(f"REST GET {address.address} returned HTTP {response.status_code}", raw_detail=response.text[:200])

        try:
            body = response.json()
        except ValueError as exc:
            self._error_count += 1
            raise PayloadSchemaInvalid(f"REST response from {address.address} is not valid JSON", raw_detail=str(exc)) from exc

        value = _get_dotted(body, address.extra["value_field"])
        unit_field = address.extra.get("unit_field")
        unit = _get_dotted(body, unit_field) if unit_field else address.extra.get("unit")

        self._last_success_at = utcnow()
        return to_raw_observation(
            connector_id=self.connector_id,
            connector_version=self.connector_version,
            device_id=self.device_id,
            mapping_id=address.extra.get("mapping_id", address.address),
            source=SourceRef(protocol="REST", address=address.address),
            value=value,
            unit=unit,
            quality_hint="GOOD",
        )

    async def health_check(self) -> DriverHealth:
        connected = self._client is not None
        return DriverHealth(
            connected=connected, last_success_at=self._last_success_at, error_count=self._error_count,
            latency_ms=None, diagnostics={"session_id": self._session_id},
        )
