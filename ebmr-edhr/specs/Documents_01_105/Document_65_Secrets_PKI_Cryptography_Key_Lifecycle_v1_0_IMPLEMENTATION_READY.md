# US eBMR / eDHR Regulated Manufacturing Platform
## Document 65 — Secrets Management, PKI, Cryptography & Key Lifecycle — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-SEC-005  
**Parent Documents:** Documents 01–60  
**Primary Dependencies:** Documents 04–06, 43–53, 61–64; Infrastructure  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is intended for direct ingestion by Claude Code, Codex, and human engineering/security teams.

Before implementation, the coding agent shall extract:

1. requirement registry;
2. security-control catalogue;
3. module/service responsibility map;
4. function/service contract catalogue;
5. typed input/output schemas;
6. authorization/signature dependencies;
7. database reads/writes and transaction boundaries;
8. API/event contracts;
9. configuration and secret inventory;
10. threat/control/test mapping;
11. security logging requirements;
12. negative/abuse-case tests;
13. validation traceability.

For every public/domain/security function specified here, preserve:

- purpose;
- caller/trigger;
- typed inputs and source;
- authentication/authorization/qualification/SoD/signature prerequisites;
- business/security preconditions;
- database reads;
- database writes;
- transaction boundary;
- output;
- emitted/consumed events;
- stable error codes;
- idempotency/concurrency;
- audit evidence;
- security telemetry;
- positive, negative, abuse, failure and recovery tests.

If a missing decision materially changes security or regulated behavior, create a `SPEC_GAP` rather than inventing a rule.

# Security Framework Baseline

The security engineering baseline uses the following current references as implementation guidance:

- NIST Cybersecurity Framework (CSF) 2.0 for governance and cybersecurity outcomes.
- NIST SP 800-207 Zero Trust Architecture for resource/subject-centric access and no implicit network trust.
- NIST SP 800-218 SSDF v1.1 as the final secure-software-development baseline. NIST's v1.2 update is still draft as of this specification date and is treated only as a future design input.
- OWASP Application Security Verification Standard (ASVS) 5.0.0, released May 30, 2025, as a detailed application-security verification reference.
- OWASP API Security Top 10 2023 for API-specific abuse and authorization risks.
- CISA Secure by Design principles as voluntary product-security design guidance, especially secure defaults and shifting security burden away from customers.

Primary references:
- https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20
- https://csrc.nist.gov/pubs/sp/800/207/final
- https://csrc.nist.gov/pubs/sp/800/218/final
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- https://www.cisa.gov/securebydesign

# Security / GxP Boundary

Security controls support, but do not replace, GxP controls.

```text
Identity Provider / MFA
        ↓
Authentication Context
        ↓
Policy Service / Document 07
        ↓
Authorized GxP Action
        ↓
Part 11 Signature / Document 04 when required
        ↓
Mutation Gateway / Audit / Vault
```

Normal SSO login, MFA, or an administrator role is never automatically equivalent to a regulated electronic signature or Quality authority.

# 1. Objective

Define secrets, service certificates, TLS, encryption, hashing and key lifecycle so credentials and cryptographic trust are isolated, rotatable and recoverable across cloud and on-prem deployments.

# 2. Actors / Components

