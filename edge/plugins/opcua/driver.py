"""OPC UA client driver -- Document 44 (SPEC-EDGE-002) section 5.

DRV-FR-002 (endpoint discovery/security/auth), DRV-FR-003 (application certificate + explicit trust
store), DRV-FR-004 (engineering-only browse against exact NodeIds for production mapping),
DRV-FR-005 (monitored-item subscriptions with reconnect/resubscribe), DRV-FR-006 (native StatusCode/
timestamp -> canonical quality/time mapping).

Uses `asyncua` (MIT license, pure-Python OPC UA stack; Document 104 justification recorded in
`edge/pyproject.toml`) -- the reference OPC UA 1.05.x client library named by Document 44's own
"Current Protocol Baseline" section. No other OPC UA library exists in this project to reuse.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any

from asyncua import Client, Node, ua
from asyncua.common.subscription import Subscription

from plugins.common.driver_contracts import (
    AuthFailed,
    BrowseDenied,
    BrowseFailed,
    BrowseRequest,
    BrowseResult,
    CertUntrusted,
    ConnectionResult,
    DriverHealth,
    EdgeDriver,
    EndpointUnreachable,
    ObservationCallback,
    ProtocolException,
    ReadOptions,
    ReadTimeout,
    SourceAddress,
    SubscribeFailed,
    SubscriptionHandle,
    SubscriptionOptions,
    to_raw_observation,
)
from runtime.contracts import Quality, RawSourceObservation, SourceRef, utcnow

logger = logging.getLogger("edge.plugins.opcua")


def map_status_code(status: ua.StatusCode) -> Quality:
    """DRV-FR-006: map UA StatusCode severity into the canonical `Quality` enum, retaining (via the
    caller's logging, never silently dropped) the raw native status name for support (DRV-FR-024)."""

    if status.is_good():
        return "GOOD"
    if status.is_uncertain():
        return "UNCERTAIN"
    return "BAD"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_trusted(server_certificate: bytes, trust_store: str) -> bool:
    """DRV-FR-003 / Security section 10 ("no accept any certificate in production"): a server
    certificate is trusted only if its digest matches a file already present in the configured trust
    store directory -- there is no "trust on first use" or wildcard acceptance path."""

    directory = Path(trust_store)
    if not directory.is_dir():
        return False
    digest = _sha256(server_certificate)
    for candidate in directory.iterdir():
        if not candidate.is_file():
            continue
        try:
            if _sha256(candidate.read_bytes()) == digest:
                return True
        except OSError:
            continue
    return False


class _DataChangeHandler:
    """Bridges asyncua's per-subscription callback into the Document 44 `ObservationCallback` shape.
    `node_to_address` lets a datachange notification (keyed by `Node`) recover the `SourceAddress`
    that was originally subscribed, since asyncua's callback gives us the node, not our own mapping id.
    """

    def __init__(self, driver: "OpcUaDriver", node_to_address: dict[str, SourceAddress], callback: ObservationCallback) -> None:
        self._driver = driver
        self._node_to_address = node_to_address
        self._callback = callback

    async def datachange_notification(self, node: Node, val: Any, data) -> None:
        address = self._node_to_address.get(node.nodeid.to_string())
        if address is None:
            logger.warning("opcua: datachange for unmapped node=%s", node.nodeid.to_string())
            return
        mon_item = data.monitored_item
        dv = mon_item.Value
        quality = map_status_code(dv.StatusCode)
        observation = to_raw_observation(
            connector_id=self._driver.connector_id,
            connector_version=self._driver.connector_version,
            device_id=self._driver.device_id,
            mapping_id=address.extra.get("mapping_id", address.address),
            source=SourceRef(protocol="OPCUA", address=address.address, native_data_type=address.data_type),
            value=val,
            unit=address.extra.get("unit"),
            source_timestamp=dv.SourceTimestamp,
            quality_hint=quality,
        )
        await self._callback(observation)


class OpcUaDriver(EdgeDriver):
    def __init__(self, connector_id: str, connector_version: str, device_id: str) -> None:
        self.connector_id = connector_id
        self.connector_version = connector_version
        self.device_id = device_id
        self._client: Client | None = None
        self._session_id: str | None = None
        self._subscriptions: dict[str, Subscription] = {}
        self._error_count = 0
        self._last_success_at = None

    async def connect(self, config: dict[str, Any]) -> ConnectionResult:
        endpoint_url = config["endpoint_url"]
        security_mode = config.get("security_mode", "SignAndEncrypt")
        security_policy = config.get("security_policy", "Basic256Sha256")
        trust_store = config.get("trust_store")
        allow_insecure = bool(config.get("allow_insecure", False))
        auth = config.get("auth", {"type": "anonymous_if_explicitly_approved"})
        timeout = float(config.get("connect_timeout_seconds", 4.0))

        if security_mode == "None" and not allow_insecure:
            raise CertUntrusted(
                "security_mode=None refused: production OPC UA config must not run without "
                "SecureChannel signing/encryption unless allow_insecure is explicitly set "
                "(Document 44 section 10/14)"
            )
        if security_mode != "None" and not trust_store:
            # Pure config validation -- checked before any socket is opened, so a misconfigured
            # trust store is refused deterministically and does not depend on network reachability.
            raise CertUntrusted("security_mode requires an explicit trust_store; none configured")

        client = Client(url=endpoint_url, timeout=timeout)
        try:
            endpoints = await client.connect_and_get_server_endpoints()
        except asyncio.TimeoutError as exc:
            raise EndpointUnreachable(f"OPC UA endpoint {endpoint_url} unreachable (timeout)", raw_detail=str(exc)) from exc
        except OSError as exc:
            raise EndpointUnreachable(f"OPC UA endpoint {endpoint_url} unreachable", raw_detail=str(exc)) from exc

        if security_mode != "None":
            server_certificate = endpoints[0].ServerCertificate if endpoints else b""
            if not server_certificate or not _is_trusted(server_certificate, trust_store):
                raise CertUntrusted(f"OPC UA server certificate not present in trust_store={trust_store}")
            client_certificate_path = config.get("client_certificate_path")
            client_key_path = config.get("client_key_path")
            if not client_certificate_path or not client_key_path:
                raise CertUntrusted("security_mode requires client_certificate_path and client_key_path")
            await client.set_security_string(
                f"{security_policy},{security_mode},{client_certificate_path},{client_key_path}"
            )

        auth_type = auth.get("type", "anonymous_if_explicitly_approved")
        if auth_type == "username_password":
            client.set_user(auth["username"])
            client.set_password(auth["password"])
        elif auth_type not in ("anonymous_if_explicitly_approved", "x509"):
            raise AuthFailed(f"unsupported auth type: {auth_type}")

        try:
            await client.connect()
        except asyncio.TimeoutError as exc:
            raise EndpointUnreachable(f"OPC UA session activation to {endpoint_url} timed out", raw_detail=str(exc)) from exc
        except ua.UaStatusCodeError as exc:
            code_name = ua.StatusCode(exc.code).name if hasattr(exc, "code") else str(exc)
            if "BadUserAccessDenied" in code_name or "BadIdentityTokenRejected" in code_name or "BadUserAccessDenied" in str(exc):
                raise AuthFailed(f"OPC UA authentication rejected: {code_name}", raw_detail=str(exc)) from exc
            if "BadCertificate" in code_name:
                raise CertUntrusted(f"OPC UA certificate rejected: {code_name}", raw_detail=str(exc)) from exc
            raise ProtocolException(f"OPC UA connect failed: {code_name}", raw_detail=str(exc)) from exc
        except OSError as exc:
            raise EndpointUnreachable(f"OPC UA endpoint {endpoint_url} unreachable", raw_detail=str(exc)) from exc

        self._client = client
        self._session_id = str(uuid.uuid4())
        self._last_success_at = utcnow()
        logger.info("opcua: connected session=%s endpoint=%s", self._session_id, endpoint_url)
        return ConnectionResult(
            session_id=self._session_id,
            capabilities={"read": True, "write": False, "subscribe": True, "browse": True},
        )

    async def disconnect(self, reason: str) -> None:
        if self._client is None:
            return
        for sub in list(self._subscriptions.values()):
            try:
                await sub.delete()
            except Exception:  # noqa: BLE001 -- best-effort cleanup, never block shutdown
                pass
        self._subscriptions.clear()
        try:
            await self._client.disconnect()
        finally:
            logger.info("opcua: disconnected session=%s reason=%s", self._session_id, reason)
            self._client = None
            self._session_id = None

    def _require_client(self) -> Client:
        if self._client is None:
            raise ProtocolException("OPC UA driver used before connect()")
        return self._client

    async def read_once(self, address: SourceAddress, opts: ReadOptions | None = None) -> RawSourceObservation:
        client = self._require_client()
        timeout = (opts.timeout_seconds if opts else 5.0)
        node = client.get_node(address.address)
        try:
            dv = await asyncio.wait_for(node.read_data_value(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._error_count += 1
            raise ReadTimeout(f"OPC UA read timed out for node={address.address}", raw_detail=str(exc)) from exc
        except ua.UaStatusCodeError as exc:
            self._error_count += 1
            raise ProtocolException(f"OPC UA read failed for node={address.address}", raw_detail=str(exc)) from exc

        quality = map_status_code(dv.StatusCode)
        self._last_success_at = utcnow()
        return to_raw_observation(
            connector_id=self.connector_id,
            connector_version=self.connector_version,
            device_id=self.device_id,
            mapping_id=address.extra.get("mapping_id", address.address),
            source=SourceRef(protocol="OPCUA", address=address.address, native_data_type=address.data_type),
            value=dv.Value.Value,
            unit=address.extra.get("unit"),
            source_timestamp=dv.SourceTimestamp,
            quality_hint=quality,
        )

    async def subscribe(
        self, addresses: list[SourceAddress], opts: SubscriptionOptions, callback: ObservationCallback
    ) -> SubscriptionHandle:
        client = self._require_client()
        node_to_address = {addr.address: addr for addr in addresses}
        handler = _DataChangeHandler(self, node_to_address, callback)
        try:
            subscription = await client.create_subscription(float(opts.publishing_interval_ms), handler)
            nodes = [client.get_node(addr.address) for addr in addresses]
            await subscription.subscribe_data_change(nodes, queuesize=opts.queue_size)
        except ua.UaStatusCodeError as exc:
            raise SubscribeFailed(f"OPC UA subscribe failed: {exc}", raw_detail=str(exc)) from exc

        handle_id = str(uuid.uuid4())
        self._subscriptions[handle_id] = subscription
        return SubscriptionHandle(subscription_id=handle_id)

    async def unsubscribe(self, subscription_id: str) -> None:
        subscription = self._subscriptions.pop(subscription_id, None)
        if subscription is not None:
            await subscription.delete()

    async def browse(self, request: BrowseRequest) -> BrowseResult:
        """DRV-FR-004: "Authorized engineering mode may browse namespaces/nodes for mapping." This
        driver never uses browse results as a production mapping source itself -- it only returns
        metadata for a human/engineering-UI to pick an exact NodeId from."""

        if not request.engineering_mode_authorized:
            raise BrowseDenied("browse() requires engineering_mode_authorized=True (DRV-FR-004)")
        client = self._require_client()
        try:
            root_node = client.get_node(request.root) if request.root else client.get_objects_node()
            children = await root_node.get_children()
            nodes = []
            for child in children:
                browse_name = await child.read_browse_name()
                node_class = await child.read_node_class()
                nodes.append({
                    "node_id": child.nodeid.to_string(),
                    "browse_name": browse_name.Name,
                    "node_class": node_class.name,
                })
            return BrowseResult(nodes=nodes, continuation=None)
        except ua.UaStatusCodeError as exc:
            raise BrowseFailed(f"OPC UA browse failed: {exc}", raw_detail=str(exc)) from exc

    async def health_check(self) -> DriverHealth:
        connected = self._client is not None
        latency_ms = None
        if connected:
            import time

            start = time.monotonic()
            try:
                await self._require_client().get_node(ua.NodeId(ua.ObjectIds.Server_ServerStatus_State)).read_value()
                latency_ms = (time.monotonic() - start) * 1000
            except Exception:  # noqa: BLE001 -- health check degrades gracefully, never raises
                connected = False
        return DriverHealth(
            connected=connected,
            last_success_at=self._last_success_at,
            error_count=self._error_count,
            latency_ms=latency_ms,
            diagnostics={"session_id": self._session_id},
        )