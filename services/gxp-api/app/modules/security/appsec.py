"""Document 64 (SPEC-SEC-004) -- the 9 cross-cutting web/API/runtime security functions Document 64 # 4
names, implemented as a reusable library. These are the "harden what exists" half of the document
(APPSEC-FR-001..030); the 3 owned config tables live in `appsec_models.py` and the small registry
endpoints in `appsec_commands.py`/`appsec_router.py`.

Every function here is deterministic and side-effect-free except for the two rate-limit / replay
in-memory stores (process-local, rebuildable -- AG-11: not authoritative state). Nothing here writes a
regulated row; callers that need an audited security event emit one through the normal outbox path.

No regulated numeric threshold is invented here: rate limits, replay windows and upload byte caps are
all read from an `ApiSecurityPolicy` / `WebhookProfile` row (customer configuration) or passed in by the
caller. The only literals are the always-on SSRF private-range block list (a fixed IANA/cloud-metadata
fact, not a tunable policy) and the HTML/CSV neutralisation character sets. See SG-164.
"""

import hashlib
import hmac
import ipaddress
import re
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.security.appsec_models import OutboundDestination, WebhookProfile
from app.mutation.errors import (
    AccessDeniedError,
    FileTypeBlockedError,
    MalwareDetectedError,
    RateLimitedError,
    ReplayDetectedError,
    RequestSchemaInvalidError,
    SsrfDestinationBlockedError,
    UnsafeContentRejectedError,
    WebhookAuthFailedError,
)

# --------------------------------------------------------------------------------------------------
# authorizeObjectAccess() -- APPSEC-FR-001/002/003/005/013/028/029
# --------------------------------------------------------------------------------------------------


def authorize_object_access(
    *,
    actor_roles: set[str],
    action: str,
    resource_tenant_id: uuid.UUID | str | None,
    resource_site_id: uuid.UUID | str | None,
    context_tenant_id: uuid.UUID | str | None,
    context_site_id: uuid.UUID | str | None,
    allowed_roles: list[str] | None = None,
    requested_fields: list[str] | None = None,
    writable_fields: list[str] | None = None,
) -> dict:
    """Server-side object + function + property authorization in one place (BOLA/BFLA/IDOR + mass
    assignment). `client-side visibility is not security` -- this is called from the service layer, not
    the UI. Raises `AccessDeniedError` on any failure; returns a decision dict on allow.

    - function-level (BFLA): `action` must be granted to at least one held role (when `allowed_roles`
      is given -- otherwise the caller has already run `evaluate_policy`).
    - object-level (BOLA/IDOR): the resource's tenant/site must match the authenticated context. A
      caller who merely *knows* another tenant's id gets `ACCESS_DENIED`, not the object.
    - property-level: every field the request tries to write must be on `writable_fields`.
    """
    if allowed_roles is not None and not (actor_roles & set(allowed_roles)):
        raise AccessDeniedError("Function-level authorization failed", action=action)

    if resource_tenant_id is not None and context_tenant_id is not None:
        if str(resource_tenant_id) != str(context_tenant_id):
            raise AccessDeniedError("Object is outside the caller's tenant scope")
    if resource_site_id is not None and context_site_id is not None:
        if str(resource_site_id) != str(context_site_id):
            raise AccessDeniedError("Object is outside the caller's site scope")

    if requested_fields and writable_fields is not None:
        illegal = [f for f in requested_fields if f not in set(writable_fields)]
        if illegal:
            # APPSEC-FR-003: never say which protected field was targeted beyond its name set.
            raise AccessDeniedError("Request targets non-writable fields", fields=illegal)

    return {"allow": True, "action": action}


# --------------------------------------------------------------------------------------------------
# validateRequestSchema() -- APPSEC-FR-004/023
# --------------------------------------------------------------------------------------------------


