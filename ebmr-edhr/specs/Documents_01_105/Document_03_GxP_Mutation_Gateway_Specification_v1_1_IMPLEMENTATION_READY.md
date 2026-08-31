# US eBMR / eDHR Regulated Manufacturing Platform
## Document 03 — GxP Mutation Gateway — Detailed Functional & Technical Specification — v1.1

**Specification ID:** SPEC-GXP-001  
**Parent Documents:** Document 01 v1.1 (FROZEN) and Document 02 v1.0  
**Dependencies:** Documents 01–02; SPEC-GXP-002/003/004; SPEC-IAM-001; SPEC-GXP-006 Rules Engine  
**Status:** Proposed v1.1 — IMPLEMENTATION-READY BASELINE / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products  
**Future Profiles:** Medical Devices and Pharmaceuticals  
**Date:** 2026-08-20

---

# 1. Objective

Define the sole controlled technical pathway through which authoritative regulated state may be created or changed.

The Mutation Gateway is the enforcement point that makes the architecture materially different from an ordinary Frappe application. It prevents UI, generic REST CRUD, background workers, integrations and privileged application code from silently changing GxP truth without authorization, version control, audit evidence and required signatures.

# 2. Scope

Included:
- human commands;
- service/integration commands;
- device/equipment-originated accepted evidence commands;
- domain validation;
- authorization;
- optimistic concurrency;
- reason-for-change;
- signature gating;
- authoritative transaction;
- audit;
- outbox;
- idempotency;
- mutation receipts;
- failure/recovery behavior.

Excluded:
- detailed electronic-signature mechanics → Document 04;
- audit storage/review internals → Document 05;
- record-vault internals → Document 06;
- IAM/SoD policy details → Document 07;
- rule-authoring/calculation details → Document 08.

# 3. Architecture

```text
Frappe UI / API / ERP / LIMS / Edge
                │
                ▼
        GxP Mutation Gateway
                │
     ┌──────────┼───────────┐
     │          │           │
     ▼          ▼           ▼
 Identity    Policy      Rules
 Context     Service     Engine
                │
          Signature?
                │
                ▼
       PostgreSQL Transaction
       ├── Domain State
       ├── Record Version
       ├── Audit Event
       └── Outbox Event
                │
              COMMIT
                │
        ┌───────┴────────┐
        ▼                ▼
 Mutation Receipt    Async Publisher
                         │
                  Frappe/ERP/LIMS/etc.
```

# 4. Command Lifecycle

```text
RECEIVED
  ↓
AUTHENTICATED
  ↓
SCHEMA_VALIDATED
  ↓
CONTEXT_RESOLVED
  ↓
AUTHORIZED
  ↓
STATE_VERSION_VALIDATED
  ↓
RULES_EVALUATED
  ↓
SIGNATURE_PENDING (only when required)
  ↓
SIGNATURE_VERIFIED
  ↓
COMMITTING
  ↓
COMMITTED
  ↓
PUBLISHED / PROJECTION_PENDING
```

Terminal negative states:
`REJECTED_VALIDATION`, `REJECTED_AUTHORIZATION`, `REJECTED_STALE`, `REJECTED_RULE`, `REJECTED_SIGNATURE`, `FAILED_SYSTEM`.

# 5. Detailed Functional Requirements

