"""Document 65 (SPEC-SEC-005) -- the cryptography / secret-resolution library functions Document 65 # 4
names: `resolveSecret`, `encryptSensitiveField`, `decryptSensitiveField`, `hashEvidence`, plus the
`crypto-health` self-test (KEY-FR-028) and the trust-all guard (KEY-FR-025). The certificate/secret
lifecycle *mutations* live in `crypto_commands.py`; this module is stateless helpers.

Real AEAD: `encrypt_sensitive_field` uses `cryptography`'s AES-256-GCM (`cryptography` is already a
transitive dependency of the approved `python-jose[cryptography]` -- no new dependency). The KEK is a
per-key-context 32-byte key; in this build it is derived deterministically from a process secret +
key-context label via HKDF so tests are reproducible, and a real deployment injects it from the KMS.
KEY-FR-015: the derivation label separates data-encryption keys from any TLS/audit-checkpoint key.

Never logs a secret value, a private key, or plaintext (Document 65 # 14 / KEY-FR-023).
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.security.crypto_models import CertificateMetadata, CryptoProfile, SecretMetadata
from app.mutation.errors import (
    FieldDecryptionDeniedError,
    FieldEncryptionFailedError,
    SecretAccessDeniedError,
    TrustAllProhibitedError,
)

# KEY-FR-015: a single process-level master secret feeds HKDF; each key context gets a distinct derived
# DEK, and the info label is namespaced so a data-encryption key can never collide with a TLS or
# audit-checkpoint key. A real deployment supplies GXP_FIELD_MASTER_KEY from the KMS.
_MASTER = os.environ.get("GXP_FIELD_MASTER_KEY", "dev-only-field-master-key-not-for-production").encode()
_DEK_VERSION = "v1"


def _derive_dek(key_context: str) -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"ebmr-field-encryption",
                info=f"data-encryption-key/{_DEK_VERSION}/{key_context}".encode())
    return hkdf.derive(_MASTER)


# --------------------------------------------------------------------------------------------------
# resolveSecret() -- KEY-FR-002/003/004
# --------------------------------------------------------------------------------------------------


async def resolve_secret(
    session: AsyncSession, *, secret_ref: str, service_identity: str, purpose: str
) -> dict:
    """Return a *handle* (never the value) for a managed secret, after checking the requesting service
    identity is on the secret's `consumer_identities` allowlist and the ref is ACTIVE. Raises
    `SecretAccessDeniedError` (SECRET_ACCESS_DENIED) otherwise. The caller's runtime then fetches the
    actual value straight from the provider into process memory -- it is never persisted or logged."""
    async def _deny(reason: str) -> None:
        from app.modules.security.telemetry import record_security_event
        await record_security_event("SecretAccessDenied", {
            "secret_ref": secret_ref, "service_identity": service_identity, "reason": reason,
        })

    row = (
        await session.execute(select(SecretMetadata).where(SecretMetadata.secret_ref == secret_ref))
    ).scalar_one_or_none()
    if row is None or row.state != "ACTIVE":
        await _deny("unknown or inactive secret reference")
        raise SecretAccessDeniedError("Secret reference is unknown or not active", secret_ref=secret_ref)
    if row.consumer_identities and service_identity not in set(row.consumer_identities):
        await _deny("service identity not on the consumer allowlist")
        raise SecretAccessDeniedError("Service identity is not an authorized consumer of this secret")
    return {
        "secret_ref": row.secret_ref,
        "provider": row.provider,
        "version": row.version,
        "purpose": purpose,
        "resolved": True,
    }


# --------------------------------------------------------------------------------------------------
# encryptSensitiveField() / decryptSensitiveField() -- KEY-FR-013/014/015/016
# --------------------------------------------------------------------------------------------------


def encrypt_sensitive_field(*, key_context: str, plaintext: bytes, aad: bytes = b"") -> dict:
    """Envelope-encrypt a sensitive field with AES-256-GCM under the DEK for `key_context` (tenant /
    data-class). Returns the ciphertext envelope: algorithm, key version, nonce, tag-carrying
    ciphertext (GCM appends the tag) and the AAD bound. Raises `FieldEncryptionFailedError` if the
    key context cannot produce a key."""
    try:
        dek = _derive_dek(key_context)
        nonce = os.urandom(12)
        ct = AESGCM(dek).encrypt(nonce, plaintext, aad or None)
    except Exception as exc:  # noqa: BLE001 -- any crypto failure is a fail-closed FIELD_ENCRYPTION_FAILED
        raise FieldEncryptionFailedError("Field encryption failed", key_context=key_context) from exc
    return {
        "algorithm": "AES-256-GCM",
        "key_version": _DEK_VERSION,
        "key_context": key_context,
        "nonce": nonce.hex(),
        "ciphertext": ct.hex(),
        "aad": aad.hex(),
    }


def decrypt_sensitive_field(*, envelope: dict, access_context: dict | None = None) -> bytes:
    """Decrypt a field envelope. Raises `FieldDecryptionDeniedError` (FIELD_DECRYPTION_DENIED) on a
    wrong key context/version, an authorization-context mismatch, or AEAD tag failure (tamper /
    wrong-tenant-key). Never returns partial plaintext."""
    required_ctx = envelope.get("key_context")
    if access_context is not None and access_context.get("key_context") not in (None, required_ctx):
        raise FieldDecryptionDeniedError("Access context is not authorized for this field's key context")
    if envelope.get("key_version") != _DEK_VERSION:
        raise FieldDecryptionDeniedError("Field was encrypted under a retired key version")
    try:
        dek = _derive_dek(required_ctx)
        aad = bytes.fromhex(envelope.get("aad", "")) or None
        return AESGCM(dek).decrypt(bytes.fromhex(envelope["nonce"]), bytes.fromhex(envelope["ciphertext"]), aad)
    except Exception as exc:  # noqa: BLE001
        raise FieldDecryptionDeniedError("Field decryption failed (wrong key or tampered ciphertext)") from exc


# --------------------------------------------------------------------------------------------------
# hashEvidence() -- KEY-FR-017
# --------------------------------------------------------------------------------------------------

_HASH_ALGOS = {"SHA-256": hashlib.sha256, "SHA-384": hashlib.sha384, "SHA-512": hashlib.sha512}


def hash_evidence(data: bytes, *, algorithm: str = "SHA-256") -> dict:
    """Compute a digest with the algorithm from the effective crypto profile, recording the algorithm
    name alongside the hash (KEY-FR-017 -- an unlabelled hash is not evidence). Raises ValueError for an
    unsupported algorithm rather than silently downgrading."""
    fn = _HASH_ALGOS.get(algorithm)
    if fn is None:
        raise ValueError(f"Unsupported hash algorithm {algorithm!r}")
    return {"algorithm": algorithm, "digest": fn(data).hexdigest(), "digest_bits": fn().digest_size * 8}


# --------------------------------------------------------------------------------------------------
# KEY-FR-025 -- trust-all guard
# --------------------------------------------------------------------------------------------------

_TRUST_ALL_MARKERS = {"trust_all", "accept_all", "insecure_skip_verify", "*", "any"}


def assert_not_trust_all(trust_store_config: dict) -> None:
    """Document 65 # 14: reject any production trust-store configuration that asks to accept all
    certificates. Raises `TrustAllProhibitedError`."""
    mode = str(trust_store_config.get("mode", "")).strip().lower()
    if mode in _TRUST_ALL_MARKERS or trust_store_config.get("verify") is False:
        raise TrustAllProhibitedError("'trust-all' certificate mode is not permitted in production")
    anchors = trust_store_config.get("trust_anchors")
    if anchors is not None and (anchors == "*" or anchors == ["*"]):
        raise TrustAllProhibitedError("Trust anchors cannot be a wildcard")


# --------------------------------------------------------------------------------------------------
# crypto-health self-test -- KEY-FR-028
# --------------------------------------------------------------------------------------------------


async def check_crypto_health(session: AsyncSession, *, now: datetime | None = None) -> dict:
    """KEY-FR-028: detect missing/expired/inaccessible critical keys and certificates. Returns a
    structured health report; the router raises `CryptoHealthFailedError` (503) when `healthy` is
    False so the caller fails safe rather than proceeding with broken crypto."""
    current = now or datetime.now(timezone.utc)
    findings: list[dict] = []

    # An effective crypto profile must exist.
    effective = (
        await session.execute(
            select(CryptoProfile).where(CryptoProfile.state == "EFFECTIVE").order_by(CryptoProfile.effective_from.desc())
        )
    ).scalars().first()
    if effective is None:
        findings.append({"check": "crypto_profile", "severity": "CRITICAL", "detail": "no EFFECTIVE crypto_profile"})

    # No ACTIVE certificate may be past expiry.
    active_certs = (
        await session.execute(select(CertificateMetadata).where(CertificateMetadata.state == "ACTIVE"))
    ).scalars().all()
    for cert in active_certs:
        exp = cert.expires_at if cert.expires_at.tzinfo else cert.expires_at.replace(tzinfo=timezone.utc)
        if exp <= current:
            findings.append({"check": "certificate_expiry", "severity": "CRITICAL",
                             "detail": f"certificate {cert.serial} is ACTIVE but expired at {exp.isoformat()}"})

    # Field-encryption self-test: round-trip a known value.
    try:
        env = encrypt_sensitive_field(key_context="health-check", plaintext=b"ping")
        if decrypt_sensitive_field(envelope=env) != b"ping":
            findings.append({"check": "field_encryption", "severity": "CRITICAL", "detail": "AEAD round-trip mismatch"})
    except Exception as exc:  # noqa: BLE001
        findings.append({"check": "field_encryption", "severity": "CRITICAL", "detail": f"AEAD self-test raised: {type(exc).__name__}"})

    # Audit-checkpoint hash algorithm must be available.
    try:
        hash_evidence(b"ping", algorithm="SHA-256")
    except Exception:  # noqa: BLE001
        findings.append({"check": "hash_algorithm", "severity": "CRITICAL", "detail": "SHA-256 unavailable"})

    return {
        "checked_at": current.isoformat(),
        "healthy": not any(f["severity"] == "CRITICAL" for f in findings),
        "effective_crypto_profile": effective.profile_name if effective else None,
        "active_certificate_count": len(active_certs),
        "findings": findings,
    }


async def emit_security_event(
    session: AsyncSession, *, event_type: str, payload: dict, aggregate_id: uuid.UUID | None = None
) -> None:
    """MUT-FR-031 / Document 65 # 9: security-monitoring events written to the outbox separately from
    any GxP audit row. Thin wrapper over the Mutation Gateway's `write_outbox_event`."""
    from app.mutation.gateway import write_outbox_event

    await write_outbox_event(
        session, event_type=event_type, aggregate_type="security_event",
        aggregate_id=aggregate_id or uuid.uuid4(), aggregate_version=1, payload=payload,
        correlation_id=uuid.uuid4(),
    )
