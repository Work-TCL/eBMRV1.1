# US eBMR / eDHR Regulated Manufacturing Platform
## Document 72 — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-004  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 05–06, 16, 30, 42–47, 65, 69; Retention/DR  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is intended for direct ingestion by Claude Code, Codex, and human engineering/operations teams.

Before implementation, the coding agent shall extract this document into:

1. requirement registry;
2. module/submodule and infrastructure-component map;
3. function/service contract catalogue;
4. typed input/output schemas;
5. database/storage ownership map;
6. data lifecycle and retention map;
7. API/event contracts;
8. transaction and concurrency model;
9. availability and failure-mode model;
10. backup/restore/DR controls;
11. observability/SLO/capacity controls;
12. configuration and deployment contracts;
13. positive/negative/failure/concurrency/restore tests;
14. requirement-to-test traceability.

For every public/domain/infrastructure function specified here, preserve:

- function name and purpose;
- caller/trigger;
- typed inputs and source;
- authorization/qualification/SoD/signature prerequisites where applicable;
- preconditions and validations;
- database/storage reads;
- database/storage writes;
- transaction boundary;
- output/result;
- emitted/consumed events;
- downstream consumers;
- stable errors;
- idempotency/concurrency;
- audit/operational evidence;
- observability;
- test obligations.

If a missing decision changes regulated behavior, data durability, recovery semantics, or infrastructure trust boundaries, create a `SPEC_GAP` rather than guessing.

# Data / Infrastructure Architectural Invariants

- PostgreSQL is the authoritative database for proprietary GxP Core regulated state.
- MariaDB is the Frappe operational/UI/configuration database and may contain projections, workflow/UI metadata, and non-authoritative application state.
- A regulated authoritative entity must not be dual-mastered between PostgreSQL and MariaDB.
- Immutable/released evidence and large binary artifacts are stored in object storage through Evidence/Vault services with content hashes and retention/WORM controls.
- NATS/JetStream is an asynchronous event-delivery layer. The authoritative event/outbox record originates from the same PostgreSQL transaction as the GxP state change.
- Temporal coordinates long-running processes and retries but is not the regulatory system of record.
- Redis/cache/search indexes are disposable/rebuildable accelerators or projections; they are never the only copy of regulated truth.
- Kubernetes, VM disks, PVCs and replicas are runtime infrastructure; none of them substitute for tested backups.
- Every persistent component must have explicit backup, restore, retention, encryption, monitoring, ownership and recovery behavior.
- Data retention/deletion is controlled by regulatory/product/customer/legal-hold policy and cannot be inferred from storage cost alone.

# Current Technical Reference Baseline

- PostgreSQL current official documentation is on major version 18. PostgreSQL WAL, replication, backup and declarative partitioning are used as reference capabilities, but deployment shall pin a validated supported version rather than follow `latest`.
- PostgreSQL WAL and archived WAL support crash recovery and point-in-time recovery architectures when correctly configured.
- NATS/JetStream provides durable streams/consumers and messaging primitives; application-level outbox/idempotency remains mandatory.
- Temporal provides durable workflow execution/recovery; workflow code must remain deterministic and activities must isolate external side effects.
- Kubernetes StatefulSets can provide stable identity/storage mechanics for stateful workloads, but production database/object-store deployment may also use managed services or dedicated operators/VMs depending on deployment profile.

Primary references:
- https://www.postgresql.org/docs/current/
- https://www.postgresql.org/docs/current/wal.html
- https://www.postgresql.org/docs/current/ddl-partitioning.html
- https://docs.nats.io/
- https://docs.temporal.io/
- https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- https://kubernetes.io/docs/concepts/services-networking/network-policies/

# 1. Objective

Define cloud-neutral object/evidence storage for immutable files, raw instrument data, images, PDFs, cycle files and evidence manifests, including content integrity, WORM retention, legal hold, export and provider migration.

# 2. Actors / Components