| ID | Requirement | Detailed behavior / sub-functionalities | Acceptance intent |
|---|---|---|---|
| MUT-FR-001 | Single regulated mutation entry point | Every regulated create, modify, correct, approve, verify, release, reject, hold, resume, disposition, quality-state change and integration write shall enter through the GxP Mutation Gateway. Frappe generic CRUD, direct DB writes, background scripts and adapters shall not create authoritative GxP state. | Architectural tests prove no supported bypass path. |
| MUT-FR-002 | Authenticated actor context | Resolve human, service, integration or device identity from trusted server-side authentication context. Ignore client-supplied actor IDs/names for authority decisions. | Spoofed actor fields do not change attribution. |
| MUT-FR-003 | Tenant/site scope enforcement | Resolve customer, legal entity, site and resource scope before business validation. Requests crossing tenant/site boundaries fail closed. | Cross-site negative tests enforced. |
| MUT-FR-004 | Command classification | Each mutation uses a versioned command type such as CompleteBatchStep, CorrectResult, ApproveDeviation, ReleaseBatch, UpdateMaterialStatus or AcceptLIMSResult. | Unknown/unversioned commands rejected. |
| MUT-FR-005 | Schema validation | Validate command envelope and payload against versioned JSON Schema/OpenAPI contract before domain processing. | Malformed/additional prohibited fields rejected. |
| MUT-FR-006 | Authorization decision | Call Policy/Authorization Service using subject, role, site, qualifications, resource state, requested action and SoD context. | Every regulated command has explicit allow/deny evidence. |
| MUT-FR-007 | Qualification/training gate | Where configured, confirm required current training, equipment qualification, area qualification or task competency before allowing action. | Expired qualification blocks action. |
| MUT-FR-008 | State-transition validation | Validate requested command against authoritative current state and allowed transition table; UI state is never authoritative. | Illegal transitions fail deterministically. |
| MUT-FR-009 | Expected-version concurrency | Require expected aggregate/record version for mutations. Reject stale commands using optimistic concurrency. | Two simultaneous conflicting writes cannot silently overwrite. |
| MUT-FR-010 | Idempotency | Require idempotency key for commands capable of duplicate submission. Persist key, actor/source, command hash and resulting receipt. | Retries return same result without duplicate regulated event. |
| MUT-FR-011 | Reason-for-change enforcement | Rules identify commands requiring controlled reason/comment. Reason is structured, required before commit and preserved in audit. | Correction/override cannot proceed without required reason. |
| MUT-FR-012 | Signature requirement determination | Determine whether electronic signature is required, signature meaning, required signer class and whether one or multiple signatures are required. | Signature need cannot be bypassed by client. |
| MUT-FR-013 | Signature challenge integration | If signature is required, produce/consume a challenge bound to command, record ID, expected version/hash, meaning and expiry. Commit only after valid signature proof. | Expired/stale challenge prevents commit. |
| MUT-FR-014 | Domain-rule evaluation | Execute applicable released rule/calculation versions for materials, equipment, limits, eligibility, sequence, QMS and release controls. | Rule result and version are persisted. |
| MUT-FR-015 | Authoritative PostgreSQL transaction | Persist domain state, new version, audit event and outbox message in one PostgreSQL transaction. | No state can commit without its audit/outbox companion. |
| MUT-FR-016 | Audit event creation | Create audit record with actor, UTC time, source, action, old/new representation or references, reason, signature, correlation and rule/software versions. | Each committed mutation has auditable event. |
| MUT-FR-017 | Record hash | Canonicalize resulting regulated record/version and calculate cryptographic digest where the record class requires integrity binding. | Receipt exposes algorithm + digest. |
| MUT-FR-018 | Transactional outbox | Write integration/domain event into outbox in the same transaction; external bus publishing occurs only after commit. | Bus outage cannot lose committed event. |
| MUT-FR-019 | Mutation receipt | Return immutable identifiers: command ID, aggregate ID, resulting version, audit event ID, signature ID if applicable, correlation ID and record hash where applicable. | Caller can reconcile exact outcome. |
| MUT-FR-020 | Projection update isolation | Frappe projection/read model updates occur asynchronously after authoritative commit and may be retried without altering regulatory truth. | Projection failure does not roll back valid GxP commit. |
| MUT-FR-021 | Failure classification | Return stable machine-readable error codes for authentication, authorization, stale version, state violation, missing signature, rule failure, validation, dependency unavailable and system fault. | Clients do not depend on free-text errors. |
| MUT-FR-022 | Fail closed for compliance dependencies | If authoritative DB, Signature Service for required signings, Policy Service or integrity-critical component is unavailable, mutation does not succeed. | No degraded-mode bypass. |
| MUT-FR-023 | Integration identity | ERP/LIMS/Edge commands use non-human identities with narrowly scoped permissions and source-system IDs. | Integration cannot impersonate a human signer. |
| MUT-FR-024 | Device/input source validation | For machine-originated mutations/evidence, verify registered source/device identity and mapping before acceptance. | Unknown device source rejected/quarantined. |
| MUT-FR-025 | Late/replayed command control | Detect timestamp/sequence anomalies and duplicate/replayed integration/device commands using source event IDs, sequences and idempotency. | Replay cannot duplicate consumption/result. |
| MUT-FR-026 | Controlled administrative mutation | Exceptional admin/data-repair actions require dedicated privileged command types, incident/change/deviation reference, stronger authorization and independent review. | No generic DBA correction process. |
| MUT-FR-027 | Correlation/causation | Every command and generated event carries request, correlation and causation identifiers across services and adapters. | End-to-end trace reconstruction possible. |
| MUT-FR-028 | Command retention | Retain sufficient command/receipt metadata for investigation, duplicate detection and validation evidence according to record class. | Historic mutation can be reconstructed. |
| MUT-FR-029 | No arbitrary execution | Command handlers shall call validated domain services; customer-provided Python/JavaScript is prohibited in authoritative mutation execution. | Code injection path absent. |
| MUT-FR-030 | Schema/version compatibility | Command handlers explicitly support/deprecate schema versions; semantic changes require new version and migration/compatibility assessment. | Existing validated clients do not silently change behavior. |
| MUT-FR-031 | Security-event interface | Repeated denied, replayed, malformed, privilege-escalation or suspicious mutations generate security monitoring events separate from GxP audit where appropriate. | Security monitoring receives actionable events. |
| MUT-FR-032 | Inspection/reconciliation support | Provide query by command ID/correlation ID/record to trace command → decision → signature → version → audit → outbox. | QA/validation can prove transaction chain. |

