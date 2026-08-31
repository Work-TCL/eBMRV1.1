# US eBMR / eDHR Regulated Manufacturing Platform
## Document 04 — 21 CFR Part 11 Electronic Signature — Detailed Functional & Technical Specification — v1.1

**Specification ID:** SPEC-GXP-002  
**Parent Documents:** Document 01 v1.1 (FROZEN) and Document 02 v1.0  
**Dependencies:** Documents 01–03; Document 07 IAM/SoD; Document 05 Audit; Document 06 Record Vault  
**Status:** Proposed v1.1 — IMPLEMENTATION-READY BASELINE / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products  
**Future Profiles:** Medical Devices and Pharmaceuticals  
**Date:** 2026-08-20

---

# 1. Objective

Define the electronic-signature subsystem used for regulated signings throughout eBMR/eDHR, QMS, QC, materials, equipment and release workflows.

A normal authenticated Frappe session, workflow transition, typed name, uploaded image, checkbox, or Frappe Signature field is **not** sufficient by itself.

# 2. Regulatory Design Basis

The design explicitly addresses:
- §11.50 — printed name, date/time and meaning;
- §11.70 — signature-to-record linkage;
- §11.100 — uniqueness, identity verification and customer certification responsibilities;
- §11.200 — electronic-signature components/controls;
- §11.300 — identification code/password governance where applicable;
- §11.10(d),(g),(j) — authorized access, authority checks and accountability policies.

# 3. Architecture

```text
Record/Action needs signature
        ↓
Policy evaluates signer requirement
        ↓
Signature Service creates Challenge
        ↓
User sees exact target + meaning
        ↓
Fresh Step-Up at Keycloak/Customer IdP
        ↓
Trusted auth response/token
        ↓
Signature Service verifies:
  identity + challenge + nonce + expiry
  record version/hash + role/qualification/SoD
        ↓
Signature Record committed
        ↓
Mutation Gateway commits signed action
        ↓
Audit + Record Version + Export Manifest
```

# 4. Signature State Model

`CREATED → AUTH_PENDING → AUTHENTICATED → VERIFIED → CONSUMED`

Negative/terminal:
`EXPIRED`, `CANCELLED`, `DENIED`, `REPLAYED`, `STALE_RECORD`, `AUTH_FAILED`.

A `VERIFIED` signature challenge shall be consumed only by the intended regulated mutation.

# 5. Detailed Requirements

