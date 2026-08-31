# US eBMR / eDHR Regulated Manufacturing Platform
## Document 76 — Backup, Restore, Point-in-Time Recovery & Disaster Recovery — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-008  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 05–06, 65, 69–75; Security Incident Response  
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

Define component-specific backup, PITR, restore, failover, disaster recovery and validation so regulated data and evidence can be demonstrably recovered within agreed objectives.

# 2. Actors / Components

- DR Operator
- DBA
- SRE
- Security
- QA/Validation
- Customer IT
- Object Storage Admin
- Incident Commander

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| DR-FR-001 | Recovery objectives | Define RPO/RTO per component and business capability, approved by customer/product profile. | Measurable recovery. |
| DR-FR-002 | Tier classification | Classify GxP PostgreSQL, MariaDB, object evidence, NATS, Temporal, search/cache, observability, config/secrets by criticality. | Prioritized. |
| DR-FR-003 | PostgreSQL backup | Use base/full/incremental/managed backups plus WAL/PITR according to deployment profile. | Recoverability. |
| DR-FR-004 | WAL archive | WAL archiving protected, monitored and retained to meet PITR/RPO window. | PITR. |
| DR-FR-005 | Backup manifest | Backup includes manifest/checksum/metadata and is immutable/protected from production compromise. | Integrity. |
| DR-FR-006 | MariaDB backup | Frappe/MariaDB backups scheduled and encrypted; projection freshness expected after restore. | Operational recovery. |
| DR-FR-007 | Object storage protection | Object versioning/immutability/replication plus independent backup/export strategy as deployment requires. | Evidence recovery. |
| DR-FR-008 | NATS backup | Stream configuration/state backup/recovery documented, but domain recovery must not depend solely on NATS history. | Messaging recovery. |
| DR-FR-009 | Temporal backup | Temporal persistence backup/managed DR configured for orchestration; GxP records recover independently. | Orchestration recovery. |
| DR-FR-010 | Secrets/KMS backup | Key/secret recovery strategy prevents encrypted backups becoming unrecoverable. | Crypto recovery. |
| DR-FR-011 | Infrastructure config | IaC, manifests, config versions, certificates/trust metadata and deployment parameters backed by source/control plane. | Rebuildability. |
| DR-FR-012 | Offsite/isolation | Backups logically/physically isolated from normal production credentials/ransomware path. | Resilience. |
| DR-FR-013 | Encryption | Backups encrypted in transit/at rest; key access separate. | Security. |
| DR-FR-014 | Retention generations | Daily/weekly/monthly or equivalent retention derived from RPO/history/regulatory needs, not one hardcoded schedule. | Flexible. |
| DR-FR-015 | Backup monitoring | Backup start/completion/size/age/checksum/WAL gap/replication failures alert. | Reliability. |
| DR-FR-016 | Restore testing | Automated regular restore test into isolated environment; application-level integrity checks mandatory. | Evidence. |
| DR-FR-017 | PITR test | Demonstrate recovery to selected timestamp/LSN within objective and validate audit/event continuity. | Point-in-time confidence. |
| DR-FR-018 | Application consistency | Restore runbook defines recovery order/checkpoints across PostgreSQL/object/MariaDB/Temporal/NATS. | Cross-system consistency. |
| DR-FR-019 | Object reconciliation | After restore verify evidence metadata→object references/hashes. | Evidence integrity. |
| DR-FR-020 | Projection rebuild | Frappe/search/cache/read models can rebuild from recovered authoritative data. | Recovery simplification. |
| DR-FR-021 | DR site/region | Enterprise profile can use secondary region/site with documented replication/failover mode. | Availability. |
| DR-FR-022 | Failover authority | Primary DB promotion/failover uses controlled operator/automation with split-brain prevention. | Data integrity. |
| DR-FR-023 | Failback | Failback/rejoin procedure tests data divergence and does not simply overwrite new primary. | Recovery. |
| DR-FR-024 | Disaster declaration | DR activation has incident/change record, owner, time and affected services. | Governance. |
| DR-FR-025 | Validation before reopen | Recovered environment passes defined smoke/integrity/security/GxP checks before accepting regulated work. | Safe restart. |
| DR-FR-026 | Data-loss assessment | If recovery loses data beyond expected RPO, system identifies missing range/events and creates incident/GxP assessment. | Transparency. |
| DR-FR-027 | Offline customer | On-prem customer backup destination/runbook supports customer-operated storage without weakening integrity evidence. | Deployment. |
| DR-FR-028 | Backup deletion | Backup expiry/destruction follows controlled lifecycle and legal/security policies. | Governance. |
| DR-FR-029 | Restore access | Only privileged recovery role may perform restore; all operations audited. | Security. |
| DR-FR-030 | DR evidence | Each test records backup set, restore target, timings, checks, RPO/RTO achieved, failures and remediation. | Validation. |
| DR-FR-031 | Capacity | Backup target has growth forecast and alerts before exhaustion. | Operations. |
| DR-FR-032 | No replica-as-backup | Replication/standby alone is not considered backup. | Correct resilience. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createRecoveryObjectiveProfile() | Platform/Customer Admin | component/capability; RPO; RTO; durability/region profile | Authorized and architecture compatible | Stores versioned objective profile/evidence | RecoveryObjectiveProfile | RecoveryObjectiveConfigured |
| verifyBackupFreshness() | Scheduled monitor | component; objective profile; backup/WAL metadata | Backup provider reachable | Calculates age/gaps vs RPO, raises alerts | BackupHealth | BackupRPOAtRisk |
| executePostgresRestoreTest() | DR automation | backup set; PITR target; isolated target profile | Backup/key/WAL available | Restores PostgreSQL, runs DB/integrity/app checks, records timings/evidence | RestoreTestReport | PostgresRestoreTestCompleted |
| reconcileEvidenceAfterRestore() | DR validation | restored GxP metadata; object provider/snapshot | Metadata/object restore available | Checks referenced evidence existence/hash/sample/full mode | EvidenceRecoveryReport | EvidenceRestoreMismatch |
| rebuildDerivedStoresAfterRestore() | Recovery orchestration | projection/search/cache scopes; authoritative cutoff | Authoritative services healthy | Rebuilds derived stores and checkpoints | DerivedRecoveryResult | DerivedStoresRebuilt |
| promoteStandby() | DR operator/automation | cluster; target replica; incident/change ID | Quorum/split-brain checks; authority valid | Promotes selected replica; reconfigures endpoints; records timeline | FailoverReceipt | DatabaseFailoverCompleted |
| validateRecoveredPlatform() | DR validation gate | recovery environment; component reports; smoke/test profile | Required stores restored | Runs security, auth, audit hash, signatures, object refs, batch/QMS smoke and projection checks | RecoveryValidationDecision | PlatformRecoveryValidated/RECOVERY_VALIDATION_FAILED |
| recordDataLossAssessment() | Security/QA/DR | restore point; expected latest; missing interval/events | Recovery complete enough to compare | Creates incident/GxP impact report and required QMS actions | DataLossAssessment | RecoveryDataLossDetected |