# 6. Canonical Command Envelope

```json
{
  "command_id": "uuid",
  "command_type": "CompleteBatchStep",
  "schema_version": "1.0",
  "tenant_id": "TEN-001",
  "site_id": "SITE-001",
  "aggregate_type": "Batch",
  "aggregate_id": "BATCH-000123",
  "expected_version": 44,
  "idempotency_key": "uuid-or-source-key",
  "requested_at": "2026-08-20T10:00:00Z",
  "payload": {},
  "reason": null
}
```

`tenant_id`, `site_id` and resource IDs are assertions that must be cross-checked against authenticated context. Actor identity is never accepted from the payload.

# 7. Core Data Objects

## 7.1 CommandReceipt
- command_id
- command_type
- aggregate_id
- previous_version
- resulting_version
- decision
- audit_event_id
- signature_id(s)
- record_hash
- correlation_id
- committed_at_utc
- projection_status

## 7.2 IdempotencyRecord
- tenant/site/source
- idempotency_key
- command_hash
- first_seen_at
- resulting_command_id
- resulting_version
- status

## 7.3 OutboxEvent
- event_id
- topic/type
- schema_version
- aggregate/version
- payload/reference
- publish_attempts
- published_at
- next_retry_at

# 8. API Surface

Minimum:
- `POST /gxp/v1/commands/{commandType}`
- `GET /gxp/v1/commands/{commandId}/receipt`
- `GET /gxp/v1/records/{type}/{id}/mutation-history`
- internal signature-challenge callbacks
- internal outbox health/replay controls

No generic `PATCH /regulated-record/{id}` is permitted.

# 9. Transaction & Concurrency Rules

1. Domain state + version + audit + outbox commit atomically in PostgreSQL.
2. Never use distributed 2PC across MariaDB/PostgreSQL/ERP/LIMS.
3. Use expected-version checks for user commands.
4. Use unique constraints/idempotency for external commands.
5. For scarce resources such as material reservations, add row/advisory locks where optimistic concurrency alone is insufficient.
6. Do not hold DB transactions while waiting for human signature challenge.

# 10. Frappe Integration

Frappe:
- collects UI input;
- calls command endpoint;
- displays returned receipt/error;
- refreshes projection.

Frappe shall not:
- execute a parallel authoritative write;
- mark a batch released because its local Workflow changed;
- invent signer identity;
- bypass stale-version errors.

# 11. Security

- service endpoint private/internal where possible;
- OAuth2/OIDC workload identity;
- mTLS for sensitive integration paths;
- strict scopes per command family;
- rate limiting;
- structured input validation;
- no secrets or raw credentials in command payloads/logs;
- PII/sensitive values redacted from operational logs without weakening GxP audit.

# 12. Failure & Recovery

| Failure | Required behavior |
|---|---|
| PostgreSQL unavailable | No regulated mutation succeeds |
| Policy unavailable | Fail closed |
| Signature unavailable and signature required | Command remains uncommitted |
| Event bus unavailable | Authoritative commit succeeds if outbox commit succeeds; publish later |
| Frappe projection failure | Retry projection; GxP record remains valid |
| ERP callback failure | Mark integration pending and reconcile |
| Duplicate request | Return existing receipt |
| Stale version | Reject with current version reference |
| Worker crash after DB commit | Receipt recoverable; outbox continues |

