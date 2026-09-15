"""SNMP client driver -- Document 44 (SPEC-EDGE-002) DRV-FR-012 ("Support v3 preferred with scoped
credentials, OID mapping and polling/trap profile where appropriate").

SNMPv3 only (USM authentication + privacy) -- Document 44 section 8 says "Prefer SNMPv3 auth/privacy"
and this codebase's Security section 10 lists "SNMPv3 preferred" among its non-negotiables; v1/v2c
(community-string, no encryption) is not implemented here so this reference build cannot be misconfigured
into the weaker default. OID mapping is versioned the same way every other driver's mapping is -- each
`SourceAddress.extra["mapping_id"]` names one released config entry, never an ad-hoc OID typed at runtime.
Trap ingestion (the other half of "polling/trap profile") is out of scope for this reference driver: it is
a passive listener role, architecturally different from every other driver in this codebase (which all
poll or subscribe outward), and Document 44 does not specify trap authentication/dedup semantics beyond
"separately authenticated" -- building one honestly needs its own design pass, not a guess bolted onto the
polling driver.

Uses `pysnmp` (BSD-2-Clause; Document 104 justification recorded in `edge/pyproject.toml`). Tests run
against a real local SNMPv3 agent (`pysnmp.entity` command responder) in `edge/tests/test_plugin_snmp.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from plugins.common.driver_contracts import (
    AuthFailed,
    ConnectionResult,
    DriverHealth,
    EdgeDriver,
    EndpointUnreachable,
    ProtocolException,
    ReadOptions,
    ReadTimeout,
    SourceAddress,
    SourceMappingNotFound,
    to_raw_observation,
)
from runtime.contracts import RawSourceObservation, SourceRef, utcnow

_AUTH_PROTOCOLS_BY_NAME: dict[str, Any] = {}
_PRIV_PROTOCOLS_BY_NAME: dict[str, Any] = {}


def _load_protocol_tables() -> None:
    """Deferred import -- `pysnmp.hlapi.v3arch.asyncio` pulls in the full USM/crypto stack, which this
    codebase's other protocol plugins (Modbus/OPC UA/MQTT) must never see (Document 44 Prohibitions)."""
    if _AUTH_PROTOCOLS_BY_NAME:
        return
    import pysnmp.hlapi.v3arch.asyncio as hl

    _AUTH_PROTOCOLS_BY_NAME.update({
        "NONE": hl.USM_AUTH_NONE, "MD5": hl.USM_AUTH_HMAC96_MD5, "SHA": hl.USM_AUTH_HMAC96_SHA,
        "SHA224": hl.USM_AUTH_HMAC128_SHA224, "SHA256": hl.USM_AUTH_HMAC192_SHA256,
        "SHA384": hl.USM_AUTH_HMAC256_SHA384, "SHA512": hl.USM_AUTH_HMAC384_SHA512,
    })
    _PRIV_PROTOCOLS_BY_NAME.update({
        "NONE": hl.USM_PRIV_NONE, "DES": hl.USM_PRIV_CBC56_DES, "3DES": hl.USM_PRIV_CBC168_3DES,
        "AES128": hl.USM_PRIV_CFB128_AES, "AES192": hl.USM_PRIV_CFB192_AES, "AES256": hl.USM_PRIV_CFB256_AES,
    })