# 5. State / Runtime / Ownership Model

```text
NORMAL
  ↓ backup/WAL/replication
PROTECTED RECOVERY SETS
  ↓ scheduled restore tests

DISASTER
  ↓ declare
CONTAIN / SELECT RECOVERY POINT
  ↓
RESTORE/PROMOTE AUTHORITATIVE STORES
  ↓
RECONCILE OBJECT EVIDENCE
  ↓
RESTORE/REBUILD DERIVED STORES
  ↓
SECURITY/GxP RECOVERY VALIDATION
  ├→ FAIL → REMEDIATE
  └→ PASS → SERVICE REOPEN

```

# 6. Data / Configuration Model

## `recovery_objective_profile`
- business capability/component
- RPO
- RTO
- backup frequency
- PITR window
- secondary region/site requirements
- owner/approver

## `backup_inventory`
- component
- backup ID/type
- start/end
- source version/timeline
- size/hash/manifest
- WAL coverage
- encryption/key ref
- storage location
- retention

## `restore_test`
- backup set
- target
- PITR target
- elapsed time
- integrity checks
- RPO/RTO achieved
- evidence/report


# 7. APIs / Internal Interfaces

- `DR automation/runbooks`
- `POST /platform/v1/recovery-objectives`
- `GET /platform/v1/backups/health`
- `POST /platform/v1/restore-tests`

# 8. UI / Operations Screens

1. Backup Health
2. WAL/PITR Coverage
3. Restore Tests
4. DR Objectives
5. Failover/Incident
6. Recovery Validation

# 9. Events / Operational Signals

- `BackupRPOAtRisk`
- `RestoreTestFailed`
- `DatabaseFailoverCompleted`
- `EvidenceRestoreMismatch`
- `PlatformRecoveryValidated`
- `RecoveryDataLossDetected`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/backup-restore-point-in-time-recovery-disaster-recovery/
services/platform/backup-restore-point-in-time-recovery-disaster-recovery/
packages/data-contracts/
validation/infrastructure/backup-restore-point-in-time-recovery-disaster-recovery/
tests/infrastructure/backup-restore-point-in-time-recovery-disaster-recovery/
docs/runbooks/backup-restore-point-in-time-recovery-disaster-recovery/
```

# 12. Mandatory Test Catalogue

- backup success flag but corrupt restore
- WAL gap
- PITR to 10 minutes before incident
- object evidence missing
- MariaDB older than GxP then projection rebuild
- standby promotion
- split brain prevention
- lost encryption key drill
- RPO exceeded

# 13. Acceptance Criteria

A restore test proves that authoritative GxP data, audit history and referenced evidence can be recovered and validated—not merely that a backup job reported success.

# 14. Claude Code / Codex Prohibitions

- Never call a replication standby a backup.
- Never mark DR complete before application-level integrity validation.
- Never restore MariaDB projection and assume it is newer than GxP.
- Never delete backup encryption keys while retained backups still require them.

# 15. Required Claude Code Artifact

Generate `26_RPO_RTO_BACKUP_RESTORE_MATRIX.md` containing every persistent component, backup method, PITR capability, retention, RPO/RTO, restore order and validation test.

