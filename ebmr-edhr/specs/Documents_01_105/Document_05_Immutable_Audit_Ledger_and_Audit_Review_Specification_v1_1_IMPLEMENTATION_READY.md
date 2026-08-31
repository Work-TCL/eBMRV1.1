# US eBMR / eDHR Regulated Manufacturing Platform
## Document 05 — Immutable Audit Ledger & Audit Review — Detailed Functional & Technical Specification — v1.1

**Specification ID:** SPEC-GXP-003  
**Parent Documents:** Document 01 v1.1 (FROZEN) and Document 02 v1.0  
**Dependencies:** Documents 01–04; Document 06 Vault; Document 07 IAM; Security/Infrastructure specifications  
**Status:** Proposed v1.1 — IMPLEMENTATION-READY BASELINE / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products  
**Future Profiles:** Medical Devices and Pharmaceuticals  
**Date:** 2026-08-20

---

# 1. Objective

Define the independent GxP audit system that records who did what, when, to which regulated record, from which source, under which rule/signature context, while preserving previous information and supporting long-term review.

# 2. Architecture

```text
Mutation Gateway
      │ same DB transaction
      ▼
Audit Event Insert
      │
      ├── Append-only PostgreSQL partition
      ├── Per-record event hash chain
      └── Outbox / audit index projection
                       │
                       ▼
             Integrity Checkpoint Job
                       │
             Signed Integrity Manifest
                       │
            Immutable-capable Storage
```

Frappe Version, application logs, Temporal workflow history and SIEM remain supplemental.

# 3. Event Families

- master/version lifecycle;
- batch/step execution;
- material/inventory regulated status;
- QC result;
- QMS event;
- equipment/qualification;
- signature;
- release/disposition;
- integration acceptance/rejection;
- controlled correction/amendment;
- migration/import;
- privileged repair.

# 4. Detailed Requirements

| ID | Requirement | Detailed behavior / sub-functionalities | Acceptance intent |
|---|---|---|---|
| AUD-FR-001 | Independent audit ledger | GxP audit is a dedicated authoritative ledger separate from Frappe Version, application logs, Temporal history and SIEM logs. | Removing Frappe history does not remove GxP audit. |
| AUD-FR-002 | Automatic generation | Committed regulated mutations automatically generate audit events; users cannot choose whether an applicable event is audited. | No optional audit checkbox. |
| AUD-FR-003 | UTC timestamp | Each event receives authoritative server UTC time plus source/device timestamp metadata where relevant. | Browser clock irrelevant. |
| AUD-FR-004 | Actor attribution | Record human/service/device actor type, immutable subject/source ID and display/context metadata. | API/service actions distinguishable from humans. |
| AUD-FR-005 | Action semantics | Use stable event types: Created, Changed, Corrected, Signed, Approved, Released, StatusChanged, Consumed, Returned, IntegrationAccepted, etc. | Audit is understandable, not generic 'update'. |
| AUD-FR-006 | Old/new preservation | For changed regulated data preserve old and new values or immutable version references sufficient to reconstruct the change. | Previous information never obscured. |
| AUD-FR-007 | Changed field set | Record normalized changed fields for review/search without relying only on full JSON diff. | QA can filter changed critical parameters. |
| AUD-FR-008 | Reason linkage | Store mandatory reason/comment for controlled correction, override, manual replacement, admin repair and other policy-defined changes. | Reason retrievable with event. |
| AUD-FR-009 | Signature linkage | Audit event references signature ID(s) and meaning where action is signed. | Audit and signature reconcile. |
| AUD-FR-010 | Record/version linkage | Every event references aggregate/record and resulting version; where applicable record digest. | History order deterministic. |
| AUD-FR-011 | Correlation/causation | Persist request/correlation/causation IDs to connect UI command, background activity and integration side effects. | Investigation trace end-to-end. |
| AUD-FR-012 | Source attribution | Identify Frappe UI, REST API, ERP, LIMS, Edge, background system, migration or privileged repair source. | Source reports possible. |
| AUD-FR-013 | Software/rule version | Record product release and critical rule/calculation version used for action where relevant. | Historical decision reproducible. |
| AUD-FR-014 | Append-only application permissions | Application DB role may INSERT audit events and SELECT authorized records; no UPDATE/DELETE privilege for audit tables. | Privilege test enforced. |
| AUD-FR-015 | Partitioning without semantic loss | Time/tenant partitioning permitted for scale, but event IDs/order, retention and search remain consistent. | Partition maintenance cannot erase retained events. |
| AUD-FR-016 | Per-record hash chain | Regulated aggregate event streams include previous event hash/current event hash using canonical event representation. | Tampering detectable. |
| AUD-FR-017 | Integrity checkpoints | Periodically create signed integrity manifest/Merkle-style root or equivalent over audit ranges and store in immutable-capable storage. | Independent verification possible. |
| AUD-FR-018 | Integrity verification job | Scheduled process verifies chain/checkpoint consistency and alarms on mismatch/missing ranges. | Tamper issue not silent. |
| AUD-FR-019 | Privileged DB monitoring | DBA/cloud-admin access and extraordinary actions are monitored through independent infrastructure/security logs and controlled procedures. | DBA is not invisible. |
| AUD-FR-020 | Audit review UI | Authorized QA/auditor can filter by record, batch, user, event type, field, time, site, signature, source and reason. | Review does not require SQL. |
| AUD-FR-021 | Audit review annotations | If customer procedure requires documented audit-trail review, create separate review record/signature without changing the underlying audit events. | Audit event remains immutable. |
| AUD-FR-022 | Export | Generate human-readable and structured audit export tied to exact record/export manifest and integrity checks. | Inspection-ready. |
| AUD-FR-023 | Retention | Audit retained at least as long as associated regulated record policy; archival retains search/retrieval and integrity evidence. | No premature purge. |
| AUD-FR-024 | Legal/quality hold | Retention engine can suspend disposal/archive transitions for held records/events. | Held audit preserved. |
| AUD-FR-025 | Sensitive-data handling | Operational logs may redact sensitive values, but authorized GxP audit/evidence must preserve required content/meaning. Secrets must never be captured. | No credential leakage. |
| AUD-FR-026 | Migration audit | Migrated records include provenance/migration events and source checksums without pretending migrated events occurred natively. | Migration distinguishable. |
| AUD-FR-027 | Failed-action security trail | Policy-denied/replay/attack events may be sent to security ledger/SIEM; only failed actions with GxP significance need GxP audit according to risk/policy. | Avoid misleading committed-record audit. |
| AUD-FR-028 | Time ordering | Persist per-aggregate monotonic version/sequence and database commit order metadata where needed; source timestamp does not control authoritative order. | Late device data handled explicitly. |
| AUD-FR-029 | Backup/restore integrity | Restore procedure verifies audit record counts, hash checkpoints, references and signature linkage. | Restore qualification includes integrity. |
| AUD-FR-030 | No ordinary purge UI | Application users and admins cannot delete audit events via normal UI/API. Retention disposal, if ever permitted, is a separately controlled archival process based on applicable policy. | Deletion path controlled and testable. |