def classify_snmp_error(error_indication: object) -> Exception:
    """pysnmp reports both transport-level failures (timeout, unreachable) and USM auth/decryption
    failures through the same `errorIndication` string slot -- there is no separate exception type to
    catch, so classification is by message content, same technique as `plugins/modbus/driver.py::
    classify_modbus_exception`'s CRC-vs-timeout split for `ModbusIOException`.

    Real, empirically-confirmed limitation (proven against a real local SNMPv3 agent in this pass, not
    assumed from documentation): USM's engine-discovery/report exchange gives a distinguishable message
    ("Unknown USM user") only when the *username itself* is unrecognized. A correctly-named user with a
    *wrong* auth or privacy key is, by design, indistinguishable from a network timeout -- a compliant
    SNMPv3 agent silently drops a request it cannot authenticate/decrypt rather than confirming which
    credential was wrong (this is a deliberate anti-enumeration security property of USM, not a gap in
    this driver). `classify_snmp_error()` therefore only ever returns `AuthFailed` for the narrow set of
    errors USM actually reports; a wrong password for a real username surfaces as `ReadTimeout` here, and
    callers must not expect anything more precise than the protocol itself provides."""
    text = str(error_indication).lower()
    if any(needle in text for needle in ("unknown usm user", "wrong digest", "decryption error", "unsupported security level", "authorization error")):
        return AuthFailed(str(error_indication))
    if "timeout" in text or "no snmp response" in text:
        return ReadTimeout(str(error_indication))
    return EndpointUnreachable(str(error_indication))


def _check_no_such_value(raw_value: object, address: str) -> None:
    """A plain SNMP GET on a nonexistent OID or one outside the caller's VACM view does not set the PDU's
    `error_status` (that is an SNMPv1-only behavior) -- SNMPv2c/v3 instead returns a special exception
    value (`NoSuchObject`/`NoSuchInstance`/`EndOfMibView`) *as the varbind's value*. Missing this check
    would silently turn "this OID does not exist/is not authorized" into a fabricated GOOD-quality
    observation carrying that exception object's `prettyPrint()` string as if it were real data --
    confirmed by first running this test without the check and observing exactly that fabrication."""
    import pysnmp.hlapi.v3arch.asyncio as hl

    if isinstance(raw_value, (hl.NoSuchObject, hl.NoSuchInstance, hl.EndOfMibView)):
        raise SourceMappingNotFound(f"SNMP OID {address} does not exist or is outside the authorized view: {raw_value.prettyPrint()}")


