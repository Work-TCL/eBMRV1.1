"""Document 65 (SPEC-SEC-005) -- Secrets Management, PKI, Cryptography & Key Lifecycle. Same `security`
PostgreSQL schema Documents 61-64 created; adds the 3 owned entities the approved
`04_DATA_MODEL_CATALOGUE.md` lists: `secret_metadata`, `certificate_metadata`, `crypto_profile`, plus
`secret_value` (SG-126 gap resolution, added WP-07 pass -- the ON_PREM provider's encrypted value store).

**Metadata only -- never a secret or private key value in the clear.** Document 65 # 14 prohibits storing
private keys/secret values in ordinary application tables and logging them. `secret_metadata` holds a
*reference* (`secret_ref`) into an external secret manager plus lifecycle metadata; `certificate_metadata`
holds the serial / subject / SANs / validity / state; neither ever holds key material.
`app/modules/security/crypto.py::resolve_secret()` returns a handle, not a value.

`secret_value` is the one exception, and it does not violate # 14: for `provider="ON_PREM"` secrets it
stores only the AES-256-GCM envelope (nonce + ciphertext + tag) `encrypt_sensitive_field()` produces --
the same envelope shape already used for every other sensitive field in this codebase, never plaintext.
K8S_SECRET/AWS_SM/VAULT secrets get no row here; fetching those fails closed (SECRET_PROVIDER_NOT_INTEGRATED,
SG-126) rather than the platform pretending to host their value.

**Signature: certificate issue/rotate/revoke require a `Released` signature** -- Document 106 rows
137-139 (QA Approver / Batch Release, MUST be independent of every production performer). Resolved to
the existing **QA Releaser** role, the same established non-QMS mapping this codebase already uses for
every "QA Approver / Batch Release" family default (batch.release, edge_gateway.certificate_rotation,
privileged_session.close, ...). `secrets/{id}/rotate` has **no** Document 106 row -> RBAC-gated only
(Security Admin), no signature. `crypto-health` is a read-only GET.

**No `site_id`.** Document 65's actors (Security Admin, PKI/KMS Service, DevOps/SRE, ...) and its data
model operate at the platform/deployment level, same as every other `security.*` table. `tenant_id`
dropped per ADR-0006; per-tenant key strategy (KEY-FR-026) is expressed as a `crypto_profile` scoped by
name/deployment, not a tenant_id column.

**No binary float.** `rotation_interval_days`, `validity_days` and key sizes are integers.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

SECRET_STATES = ("ACTIVE", "ROTATING", "RETIRED", "REVOKED", "DESTROYED")
CERTIFICATE_STATES = ("REQUESTED", "ACTIVE", "ROTATING", "REVOKED", "EXPIRED", "DESTROYED")
CRYPTO_PROFILE_STATES = ("DRAFT", "EFFECTIVE", "SUPERSEDED")
REVOCATION_REASONS = (
    "KEY_COMPROMISE", "CA_COMPROMISE", "AFFILIATION_CHANGED", "SUPERSEDED",
    "CESSATION_OF_OPERATION", "PRIVILEGE_WITHDRAWN", "UNSPECIFIED",
)


class SecretMetadata(Base):
    """Document 65 # 6 `secret_metadata` -- reference + lifecycle metadata for one managed secret
    (DB password, OAuth secret, API key, signing key, mTLS key, Edge cert key, encryption key).
    `resolveSecret()` reads `consumer_identities` to enforce least access (KEY-FR-004); `rotateSecret()`
    bumps `version` and the rotation timestamps (KEY-FR-005/006)."""

    __tablename__ = "secret_metadata"
    __table_args__ = (
        UniqueConstraint("secret_ref"),
        Index("ix_secret_metadata_state", "state"),
        {"schema": "security"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    secret_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)  # e.g. K8S_SECRET, AWS_SM, VAULT, ON_PREM
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    # KEY-FR-004: service-identity refs allowed to resolve this secret. [] means "no consumer yet".
    consumer_identities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rotation_interval_days: Mapped[int] = mapped_column(BigInteger, nullable=False, default=90)
    last_rotated_at: Mapped[datetime | None] = mapped_column()
    next_rotation_at: Mapped[datetime | None] = mapped_column()
    # KEY-FR-006: incident/change linkage for an emergency rotation. NULL for routine rotation.
    incident_ref: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class SecretValue(Base):
    """SG-126 (Document 65 # 6 gap resolution, ON_PREM provider only). The AES-256-GCM ciphertext
    envelope for a `secret_metadata` row registered with `provider="ON_PREM"` -- never the plaintext
    value (Document 65 # 14 is satisfied because `envelope` holds only nonce/ciphertext/tag under a DEK
    that never leaves `crypto.py`, the same shape `encrypt_sensitive_field()` already produces for every
    other sensitive field). One row per secret; `set_secret_value()` overwrites it under optimistic
    concurrency on `version`, same pattern as every other mutable aggregate.

    K8S_SECRET/AWS_SM/VAULT secrets never get a row here -- `fetch_secret_value()` fails closed with
    SECRET_PROVIDER_NOT_INTEGRATED for those providers rather than this table pretending to hold their
    value (no live external target in this build, see SG-126)."""

    __tablename__ = "secret_value"
    __table_args__ = (UniqueConstraint("secret_id"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    secret_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("security.secret_metadata.id"), nullable=False)
    envelope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    set_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class CertificateMetadata(Base):
    """Document 65 # 6 `certificate_metadata` -- issued service/Edge/admin certificate identity.
    `issueServiceCertificate()` creates it (REQUESTED -> ACTIVE); `rotateCertificate()` issues a
    replacement and overlaps; `revokeCertificate()` sets REVOKED + reason. All three are Part 11
    signed (Document 106 rows 137-139, Released, QA Releaser, independent)."""

    __tablename__ = "certificate_metadata"
    __table_args__ = (
        UniqueConstraint("serial"),
        Index("ix_certificate_metadata_state", "state"),
        {"schema": "security"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial: Mapped[str] = mapped_column(String(120), nullable=False)
    # KEY-FR-008: subject + SANs + purpose, validated before issuance.
    subject_sans: Mapped[dict] = mapped_column(JSONB, nullable=False)
    identity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    profile: Mapped[str] = mapped_column(String(60), nullable=False)  # e.g. SERVICE_MTLS, EDGE_GATEWAY, ADMIN
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="REQUESTED")
    issuer_ref: Mapped[str] = mapped_column(String(200), nullable=False)  # issuing CA / KMS reference
    # KEY-FR-009: the certificate this one replaced, for the overlap window. NULL on first issue.
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("security.certificate_metadata.id"))
    revocation_reason: Mapped[str | None] = mapped_column(String(40))
    revoked_at: Mapped[datetime | None] = mapped_column()
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class CryptoProfile(Base):
    """Document 65 # 6 `crypto_profile` -- the versioned crypto-agility record (KEY-FR-016): approved
    TLS baseline, hash algorithms, symmetric/asymmetric algorithms, key sizes and effective dates.
    Seed-populated + superseded (no in-place edit); read by `hash_evidence()` / field-encryption to
    pick the effective algorithm set, and by `crypto-health` for the self-test."""

    __tablename__ = "crypto_profile"
    __table_args__ = (UniqueConstraint("profile_name", "version"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_name: Mapped[str] = mapped_column(String(80), nullable=False)
    tls_baseline: Mapped[dict] = mapped_column(JSONB, nullable=False)          # {min_version, allowed_ciphers, disabled}
    hash_algorithms: Mapped[dict] = mapped_column(JSONB, nullable=False)       # {evidence: "SHA-256", ...}
    symmetric_algorithms: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {field_encryption: "AES-256-GCM"}
    asymmetric_algorithms: Mapped[dict] = mapped_column(JSONB, nullable=False)
    key_sizes: Mapped[dict] = mapped_column(JSONB, nullable=False)             # {rsa: 3072, ec: "P-256"}
    effective_from: Mapped[datetime] = mapped_column(nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column()
    migration_notes: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
