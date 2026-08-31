# US eBMR / eDHR Regulated Manufacturing Platform
## Document 06 — Record Version Vault, Locking, Amendment & Controlled Correction — Specification — v1.1

**Specification ID:** SPEC-GXP-004  
**Parent Documents:** Document 01 v1.1 (FROZEN) and Document 02 v1.0  
**Dependencies:** Documents 01–05; Recipe/Batch specifications; Evidence/Object Storage specification  
**Status:** Proposed v1.1 — IMPLEMENTATION-READY BASELINE / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products  
**Future Profiles:** Medical Devices and Pharmaceuticals  
**Date:** 2026-08-20

---

# 1. Objective

Define how regulated information becomes immutable, versioned, historically reproducible and safely correctable without obscuring the original record.

# 2. Core Principle

```text
AUTHORING OBJECT (mutable draft)
          ↓ approval/release
CANONICAL RELEASE SNAPSHOT
          ↓
IMMUTABLE VAULT VERSION
          ↓
Referenced by Batch / Signature / Audit / Export
```

A future edit creates another controlled version; it never mutates the released version.

# 3. Vault Object Classes

- product/constituent configuration;
- master recipe/manufacturing record;
- material/component specification;
- packaging/label specification;
- QC/test specification;
- equipment/process specification;
- controlled document snapshot;
- batch issue snapshot;
- completed batch/eDHR record;
- correction/amendment;
- final release/disposition package;
- regulatory export/evidence manifest.

# 4. Detailed Requirements

| ID | Requirement | Detailed behavior / sub-functionalities | Acceptance intent |
|---|---|---|---|
| VLT-FR-001 | Immutable released version | Every released master, specification, controlled document snapshot and regulated final record receives immutable vault version ID. | Released content cannot be edited in place. |
| VLT-FR-002 | Canonical snapshot | Vault stores canonical structured representation sufficient to reproduce content/meaning independent of mutable Frappe master. | Changing Frappe draft does not change vault object. |
| VLT-FR-003 | Cryptographic digest | Calculate and store algorithm + digest over canonical representation and evidence manifest. | Integrity test reproducible. |
| VLT-FR-004 | Release metadata | Store object type, business ID, version, status, effective dates, release reason, authors/approvers/signatures and software/schema versions. | Full release context retained. |
| VLT-FR-005 | Evidence manifest | Link immutable file/evidence IDs, hashes, media types and versions used by released object. | Attachments cannot silently swap. |
| VLT-FR-006 | Batch issue snapshot | At batch/device work issuance, freeze exact released recipe/specification/material/equipment/rule references required for that execution. | Later master change cannot rewrite active/history. |
| VLT-FR-007 | Snapshot dependency closure | Snapshot captures exact IDs/versions/hashes of dependent released objects rather than only business names. | Dependency reproducible. |
| VLT-FR-008 | Effective dating | Released versions have controlled effective-from/effective-to/obsolete lifecycle; selection engine prevents unauthorized obsolete/future use. | Batch issue chooses eligible version. |
| VLT-FR-009 | Supersession | New approved version supersedes prior for future use but never deletes prior version or its historical references. | Old batches still resolve old version. |
| VLT-FR-010 | Controlled correction | Corrections to regulated completed/released records create amendment/superseding version referencing original, reason, authority, signatures and changed fields. | Original remains visible. |
| VLT-FR-011 | Correction eligibility | Policy defines which record states/types permit correction, who may initiate/approve, and whether downstream impact assessment is required. | Unauthorized correction blocked. |
| VLT-FR-012 | No silent overwrite | Any attempt to overwrite a vault object/version through application API is rejected. | Immutability negative test. |
| VLT-FR-013 | Void/cancel semantics | Where a record must be voided/cancelled, retain original and add controlled status/event/reason rather than physical deletion. | Voided history remains. |
| VLT-FR-014 | Signature binding | Signatures reference exact vault version/hash or pre-commit canonical target that becomes exact resulting version. | Signature cannot float to new content. |
| VLT-FR-015 | Audit linkage | Version creation/release/supersession/correction is represented in Audit Ledger. | Vault history and audit reconcile. |
| VLT-FR-016 | Inspection retrieval | Authorized user can retrieve any historical version plus relationships, signatures, audit and evidence manifest. | Historical record is readable. |
| VLT-FR-017 | Deterministic export | Export service can regenerate human-readable representation from stored authoritative version using controlled renderer/version or preserve signed release export. | Meaning remains available after upgrade. |
| VLT-FR-018 | Schema evolution | Older canonical schema versions remain readable. Migrations never rewrite historical semantic content without controlled migration provenance. | Old records survive software upgrade. |
| VLT-FR-019 | Retention class | Each object gets retention class based on profile/record type/customer policy; no normal application deletion. | Retention auditable. |
| VLT-FR-020 | Legal/quality hold | Hold prevents disposal/archival transitions and is itself controlled/audited. | Hold honored. |
| VLT-FR-021 | Archive tiering | Move old vault objects/evidence to archival storage only if integrity, retrieval and meaning are preserved. | Archive retrieval qualified. |
| VLT-FR-022 | WORM-capable evidence | Released file packages/checkpoints may use object-storage retention lock/WORM where deployment supports it. | Infrastructure immutability can be verified. |
| VLT-FR-023 | Version numbering | Use immutable internal version IDs plus human/business version labels; never rely only on editable semantic label. | Duplicate labels cannot confuse history. |
| VLT-FR-024 | Content addressing | Evidence objects may be deduplicated by digest while preserving record-specific manifest references and retention. | No cross-record mutation. |
| VLT-FR-025 | Cross-constituent snapshot | DDCP snapshot can bind exact drug constituent version, device constituent version, compatibility version and final assembly/release rules. | Final DDCP scope reproducible. |
| VLT-FR-026 | Migration provenance | Imported historical versions are flagged migrated, with source system, source ID, extraction checksum and migration batch. | Native vs migrated distinguishable. |
| VLT-FR-027 | Restore verification | Backup restore checks version counts, hashes, evidence manifests, signatures and audit relationships. | Restored vault trustworthy. |
| VLT-FR-028 | Access control | Draft authorship access does not imply released-vault write access; runtime exposes read plus controlled release/correction commands only. | Least privilege. |
| VLT-FR-029 | Reference integrity | Foreign references to released version use immutable identifiers and DB constraints/service validation; no dangling reference on normal operation. | Batch can always resolve snapshot. |
| VLT-FR-030 | Disposition package | Final release/closure creates or references a complete immutable record package suitable for regulatory export and long-term retrieval. | Release package complete. |

