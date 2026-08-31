# US eBMR / eDHR Regulated Manufacturing Platform
## Document 64 — Application, API, UI & Secure Runtime Engineering — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-SEC-004  
**Parent Documents:** Documents 01–60  
**Primary Dependencies:** Documents 03, 07, 43–53; Frappe UI/API; Integration Gateway  
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

Define implementation-level web, API and service security controls aligned to OWASP ASVS 5.0 and API Security Top 10, with server-side authorization, strict schemas, injection prevention, SSRF controls, safe file handling and abuse protection.

# 2. Actors / Components

- Frontend Developer
- Backend Developer
- API Gateway
- Policy Service
- Integration Developer
- Security Engineer
- Pen Tester

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| APPSEC-FR-001 | Server-side authorization | Every object/function/property mutation/read is authorized server-side; client-side visibility is not security. | BOLA/BFLA defense. |
| APPSEC-FR-002 | Object scope | Tenant/site/resource identifiers are derived/validated against AuthContext and Policy decision. | No IDOR. |
| APPSEC-FR-003 | Property authorization | Request DTO allowlists writable fields; mass-assignment to protected fields impossible. | Property-level security. |
| APPSEC-FR-004 | Input schemas | All API inputs validated by typed schema including length, ranges, enums, formats and unknown-property policy. | Injection/malformed defense. |
| APPSEC-FR-005 | Output minimization | Responses expose only required fields by role/context; sensitive fields omitted/masked. | Least disclosure. |
| APPSEC-FR-006 | SQL safety | Parameterized queries/ORM safe APIs only; no string-concatenated SQL from request data. | Injection defense. |
| APPSEC-FR-007 | Command injection | No shell command interpolation from untrusted input; use typed process APIs/allowlists where unavoidable. | RCE defense. |
| APPSEC-FR-008 | XSS | Frappe/UI escapes untrusted output; rich text sanitized with allowlist; no unsafe HTML rendering. | Browser protection. |
| APPSEC-FR-009 | CSRF | Cookie-authenticated browser mutations use robust CSRF protection/SameSite and origin controls; token APIs use appropriate model. | Request integrity. |
| APPSEC-FR-010 | CORS | CORS deny-by-default, allowlisted exact origins per deployment; credentials not wildcarded. | Cross-origin security. |
| APPSEC-FR-011 | SSRF | Outbound URL operations use allowlisted destinations/network egress controls; user-supplied URL cannot reach metadata/internal networks. | API7 defense. |
| APPSEC-FR-012 | File upload | Validate size/type/content policy, filename handling, malware scanning/quarantine where required, store outside executable paths. | Upload security. |
| APPSEC-FR-013 | Download authorization | Every attachment/evidence download rechecks object authorization; unguessable URL alone insufficient. | Data protection. |
| APPSEC-FR-014 | Rate limits | Authentication, exports, search, expensive reports, integrations and sensitive business flows have rate/resource limits. | Resource protection. |
| APPSEC-FR-015 | Pagination/bounds | List/search/report endpoints enforce result/time/size bounds. | DoS mitigation. |
| APPSEC-FR-016 | API inventory | All endpoints/version/deprecation/auth scopes documented in OpenAPI/inventory. | Asset management. |
| APPSEC-FR-017 | Debug exposure | Debug/admin/schema endpoints disabled or protected in production. | Misconfiguration defense. |
| APPSEC-FR-018 | Error responses | Client gets stable non-sensitive error; stack traces/internal secrets never exposed. | Information control. |
| APPSEC-FR-019 | Third-party API validation | Treat ERP/LIMS/IdP/Edge responses as untrusted; schema/size/status validation before consumption. | Unsafe API consumption defense. |
| APPSEC-FR-020 | Webhook validation | Authenticate/signature/mTLS as configured; replay/idempotency checks. | Inbound trust. |
| APPSEC-FR-021 | Export safety | CSV/spreadsheet export neutralizes formula injection where applicable and respects field permissions. | Office-client safety. |
| APPSEC-FR-022 | Template safety | No arbitrary template/code evaluation from customer-configured expressions; rules use constrained DSL. | RCE prevention. |
| APPSEC-FR-023 | Serialization | Avoid unsafe object deserialization; use explicit DTO schemas. | Code execution defense. |
| APPSEC-FR-024 | Secrets in URLs | Credentials/tokens/sensitive values not placed in URLs/query strings unless protocol unavoidably requires and mitigated. | Leak prevention. |
| APPSEC-FR-025 | Cookies | Secure, HttpOnly, SameSite cookies; session identifiers regenerated on auth privilege change as applicable. | Session defense. |
| APPSEC-FR-026 | Security headers | CSP, frame-ancestors/X-Frame controls, Referrer-Policy, MIME sniff protection and HSTS where appropriate. | Browser hardening. |
| APPSEC-FR-027 | API versioning | Deprecated insecure endpoint versions have removal plan/telemetry and cannot linger undocumented. | Attack surface. |
| APPSEC-FR-028 | Graph/relationship queries | Prevent unauthorized traversal through genealogy/search/report endpoints. | Indirect disclosure. |
| APPSEC-FR-029 | Bulk operations | Bulk mutations apply per-object authorization/business rules and bounded transaction behavior. | No batch bypass. |
| APPSEC-FR-030 | Security tests | ASVS/API Security requirements mapped to automated tests and penetration test scenarios. | Verification. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| authorizeObjectAccess() | API/service method | AuthContext; action; resource type/id; requested fields | Authenticated; tenant scope known | Calls Policy Service and property-level rules; no DB mutation | AuthorizationDecision | ACCESS_DENIED |
| validateRequestSchema() | API middleware | operationId; request body/query/path | Schema version registered | Parses strict schema, rejects unknown/invalid fields per contract | ValidatedRequest | REQUEST_SCHEMA_INVALID |
| sanitizeRichText() | UI/API input | html/text; sanitizer policy version | Field explicitly rich-text capable | Sanitizes against allowlist; stores canonical safe content | SanitizedContent | UNSAFE_CONTENT_REJECTED |
| validateOutboundDestination() | Integration/file fetch | URL/host/service ID; purpose | Outbound operation allowed | Resolves against destination registry, blocks private/metadata/redirect escape per policy | DestinationDecision | SSRF_DESTINATION_BLOCKED |
| validateFileUpload() | Upload endpoint | stream; filename; declared type; expected context | Authorized context; quotas | Checks size/signature/type; scans/quarantines; stores evidence metadata | UploadReceipt | FILE_TYPE_BLOCKED/MALWARE_DETECTED |
| protectSpreadsheetExport() | Export service | rows/columns; field metadata | Export authorized | Escapes formula-leading values and applies masking/field rules | SafeExportDataset | none |
| enforceRateLimit() | Gateway/middleware | subject/client/IP/operation; cost | Rate policy loaded | Token bucket/leaky bucket or equivalent; records counters | RateLimitDecision | RATE_LIMITED |
| verifyWebhook() | Inbound integration | headers/cert/body; provider profile | Provider active | Verifies signature/mTLS/time/replay; validates body schema | VerifiedWebhook | WEBHOOK_AUTH_FAILED/REPLAY_DETECTED |
| mapSafeErrorResponse() | API exception handler | internal error; correlation ID | None | Maps to stable public error; logs internal details separately | PublicError | none |