# 5. Audit Event Schema

```text
event_id UUID
schema_version
tenant_id
site_id
aggregate_type
aggregate_id
aggregate_version
event_type
actor_type
actor_subject_id
actor_display_name
role_context
source_type
source_id
occurred_at_utc
source_timestamp
request_id
correlation_id
causation_id
changed_fields[]
old_value / old_version_ref
new_value / new_version_ref
reason_code
reason_text
signature_ids[]
rule_versions[]
application_version
previous_record_event_hash
event_hash
db_commit_sequence / partition metadata
```

# 6. Canonical Event Hash

Hash input shall exclude mutable storage metadata but include all semantically relevant audit fields.

The hashing/canonicalization library must:
- have a version;
- use deterministic serialization;
- normalize timestamps;
- normalize decimal representation;
- define null/absent semantics;
- have golden test vectors.

# 7. Audit Review

## Views
- Record History
- Batch Audit
- Changed Critical Values
- Electronic Signatures
- User Activity
- Manual Overrides
- Corrections
- Integration/Device Sources
- Release Audit
- Integrity Health

Audit review is read-only. Review conclusions are separate records.

# 8. Database Security

Recommended roles:
- `gxp_mutation_writer`: INSERT audit through stored/domain path; no UPDATE/DELETE;
- `gxp_audit_reader`: SELECT authorized;
- `gxp_integrity_worker`: read + write checkpoint metadata only;
- migration/admin roles restricted and not used by runtime.

Use DB/network/IAM monitoring to detect privileged actions outside application controls.

# 9. Retention & Archive

Retention policy is configurable by record class/profile/customer and must trace to applicable predicate rules/customer policy.

Archive must preserve:
- content and meaning;
- signature linkage;
- hash/checkpoint evidence;
- retrieval;
- human-readable export.

# 10. Failure Behavior

If audit insert in the authoritative transaction fails, regulated mutation fails.
If integrity-checkpoint generation fails after prior audit events were committed, events remain valid but health alert is raised and checkpoint retried.
If audit read projection fails, authoritative ledger remains available through controlled fallback query.

# 11. Validation Tests

- create/change/delete-like correction events;
- previous value preservation;
- reason;
- signature link;
- human vs integration identity;
- event ordering;
- late source timestamp;
- attempted application UPDATE;
- attempted application DELETE;
- per-record hash tamper;
- missing event tamper;
- checkpoint verification;
- partition rollover;
- backup/restore;
- archive/retrieve;
- audit export;
- role-restricted review;
- privileged DB access monitoring;
- migration provenance;
- performance at target volume.

# 12. Performance

Design for millions of events/day without architecture redesign:
- PostgreSQL partitioning;
- indexes on tenant/site/aggregate/time/event_type/actor;
- large old/new payloads may reference immutable record versions rather than duplicate huge JSON;
- exports run asynchronously.

# 13. Developer / AI-Agent Rules

Never use Frappe Version as the GxP audit source.
Never UPDATE or DELETE an audit event.
Never suppress audit because a change came from an API/background worker.
Never store passwords/tokens/secrets in audit.
Never make hash-chain verification a cosmetic UI function; it must be independently testable.

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



