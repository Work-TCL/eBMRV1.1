# US eBMR / eDHR Regulated Manufacturing Platform
## Document 07 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties — Specification — v1.1

**Specification ID:** SPEC-IAM-001  
**Parent Documents:** Document 01 v1.1 (FROZEN) and Document 02 v1.0  
**Dependencies:** Documents 01–06; Keycloak/customer IdP; Training/Qualification specification; Security specification  
**Status:** Proposed v1.1 — IMPLEMENTATION-READY BASELINE / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products  
**Future Profiles:** Medical Devices and Pharmaceuticals  
**Date:** 2026-08-20

---

# 1. Objective

Define identity and authority so that only properly authenticated, authorized and qualified humans/services/devices can perform the exact regulated action at the exact site/resource/state.

# 2. Authorization Model

```text
SUBJECT
  ├ identity
  ├ roles
  ├ site/area scopes
  ├ qualifications
  ├ training
  └ signature entitlement
          +
RESOURCE
  ├ tenant/site
  ├ record type
  ├ state
  ├ product/process
  └ prior actors/signers
          +
ACTION
          +
CONTEXT
  ├ time
  ├ emergency status
  └ customer policy
          ↓
Policy Service
          ↓
ALLOW / DENY + reason + policy version
```

# 3. Reference Role Families

Production:
- Production Manager
- Production Supervisor
- Operator
- Dispensing Operator
- Packaging Operator

Quality:
- Head of Quality
- QA Manager
- QA Reviewer
- QA Release
- Deviation Investigator
- CAPA Owner

QC:
- QC Manager
- QC Analyst
- Sampler

Warehouse/Procurement:
- Warehouse Manager
- Material Receiver
- Material Issuer
- Buyer
- Procurement Manager
- Supplier Quality

Engineering:
- Engineering Manager
- Maintenance Technician
- Calibration Technician
- Equipment Administrator

Controlled Support:
- Document Controller
- Training Coordinator
- Complaint Investigator
- Internal Auditor
- Read-only Inspector

IT:
- Application Administrator
- Security Administrator
- Identity Administrator
- Integration Service Account

# 4. Detailed Requirements

| ID | Requirement | Detailed behavior / sub-functionalities | Acceptance intent |
|---|---|---|---|
| IAM-FR-001 | Unique human identity | Each user has immutable internal subject mapping to enterprise identity; shared regulated accounts prohibited. | Two users cannot share signing identity. |
| IAM-FR-002 | External identity federation | Support OIDC/SAML through Keycloak-compatible boundary; customer Entra/Okta/AD or equivalent may be source. | Authentication provider replaceable. |
| IAM-FR-003 | Local identity fallback | On-prem deployments may use controlled local Keycloak identity where customer SSO unavailable, subject to equivalent policies. | No cloud IdP hard dependency. |
| IAM-FR-004 | User lifecycle | Provision, activate, suspend, disable, terminate and retain historical identity metadata. | Disabled user cannot act/sign. |
| IAM-FR-005 | Role catalogue | Reference roles grouped by Production, QA, QC, Warehouse, Procurement, Engineering, QMS, IT and Auditor. | Role names configurable but permissions controlled. |
| IAM-FR-006 | Permission actions | Permissions are action/resource based, not merely screen access: view, create-draft, execute, verify, approve, release, correct, administer, export, etc. | UI hiding not permission. |
| IAM-FR-007 | Tenant scope | Identity cannot access another customer environment/data. | Isolation negative test. |
| IAM-FR-008 | Site/area scope | User access can be limited to site, building, area/room/line and function where required. | Cross-site operation blocked. |
| IAM-FR-009 | Product/process scope | Authorization may restrict user to product family, process type or specialized operation. | Specialized task protected. |
| IAM-FR-010 | Qualification object | Model qualifications such as dispensing, sterile-area, aseptic operation, QA release, equipment use and specialized testing. | Qualification has status/effective/expiry. |
| IAM-FR-011 | Training gate | Required training/SOP curriculum status can be evaluated before execution/signing. | Expired training blocks configured action. |
| IAM-FR-012 | Equipment qualification authorization | User may require equipment-specific or class qualification before operating/verifying. | Execution gate server-side. |
| IAM-FR-013 | Signature entitlement | Only users with active electronic-signature entitlement and verified identity status may complete regulated signature challenges. | Role alone insufficient. |
| IAM-FR-014 | Segregation-of-duties policy | Support performer != verifier, author != approver, independent QA release, and configurable incompatible role/action combinations. | Same-user negative tests. |
| IAM-FR-015 | Dynamic SoD context | SoD evaluates record history, not only static role membership; e.g. user who performed step cannot verify same step. | History-aware decision. |
| IAM-FR-016 | Delegation of work | Tasks/approvals may be reassigned/delegated under controlled workflow, but electronic signature is never delegated. | New assignee signs self. |
| IAM-FR-017 | Temporary authorization | Time-limited authorization has reason, scope, start/end, approver and audit; auto-expires. | No permanent hidden elevation. |
| IAM-FR-018 | Break-glass access | Emergency access is explicitly invoked, MFA-protected, time-limited, reason-coded, heavily audited and independently reviewed. | Emergency use visible. |
| IAM-FR-019 | Privileged role separation | Application admin, Security admin, Identity admin, DB admin and infrastructure admin remain separate from product release authority. | Admin cannot release by privilege. |
| IAM-FR-020 | Vendor support access | Support access requires customer-approved/time-limited identity, scoped permissions and logging; no shared vendor root account. | Support access traceable. |
| IAM-FR-021 | Service accounts | Non-human identities have owner, purpose, scopes, credential/certificate lifecycle, rotation and no human signature capability. | Service identity inventory complete. |
| IAM-FR-022 | Device identities | Edge/instruments use registered non-human device identities/certificates separate from service/human users. | Machine evidence attributable. |
| IAM-FR-023 | Session controls | Configurable idle/absolute timeout, reauthentication rules and session revocation. Regulated signature still uses fresh step-up. | Stolen long session limited. |
| IAM-FR-024 | MFA | MFA required for privileged access and configured enterprise policies; signature authentication follows Document 04 assurance. | Privileged account cannot use password-only baseline. |
| IAM-FR-025 | Role assignment approval | High-risk role/entitlement assignment uses controlled approval and audit; assignment effective dates supported. | QA release role cannot self-assign. |
| IAM-FR-026 | Access review | Periodic report/review of active users, roles, sites, qualifications, service accounts and privileged access. | Review evidence exportable. |
| IAM-FR-027 | Joiner/mover/leaver | Identity changes synchronize through IdP/manual process while preserving immutable historical actor IDs. | Department change doesn't rewrite history. |
| IAM-FR-028 | Policy decision evidence | Authorization response contains allow/deny, policy version, evaluated subject/resource/action and reason codes. | Validation can prove why denied. |
| IAM-FR-029 | Least privilege defaults | New users/service accounts have no regulated privileges until explicitly assigned. | Default deny. |
| IAM-FR-030 | No client-side authority | Frappe permissions improve UX but GxP Policy Service independently enforces every authoritative regulated action. | API bypass fails. |
| IAM-FR-031 | Qualification override | Any permitted emergency qualification override requires dedicated policy, reason, authorized signer and quality-event/audit linkage. | No silent override. |
| IAM-FR-032 | Historical access | User/account deletion is avoided where history is required; deactivated identity remains referencable for old records/signatures. | Old actor resolves. |