- Evidence Service
- Vault Service
- Uploader
- Edge/Integration
- QA/Inspector
- Records Manager
- Object Storage Provider
- Backup/DR Operator

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| OBJ-FR-001 | Evidence object abstraction | Support S3-compatible, Azure Blob and on-prem object storage through one EvidenceStore provider. | Cloud-neutral. |
| OBJ-FR-002 | Content addressing | Evidence object identified by generated immutable evidence ID plus SHA-256/approved digest; optional content-addressed path. | Integrity. |
| OBJ-FR-003 | Upload staging | Upload enters STAGED/QUARANTINE until checksum/type/security validation completes. | Safe ingestion. |
| OBJ-FR-004 | Immutable promotion | Validated evidence promoted/finalized into immutable object key/version; overwrite prohibited. | History. |
| OBJ-FR-005 | Metadata authority | PostgreSQL stores evidence metadata, ownership, hash, size, MIME, source, retention, legal hold and object version/reference. | Searchable control. |
| OBJ-FR-006 | WORM/immutability | Release/archive profile supports Object Lock/immutability policy or equivalent on-prem retention lock. | Tamper resistance. |
| OBJ-FR-007 | Retention mode | Governance/compliance/provider-specific retention mode selected by deployment and legal requirements; config protected. | Controlled storage. |
| OBJ-FR-008 | Evidence manifest | Regulated record/release package references immutable manifest of evidence IDs/hashes/versions. | Inspection. |
| OBJ-FR-009 | Large raw evidence | Machine files, images, PDFs, instrument exports, reports and cycle evidence stored without loading into DB blob columns. | Scale. |
| OBJ-FR-010 | Multipart upload | Large files use resumable/multipart upload with final whole-object integrity verification. | Reliability. |
| OBJ-FR-011 | Pre-signed URL | Temporary upload/download URLs can be issued only after authorization and short expiry; URL alone not permanent authority. | Secure transfer. |
| OBJ-FR-012 | Download authorization | Service validates subject/resource/evidence access before generating download token. | Confidentiality. |
| OBJ-FR-013 | Encryption | Provider at-rest encryption with customer/dedicated keys where profile requires; TLS in transit. | Security. |
| OBJ-FR-014 | Malware/quarantine | Externally uploaded files scanned/quarantined before ordinary access where applicable. | Security. |
| OBJ-FR-015 | Type validation | MIME/extension/content signature/size policies validated; filenames treated as metadata only. | Upload safety. |
| OBJ-FR-016 | Hash verification | Hash verified at ingest, copy/archive, restore and optionally periodic integrity scans. | Integrity. |
| OBJ-FR-017 | No in-place edit | Corrected document/file creates new evidence object/version and relationship; original retained. | History. |
| OBJ-FR-018 | Legal hold | Hold prevents normal expiry/delete regardless of retention schedule. | Governance. |
| OBJ-FR-019 | Retention expiration | Purge eligibility determined by Records service + holds + reference policy, not bucket lifecycle alone. | Controlled deletion. |
| OBJ-FR-020 | Lifecycle tiers | Archive/cold tiers allowed if retrieval SLA/validation/immutability requirements met. | Cost control. |
| OBJ-FR-021 | Cross-region/site replication | Optional replication configured per deployment/DR profile; replica integrity monitored. | DR. |
| OBJ-FR-022 | Backup distinction | Replication/versioning is not backup; backup/restore strategy explicitly tested. | Resilience. |
| OBJ-FR-023 | Missing object | Broken evidence metadata→object relation triggers critical integrity event and release/inspection blocker where relevant. | Fail safe. |
| OBJ-FR-024 | Orphan detection | Unreferenced objects/staged uploads detected and handled via controlled cleanup policies. | Hygiene. |
| OBJ-FR-025 | Evidence provenance | Store producer, source device/system, uploaded actor/service, timestamps and source hash where supplied. | Traceability. |
| OBJ-FR-026 | Rendering | Generated PDFs/renditions are separate evidence objects linked to canonical data/version and renderer version. | Reproducibility. |
| OBJ-FR-027 | Export package | Inspection export creates manifest, files, hashes and metadata without changing source evidence. | Portable evidence. |
| OBJ-FR-028 | Restore validation | Restored archive verifies object count/manifests/hashes and sampled retrieval before healthy. | DR assurance. |
| OBJ-FR-029 | Provider migration | Storage-provider migration uses manifest/hash copy verification and retains old location until acceptance. | Cloud portability. |
| OBJ-FR-030 | No bucket browsing | Users/apps do not receive broad bucket listing credentials; access is resource-scoped. | Least privilege. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| stageEvidenceUpload() | UI/Edge/Integration | owner context; filename; MIME; size; expected hash? | Uploader authorized; policy/quotas | Creates STAGED metadata and short-lived upload session/URL | EvidenceUploadSession | EvidenceUploadStaged; EVIDENCE_UPLOAD_DENIED |
| finalizeEvidenceUpload() | Upload callback/service | evidence_id; provider object/version; calculated hash; size | Upload complete; malware/type checks passed | Verifies hash/size; changes metadata to IMMUTABLE_AVAILABLE; records object version | EvidenceRef | EvidenceFinalized; EVIDENCE_HASH_MISMATCH |
| createEvidenceManifest() | Vault/Release/Export | owner record/version; evidence refs; manifest type | All refs available/current | Canonical sorts/hashes manifest and stores immutable manifest evidence | EvidenceManifestRef | EvidenceManifestCreated |
| authorizeEvidenceDownload() | Download API | AuthContext; evidence_id; purpose | Resource authorization/retention state valid | Returns short-lived signed URL/stream token without broad storage access | EvidenceDownloadGrant | EVIDENCE_ACCESS_DENIED |
| verifyEvidenceIntegrity() | Scheduled/restore/inspection | evidence scope; sampling/full mode | Objects readable | Recomputes/provider-verifies hashes/version/retention state | EvidenceIntegrityReport | EVIDENCE_MISSING/EVIDENCE_HASH_MISMATCH |
| applyEvidenceLegalHold() | Records/Legal | evidence scope; hold_id; reason | Authorized hold | Updates metadata and provider retention/lock policy where supported | HoldReceipt | EvidenceLegalHoldApplied |
| purgeExpiredEvidence() | Retention worker | eligibility set; policy version | Retention elapsed; no hold; no blocking reference | Deletes only through provider controlled path and records destruction evidence | PurgeReport | EVIDENCE_PURGE_BLOCKED |
| migrateEvidenceProvider() | Migration tool | source provider; target provider; manifest scope | Migration approved; target configured | Copies immutable objects, verifies hashes/metadata, records mapping; cutover after reconciliation | ProviderMigrationReport | EvidenceProviderMigrated |


