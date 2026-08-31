# US eBMR / eDHR Regulated Manufacturing Platform
## Document 63 — Privileged Access, Support Access, Break-Glass & Administrative Security — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-SEC-003  
**Parent Documents:** Documents 01–60  
**Primary Dependencies:** Documents 07, 29, 61–62; Infrastructure/Operations  
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

Define controlled privileged technical access to production and customer environments so administrators and support personnel can operate the platform without acquiring Quality authority or bypassing GxP mutation controls.

# 2. Actors / Components

- Platform Admin
- Security Admin
- Infrastructure Admin
- DB Admin
- Integration Admin
- Vendor Support Engineer
- Customer Admin
- Approver
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| PAM-FR-001 | Privileged role catalogue | Define platform admin, security admin, DB admin, infrastructure admin, support engineer, integration admin and customer admin separately. | Role separation. |
| PAM-FR-002 | Admin not Quality | Privileged technical role never implies production/QC/QA/release/signature authority. | SoD. |
| PAM-FR-003 | Named accounts | Privileged actions require named human account; shared admin accounts prohibited. | Attribution. |
| PAM-FR-004 | MFA | Privileged interactive access requires MFA. | Strong admin auth. |
| PAM-FR-005 | JIT access | Support just-in-time elevated access with ticket/reason/scope/start/expiry and approver. | Least privilege. |
| PAM-FR-006 | Support access | Vendor/support access disabled by default and enabled per customer/site/time window. | Customer control. |
| PAM-FR-007 | Support purpose | Support session has case/ticket, reason, customer approval where required and explicit resource scope. | Purpose limitation. |
| PAM-FR-008 | Read-only default | Support role defaults read-only diagnostics; mutation requires separately approved privileged change path. | Safe support. |
| PAM-FR-009 | Production shell | Interactive shell/SSH/kubectl access to production minimized and controlled by JIT/bastion/PAM pattern. | Reduced exposure. |
| PAM-FR-010 | Database access | Direct production DB access restricted; GxP data repair uses controlled repair commands, not ad-hoc UPDATE. | Data integrity. |
| PAM-FR-011 | Break-glass | Emergency account/path is disabled/sealed or tightly monitored, requires explicit reason and immediate post-use review. | Emergency resilience. |
| PAM-FR-012 | Break-glass scope | Break-glass does not grant electronic-signature or QA release rights. | GxP boundary. |
| PAM-FR-013 | Session recording | Privileged shell/admin session commands/activity recorded where deployment permits; database diagnostic queries logged where feasible. | Forensics. |
| PAM-FR-014 | Clipboard/download restriction | Support export/download of sensitive data limited and audited. | Data protection. |
| PAM-FR-015 | No impersonation | Support cannot impersonate end user to create GxP actions/signatures. | Integrity. |
| PAM-FR-016 | Approval separation | Requester cannot approve own privileged elevation except emergency path requiring retrospective review. | SoD. |
| PAM-FR-017 | Time bound | Elevation expires automatically; no permanent hidden grants. | Least privilege. |
| PAM-FR-018 | Command allowlist | High-risk admin operations exposed as controlled commands with validation/audit rather than arbitrary DB/scripts. | Safe operations. |
| PAM-FR-019 | Config changes | Security/infra production configuration changes link Change Control where GxP-impacting. | Validated state. |
| PAM-FR-020 | Customer data access | Vendor staff tenant access requires explicit tenant scope and support entitlement. | Isolation. |
| PAM-FR-021 | Secrets access | Viewing raw production secrets is restricted and exceptional; prefer delegated operations without secret disclosure. | Credential hygiene. |
| PAM-FR-022 | Admin API | Administrative APIs separate namespace/scopes/rate limits and not exposed publicly unless required. | Attack surface. |
| PAM-FR-023 | Activity monitoring | Privileged events produce high-signal telemetry and alerts for unusual scope/time/actions. | Detection. |
| PAM-FR-024 | Periodic review | Privileged assignments and support entitlements reviewed periodically. | Governance. |
| PAM-FR-025 | Offboarding | Termination/vendor access removal immediately revokes sessions/keys/JIT grants. | Lifecycle. |
| PAM-FR-026 | Emergency repair evidence | Any emergency technical repair records original issue, command, before/after hashes, approver and linked deviation/change/security incident. | Inspection-ready. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| requestPrivilegedAccess() | Admin/Support user | requested_role; tenant/site/resources; reason; ticket; duration | Named user/MFA; entitlement/request policy valid | Creates PENDING JIT request, no privilege yet | PrivilegedAccessRequest | PrivilegedAccessRequested |
| approvePrivilegedAccess() | Authorized approver | request_id; decision; comments | Approver distinct unless emergency; request not stale | Creates time-bound grant/token/session entitlement | PrivilegedGrant | PrivilegedAccessGranted |
| evaluatePrivilegedGrant() | Admin middleware | subject; operation; resource; current time | Grant active; MFA/session valid | Checks role/scope/time/ticket and returns allow/deny | PrivilegedDecision | PRIVILEGED_ACCESS_DENIED |
| openSupportSession() | Support portal | grant_id; customer tenant; support case | Support entitlement/customer approval valid | Creates scoped support session with read-only default | SupportSession | SupportSessionOpened |
| executeControlledAdminCommand() | Admin UI/CLI | command_code; parameters; grant; reason | Command allowlisted; grant authorizes; validation passes | Runs typed operation; stores command/audit/result | AdminCommandReceipt | AdminCommandExecuted; ADMIN_COMMAND_NOT_ALLOWED |
| activateBreakGlass() | Emergency operator | emergency identity/path; incident ID; reason | Emergency criteria; strong auth; alerting available | Creates short emergency grant; alerts Security/Quality; no GxP signer authority | BreakGlassSession | BreakGlassActivated |
| closePrivilegedSession() | User/system expiry | session_id; outcome | Session exists | Revokes access; seals session evidence; schedules review if break-glass | CloseReceipt | PrivilegedSessionClosed |
| reviewPrivilegedSession() | Security reviewer | session_id; evidence; findings | Session closed | Records review, incidents/deviations/remediation | PrivilegedReview | PrivilegedSessionReviewed |