| ID | Requirement | Detailed behavior / sub-functionalities | Acceptance intent |
|---|---|---|---|
| SIG-FR-001 | Unique signer identity | Every electronic signature is linked to one immutable individual subject identifier. Display names may change historically, but signer subject cannot be reassigned. | Historical signature remains attributable after rename/deactivation. |
| SIG-FR-002 | Identity verification responsibility | Customer organization must have a controlled process to verify identity before granting electronic-signature authority; system stores status/evidence reference where configured. | Unverified identity cannot receive signing entitlement. |
| SIG-FR-003 | Signature meaning catalogue | Controlled meanings include Performed, Verified, Reviewed, Approved, Released, Rejected, Authored, Witnessed and customer-approved extensions. | Meaning is explicit in challenge, record and export. |
| SIG-FR-004 | Signature policy mapping | Record/action policy defines required meaning, signer role/qualification, number/order of signatures, independent signer restrictions and authentication assurance. | Client cannot alter required signer policy. |
| SIG-FR-005 | Challenge creation | Create server-side unique signature challenge containing challenge ID, signer subject, tenant/site, record ID, version/hash, action/meaning, nonce and expiry. | Challenge is unique and short-lived. |
| SIG-FR-006 | Fresh step-up authentication | Every regulated Part 11 signature in V1 requires fresh step-up authentication through configured IdP; normal existing session alone is insufficient. | Recorded authentication time/assurance meets configured policy. |
| SIG-FR-007 | Identification components | Non-biometric signature configuration must be validated to meet applicable §11.200 component controls. IdP policy must not silently downgrade required factors/components. | Configured test demonstrates required components. |
| SIG-FR-008 | Continuous-access policy | Although Part 11 distinguishes continuous sessions, V1 intentionally applies fresh step-up for every regulated signature as a stronger product baseline. | No session-only signing path exists. |
| SIG-FR-009 | Authentication context capture | Persist trusted IdP issuer, subject, authentication time, method/AMR, assurance/ACR where available, session reference and challenge reference. | Signature proves authentication event context. |
| SIG-FR-010 | Record/version/hash binding | Signature binds exact regulated record ID, version and cryptographic hash (or canonical immutable snapshot ID). | Signature invalid for modified/superseding version. |
| SIG-FR-011 | Command/action binding | Signature also binds intended action and meaning; an approval signature cannot be reused for release or correction. | Cross-action replay rejected. |
| SIG-FR-012 | Nonce/replay prevention | Nonce/challenge is single use. Repeated callback/token cannot create second signature. | Replay negative test passes. |
| SIG-FR-013 | Challenge expiry | Expired challenge cannot be completed; new challenge requires re-evaluation against current record state/version. | Expired challenge fails closed. |
| SIG-FR-014 | Changed-record invalidation | If record or command-relevant state changes after challenge creation, signature challenge is invalidated. | Stale signing rejected. |
| SIG-FR-015 | Signature manifestation | Signed record and human-readable export show printed name, execution date/time and signature meaning. | PDF/display test confirms manifestation. |
| SIG-FR-016 | Signature/record linking | Signature record is linked by immutable identifiers/hash so it cannot be excised, copied or transferred to another record by ordinary application means. | Copying signature ID to another record fails integrity checks. |
| SIG-FR-017 | Multiple signatures | Support performer/verifier, author/approver, QA reviewer/releaser and other ordered or independent signature chains. | Order and independence enforced server-side. |
| SIG-FR-018 | Segregation of duties | Policy may require signer != performer/author/previous signer; signer role and qualification checked at signature completion time. | Same-user prohibited scenario rejected. |
| SIG-FR-019 | Failed attempts | Failed step-up, expired challenge, wrong identity, denied policy and replay attempts do not create valid signature; security-relevant attempts are logged. | No orphan valid signature on failure. |
| SIG-FR-020 | User deactivation | Disabling signer prevents future signatures but does not invalidate historical legitimate signatures. | Historical exports remain valid. |
| SIG-FR-021 | Credential reset/recovery | Identity credential recovery is handled by IdP policy; product does not expose old credentials. High-risk recovery may suspend signing until customer process completes. | Recovered account policy testable. |
| SIG-FR-022 | No signature delegation | Users cannot delegate their electronic signature. Workflow delegation may reassign work but new assignee signs as self. | Delegated task preserves distinct signer. |
| SIG-FR-023 | Service account prohibition | Service/integration/device identity cannot create human Part 11 signature. | Service token rejected on human signature endpoint. |
| SIG-FR-024 | Biometric extensibility | Architecture may accept customer IdP biometric/WebAuthn assurance later, but the GxP Signature Service still creates the regulatory signature record. | Authentication technology does not replace GxP record. |
| SIG-FR-025 | Time source | Signature execution time is assigned server-side in UTC; local timezone is presentation metadata. | Browser clock manipulation has no effect. |
| SIG-FR-026 | Signer acknowledgement | UI clearly displays what is being signed, meaning, relevant record identity/version and any required statement before step-up. | User cannot sign ambiguous hidden target. |
| SIG-FR-027 | Signature receipt | Return signature_id, challenge_id, signer subject/name, time, meaning, record/version/hash and auth context reference. | Downstream transaction can reference exact signature. |
| SIG-FR-028 | Revocation/correction handling | A historical signature is never deleted. If signed record is superseded/corrected, old signature remains on old version; new version requires required new signatures. | Correction preserves prior signatures. |
| SIG-FR-029 | Customer Part 11 certification support | Provide configurable evidence/report supporting customer's §11.100 certification/governance responsibilities; software does not submit certification automatically unless separately designed. | Responsibility remains explicit. |
| SIG-FR-030 | Inspection/reporting | Authorized auditor can list all signatures for record/batch/user/time range and export manifestation plus linkage/integrity metadata. | Inspection query is reproducible. |

# 6. Signature Challenge Data Model

```text
challenge_id
tenant_id
site_id
signer_subject_id
record_type
record_id
record_version
record_hash
command_id
action
signature_meaning
required_auth_policy
nonce
created_at_utc
expires_at_utc
status
```

# 7. Signature Record Data Model