# 5. State / Runtime / Ownership Model

```text
UPLOAD REQUEST
   ↓
STAGED / QUARANTINED
   ↓ validate scan/type/hash
IMMUTABLE_AVAILABLE
   ↓
REFERENCED BY RECORD/VERSION/MANIFEST
   ↓
ACTIVE / ARCHIVED / COLD
   ├→ LEGAL_HOLD
   └→ PURGE_ELIGIBLE → CONTROLLED_DESTROYED

```

# 6. Data / Configuration Model

## `evidence_object`
```text
id uuid PK
tenant_id uuid
owner_type/id/version
provider varchar
bucket/container varchar
object_key varchar
provider_version_id varchar
size_bytes bigint
mime_type varchar
hash_algorithm varchar
content_hash varchar
state varchar
retention_policy_id uuid
retention_until timestamptz
legal_hold boolean
created_at timestamptz
```

## `evidence_manifest`
- owner record/version
- manifest type/version
- ordered evidence items
- canonical hash
- renderer/export version if applicable
- Vault object reference


# 7. APIs / Internal Interfaces

- `POST /evidence/v1/uploads`
- `POST /evidence/v1/{id}:finalize`
- `GET /evidence/v1/{id}/download`
- `POST /evidence/v1/manifests`
- `POST /evidence/v1/{id}/legal-holds`
- `POST /evidence/v1/integrity-checks`

# 8. UI / Operations Screens

1. Evidence Browser (authorized metadata)
2. Upload/Quarantine
3. Integrity Status
4. Retention/Hold
5. Archive Tier
6. Evidence Manifest
7. Provider Migration

# 9. Events / Operational Signals

- `EvidenceUploadStaged`
- `EvidenceFinalized`
- `EvidenceHashMismatch`
- `EvidenceMissing`
- `EvidenceLegalHoldApplied`
- `EvidencePurged`
- `EvidenceProviderMigrated`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/immutable-evidence-object-storage-worm-archive-file-lifecycle/
services/platform/immutable-evidence-object-storage-worm-archive-file-lifecycle/
packages/data-contracts/
validation/infrastructure/immutable-evidence-object-storage-worm-archive-file-lifecycle/
tests/infrastructure/immutable-evidence-object-storage-worm-archive-file-lifecycle/
docs/runbooks/immutable-evidence-object-storage-worm-archive-file-lifecycle/
```

# 12. Mandatory Test Catalogue

- hash mismatch on upload
- malware quarantine
- overwritten provider object detected
- legal hold blocks lifecycle deletion
- cold archive restore
- missing object
- provider migration hash reconciliation
- presigned URL expiry

# 13. Acceptance Criteria

An inspection package can prove each referenced file's immutable identity, hash, source, retention state and relationship to the exact regulated record version.

# 14. Claude Code / Codex Prohibitions

- Never store regulated file solely as Frappe attachment with no GxP evidence metadata.
- Never overwrite object to make a correction.
- Never let bucket lifecycle delete records without GxP retention eligibility.
- Never give users broad bucket credentials.