# 5. Version Lifecycle

```text
DRAFT (outside vault / controlled authoring)
   ↓ approved
RELEASED v1
   ↓ new controlled change
SUPERSEDED FOR FUTURE USE
   └── remains historical and referenced

Completed/Released execution record:
RELEASED RECORD v1
   ↓ controlled correction request
AMENDMENT v2
   ├── references v1
   ├── preserves changed fields/reason/signatures
   └── v1 remains accessible
```

# 6. Canonicalization Contract

Must define:
- object schema version;
- stable field names;
- array ordering semantics;
- decimal precision/rounding;
- timestamp representation;
- unit representation;
- reference representation;
- null/absent semantics;
- Unicode/text normalization where relevant.

The canonicalization package is shared by Vault, Signature and Audit.

# 7. Data Model

`vault_object`
- object_id
- tenant/site
- object_type
- business_id
- internal_version_id
- business_version_label
- schema_version
- canonical_payload/reference
- digest_algorithm
- digest
- status
- effective_from/to
- supersedes_id
- corrected_from_id
- released_at
- retention_class

`vault_evidence_manifest`
- manifest_id
- vault_object_id
- evidence_id
- evidence_version
- sha256
- media_type
- retention metadata

# 8. Frappe Boundary

Frappe may author drafts and display released versions.
Frappe shall not:
- update released Vault payload;
- change hash/effective date without controlled command;
- detach an evidence object from a released manifest;
- repoint an issued batch to a newer recipe after issue.

# 9. Controlled Correction Workflow

1. initiate correction request;
2. identify exact record/version and field(s);
3. reason/category;
4. impact assessment: batch, product, downstream records, release/distribution;
5. authorization;
6. create amended canonical version;
7. obtain required electronic signatures;
8. audit relationship;
9. update current-view pointer if policy allows;
10. retain both versions;
11. re-export/release impact if required.

# 10. Validation Tests

- released object write attempt;
- master version supersession;
- batch snapshot after master changes;
- attachment swap attempt;
- correction old/new;
- void/cancel;
- signature remains on old version;
- new signature on amendment;
- effective-date selection;
- obsolete-version issue attempt;
- schema upgrade readability;
- backup/restore hashes;
- archive/retrieve;
- DDCP constituent snapshot;
- migration provenance.

# 11. Acceptance Gate

Canonicalization library, digest test vectors, correction state model, evidence manifest and storage abstraction must be frozen before Recipe/Batch Release logic is finalized.

# 12. Developer / AI-Agent Rules