```text
signature_id
challenge_id
tenant/site
signer_subject_id
signer_display_name_at_signing
record_type/id/version/hash
action
meaning
executed_at_utc
idp_issuer
authentication_time
authentication_methods
authentication_assurance
session/reference
signature_service_version
policy_version
```

Do not store the signer's password, OTP secret or raw reusable credential.

# 8. Keycloak / Customer IdP Boundary

Keycloak/customer IdP:
- authenticates;
- applies MFA/credential policies;
- returns trusted authentication context.

GxP Signature Service:
- determines what record/action is being signed;
- binds it to challenge;
- verifies fresh auth context;
- creates immutable signature evidence;
- links signature to record/version/hash.

# 9. UI Requirements

Before sign:
- product/batch/document identity;
- exact action;
- signature meaning;
- relevant version;
- warning if data changed;
- required comment/reason;
- signer name.

After sign:
- signed status;
- signer printed name;
- UTC/local display time;
- meaning;
- signature ID;
- resulting record version.

# 10. Failure Behavior

| Condition | Result |
|---|---|
| Wrong user completes challenge | Reject |
| Record changed | Mark stale, require new challenge |
| Challenge expired | Reject |
| IdP unavailable | Signing unavailable; no bypass |
| Authentication succeeds but Mutation commit fails | Challenge/signature state must not create falsely completed business action; reconciliation required |
| Duplicate callback | Idempotent verification |
| User disabled before completion | Reject |
| Missing required SoD | Reject |

The final implementation shall ensure signature creation and signed business transition cannot become misleadingly inconsistent. Preferred approach: verified challenge is consumed by the authoritative GxP transaction, with immutable linkage to resulting record version.

# 11. Audit

Audit:
- challenge created;
- policy requirement;
- successful signature;
- denied/replayed/stale attempts where significant;
- signed business action;
- supersession/correction relationship.

Do not log passwords, OTPs or reusable authentication secrets.

# 12. Validation Tests

Minimum:
1. unique signer;
2. renamed signer history;
3. disabled signer;
4. wrong signer challenge;
5. fresh authentication required;
6. record changes before completion;
7. action/meaning mismatch;
8. challenge expiry;
9. replay;
10. duplicate callback;
11. performer/verifier SoD;
12. service account attempts signing;
13. manifestation in UI;
14. manifestation in PDF/export;
15. signature linked to exact old version after correction;
16. customer IdP outage;
17. auth method policy downgrade;
18. timezone/display;
19. history query;
20. backup/restore retains signature linkage.

# 13. Acceptance Gate

Before freeze:
- identity provider reference flow proven;
- at least one Entra/Keycloak-style enterprise SSO flow tested;
- signature challenge cryptographic/integrity design reviewed;
- Record Vault canonical hash contract frozen;
- SoD matrix reconciled with Document 07;
- Part 11 assessment maps each signature control.

# 14. Developer / AI-Agent Rules

Never implement “Approve” as a valid regulated signature solely from a logged-in session.
Never store user passwords.
Never copy a signature record to a new version.
Never allow an admin to create a signature on behalf of another user.
Never use browser time as signature time.

# Regulatory Source Basis

This specification is an engineering/control design document. Regulatory applicability remains dependent on intended use, predicate-rule records, product profile, and customer procedures.

Primary current sources used for the GxP Core baseline:

1. **21 CFR Part 11 — Electronic Records; Electronic Signatures**
   - §11.10 Controls for closed systems
   - §11.50 Signature manifestations
   - §11.70 Signature/record linking
   - §11.100 General requirements
   - §11.200 Electronic signature components and controls
   - §11.300 Controls for identification codes/passwords
2. **FDA — Part 11, Electronic Records; Electronic Signatures — Scope and Application**
3. Applicable predicate-rule requirements, including drug CGMP / device QMSR / combination-product controls.
4. For regulated calculations and batch evidence, applicable provisions may include 21 CFR §§211.68, 211.101, 211.103 and 211.188.

Reference URLs:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application
- https://www.law.cornell.edu/cfr/text/21/11.10
- https://www.law.cornell.edu/cfr/text/21/11.70
- https://www.law.cornell.edu/cfr/text/21/211.68
- https://www.law.cornell.edu/cfr/text/21/211.103
- https://www.law.cornell.edu/cfr/text/21/211.188

**Important:** this product shall be described as *designed to support compliance* and *validation-ready*. It shall not be marketed as automatically “FDA certified” or universally “Part 11 compliant.”