- Security Admin
- PKI/KMS Service
- DevOps/SRE
- Application Service
- Edge Gateway
- Integration Connector
- Backup/Restore Operator
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| KEY-FR-001 | Secret inventory | Inventory database passwords, OAuth secrets, API keys, signing keys, mTLS keys, Edge certs and encryption keys with owner/rotation policy. | Known secrets. |
| KEY-FR-002 | Secret manager abstraction | Production secrets retrieved from Kubernetes/cloud/on-prem secret manager abstraction; source-controlled plaintext prohibited. | Central management. |
| KEY-FR-003 | Secret references | Application config stores secret references/identifiers, not secret values. | Safe config. |
| KEY-FR-004 | Least access | Each service identity can retrieve only required secrets. | Least privilege. |
| KEY-FR-005 | Rotation | Rotation supported without code change; overlap/grace for credentials/certs where protocol requires. | Lifecycle. |
| KEY-FR-006 | Emergency rotation | Compromised secret can be revoked/rotated rapidly with incident linkage. | Response. |
| KEY-FR-007 | PKI hierarchy | Document root/intermediate/issuing authorities or enterprise CA integration for service/Edge certificates. | Trust. |
| KEY-FR-008 | Certificate issuance | Certificate subject/SAN/purpose/tenant/site/service binding validated before issuance. | Identity. |
| KEY-FR-009 | Certificate rotation | Automated/controlled renewal before expiry; failed renewal alerts. | Availability. |
| KEY-FR-010 | Certificate revocation | Revoked identity rejected promptly according to deployment's CRL/OCSP/trust-store approach. | Compromise containment. |
| KEY-FR-011 | TLS | TLS configured using current approved deployment baseline; obsolete protocol/cipher disabled. | Transport security. |
| KEY-FR-012 | mTLS | Use mTLS for selected service/Edge/admin integration boundaries where architecture requires. | Strong workload identity. |
| KEY-FR-013 | At-rest encryption | Volumes/object stores/backups use platform-approved at-rest encryption; sensitive application fields can use envelope/field encryption when risk requires. | Data confidentiality. |
| KEY-FR-014 | Field encryption | Patient/reporter/sensitive secret-like data fields can be encrypted with tenant/data-class keys where required. | Privacy. |
| KEY-FR-015 | Key hierarchy | Data-encryption keys separated from key-encryption/master keys; external KMS/HSM supported. | Separation. |
| KEY-FR-016 | Crypto agility | Algorithms/key sizes identified by versioned crypto profile so platform can migrate without schema redesign. | Future-proof. |
| KEY-FR-017 | Hashing | Use approved cryptographic hashing for evidence/audit/manifests; algorithm recorded with hash. | Integrity. |
| KEY-FR-018 | Passwords | Human password hashing delegated to IdP using modern adaptive hashing; app does not implement own password DB. | Correct scope. |
| KEY-FR-019 | Signature cryptography | Part 11 signature evidence integrity uses Document 04/Vault design; do not confuse cryptographic document signing with user authentication. | Semantics. |
| KEY-FR-020 | Audit checkpoints | Audit integrity checkpoint signing key separate from TLS/application credentials. | Blast radius. |
| KEY-FR-021 | Backup keys | Backup encryption keys and restore procedures documented/tested; avoid unrecoverable encrypted backups. | Recoverability. |
| KEY-FR-022 | Key access logging | KMS/HSM/secret accesses/administrative changes logged. | Detection. |
| KEY-FR-023 | No secret logging | Application/Edge/CI redacts Authorization headers, cookies, private keys, passwords/tokens and configured sensitive fields. | Leak prevention. |
| KEY-FR-024 | No secret in artifact | Container images/build outputs/packages do not contain environment secrets. | Supply-chain hygiene. |
| KEY-FR-025 | Certificate pinning/trust | OPC UA/custom partner trust stores managed explicitly; 'trust all' prohibited in production. | External security. |
| KEY-FR-026 | Tenant key strategy | Dedicated deployment/customer keys supported; shared SaaS-style keying not assumed. | Enterprise isolation. |
| KEY-FR-027 | Key destruction | Retired keys destroyed only after retention/restore/legal requirements permit; destruction evidence recorded. | Lifecycle. |
| KEY-FR-028 | Crypto self-test | Startup/health checks detect missing/expired/inaccessible critical keys/certs and fail safely. | Operational assurance. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| resolveSecret() | Service runtime | secret_ref; service identity; purpose | Identity authorized; ref active | Fetches secret from provider into process memory with no persistence/logging | SecretHandle/value | SecretAccessed; SECRET_ACCESS_DENIED |
| rotateSecret() | Security Admin/automation | secret_id; new credential material/generator; overlap policy | Rotation approved/eligible | Creates new version, updates consumers via reference/provider, validates, retires old | SecretRotationResult | SecretRotated; SECRET_ROTATION_FAILED |
| issueServiceCertificate() | PKI service | CSR; service identity; SANs; validity; profile | Identity/SAN/purpose approved | Signs/requests certificate; records serial/profile/expiry | CertificateRef | CertificateIssued |
| rotateCertificate() | Automation/Admin | certificate_id; CSR | Within rotation window or forced; identity active | Issues replacement, activates overlap, updates trust/consumer, revokes old when safe | CertificateRotation | CertificateRotated |
| revokeCertificate() | Security/Incident | certificate serial; reason | Authority validated | Revokes/updates trust metadata; emits high-signal event | RevocationReceipt | CertificateRevoked |
| encryptSensitiveField() | Application crypto service | tenant/key context; plaintext bytes; AAD | Field configured encrypted; key available | Envelope encrypts with DEK/KEK; stores ciphertext+key version+nonce/tag | EncryptedField | FIELD_ENCRYPTION_FAILED |
| decryptSensitiveField() | Authorized service | ciphertext envelope; access context | Field access authorized; key available | Decrypts in memory, logs security access metadata without plaintext | Plaintext | FIELD_DECRYPTION_DENIED |
| hashEvidence() | Evidence/Audit/Edge | stream/bytes; crypto profile | Profile effective | Computes digest and algorithm/version metadata | DigestRef | EvidenceHashed |