# 5. SoD Reference Rules

Minimum configurable patterns:
- performer cannot verify same step;
- author cannot approve same master version;
- production performer cannot independently QA-release same batch where customer procedure requires independence;
- user cannot approve own temporary authorization;
- support/admin identities cannot perform product release;
- identity/security admins cannot issue signatures for users;
- CAPA action owner may be different from effectiveness approver;
- complaint investigator and final reportability approver may be separated by policy.

# 6. Qualification Model

```text
qualification_id
qualification_type
subject_id
scope_type / scope_id
issued_by
issued_at
effective_from
expires_at
status
evidence_refs
training_refs
suspension_reason
```

Execution checks qualification **at action time**, not only at login.

# 7. Keycloak-Compatible Boundary

Required claims/mappings:
- immutable subject (`sub`);
- issuer;
- tenant/customer mapping;
- identity assurance;
- authentication time;
- group/role claims where trusted;
- session ID.

Business/site roles remain product-controlled even if synchronized from directory groups.

# 8. Policy Service API

Example:

`POST /policy/v1/decisions`

```json
{
  "subject": {"id":"..."},
  "action":"batch.release",
  "resource":{"type":"Batch","id":"B-100","version":55},
  "context":{"site":"SITE-1"}
}
```

Response:
```json
{
  "decision":"DENY",
  "reason_codes":["UNRESOLVED_CRITICAL_DEVIATION","SOD_CONFLICT"],
  "policy_version":"2026.08.1"
}
```

# 9. Security

- default deny;
- privilege changes audited;
- privileged access MFA;
- service secrets/certs rotated;
- no shared generic accounts;
- no password storage in Frappe/GxP;
- access tokens short-lived where practical;
- sensitive identity attributes minimized.

# 10. Validation Tests

- user wrong site;
- wrong role;
- expired qualification;
- missing training;
- performer=verifier;
- author=approver;
- temporary role expiry;
- break-glass;
- disabled user;
- role removed during active session;
- service account human-signature attempt;
- device identity acting as user;
- admin release attempt;
- support access expiry;
- access review output;
- customer SSO mapping;
- IdP outage behavior.

# 11. Acceptance Gate

Freeze requires:
- action catalogue;
- reference role-to-action matrix;
- initial qualification catalogue;
- SoD matrix;
- Keycloak/Entra reference integration proof;
- alignment with Electronic Signature policies.

# 12. Developer / AI-Agent Rules