# 14. Concrete Package Structure

```text
services/audit/
├── src/
│   ├── audit-writer.ts
│   ├── audit-query.service.ts
│   ├── canonical-event.ts
│   ├── hash-chain.ts
│   ├── checkpoint.service.ts
│   ├── integrity-verifier.ts
│   ├── export.service.ts
│   └── retention/
├── migrations/
├── test-vectors/
└── test/
```

Audit insertion used by Mutation Gateway should preferably be a shared repository/package in the same authoritative PostgreSQL transaction, not a remote HTTP call that can fail after domain write.

# 15. PostgreSQL Schema

Partitioned table example:

```text
gxp_audit_event
event_id uuid
tenant_id uuid
site_id uuid
aggregate_type varchar(80)
aggregate_id uuid
aggregate_version bigint
aggregate_sequence bigint
event_type varchar(120)
actor_type varchar(40)
actor_subject_id varchar(255)
actor_display_name varchar(255)
role_context jsonb
source_type varchar(50)
source_id varchar(255)
occurred_at timestamptz
source_timestamp timestamptz
request_id uuid
correlation_id uuid
causation_id uuid
changed_fields jsonb
old_value jsonb
new_value jsonb
reason_code varchar(80)
reason_text text
signature_ids jsonb
rule_versions jsonb
application_version varchar(40)
previous_event_hash char(64)
event_hash char(64)
created_at timestamptz
PRIMARY KEY (event_id, occurred_at)
```

Recommended partition:
- monthly by `occurred_at`;
- optionally subpartition or indexed by tenant.

Critical indexes:
- `(tenant_id, aggregate_type, aggregate_id, aggregate_sequence)`;
- `(tenant_id, occurred_at desc)`;
- `(tenant_id, actor_subject_id, occurred_at desc)`;
- `(tenant_id, event_type, occurred_at desc)`;
- GIN on `changed_fields` only if justified by query tests.

Unique invariant:
`(tenant_id, aggregate_type, aggregate_id, aggregate_sequence)` unique.

# 16. Database Privileges

Runtime mutation role:
- INSERT audit;
- SELECT minimal verification;
- NO UPDATE;
- NO DELETE.

Audit query role:
- SELECT only.

Checkpoint role:
- SELECT audit;
- INSERT checkpoint metadata;
- NO audit UPDATE/DELETE.

Migrations run via separate controlled deployment identity.

# 17. Checkpoint Tables

`gxp_audit_checkpoint`

```text
checkpoint_id uuid PK
tenant_id uuid
range_start timestamptz
range_end timestamptz
event_count bigint
root_hash char(64)
algorithm varchar(40)
signing_key_id varchar(255)
signature_value/reference
manifest_evidence_id uuid
created_at timestamptz
verification_status varchar(40)
```

# 18. Audit Query API

- `GET /audit/v1/records/{type}/{id}`
- `GET /audit/v1/batches/{id}`
- `GET /audit/v1/users/{subjectId}`
- `GET /audit/v1/search?...`
- `POST /audit/v1/exports`

Pagination must be cursor-based for large histories.

# 19. Audit Review UI

Screens:
1. Record Audit Timeline
2. Changed Values
3. Signature Timeline
4. Manual Overrides/Corrections
5. Integration/Device Events
6. Integrity Health
7. Audit Review Record

Each event drawer displays:
- actor/source;
- authoritative time;
- action;
- old/new;
- reason;
- linked signature;
- linked record version;
- correlation chain.

# 20. Hash Chain Algorithm

For each aggregate:
```text
event_hash = SHA256(
  canonical_event_without_hash_fields
  + previous_event_hash
)
```

Genesis event uses a defined constant/null representation.

Golden test vectors are stored in repository. Canonicalization version is part of schema governance.

# 21. Integrity Verification

Scheduled verifier:
- checks event sequence continuity;
- recomputes event hashes;
- compares checkpoint ranges;
- validates signed manifest reference;
- emits health metric;
- raises security/quality incident on mismatch.

Verifier shall not “repair” mismatches automatically.

# 22. Export Format

Structured export:
```text
audit.json
audit.csv (optional)
manifest.json
integrity-check.txt/json
```

Human-readable PDF audit may be generated, but structured data remains primary export evidence.

# 23. Observability

Metrics:
- audit inserts/sec;
- insert failures;
- checkpoint age;
- checkpoint failures;
- integrity mismatches;
- query latency;
- export queue;
- partition size;
- retention/archive backlog.

# 24. Implementation Sequence

1. event schema;
2. partitioned table;
3. insert repository;
4. old/new diff normalizer;
5. aggregate sequence;
6. canonical hash;
7. query API;
8. review UI;
9. checkpoint manifest;
10. integrity verifier;
11. export;
12. retention/archive;
13. privileged-access monitoring integration.

# 25. Performance Test

Synthetic benchmark shall test:
- single-record histories with thousands of events;
- tenant with millions/day;
- batch audit query;
- user/time-range query;
- changed-field query;
- archive export;
- checkpoint generation.