# 5. State / Control Model

```text
REQUEST
  ↓ authenticate
AUTH_CONTEXT
  ↓ schema/resource bounds
VALIDATED_REQUEST
  ↓ authorization/object/property checks
AUTHORIZED_REQUEST
  ↓ business/domain validation
DOMAIN_COMMAND
  ↓
RESPONSE MINIMIZATION + SECURITY HEADERS

FAILURE AT ANY SECURITY GATE → REJECT + SECURITY/AUDIT TELEMETRY AS APPLICABLE
```

# 6. Data Model

## `api_security_policy`
- operationId
- auth mode
- allowed roles/scopes
- object policy
- writable/readable field sets
- rate/resource limits
- file/export policy
- CORS/CSRF profile

## `outbound_destination`
- service ID
- schemes/hosts/ports
- IP range restrictions
- redirect policy
- auth/secret ref
- purpose/state

## `webhook_profile`
- provider
- auth mechanism
- replay window
- schema version
- size limits


# 7. APIs / Internal Interfaces

- `All OpenAPI endpoints inherit security middleware`
- `POST /security/v1/outbound-destinations`
- `POST /security/v1/webhook-profiles`
- `GET /security/v1/api-inventory`

All security-sensitive mutations are server-side and auditable.

# 8. UI / Administrative Screens

1. API Security Inventory
2. Rate-Limit Policies
3. Outbound Destination Registry
4. Webhook Profiles
5. File Quarantine
6. Security Test Coverage

# 9. Security Events

- `APIAccessDenied`
- `RateLimitTriggered`
- `SSRFBlocked`
- `MaliciousUploadDetected`
- `WebhookReplayDetected`
- `DeprecatedAPIUsed`

# 10. Failure / Recovery

- Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies.
- Security subsystem outage must not silently downgrade protection.
- Retryable infrastructure failures use bounded retry/backoff.
- Security-control bypass requires a separate controlled emergency path, not a hidden fallback.
- Recovery actions are themselves logged and reviewable.

# 11. Repository Structure

```text
services/security/application-api-ui-secure-runtime-engineering/
packages/security-contracts/
infrastructure/security/
apps/ebmr_frappe/ebmr/security/application-api-ui-secure-runtime-engineering/
validation/security/application-api-ui-secure-runtime-engineering/
tests/security/application-api-ui-secure-runtime-engineering/
```

# 12. Mandatory Test Catalogue

- BOLA cross-tenant ID
- mass assignment state/role field
- SQL injection payload
- stored XSS
- CSRF mutation
- SSRF metadata IP
- oversized upload
- malware file
- CSV formula injection
- third-party API malformed payload
- bulk auth bypass

# 13. Acceptance Criteria

No public or internal API can access or mutate an object solely because a caller knows its ID; every request is schema-valid, resource-bounded and server-authorized.

# 14. Claude Code / Codex Prohibitions

- Never trust hidden UI controls for authorization.
- Never bind request JSON directly to ORM/model entity.
- Never permit arbitrary user URL fetch from application servers.
- Never expose stack trace/secrets in production error.