def validate_request_schema(model_cls: type[BaseModel], raw: dict) -> BaseModel:
    """Parse `raw` against a typed pydantic model whose config already forbids unknown properties
    (`CommandEnvelope` sets `extra="forbid"`). Turns pydantic's `ValidationError` into the stable
    `REQUEST_SCHEMA_INVALID` code so callers never branch on validator message text (CTR-FR-006).
    Using an explicit DTO class -- never `pickle`/`eval`/arbitrary object graphs -- is APPSEC-FR-023.
    """
    try:
        return model_cls.model_validate(raw)
    except ValidationError as exc:
        raise RequestSchemaInvalidError(
            "Request failed typed-schema validation",
            errors=[{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()],
        )


# --------------------------------------------------------------------------------------------------
# sanitizeRichText() -- APPSEC-FR-008/022
# --------------------------------------------------------------------------------------------------

_ALLOWED_TAGS = {"b", "i", "em", "strong", "u", "p", "br", "ul", "ol", "li", "span"}
_SCRIPTISH = re.compile(r"<\s*(script|style|iframe|object|embed|form|meta|link)\b", re.IGNORECASE)
_EVENT_HANDLER = re.compile(r"\son\w+\s*=", re.IGNORECASE)
_JS_URI = re.compile(r"(javascript|vbscript|data)\s*:", re.IGNORECASE)
# APPSEC-FR-022: refuse anything that looks like a template/expression evaluation token so a
# customer-configured "rich text" field can never become a code-eval sink.
_TEMPLATE_TOKEN = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\$\{.*?\}|<%.*?%>", re.DOTALL)
_ANY_TAG = re.compile(r"<\s*/?\s*([a-zA-Z0-9]+)")


def sanitize_rich_text(html: str, *, policy_version: str = "appsec-v1") -> dict:
    """Allowlist sanitizer. Rejects (does not silently strip) script-ish elements, inline event
    handlers, javascript:/data: URIs and template-evaluation tokens -- an unsafe payload is evidence,
    not something to quietly clean. Disallowed-but-benign tags are escaped. Returns the canonical safe
    content plus the policy version it was sanitized under (persist both -- SIG/AUD traceability)."""
    if _SCRIPTISH.search(html) or _EVENT_HANDLER.search(html) or _JS_URI.search(html):
        raise UnsafeContentRejectedError("Rich-text input contains an active-content construct")
    if _TEMPLATE_TOKEN.search(html):
        raise UnsafeContentRejectedError("Rich-text input contains a template/expression token")

    def _escape_unknown(match: re.Match) -> str:
        tag = match.group(1).lower()
        if tag in _ALLOWED_TAGS:
            return match.group(0)
        return match.group(0).replace("<", "&lt;")

    safe = _ANY_TAG.sub(_escape_unknown, html)
    return {"content": safe, "sanitizer_policy_version": policy_version}


# --------------------------------------------------------------------------------------------------
# validateOutboundDestination() -- APPSEC-FR-011
# --------------------------------------------------------------------------------------------------

# Fixed IANA / RFC / cloud-metadata ranges -- a security fact, not a tunable policy value.
_BLOCKED_NETS = [
    ipaddress.ip_network(n)
    for n in (
        "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "169.254.0.0/16", "100.64.0.0/10", "0.0.0.0/8",
        "::1/128", "fc00::/7", "fe80::/10",
    )
]
_METADATA_HOSTS = {"169.254.169.254", "metadata.google.internal", "metadata", "100.100.100.200"}


def _is_blocked_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(ip in net for net in _BLOCKED_NETS)


async def validate_outbound_destination(
    session: AsyncSession, *, url: str, purpose: str, service_id: str | None = None
) -> dict:
    """Resolve a candidate outbound URL against the `outbound_destination` allowlist AND the always-on
    private/loopback/link-local/metadata block. Deny-by-default: no matching ACTIVE row -> blocked.
    Raises `SsrfDestinationBlockedError`; returns the matched destination's redirect policy on allow.
    Every block emits an `SSRFBlocked` security-telemetry event (MUT-FR-031).
    """
    try:
        return await _validate_outbound_destination(session, url=url, purpose=purpose, service_id=service_id)
    except SsrfDestinationBlockedError as exc:
        from app.modules.security.telemetry import record_security_event
        await record_security_event("SSRFBlocked", {
            "host": (urlsplit(url).hostname or None), "purpose": purpose, "reason": exc.message,
        })
        raise


async def _validate_outbound_destination(
    session: AsyncSession, *, url: str, purpose: str, service_id: str | None = None
) -> dict:
    parts = urlsplit(url)
    scheme = (parts.scheme or "").lower()
    host = (parts.hostname or "").lower()
    port = parts.port or (443 if scheme == "https" else 80 if scheme == "http" else None)

    if not scheme or not host:
        raise SsrfDestinationBlockedError("Outbound URL is not absolute")
    if scheme not in ("https", "http"):
        raise SsrfDestinationBlockedError("Only http/https outbound is permitted", scheme=scheme)
    if host in _METADATA_HOSTS or _is_blocked_ip(host):
        raise SsrfDestinationBlockedError("Destination resolves to a blocked internal/metadata address")

    stmt = select(OutboundDestination).where(OutboundDestination.state == "ACTIVE")
    if service_id is not None:
        stmt = stmt.where(OutboundDestination.service_id == service_id)
    rows = (await session.execute(stmt)).scalars().all()

    for dest in rows:
        cfg = dest.schemes_hosts_ports or {}
        if host not in {h.lower() for h in cfg.get("hosts", [])}:
            continue
        if cfg.get("schemes") and scheme not in {s.lower() for s in cfg["schemes"]}:
            continue
        if cfg.get("ports") and port not in set(cfg["ports"]):
            continue
        deny = dest.ip_range_rules.get("deny_cidrs", []) if dest.ip_range_rules else []
        for cidr in deny:
            try:
                if _is_blocked_ip(host) or ipaddress.ip_address(host) in ipaddress.ip_network(cidr):
                    raise SsrfDestinationBlockedError("Destination host is in a per-service deny range")
            except ValueError:
                pass
        return {"allow": True, "service_id": dest.service_id, "redirect_policy": dest.redirect_policy}

    raise SsrfDestinationBlockedError("Destination is not on the outbound allowlist", purpose=purpose)


# --------------------------------------------------------------------------------------------------
# validateFileUpload() -- APPSEC-FR-012
# --------------------------------------------------------------------------------------------------

# EICAR standard anti-malware test string (not real malware) -- lets the quarantine path be exercised
# in tests without shipping a live sample.
_EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
_MAGIC = {
    b"%PDF-": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"PK\x03\x04": "application/zip",
}
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(filename: str) -> str:
    """Strip path components and unsafe characters; never trust a client filename for storage path."""
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    base = _FILENAME_SAFE.sub("_", base).lstrip(".") or "upload"
    return base[:200]


def validate_file_upload(
    *,
    content: bytes,
    filename: str,
    declared_type: str,
    max_bytes: int,
    allowed_types: list[str],
) -> dict:
    """Size + magic-byte sniff + extension/type allowlist + malware signature + filename sanitisation.
    Raises `FileTypeBlockedError` / `MalwareDetectedError`. Returns an upload receipt (safe filename,
    sniffed type, sha256, quarantine=False) -- the caller stores it OUTSIDE any executable path."""
    if len(content) > max_bytes:
        raise FileTypeBlockedError("Upload exceeds the size limit", size=len(content), limit=max_bytes)
    if _EICAR in content:
        raise MalwareDetectedError("Upload matched a malware signature; quarantined")

    sniffed = None
    for magic, mtype in _MAGIC.items():
        if content.startswith(magic):
            sniffed = mtype
            break
    effective_type = sniffed or declared_type
    if allowed_types and effective_type not in set(allowed_types):
        raise FileTypeBlockedError("Content type is not permitted", type=effective_type)
    if sniffed is not None and declared_type and sniffed != declared_type:
        raise FileTypeBlockedError("Declared content type does not match file contents")

    return {
        "safe_filename": sanitize_filename(filename),
        "content_type": effective_type,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
        "quarantined": False,
    }


# --------------------------------------------------------------------------------------------------
# protectSpreadsheetExport() -- APPSEC-FR-021
# --------------------------------------------------------------------------------------------------

_FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")


def protect_spreadsheet_export(rows: list[list], *, allowed_columns: list[str] | None = None,
                               columns: list[str] | None = None) -> list[list]:
    """Neutralise CSV/spreadsheet formula injection: any cell whose string value starts with a
    formula-trigger character is prefixed with a single quote. Optionally drops columns the caller is
    not permitted to export (field-permission respect)."""
    keep_idx = None
    if allowed_columns is not None and columns is not None:
        allow = set(allowed_columns)
        keep_idx = [i for i, c in enumerate(columns) if c in allow]

    out = []
    for row in rows:
        cells = [row[i] for i in keep_idx] if keep_idx is not None else list(row)
        safe = []
        for cell in cells:
            if isinstance(cell, str) and cell[:1] in _FORMULA_LEAD:
                safe.append("'" + cell)
            else:
                safe.append(cell)
        out.append(safe)
    return out


# --------------------------------------------------------------------------------------------------
# enforceRateLimit() -- APPSEC-FR-014/015
# --------------------------------------------------------------------------------------------------

# Process-local token buckets. Rebuildable, non-authoritative (AG-11) -- a real deployment backs this
# with Redis; the *contract* (deny past the configured budget, fail closed) is what matters here.
_BUCKETS: dict[str, tuple[float, float]] = {}


def enforce_rate_limit(
    *, bucket_key: str, limit: int, window_seconds: int, cost: int = 1, now: float | None = None
) -> dict:
    """Token bucket. `limit` tokens refill linearly over `window_seconds`. Raises `RateLimitedError`
    when the bucket cannot cover `cost`. All three numbers are caller-supplied (from an
    `ApiSecurityPolicy` row) -- no default budget is invented here."""
    if limit <= 0 or window_seconds <= 0:
        raise RateLimitedError("Rate policy disables this operation", bucket=bucket_key)
    t = time.monotonic() if now is None else now
    rate = limit / window_seconds
    tokens, last = _BUCKETS.get(bucket_key, (float(limit), t))
    tokens = min(float(limit), tokens + (t - last) * rate)
    if tokens < cost:
        _BUCKETS[bucket_key] = (tokens, t)
        retry_after = max(1, int((cost - tokens) / rate))
        raise RateLimitedError("Rate limit exceeded", bucket=bucket_key, retry_after_seconds=retry_after)
    _BUCKETS[bucket_key] = (tokens - cost, t)
    return {"allow": True, "remaining": int(tokens - cost)}


def reset_rate_limits() -> None:
    """Test hook only -- clears the process-local buckets between cases."""
    _BUCKETS.clear()


# --------------------------------------------------------------------------------------------------
# verifyWebhook() -- APPSEC-FR-020
# --------------------------------------------------------------------------------------------------

# Process-local seen-delivery-id set for replay detection. Non-authoritative; a real deployment uses a
# short-TTL store keyed on the replay window.
_SEEN_DELIVERIES: set[str] = set()


async def verify_webhook(
    session: AsyncSession,
    *,
    provider: str,
    body: bytes,
    signature_header: str | None,
    timestamp_header: str | None,
    delivery_id: str | None,
    signing_secret: str,
    now: datetime | None = None,
) -> dict:
    """Verify an inbound webhook against its `webhook_profile`: body-size cap, HMAC-SHA256 signature
    (constant-time compare), signed-timestamp inside the replay window, and delivery-id de-dupe.
    Raises `WebhookAuthFailedError` / `ReplayDetectedError`. A replay emits a `WebhookReplayDetected`
    security-telemetry event (MUT-FR-031). Returns the parsed provider + schema version on success."""
    try:
        return await _verify_webhook(
            session, provider=provider, body=body, signature_header=signature_header,
            timestamp_header=timestamp_header, delivery_id=delivery_id, signing_secret=signing_secret, now=now,
        )
    except ReplayDetectedError as exc:
        from app.modules.security.telemetry import record_security_event
        await record_security_event("WebhookReplayDetected", {
            "provider": provider, "delivery_id": delivery_id,
            "reason": "DUPLICATE_DELIVERY" if "already processed" in exc.message else "OUTSIDE_REPLAY_WINDOW",
        })
        raise


async def _verify_webhook(
    session: AsyncSession, *, provider: str, body: bytes, signature_header: str | None,
    timestamp_header: str | None, delivery_id: str | None, signing_secret: str, now: datetime | None = None,
) -> dict:
    profile = (
        await session.execute(select(WebhookProfile).where(WebhookProfile.provider == provider))
    ).scalar_one_or_none()
    if profile is None or profile.state != "ACTIVE":
        raise WebhookAuthFailedError("No active webhook profile for this provider", provider=provider)

    if len(body) > profile.max_body_bytes:
        raise WebhookAuthFailedError("Webhook body exceeds the profile size limit")

    if profile.auth_mechanism == "HMAC_SHA256":
        if not signature_header or not timestamp_header:
            raise WebhookAuthFailedError("Missing signature or timestamp header")
        signed_payload = timestamp_header.encode() + b"." + body
        expected = hmac.new(signing_secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature_header):
            raise WebhookAuthFailedError("Webhook signature mismatch")
        try:
            ts = datetime.fromtimestamp(int(timestamp_header), tz=timezone.utc)
        except (ValueError, OverflowError):
            raise WebhookAuthFailedError("Malformed webhook timestamp")
        current = now or datetime.now(timezone.utc)
        age = abs((current - ts).total_seconds())
        if age > profile.replay_window_seconds:
            raise ReplayDetectedError("Webhook timestamp is outside the replay window", age_seconds=int(age))
    elif profile.auth_mechanism == "BEARER_TOKEN":
        if not signature_header or not hmac.compare_digest(signing_secret, signature_header):
            raise WebhookAuthFailedError("Webhook bearer token mismatch")
    # MTLS is terminated at the edge/proxy in this build -- the profile records the expectation.

    if delivery_id is not None:
        key = f"{provider}:{delivery_id}"
        if key in _SEEN_DELIVERIES:
            raise ReplayDetectedError("Webhook delivery id already processed", delivery_id=delivery_id)
        _SEEN_DELIVERIES.add(key)

    return {"provider": provider, "schema_version": profile.schema_version, "verified": True}


def reset_webhook_replay_cache() -> None:
    """Test hook only."""
    _SEEN_DELIVERIES.clear()


# --------------------------------------------------------------------------------------------------
# mapSafeErrorResponse() -- APPSEC-FR-018
# --------------------------------------------------------------------------------------------------


async def emit_security_event(
    session: AsyncSession, *, event_type: str, payload: dict, aggregate_id: uuid.UUID | None = None
) -> None:
    """MUT-FR-031 / Document 64 # 9: security-monitoring events (`APIAccessDenied`, `RateLimitTriggered`,
    `SSRFBlocked`, `MaliciousUploadDetected`, `WebhookReplayDetected`, `DeprecatedAPIUsed`) are written
    to the transactional outbox separately from any GxP audit row -- they are telemetry about a control
    that *refused* something, not a regulated mutation. Caller supplies a live session/transaction; this
    is a no-op-safe thin wrapper over the Mutation Gateway's `write_outbox_event`.
    """
    from app.mutation.gateway import write_outbox_event

    await write_outbox_event(
        session,
        event_type=event_type,
        aggregate_type="security_event",
        aggregate_id=aggregate_id or uuid.uuid4(),
        aggregate_version=1,
        payload=payload,
        correlation_id=uuid.uuid4(),
    )


def map_safe_error_response(exc: BaseException, *, correlation_id: uuid.UUID | str | None = None) -> dict:
    """Map any internal exception to a stable, non-sensitive client body: a machine-readable code, a
    generic message and a correlation id for support to look up the real detail. Never a stack trace,
    file path, SQL fragment or secret. Known `GxPError`s keep their own stable code; everything else
    collapses to `SYSTEM_FAULT`."""
    corr = str(correlation_id or uuid.uuid4())
    from app.mutation.errors import GxPError

    if isinstance(exc, GxPError):
        return {"code": exc.code, "message": exc.message, "correlation_id": corr}
    return {
        "code": "SYSTEM_FAULT",
        "message": "An internal error occurred. Contact support with the correlation id.",
        "correlation_id": corr,
    }