Never make Frappe role permission the sole GxP authorization.
Never trust a role claim without tenant/site mapping policy.
Never hard-code one customer's role names into domain logic.
Never permit shared Production/QA accounts.
Never treat an administrator as automatically authorized for manufacturing/QA actions.

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



# 13. Concrete Package Structure

```text
services/gxp-api/src/modules/iam/
├── identity-context.ts
├── policy.service.ts
├── qualification.service.ts
├── training-status.client.ts
├── sod.service.ts
├── role-mapping.service.ts
├── temporary-access.service.ts
├── break-glass.service.ts
└── access-review.service.ts

infrastructure/keycloak/
├── realms/
├── clients/
├── authentication-flows/
└── reference-mappings/
```

# 14. PostgreSQL Tables

## `iam_subject`

```text
subject_id uuid PK
tenant_id uuid NOT NULL
external_issuer varchar(500)
external_subject varchar(255)
display_name varchar(255)
email varchar(320)
subject_type varchar(40) NOT NULL
status varchar(40) NOT NULL
identity_verified boolean
signing_entitled boolean
created_at timestamptz
disabled_at timestamptz
```

Unique `(tenant_id, external_issuer, external_subject)`.

## `iam_role_assignment`

```text
assignment_id uuid PK
tenant_id uuid
subject_id uuid
role_code varchar(100)
scope_type varchar(40)
scope_id uuid
effective_from timestamptz
expires_at timestamptz
status varchar(40)
approved_by_reference uuid
```

## `iam_qualification`

Use fields already defined in Document 07 plus evidence/version metadata.

## `iam_temporary_authorization`
- subject;
- granted permissions;
- scope;
- reason;
- start/end;
- approving signature;
- review status.

# 15. Policy Model

Policy shall be explicit and testable.

Example rule object:

```json
{
  "policy_id":"POL-BATCH-RELEASE-001",
  "version":"1.2",
  "action":"batch.release",
  "required_roles":["QA_RELEASE"],
  "required_qualifications":["BATCH_RELEASE"],
  "sod":[
    {"type":"NOT_PRIOR_ACTOR","actions":["batch.execute"]}
  ],
  "site_scope_required":true
}
```

# 16. API Contract

- `POST /policy/v1/decisions`
- `GET /iam/v1/subjects/{id}/effective-authority`
- `GET /iam/v1/subjects/{id}/qualifications`
- `POST /iam/v1/temporary-authorizations`
- `POST /iam/v1/break-glass`
- `POST /iam/v1/access-reviews`
- `GET /iam/v1/access-reviews/{id}/report`

Policy decision endpoint is latency-sensitive and horizontally scalable.

# 17. Error / Denial Reason Codes

```text
SUBJECT_INACTIVE
ROLE_MISSING
SITE_SCOPE_DENIED
AREA_SCOPE_DENIED
PRODUCT_SCOPE_DENIED
QUALIFICATION_MISSING
QUALIFICATION_EXPIRED
TRAINING_INCOMPLETE
SIGNING_ENTITLEMENT_MISSING
SOD_CONFLICT
TEMP_AUTH_EXPIRED
BREAK_GLASS_REQUIRED
PRIVILEGED_ROLE_RESTRICTED
```

# 18. Frappe Mapping

Frappe roles may provide UI visibility only.
At runtime:
- Frappe user maps to immutable `iam_subject`;
- site/resource/action passed to policy service;
- server decision controls authoritative command.

Do not assume Frappe Administrator/System Manager implies GxP authority.

# 19. Keycloak Reference Configuration

Create separate clients:
- Frappe web client;
- GxP API;
- Signature Service;
- service integrations.

Use:
- PKCE for browser/public flows;
- client credentials/workload identity for services;
- dedicated step-up authentication flow for signature policy;
- MFA for privileged roles.

Exact realm JSON becomes infrastructure-as-code and version-controlled.

# 20. UI Screens

- User Directory Mapping
- Role Assignment
- Qualification Assignment
- Temporary Authorization
- Break-Glass Review
- Service Account Registry
- Device Identity Registry
- Access Review Dashboard

Every privileged assignment/action is audit-visible.

# 21. Access Review

Review output shall list:
- active users;
- roles;
- sites/scopes;
- signing entitlement;
- qualifications/expiry;
- temporary permissions;
- privileged roles;
- service/device identities;
- orphaned/inactive accounts.

Reviewer disposition:
`CONFIRM`, `REMOVE`, `CHANGE`, `INVESTIGATE`.

# 22. Observability

Metrics:
- policy allows/denies;
- deny reasons;
- expired qualifications;
- temporary access active;
- break-glass usage;
- privileged role assignments;
- IdP token validation failures;
- access review overdue.

# 23. Implementation Sequence

1. subject mapping;
2. JWT/OIDC validation;
3. role/scope tables;
4. policy evaluation framework;
5. qualifications;
6. training integration;
7. SoD history checks;
8. signature entitlement;
9. temporary auth;
10. break-glass;
11. access review;
12. Keycloak reference deployment.