---

# IMPLEMENTATION-GRADE BLUEPRINT

The sections below are normative for implementation. A coding agent shall not invent missing behavior where this specification is explicit. If an implementation question changes regulated behavior, state, authorization, signature, audit, retention or data ownership, implementation must stop and raise a specification issue/change request rather than guessing.

## A. Required Deliverables from the Implementation Team

For this module, the implementation PR/release shall include:

1. application/domain code;
2. database migrations;
3. OpenAPI contract updates;
4. JSON Schema/event contract updates;
5. unit tests;
6. API tests;
7. authorization/negative tests;
8. concurrency/idempotency tests where applicable;
9. failure/recovery tests;
10. audit/signature traceability tests;
11. observability/health instrumentation;
12. configuration defaults;
13. migration/rollback notes;
14. requirement-to-test traceability;
15. SBOM/license impact update;
16. validation-impact note.

## B. Definition of Done

A requirement is not “implemented” merely because a screen exists.

It is complete only when:

- server-side behavior matches the requirement;
- authorization is enforced;
- required audit/signature behavior exists;
- database constraints support the intended invariant;
- APIs and events are versioned;
- expected failures are handled;
- tests prove positive and negative behavior;
- documentation and traceability are updated;
- no prohibited bypass path exists.

## C. Cross-Cutting Engineering Conventions

### Identifiers
- UUIDv7 or another approved sortable unique identifier for internal immutable IDs.
- Human/business numbers may use controlled prefixes/sequences but never replace immutable internal IDs.
- All foreign references use immutable internal IDs.

### Time
- Store authoritative regulated time in UTC.
- Use `timestamptz` in PostgreSQL.
- Local timezone is metadata/presentation only.
- Browser/client time is never authoritative.

### Monetary/quantity/calculation values
- Use decimal/numeric types, never binary float for regulated calculations.
- Store UOM explicitly.
- Precision/scale follows released rule/specification.

### Concurrency
- Use optimistic concurrency via version columns for regulated aggregates.
- Use unique constraints/idempotency for replayable external commands.
- Use row/advisory locks only where resource reservation requires pessimistic control.

### Logging
- Operational logs include request/correlation IDs.
- Do not log credentials, tokens, OTPs, secrets, raw authentication assertions or sensitive payloads unnecessarily.
- GxP audit remains distinct from application logs.

### Database access
- Application runtime uses least-privilege service roles.
- No application feature shall require DBA privileges.
- Direct production SQL changes to regulated records are prohibited outside a controlled incident/change process.

### Testing
Every module shall include:
- happy path;
- authorization denial;
- validation failure;
- stale/concurrent write;
- duplicate/replay where applicable;
- dependency outage;
- restart/recovery;
- data integrity;
- audit verification;
- signature verification where applicable.



# 15. Concrete Service / Package Structure

```text
services/signature/
├── src/
│   ├── signature.controller.ts
│   ├── signature.service.ts
│   ├── challenge.service.ts
│   ├── auth-context-verifier.ts
│   ├── signature-policy.client.ts
│   ├── canonical-target.client.ts
│   ├── replay-protection.ts
│   ├── errors.ts
│   └── idp/
│       ├── oidc-verifier.ts
│       └── keycloak-adapter.ts
├── migrations/
├── openapi/
└── test/
```

# 16. PostgreSQL Tables

## `gxp_signature_challenge`

```text
challenge_id uuid PK
tenant_id uuid NOT NULL
site_id uuid NOT NULL
signer_subject_id varchar(255) NOT NULL
record_type varchar(80) NOT NULL
record_id uuid NOT NULL
record_version bigint NOT NULL
record_hash char(64) NOT NULL
command_id uuid NOT NULL
action varchar(120) NOT NULL
meaning_code varchar(80) NOT NULL
required_auth_policy varchar(80) NOT NULL
nonce_hash char(64) NOT NULL
status varchar(40) NOT NULL
created_at timestamptz NOT NULL
expires_at timestamptz NOT NULL
verified_at timestamptz
consumed_at timestamptz
```

Indexes:
- `(tenant_id, signer_subject_id, status, expires_at)`;
- `(record_id, record_version)`;
- unique `(command_id, meaning_code, signer_subject_id)` where policy requires one signature.

## `gxp_signature`