def _decode_snmp_value(value: object) -> object:
    """SNMP numeric types (Integer/Counter32/Counter64/Gauge32/TimeTicks/Unsigned32) all support
    `int()`; everything else (OctetString/ObjectIdentifier/IpAddress/...) is rendered through its own
    `prettyPrint()` -- the same "never guess, ask the type" approach `plugins/modbus/codec.py` uses for
    byte order rather than pattern-matching on class names."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value.prettyPrint()) if hasattr(value, "prettyPrint") else str(value)


class SnmpDriver(EdgeDriver):
    def __init__(self, connector_id: str, connector_version: str, device_id: str) -> None:
        self.connector_id = connector_id
        self.connector_version = connector_version
        self.device_id = device_id
        self._engine = None
        self._auth_data = None
        self._transport_target = None
        self._context_data = None
        self._session_id: str | None = None
        self._error_count = 0
        self._last_success_at: datetime | None = None

    async def connect(self, config: dict[str, Any]) -> ConnectionResult:
        _load_protocol_tables()
        import pysnmp.hlapi.v3arch.asyncio as hl

        try:
            auth_protocol = _AUTH_PROTOCOLS_BY_NAME[config.get("auth_protocol", "SHA")]
            priv_protocol = _PRIV_PROTOCOLS_BY_NAME[config.get("priv_protocol", "AES128")]
        except KeyError as exc:
            raise EndpointUnreachable(f"unsupported SNMP auth/priv protocol name: {exc}") from exc

        self._engine = hl.SnmpEngine()
        self._auth_data = hl.UsmUserData(
            config["username"], authKey=config.get("auth_key"), privKey=config.get("priv_key"),
            authProtocol=auth_protocol, privProtocol=priv_protocol,
        )
        timeout = float(config.get("connect_timeout_seconds", 5.0))
        try:
            self._transport_target = await hl.UdpTransportTarget.create(
                (config["host"], int(config.get("port", 161))), timeout=timeout, retries=0
            )
        except Exception as exc:  # noqa: BLE001 -- pysnmp raises plain Exception for DNS/socket setup failures
            raise EndpointUnreachable(f"SNMP transport setup failed: {exc}", raw_detail=str(exc)) from exc
        self._context_data = hl.ContextData()

        # Preflight GET (first configured mapping's OID, or an explicit health_check_oid) so connect/auth
        # failures surface at connect() time -- Document 44 section 12's mandatory contract test.
        probe_oid = config.get("health_check_oid") or (config.get("mappings") or [{}])[0].get("oid")
        if probe_oid:
            error_indication, error_status, _error_index, var_binds = await hl.get_cmd(
                self._engine, self._auth_data, self._transport_target, self._context_data,
                hl.ObjectType(hl.ObjectIdentity(probe_oid)),
            )
            if error_indication:
                classified = classify_snmp_error(error_indication)
                # Connect-phase semantics match every other driver in this codebase (Modbus/OPC UA/MQTT/
                # REST): a connect-time failure is EndpointUnreachable unless it is a *specifically*
                # identified auth problem (see classify_snmp_error's docstring for why most credential
                # failures cannot be told apart from a timeout at the protocol level).
                if isinstance(classified, AuthFailed):
                    raise classified
                raise EndpointUnreachable(str(classified), raw_detail=str(error_indication))
            if error_status:
                raise ProtocolException(f"SNMP preflight GET returned error_status={error_status}")
            _check_no_such_value(var_binds[0][1], probe_oid)

        self._session_id = str(uuid.uuid4())
        self._last_success_at = utcnow()
        return ConnectionResult(
            session_id=self._session_id,
            capabilities={"read": True, "write": False, "subscribe": False, "browse": False},
        )

    async def disconnect(self, reason: str) -> None:
        self._engine = None
        self._auth_data = None
        self._transport_target = None
        self._context_data = None
        self._session_id = None

    async def read_once(self, address: SourceAddress, opts: ReadOptions | None = None) -> RawSourceObservation:
        """Note: `opts.timeout_seconds` is accepted for interface conformance but not applied per call --
        pysnmp's `UdpTransportTarget` carries its own timeout/retries fixed at `connect()` time, and
        pysnmp's asyncio hlapi has no per-`get_cmd()` timeout override. A connector needing a different
        read timeout than its connect-time configuration reconnects with a new `connect_timeout_seconds`;
        this is a real, documented limitation, not a silent gap."""
        if self._engine is None:
            raise EndpointUnreachable("SNMP driver used before connect()")
        import pysnmp.hlapi.v3arch.asyncio as hl

        error_indication, error_status, _error_index, var_binds = await hl.get_cmd(
            self._engine, self._auth_data, self._transport_target, self._context_data,
            hl.ObjectType(hl.ObjectIdentity(address.address)),
        )
        if error_indication:
            self._error_count += 1
            raise classify_snmp_error(error_indication)
        if error_status:
            self._error_count += 1
            raise SourceMappingNotFound(f"SNMP OID {address.address} returned error_status={error_status}")

        _oid, raw_value = var_binds[0]
        try:
            _check_no_such_value(raw_value, address.address)
        except SourceMappingNotFound:
            self._error_count += 1
            raise
        self._last_success_at = utcnow()
        return to_raw_observation(
            connector_id=self.connector_id,
            connector_version=self.connector_version,
            device_id=self.device_id,
            mapping_id=address.extra.get("mapping_id", address.address),
            source=SourceRef(protocol="SNMP", address=address.address),
            value=_decode_snmp_value(raw_value),
            unit=address.extra.get("unit"),
            quality_hint="GOOD",
        )

    async def health_check(self) -> DriverHealth:
        connected = self._engine is not None
        return DriverHealth(
            connected=connected, last_success_at=self._last_success_at, error_count=self._error_count,
            latency_ms=None, diagnostics={"session_id": self._session_id},
        )