# 5. State / Control Model

```text
SECRET/CERT:
REQUESTED → ACTIVE → ROTATING → RETIRED/REVOKED → DESTROYED (when permitted)

KEY:
GENERATED/IMPORTED → ACTIVE → DECRYPT_ONLY/RETIRING → ARCHIVED → DESTROYED
```

# 6. Data Model

## `secret_metadata`
- secret ID/reference
- provider
- purpose/owner
- consumer identities
- version
- rotation interval
- last/next rotation
- state

## `certificate_metadata`
```text
id uuid PK
serial varchar UNIQUE
subject/sans jsonb
identity_id uuid
profile varchar
issued_at/expires_at
state varchar
issuer_ref
```

## `crypto_profile`
- TLS baseline
- hash algorithms
- symmetric/asymmetric algorithms
- key sizes
- effective dates
- migration notes


# 7. APIs / Internal Interfaces

- `POST /security/v1/secrets/{id}/rotate`
- `POST /security/v1/certificates:issue`
- `POST /security/v1/certificates/{id}/rotate`
- `POST /security/v1/certificates/{id}/revoke`
- `GET /security/v1/crypto-health`

All security-sensitive mutations are server-side and auditable.

# 8. UI / Administrative Screens

1. Secret Inventory (metadata only)
2. Certificate Inventory
3. Rotation Dashboard
4. Crypto Profiles
5. Trust Stores
6. Key Access Audit

# 9. Security Events

- `SecretAccessDenied`
- `SecretRotated`
- `CertificateIssued`
- `CertificateRotated`
- `CertificateRevoked`
- `CryptoHealthFailed`
- `KeyAccessAnomaly`

# 10. Failure / Recovery

- Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies.
- Security subsystem outage must not silently downgrade protection.
- Retryable infrastructure failures use bounded retry/backoff.
- Security-control bypass requires a separate controlled emergency path, not a hidden fallback.
- Recovery actions are themselves logged and reviewable.

# 11. Repository Structure

```text
services/security/secrets-management-pki-cryptography-key-lifecycle/
packages/security-contracts/
infrastructure/security/
apps/ebmr_frappe/ebmr/security/secrets-management-pki-cryptography-key-lifecycle/
validation/security/secrets-management-pki-cryptography-key-lifecycle/
tests/security/secrets-management-pki-cryptography-key-lifecycle/
```

# 12. Mandatory Test Catalogue

- expired service cert
- rotation with no outage
- revoked Edge cert
- secret leaked scanner test
- field encryption wrong tenant key
- backup restore with retired key
- trust-all cert config blocked
- hash algorithm migration

# 13. Acceptance Criteria

No production secret is required in source control or image/config plaintext, and every critical certificate/secret can be rotated/revoked without modifying regulated business data.

# 14. Claude Code / Codex Prohibitions

- Never log secret values.
- Never store private keys in ordinary application tables.
- Never use same key for TLS, audit checkpoints and data encryption.
- Never enable accept-all certificate mode in production.