# 13. Audit Requirements

Each mutation must be traceable to:
`Command → Actor → Authorization Decision → Rules → Signature(s) → Record Version → Audit Event → Outbox/Integration Effects`.

# 14. Validation / Test Catalogue

Minimum validation scenarios:
- unauthorized user;
- wrong site;
- expired qualification;
- invalid state transition;
- stale version;
- duplicate click/retry;
- duplicate ERP/LIMS callback;
- missing reason;
- missing required signature;
- record changed after signature challenge;
- signature service outage;
- DB rollback;
- outbox publisher outage;
- projection outage;
- concurrency on same batch step;
- concurrency on same material reservation;
- replayed Edge event;
- privileged repair command;
- command schema backward compatibility;
- restart recovery after commit.

# 15. Acceptance Gate

This specification is build-ready only when:
- Document 04–08 interfaces are reconciled;
- command families for initial V1 modules are catalogued;
- DB transaction proof-of-concept passes failure injection;
- direct Frappe CRUD bypass tests fail as expected;
- threat-model review covers Gateway trust boundary.

# 16. Developer / AI-Agent Rules

Never create an authoritative write outside the Gateway.
Never weaken authorization/signature checks to make a UI flow easier.
Never retry a non-idempotent integration mutation without an idempotency design.
Never accept actor identity, role, timestamp or signature proof solely from browser payload.

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



# 17. Concrete Service / Package Structure

Recommended service layout:

```text
services/gxp-api/
├── src/
│   ├── app.ts
│   ├── modules/
│   │   └── mutation/
│   │       ├── mutation.controller.ts
│   │       ├── mutation.service.ts
│   │       ├── command-registry.ts
│   │       ├── command-context.ts
│   │       ├── idempotency.service.ts
│   │       ├── concurrency.service.ts
│   │       ├── transaction.service.ts
│   │       ├── receipt.service.ts
│   │       ├── errors.ts
│   │       └── handlers/
│   ├── clients/
│   │   ├── policy.client.ts
│   │   ├── signature.client.ts
│   │   └── rules.client.ts
│   └── db/
│       ├── repositories/
│       └── migrations/
├── test/
└── openapi/
```

A command handler shall contain domain orchestration only. It shall not parse authentication tokens, access Frappe DB, publish directly to event bus before DB commit, or perform unrestricted SQL.

# 18. PostgreSQL Tables

## 18.1 `gxp_command_receipt`

Suggested fields:

```text
command_id uuid PK
tenant_id uuid NOT NULL
site_id uuid NOT NULL
command_type varchar(120) NOT NULL
schema_version varchar(20) NOT NULL
aggregate_type varchar(80) NOT NULL
aggregate_id uuid NOT NULL
expected_version bigint
resulting_version bigint
idempotency_key varchar(200)
request_hash char(64)
status varchar(40) NOT NULL
audit_event_id uuid
correlation_id uuid NOT NULL
causation_id uuid
record_hash char(64)
error_code varchar(80)
created_at timestamptz NOT NULL
committed_at timestamptz
```

Indexes:
- unique `(tenant_id, command_id)`;
- unique partial `(tenant_id, idempotency_key)` when key not null;
- `(tenant_id, aggregate_type, aggregate_id, created_at desc)`;
- `(correlation_id)`.

## 18.2 `gxp_outbox`

```text
event_id uuid PK
tenant_id uuid NOT NULL
topic varchar(160) NOT NULL
event_type varchar(160) NOT NULL
schema_version varchar(20) NOT NULL
aggregate_type varchar(80)
aggregate_id uuid
aggregate_version bigint
payload jsonb NOT NULL
correlation_id uuid
causation_id uuid
created_at timestamptz NOT NULL
published_at timestamptz
attempt_count int NOT NULL default 0
next_attempt_at timestamptz
last_error text
```

Indexes:
- `(published_at, next_attempt_at)`;
- `(tenant_id, aggregate_id, created_at)`.

## 18.3 Aggregate version invariant

Every regulated aggregate table must include:

```text
id uuid PK
tenant_id uuid NOT NULL
site_id uuid NOT NULL
version bigint NOT NULL
...
```

Mutation SQL update must include expected version in WHERE clause.

Example:

