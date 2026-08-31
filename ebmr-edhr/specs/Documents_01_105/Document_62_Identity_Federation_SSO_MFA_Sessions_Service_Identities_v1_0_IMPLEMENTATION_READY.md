# US eBMR / eDHR Regulated Manufacturing Platform
## Document 62 — Identity Federation, SSO, MFA, Sessions & Service Identities — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-SEC-002  
**Parent Documents:** Documents 01–60  
**Primary Dependencies:** Documents 04, 07; Keycloak-compatible identity abstraction; customer IdP  
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

Define secure identity federation and session handling for humans, services and Edge/device identities while preserving the separate GxP authorization and Part 11 signature layers.

# 2. Actors / Components

- End User
- Privileged User
- Customer IdP
- Keycloak-Compatible Broker
- Security Admin
- Service/Workload
- Edge Gateway
- Policy Service

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| IAMSEC-FR-001 | Federated identity | Support OIDC and SAML federation through Keycloak-compatible identity boundary; direct app password store is fallback only for approved isolated deployments. | Enterprise SSO. |
| IAMSEC-FR-002 | Local fallback IdP | On-prem/private deployments can use locally managed Keycloak-compatible realm when customer IdP unavailable. | Deployment flexibility. |
| IAMSEC-FR-003 | MFA policy | MFA requirements configurable by user risk/role/context; privileged users require MFA. | Strong auth. |
| IAMSEC-FR-004 | MFA methods | Support WebAuthn/passkeys/security keys and approved TOTP/IdP MFA methods; weak factors configurable as disallowed. | Phishing resistance. |
| IAMSEC-FR-005 | SSO session | Application accepts short-lived identity tokens/session assertions and validates issuer/audience/signature/expiry/nonce/state. | Token integrity. |
| IAMSEC-FR-006 | Session binding | Session binds tenant/user/authentication context and cannot change tenant/site silently. | Scope integrity. |
| IAMSEC-FR-007 | Session timeout | Idle and absolute session lifetimes configurable by deployment/profile; sensitive contexts shorter. | Least exposure. |
| IAMSEC-FR-008 | Reauthentication | Sensitive security/admin operations may require fresh authentication independently of Part 11 signing. | Step-up. |
| IAMSEC-FR-009 | Part 11 separation | Regulated signature ceremony always uses Document 04; normal MFA/session is never reused automatically as signature proof. | Correct semantics. |
| IAMSEC-FR-010 | Token revocation | Disabled user/critical risk/session logout/revocation invalidates or rapidly expires app access. | Lifecycle. |
| IAMSEC-FR-011 | Group/claim mapping | External groups/claims map through controlled identity mapping; external IdP does not directly assign unrestricted GxP permission. | Policy boundary. |
| IAMSEC-FR-012 | Provisioning | SCIM or controlled directory sync may provision identity metadata; authorization remains controlled in platform. | Enterprise lifecycle. |
| IAMSEC-FR-013 | Joiner/mover/leaver | Identity lifecycle integrates Document 07 role/qualification lifecycle and security session revocation. | Timely access removal. |
| IAMSEC-FR-014 | Service identity | Services use workload identities/client credentials/mTLS certificates; no shared human accounts. | Machine attribution. |
| IAMSEC-FR-015 | Device identity | Edge/connectors have distinct certificates/service principals and site scope. | Industrial identity. |
| IAMSEC-FR-016 | Credential storage | No plaintext user/service secrets in source/config/logs. | Secret hygiene. |
| IAMSEC-FR-017 | Authentication events | Success/failure/MFA/lockout/token/revocation events sent to security telemetry. | Detection. |
| IAMSEC-FR-018 | Brute-force defense | Rate-limit/lockout/risk response handled primarily at IdP and supported by application controls. | Abuse protection. |
| IAMSEC-FR-019 | Password fallback | If local passwords exist, enforce modern hashing and policy through IdP; application never implements custom password hashing. | Centralized auth. |
| IAMSEC-FR-020 | Account recovery | Recovery handled through controlled IdP/customer process; app support cannot reset identity secretly. | Identity proof. |
| IAMSEC-FR-021 | Impersonation | Human impersonation disabled by default; support troubleshooting uses controlled read-only/support-access model. | No hidden acting as user. |
| IAMSEC-FR-022 | Concurrent sessions | Configurable session/device visibility and admin/security ability to revoke sessions. | Account control. |
| IAMSEC-FR-023 | Risk context | Auth context may include MFA strength, device/trust/risk signals for policy decisions without embedding vendor-specific fields in domain. | Adaptive auth. |
| IAMSEC-FR-024 | Clock skew | Token validation uses bounded configured clock skew; large time anomalies fail/auth-alert. | Time integrity. |
| IAMSEC-FR-025 | Tenant discovery | Login flow never reveals sensitive tenant/customer existence beyond approved UX. | Information minimization. |
| IAMSEC-FR-026 | Identity audit | Identity mappings, federation changes, MFA policy and service-client changes versioned/audited. | Traceability. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| validateIdentityToken() | API gateway/session middleware | JWT/assertion; expected issuer/audience/tenant | Provider config effective; signing keys trusted | Validates signature/claims/time/nonce as applicable; creates normalized auth context | AuthContext | AuthenticationSucceeded/Failed; TOKEN_INVALID |
| createApplicationSession() | Web login callback | AuthContext; browser/device metadata | AuthContext valid; user active | Creates server/session record with tenant/auth strength/expiry; secure cookie/token | ApplicationSession | SessionCreated |
| evaluateMFARequirement() | Login/admin action | user/role/context/risk | MFA policy loaded | Returns required auth strength/method constraints | MFARequirement | MFARequired |
| revokeUserSessions() | Identity lifecycle/Security Admin | subject_id; reason | Authorized trigger | Marks active app sessions revoked and requests IdP revocation where supported | RevocationReceipt | UserSessionsRevoked |
| mapExternalIdentity() | Federation callback/provisioning | issuer; subject; claims | Issuer trusted; mapping policy effective | Resolves immutable internal subject; proposes/updates allowed identity projection only | IdentityMapping | ExternalIdentityMapped |
| provisionServiceIdentity() | Security Admin/Deployment automation | service name; scopes; tenant/site; auth method | Service registered; least-privilege scopes reviewed | Creates service principal/client/certificate metadata, secret ref only | ServiceIdentity | ServiceIdentityProvisioned |
| validateServiceToken() | Service middleware | client token/cert; target audience | Service identity active; cert/token valid | Builds service AuthContext with allowed scopes/site | ServiceAuthContext | ServiceAuthenticationSucceeded |
| requireFreshAuthentication() | Sensitive admin operation | session_id; required_age/auth_strength | Session active | Checks auth_time/strength and initiates IdP step-up if insufficient | FreshAuthResult | FRESH_AUTH_REQUIRED |


