"""Document 64 (SPEC-SEC-004) -- Application, API, UI & Secure Runtime Engineering. Same `security`
PostgreSQL schema Documents 61/62/63 created; adds the 3 owned entities Document 64's data model (# 6)
and `04_DATA_MODEL_CATALOGUE.md` list: `api_security_policy`, `outbound_destination`, `webhook_profile`.

**This document is mostly "harden what already exists", not "build a new module".** APPSEC-FR-001..030
are cross-cutting web/API/runtime controls (server-side authz, strict input schemas, injection/SSRF/
XSS/CSRF defence, safe file handling, rate limiting, security headers, safe error responses). Those
controls live in `appsec.py` as a reusable library of the 9 functions Document 64 # 4 names
(`authorizeObjectAccess`, `validateRequestSchema`, `sanitizeRichText`, `validateOutboundDestination`,
`validateFileUpload`, `protectSpreadsheetExport`, `enforceRateLimit`, `verifyWebhook`,
`mapSafeErrorResponse`) plus the security-headers / safe-error middleware wired into `app/main.py`.

The 3 owned tables here are the small **configuration backbone** those controls read:

- `api_security_policy` -- per-operation overrides (writable/readable field allowlists, rate limits,
  file/export policy, CORS/CSRF profile). No create endpoint: Document 64 # 7 lists exactly 3 APIs and
  none of them writes this table. Rows are seeded (`scripts/seed.py`) and read by
  `GET /security/v1/api-inventory` and by `appsec.authorize_object_access()` /
  `appsec.enforce_rate_limit()`. Same "catalogue table with no dedicated create function" precedent as
  Document 61's `security_control` (populated by get-or-create, not a `createSecurityControl()`).
- `outbound_destination` -- the SSRF allowlist. Created via `POST /security/v1/outbound-destinations`
  (Mutation Gateway command, **no signature** -- Document 106 has zero rows for any SPEC-SEC-004 action,
  checked the full register rows 133-141; the spec's own API table # 7 shows `Signature: —` for all
  three). Read by `appsec.validate_outbound_destination()`.
- `webhook_profile` -- inbound webhook auth/replay config. Created via
  `POST /security/v1/webhook-profiles` (Mutation Gateway, no signature). Read by
  `appsec.verify_webhook()`.

**No `site_id`.** Document 64 never lists a site field on any of its 3 tables, and its actors
(Frontend/Backend/Integration Developer, Security Engineer, Pen Tester, API Gateway, Policy Service --
# 2) operate at the platform/deployment level. Same precedent as every other `security.*` table.
`tenant_id` dropped per ADR-0006, same as every module since WP-05.

**No binary float for any regulated numeric.** `replay_window_seconds` and `max_body_bytes` are plain
integers; every rate/size limit inside the JSONB policy blobs is an integer count. There is no approved
numeric baseline for the *default* values of those limits anywhere in Documents 106-115 -- they are
customer-configured per row, engineering-default floors only, tracked as SG-164 (non-blocking, same
shape as SG-163's session-timeout gap).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

AUTH_MODES = ("BEARER_JWT", "SESSION_COOKIE", "SERVICE_BEARER", "MTLS", "NONE")
POLICY_STATES = ("ACTIVE", "RETIRED")
DESTINATION_STATES = ("ACTIVE", "SUSPENDED")
WEBHOOK_STATES = ("ACTIVE", "SUSPENDED")
WEBHOOK_AUTH_MECHANISMS = ("HMAC_SHA256", "MTLS", "BEARER_TOKEN")


class ApiSecurityPolicy(Base):
    """Per-operation security policy (Document 64 # 6 `api_security_policy`). Fields map 1:1 to the
    spec's list: operationId / auth mode / allowed roles-scopes / object policy / writable+readable
    field sets / rate+resource limits / file+export policy / CORS+CSRF profile. Seed-populated; read by
    the api-inventory endpoint and the appsec helpers. No create/update endpoint (see module docstring)."""

    __tablename__ = "api_security_policy"
    __table_args__ = (UniqueConstraint("operation_id"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    auth_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="BEARER_JWT")
    # "allowed roles/scopes" -- e.g. {"roles": ["Security Admin"], "scopes": ["security:write"]}.
    allowed_roles_scopes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # "object policy" -- tenant/site derivation + BOLA rules, e.g. {"tenant_from": "auth_context"}.
    object_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # APPSEC-FR-003/005: mass-assignment + output-minimisation allowlists.
    writable_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    readable_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # APPSEC-FR-014/015: {"requests_per_minute": 60, "max_page_size": 200, "cost": 1}.
    rate_resource_limits: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # APPSEC-FR-012/021: {"max_upload_bytes": ..., "allowed_types": [...], "csv_formula_guard": true}.
    file_export_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # APPSEC-FR-009/010: {"cors_allowed_origins": [...], "csrf": "double_submit"|"origin_check"}.
    cors_csrf_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # APPSEC-FR-016/027: deprecation metadata for the inventory. {"since": "...", "sunset": "..."}.
    deprecation: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class OutboundDestination(Base):
    """The SSRF allowlist (Document 64 # 6 `outbound_destination`). `validateOutboundDestination()`
    resolves a candidate URL against ACTIVE rows here before any application server makes an outbound
    request (APPSEC-FR-011)."""

    __tablename__ = "outbound_destination"
    __table_args__ = (UniqueConstraint("service_id"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[str] = mapped_column(String(120), nullable=False)
    # {"schemes": ["https"], "hosts": ["erp.example.com"], "ports": [443]}
    schemes_hosts_ports: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # APPSEC-FR-011: explicit deny/allow CIDR rules layered on top of the always-on private-range block.
    ip_range_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # "BLOCK" (default -- no cross-host redirect follow) | "SAME_HOST" | "ALLOWLIST".
    redirect_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="BLOCK")
    # Reference only -- never the secret itself (APPSEC-FR-024 / CTR-FR-018).
    auth_secret_ref: Mapped[str | None] = mapped_column(String(200))
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class WebhookProfile(Base):
    """Inbound webhook trust config (Document 64 # 6 `webhook_profile`). `verifyWebhook()` checks an
    inbound delivery against the named provider's ACTIVE row: auth mechanism, replay window, body-size
    limit and expected payload schema version (APPSEC-FR-020)."""

    __tablename__ = "webhook_profile"
    __table_args__ = (UniqueConstraint("provider"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    auth_mechanism: Mapped[str] = mapped_column(String(30), nullable=False, default="HMAC_SHA256")
    # APPSEC-FR-020: integer seconds; a delivery whose signed timestamp is older than this is a replay.
    replay_window_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False, default=300)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    # APPSEC-FR-012/015: integer byte cap on the inbound body.
    max_body_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1048576)
    # Reference only -- never the HMAC/mTLS secret itself.
    signing_secret_ref: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
