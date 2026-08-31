"""Document 62 (SPEC-SEC-002) — Identity Federation, SSO, MFA, Sessions & Service Identities. Same
`security` schema Document 61 created (migration 0062); this module adds the 3 owned entities Document
62 itself lists: `identity_provider_config`, `application_session`, `service_identity`.

**`service_identity` naming collision with `app.modules.iam.models.ServiceIdentity`.** That table's own
docstring already flags this: "No general Document 62 ... implementation exists in this codebase;
`User.subject_type` hints one was anticipated but nothing ever populates it with a working credential
path. This table is the interim, edge-gateway-scoped mechanism only." The two are NOT the same regulated
entity despite the name: `iam.service_identities` is a live bearer-CREDENTIAL store (`credential_hash`,
verified on every Edge request, Document 43 SG-120) scoped to edge gateways only; this module's
`security.service_identity` is Document 62's broader service-identity REGISTRY (any workload/service,
`credential_ref` -- a reference only, never the secret itself, per IAMSEC-FR-016) with tenant/site scope,
allowed audiences/scopes and lifecycle status -- a governance/inventory concern, not a credential-
verification concern. `iam.service_identities` is left completely untouched (out of scope -- WP-06/Edge is
not touched this pass). See docs/generated/18_SPEC_GAPS.md SG-162 for the consolidation note.

**`identity_mapping` has no table of its own** (only 3 owned entities exist for `mapExternalIdentity()`'s
own output type `IdentityMapping`). Two things already exist that satisfy this without inventing a table:
`iam.users` already carries `external_issuer`/`external_subject` columns (Document 07's own `iam_subject`
shape) that nothing has ever populated (see `User` model docstring precedent) -- `mapExternalIdentity()`
writes onto those. The append-only mapping *event* history is recorded on the owning
`identity_provider_config.identity_mappings` (JSONB list), same "history lives on the parent aggregate"
precedent as Document 61's `review_triggers`.

**`GET /auth/login` / `GET /auth/callback` (real OIDC/SAML redirect flow) are NOT built this pass** -- no
live external IdP is reachable from this environment to exchange an authorization code against (same class
of limitation as `DEMO_ERP_INSTANCE`, SG-125: no credentialed vendor sandbox reachable). What IS built and
real: `validateIdentityToken()` genuinely validates a JWT's issuer/audience/signature/expiry/clock-skew
against a configured `identity_provider_config`'s trust metadata (tested against a locally-generated test
RSA keypair, not a live IdP -- this is honestly a token-validation unit under test, not a live federation
handshake); the existing `/auth/token` password flow (IAMSEC-FR-001's own permitted "approved isolated
deployment" fallback) is wired to `createApplicationSession()` for real, and `/auth/logout` is new and real.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# IAMSEC-FR-001/002: OIDC and SAML federation, plus the locally-managed fallback realm.
IDP_PROTOCOLS = ("OIDC", "SAML", "LOCAL")
IDP_STATES = ("DRAFT", "ACTIVE", "RETIRED")

# Doc 62 `# 5` state model.
SESSION_STATES = ("ACTIVE", "STEP_UP_REQUIRED", "EXPIRED", "REVOKED", "LOGGED_OUT")

# IAMSEC-FR-014: workload identity auth method.
SERVICE_AUTH_METHODS = ("CLIENT_CREDENTIALS", "MTLS", "API_KEY")
# Doc 62 `# 5` service-identity state model.
SERVICE_IDENTITY_STATES = ("PROVISIONED", "ACTIVE", "ROTATING", "REVOKED")

# IAMSEC-FR-004: approved strong-auth methods; SMS is the platform-default disallowed weak factor
# (NIST SP 800-63B AAL guidance) -- configurable per identity_provider_config.trust_metadata, not
# hardcoded as an absolute prohibition.
MFA_METHODS = ("WEBAUTHN", "TOTP", "IDP_MFA")
DEFAULT_DISALLOWED_MFA_METHODS = ("SMS",)

# IAMSEC-FR-003: "privileged users require MFA" -- role-class default (ordinary engineering decision;
# MFA policy is explicitly configurable "by user risk/role/context", not a single guessed rule). Elevated
# platform/security/release authority roles, not ordinary production/QA execution roles.
PRIVILEGED_ROLE_NAMES = frozenset({
    "Admin", "Security Architect", "Security Risk Approver", "Integration Administrator",
    "Equipment Administrator", "QA Releaser",
})


class IdentityProviderConfig(Base):
    __tablename__ = "identity_provider_config"
    __table_args__ = {"schema": "security"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_label: Mapped[str] = mapped_column(String(120), nullable=False)
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)
    # IAMSEC-FR-005/024: JWKS URI or embedded public key material, algorithm, allowed clock skew seconds.
    trust_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False)
    claim_mapping_version: Mapped[str] = mapped_column(String(40), nullable=False)
    # IAMSEC-FR-011: external claim/group -> internal role mapping rules (never a direct unrestricted grant).
    claim_mapping: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    # mapExternalIdentity() append-only history -- see module docstring.
    identity_mappings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ApplicationSession(Base):
    __tablename__ = "application_session"
    __table_args__ = {"schema": "security"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    auth_time: Mapped[datetime] = mapped_column(nullable=False)
    # IAMSEC-FR-004/023: MFA method/strength and risk/device signals, vendor-neutral shape.
    auth_strength: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    idle_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    revoked_reason: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(nullable=False, default=1)


class SecurityServiceIdentity(Base):
    """Doc 62 `# 6` `service_identity` -- see module docstring for why this is distinct from
    `iam.models.ServiceIdentity`. Table name is `service_identity` (singular, matching the approved data
    model catalogue exactly); the Python class is named `SecurityServiceIdentity` to avoid import
    ambiguity with the pre-existing edge-only class."""

    __tablename__ = "service_identity"
    __table_args__ = (UniqueConstraint("service_name"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name: Mapped[str] = mapped_column(String(120), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    allowed_audiences: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    allowed_scopes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    auth_method: Mapped[str] = mapped_column(String(30), nullable=False)
    # IAMSEC-FR-016: a reference only (e.g. a secrets-manager path) -- never the secret itself.
    credential_ref: Mapped[str] = mapped_column(String(300), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROVISIONED")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