# 5. State / Control Model

```text
UNAUTHENTICATED
   ↓ federation/MFA
AUTHENTICATED
   ↓ app session
ACTIVE_SESSION
   ├→ STEP_UP_REQUIRED
   ├→ EXPIRED
   ├→ REVOKED
   └→ LOGOUT

SERVICE IDENTITY:
PROVISIONED → ACTIVE → ROTATING → REVOKED
```

# 6. Data Model

## `identity_provider_config`
- tenant/deployment
- issuer/entity ID
- protocol OIDC/SAML
- trust/signing keys metadata
- claim mapping version
- state/effective dates

## `application_session`
```text
id uuid PK
subject_id uuid
tenant_id uuid
auth_time timestamptz
auth_strength jsonb
created_at/expires_at/idle_expires_at
state varchar
revoked_reason
```

## `service_identity`
- service/client ID
- tenant/site scope
- allowed audiences/scopes
- auth method
- certificate/key refs
- lifecycle status


# 7. APIs / Internal Interfaces

- `GET /auth/login`
- `GET /auth/callback`
- `POST /auth/logout`
- `POST /security/v1/sessions/{id}/revoke`
- `POST /security/v1/service-identities`
- `POST /security/v1/identity-providers`

All security-sensitive mutations are server-side and auditable.

# 8. UI / Administrative Screens

1. Identity Provider Config
2. Active Sessions
3. Service Identities
4. Federation Mapping
5. Authentication Policy
6. Session Revocation

# 9. Security Events

- `AuthenticationSucceeded`
- `AuthenticationFailed`
- `MFARequired`
- `SessionCreated`
- `SessionRevoked`
- `ExternalIdentityMapped`
- `ServiceIdentityProvisioned`

# 10. Failure / Recovery

- Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies.
- Security subsystem outage must not silently downgrade protection.
- Retryable infrastructure failures use bounded retry/backoff.
- Security-control bypass requires a separate controlled emergency path, not a hidden fallback.
- Recovery actions are themselves logged and reviewable.

# 11. Repository Structure

```text
services/security/identity-federation-sso-mfa-sessions-service-identities/
packages/security-contracts/
infrastructure/security/
apps/ebmr_frappe/ebmr/security/identity-federation-sso-mfa-sessions-service-identities/
validation/security/identity-federation-sso-mfa-sessions-service-identities/
tests/security/identity-federation-sso-mfa-sessions-service-identities/
```

# 12. Mandatory Test Catalogue

- wrong issuer
- wrong audience
- expired token
- clock skew
- MFA missing for privileged role
- disabled user existing session
- cross-tenant claim injection
- service token wrong audience
- certificate revoked

# 13. Acceptance Criteria

Authentication cannot grant a GxP action by itself; every protected operation receives a normalized trusted AuthContext that Policy Service independently evaluates.

# 14. Claude Code / Codex Prohibitions

- Never implement custom password storage in application.
- Never use normal SSO MFA as automatic Part 11 signature.
- Never trust IdP group claim as unrestricted GxP authorization.
- Never use one shared service account for multiple services.