# 5. State / Control Model

```text
NO_ELEVATION
   ↓ request
PENDING_APPROVAL
   ├→ DENIED
   └→ ACTIVE_JIT_GRANT
           ↓
      PRIVILEGED_SESSION
           ↓
        EXPIRED/CLOSED
           ↓
        REVIEW (if required)

EMERGENCY → BREAK_GLASS_ACTIVE → CLOSED → MANDATORY_REVIEW
```

# 6. Data Model

## `privileged_access_request`
```text
id uuid PK
subject_id uuid
requested_role varchar
tenant/site/resource_scope jsonb
reason text
ticket_ref varchar
requested_start/end
state varchar
approver_id uuid
```

## `privileged_grant`
- request ID
- role/scope
- effective/expiry
- auth strength
- state

## `privileged_session`
- grant
- start/end
- connection/source
- actions/command refs
- recording/evidence ref
- review status


# 7. APIs / Internal Interfaces

- `POST /security/v1/privileged-access/requests`
- `POST /security/v1/privileged-access/requests/{id}/approve`
- `POST /security/v1/support-sessions`
- `POST /security/v1/admin-commands/{code}:execute`
- `POST /security/v1/break-glass`
- `POST /security/v1/privileged-sessions/{id}/close`

All security-sensitive mutations are server-side and auditable.

# 8. UI / Administrative Screens

1. Privileged Access Requests
2. Active Grants
3. Support Sessions
4. Controlled Admin Commands
5. Break-Glass
6. Privileged Session Review
7. Privileged Role Review

# 9. Security Events

- `PrivilegedAccessRequested`
- `PrivilegedAccessGranted`
- `SupportSessionOpened`
- `AdminCommandExecuted`
- `BreakGlassActivated`
- `PrivilegedSessionClosed`
- `PrivilegedSessionReviewed`

# 10. Failure / Recovery

- Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies.
- Security subsystem outage must not silently downgrade protection.
- Retryable infrastructure failures use bounded retry/backoff.
- Security-control bypass requires a separate controlled emergency path, not a hidden fallback.
- Recovery actions are themselves logged and reviewable.

# 11. Repository Structure

```text
services/security/privileged-access-support-access-break-glass-administrative-security/
packages/security-contracts/
infrastructure/security/
apps/ebmr_frappe/ebmr/security/privileged-access-support-access-break-glass-administrative-security/
validation/security/privileged-access-support-access-break-glass-administrative-security/
tests/security/privileged-access-support-access-break-glass-administrative-security/
```

# 12. Mandatory Test Catalogue

- self-approval denied
- grant expiry during session
- support cross-tenant access denied
- DB UPDATE attempt absent from allowed tools
- break-glass cannot sign QA release
- admin command parameter validation
- terminated support user access revoked

# 13. Acceptance Criteria

A vendor/platform administrator can troubleshoot a customer deployment without obtaining generic write access to GxP records, impersonating users, or signing/releasing product.

# 14. Claude Code / Codex Prohibitions

- Never give platform admin automatic QA/production authority.
- Never provide generic SQL repair console to support.
- Never implement permanent vendor support superuser.
- Never allow break-glass to create Part 11 signature.