```text
signature_id uuid PK
challenge_id uuid UNIQUE NOT NULL
tenant_id uuid NOT NULL
site_id uuid NOT NULL
signer_subject_id varchar(255) NOT NULL
signer_display_name varchar(255) NOT NULL
record_type varchar(80) NOT NULL
record_id uuid NOT NULL
record_version bigint NOT NULL
record_hash char(64) NOT NULL
command_id uuid NOT NULL
action varchar(120) NOT NULL
meaning_code varchar(80) NOT NULL
executed_at timestamptz NOT NULL
idp_issuer varchar(500) NOT NULL
idp_session_ref varchar(255)
auth_time timestamptz
amr jsonb
acr varchar(255)
signature_service_version varchar(40) NOT NULL
policy_version varchar(80) NOT NULL
```

No UPDATE of core signature semantics after creation.

# 17. API Contract

## Create challenge
`POST /signature/v1/challenges`

Request:
```json
{
  "record_type":"Batch",
  "record_id":"...",
  "record_version":55,
  "record_hash":"...",
  "command_id":"...",
  "action":"batch.release",
  "meaning":"RELEASE"
}
```

Server determines signer from authenticated subject and policy.

## Verify/complete challenge
`POST /signature/v1/challenges/{id}/verify`

Payload contains only non-reusable IdP authorization response/proof required by the chosen flow. Raw password/OTP shall never be sent to Signature Service.

## Consume signature
Internal-only operation used by Mutation Gateway:
`POST /signature/v1/signatures/{id}/consume`

Requires:
- same command ID;
- same record/version/hash;
- unconsumed;
- not expired/revoked;
- policy still valid.

# 18. Error Codes

```text
SIGNER_NOT_ELIGIBLE
SIGNATURE_POLICY_NOT_FOUND
CHALLENGE_EXPIRED
CHALLENGE_ALREADY_USED
CHALLENGE_CANCELLED
WRONG_SIGNER
AUTH_CONTEXT_INVALID
AUTH_NOT_FRESH
AUTH_ASSURANCE_TOO_LOW
RECORD_VERSION_CHANGED
RECORD_HASH_CHANGED
ACTION_MISMATCH
MEANING_MISMATCH
SOD_CONFLICT
SIGNATURE_ALREADY_CONSUMED
SERVICE_ACCOUNT_NOT_ALLOWED
```

# 19. Sequence — QA Batch Release

```text
QA UI
 → Mutation Gateway: request release
 ← signature required

QA UI
 → Signature Service: create challenge
 ← challenge + IdP step-up instruction

QA UI
 → IdP: fresh authentication
 ← trusted auth response

QA UI
 → Signature Service: verify challenge
 ← signature proof/id

QA UI
 → Mutation Gateway: release command + signature id
Gateway
 → Signature Service: consume/validate
 → Policy/Rules: re-evaluate
 → PostgreSQL: release + audit + outbox
 ← committed receipt
```

# 20. UI Components

Reusable component:
`<RegulatedSignatureDialog>`

Inputs:
- action;
- meaning;
- record identity/version;
- summary fields;
- required reason/comment;
- signature policy.

Must display:
- exact record target;
- exact action/meaning;
- signer identity;
- warning that signature is attributable;
- current record version;
- reason/comment if required.

# 21. Configuration

`signature_policy` configuration contains:
- action;
- meaning;
- allowed signer roles;
- qualification;
- SoD constraints;
- required authentication policy;
- challenge TTL;
- ordered multi-signature rules.

Customer can select only prevalidated policy options; cannot inject arbitrary authentication logic.

# 22. Observability

Metrics:
- challenges created;
- verified;
- expired;
- denied;
- stale;
- replay attempts;
- IdP latency/errors;
- consumed signatures;
- unconsumed verified signatures.

Alerts:
- replay spike;
- auth policy downgrade;
- excessive failed sign attempts;
- signature-service clock drift.

# 23. Implementation Sequence

1. policy/config schema;
2. challenge table;
3. OIDC validation;
4. Keycloak reference integration;
5. record target/hash verification;
6. replay/expiry;
7. signature table;
8. consume contract;
9. multi-signature;
10. UI component;
11. export manifestation;
12. negative/attack tests.

# 24. Validation Traceability

Each signature policy must map:
`policy → Part 11 control → action → role → auth requirement → SoD → UI → API → tests`.