Never change historical canonical payload.
Never “fix data” by SQL UPDATE.
Never change a batch's released recipe reference after issue.
Never delete old version because a new version is current.
Never recompute a stored historical hash with a new canonicalization algorithm and overwrite the old digest; store algorithm/version explicitly.

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
services/gxp-api/src/modules/vault/
├── vault.service.ts
├── release.service.ts
├── correction.service.ts
├── canonicalizer.ts
├── digest.service.ts
├── snapshot-builder.ts
├── evidence-manifest.ts
├── retention.service.ts
├── repositories/
└── errors.ts

packages/canonicalization/
├── src/
├── test-vectors/
└── version.ts
```

# 14. PostgreSQL Tables

## `gxp_vault_object`

```text
object_id uuid PK
tenant_id uuid NOT NULL
site_id uuid
object_type varchar(80) NOT NULL
business_id varchar(160) NOT NULL
internal_version bigint NOT NULL
business_version_label varchar(80)
schema_version varchar(30) NOT NULL
canonical_payload jsonb NOT NULL
digest_algorithm varchar(40) NOT NULL
digest char(64) NOT NULL
status varchar(40) NOT NULL
effective_from timestamptz
effective_to timestamptz
supersedes_object_id uuid
corrected_from_object_id uuid
retention_class varchar(80)
released_at timestamptz NOT NULL
created_by_subject varchar(255)
```

Unique:
- `(tenant_id, object_type, business_id, internal_version)`;
- `(tenant_id, digest, object_type)` may be indexed but do not assume semantic uniqueness.

## `gxp_vault_evidence`

```text
id uuid PK
vault_object_id uuid NOT NULL
evidence_id uuid NOT NULL
evidence_version bigint NOT NULL
evidence_sha256 char(64) NOT NULL
media_type varchar(120)
sequence int
```

## `gxp_record_correction`

```text
correction_id uuid PK
tenant_id uuid
record_object_id uuid NOT NULL
status varchar(40)
reason_code varchar(80)
reason_text text
impact_assessment jsonb
requested_by varchar(255)
approved_by_signatures jsonb
resulting_object_id uuid
created_at timestamptz
completed_at timestamptz
```

# 15. Release API

- `POST /vault/v1/masters/{type}/{businessId}/release`
- `GET /vault/v1/objects/{objectId}`
- `GET /vault/v1/objects/{objectId}/integrity`
- `POST /vault/v1/objects/{objectId}/corrections`
- `POST /vault/v1/corrections/{id}/complete`
- `GET /vault/v1/business/{type}/{businessId}/versions`

Release command goes through Mutation Gateway; Vault API may expose read/query and internal domain functions.

# 16. Snapshot Builder Contract

Input:
- released recipe object ID;
- product version;
- specification versions;
- rule versions;
- material requirement versions;
- equipment requirement versions;
- signature policies;
- DDCP constituent/compatibility versions.

Output:
`BatchExecutionSnapshot`

```json
{
  "snapshot_id":"...",
  "recipe":{"object_id":"...","digest":"..."},
  "dependencies":[
    {"type":"MaterialSpec","object_id":"...","digest":"..."}
  ],
  "rule_versions":[],
  "signature_policies":[],
  "created_at_utc":"..."
}
```

No dependency may remain a mutable “current” pointer after issue.

# 17. Canonicalization Test Vectors

Repository shall include fixtures:
- field order changes produce same hash;
- semantic value change produces different hash;
- equivalent decimal formatting normalized;
- timestamps normalized;
- array order behavior defined by field semantics;
- null vs missing behavior defined.

# 18. Correction UI

Screens:
1. View Historical Version
2. Request Correction
3. Impact Assessment
4. Compare Old vs Proposed
5. Signature/Approval
6. Corrected Version History

UI must never present corrected value without clear indication that an older value/version exists.

# 19. Export / Rendering

Every export records:
- source vault object ID/version/hash;
- renderer/template version;
- generation time;
- output file hash;
- evidence manifest ID.

If renderer changes later, old export remains preserved or reproducibility is demonstrated by versioned renderer.

# 20. Observability

Metrics:
- release count;
- correction count;
- failed digest checks;
- unresolved corrections;
- snapshot build failures;
- archive retrieval latency;
- evidence mismatch.

# 21. Implementation Sequence

1. canonicalization package;
2. digest test vectors;
3. vault table;
4. release API/domain service;
5. version query;
6. evidence manifest;
7. snapshot builder;
8. correction workflow;
9. export metadata;
10. retention/archive;
11. restore/integrity tests.

# 22. Migration Rule

Historical legacy data imported into Vault shall:
- keep source system/object ID;
- store migration batch;
- preserve original file/checksum where available;
- never be assigned fabricated native approval/signature history.