```sql
UPDATE gxp_batch
SET state = $1, version = version + 1, updated_at = now()
WHERE id = $2 AND tenant_id = $3 AND version = $4;
```

Affected-row count `0` means stale version or missing record and shall not be treated as success.

# 19. API Contract

## 19.1 Submit command

`POST /gxp/v1/commands/{command_type}`

Headers:
- `Authorization: Bearer ...`
- `Idempotency-Key`
- `X-Request-ID`
- optional `If-Match` mapped to expected version

Response 200/201:

```json
{
  "command_id":"...",
  "status":"COMMITTED",
  "aggregate":{
    "type":"Batch",
    "id":"...",
    "version":45
  },
  "audit_event_id":"...",
  "signature_ids":[],
  "record_hash":"...",
  "correlation_id":"...",
  "committed_at_utc":"..."
}
```

## 19.2 Stable Error Codes

Minimum registry:

```text
AUTHENTICATION_REQUIRED
TOKEN_INVALID
TENANT_SCOPE_DENIED
SITE_SCOPE_DENIED
ACTION_NOT_AUTHORIZED
QUALIFICATION_REQUIRED
SOD_CONFLICT
SCHEMA_INVALID
COMMAND_UNKNOWN
STATE_TRANSITION_INVALID
EXPECTED_VERSION_REQUIRED
STALE_VERSION
IDEMPOTENCY_CONFLICT
REASON_REQUIRED
SIGNATURE_REQUIRED
SIGNATURE_INVALID
SIGNATURE_STALE
RULE_FAILED
RESOURCE_INELIGIBLE
DEPENDENCY_UNAVAILABLE
SOURCE_NOT_REGISTERED
REPLAY_DETECTED
SYSTEM_ERROR
```

HTTP status maps are documented in OpenAPI and remain stable.

# 20. Command Handler Template

Pseudocode:

```text
authenticate()
resolve_actor()
validate_schema()
resolve_tenant_site()
load_aggregate()
verify_expected_version()
authorize()
verify_qualification_and_sod()
validate_reason()
evaluate_rules()

if signature_required:
    verify_consumable_signature_proof()

begin tx
    lock/compare aggregate version
    apply domain mutation
    persist new state/version
    persist audit event
    persist command receipt
    persist outbox event
commit

return receipt
```

No network call shall occur inside the final DB transaction unless explicitly proven safe and bounded. Signature/Policy/Rules decisions should be completed before transaction, then revalidated against version/state at commit.

# 21. Event Contracts

Minimum mutation event envelope:

```json
{
  "event_id":"uuid",
  "event_type":"BatchStepCompleted",
  "schema_version":"1.0",
  "tenant_id":"uuid",
  "site_id":"uuid",
  "aggregate_type":"Batch",
  "aggregate_id":"uuid",
  "aggregate_version":45,
  "occurred_at_utc":"...",
  "correlation_id":"uuid",
  "causation_id":"uuid",
  "payload":{}
}
```

Events are immutable facts. Consumers may build projections but shall not reinterpret the authoritative state transition.

# 22. Frappe Implementation Contract

Recommended Frappe client pattern:

```text
Form/Execution UI
  ↓
custom app server endpoint
  ↓ obtains authenticated user/session context
GxP API client
  ↓
Mutation Gateway
```

The custom Frappe app shall not call `frappe.db.set_value()` for authoritative regulated data.

# 23. Observability

Metrics:
- commands received/committed/rejected;
- rejection reason counts;
- stale-version count;
- idempotent-replay count;
- transaction latency;
- policy/signature/rule dependency latency;
- outbox pending count/age;
- projection lag.

Health endpoints:
- liveness;
- readiness;
- PostgreSQL;
- policy client;
- signature client;
- rules client;
- outbox publisher.

# 24. Implementation Sequence

1. command envelope + error registry;
2. auth/context middleware;
3. PostgreSQL command receipt;
4. optimistic concurrency utility;
5. idempotency store;
6. policy client;
7. rules client;
8. signature proof interface;
9. transaction template;
10. audit repository integration;
11. outbox;
12. first command: noncritical test aggregate;
13. first regulated command: released-master publish;
14. batch-step command;
15. integration command;
16. failure-injection test suite.

# 25. Traceability Template

Each command implementation shall register:

```text
command_type
requirement_ids[]
policy_ids[]
rule_ids[]
audit_event_types[]
signature_policy_id
API operationId
test_ids[]
```

