# US eBMR / eDHR Regulated Manufacturing Platform
## Document 77 — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-009  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 61–68, 69–76; AWS/Azure/on-prem/private cloud  
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

Define reproducible production deployment architecture and lifecycle across cloud and on-prem environments, including Kubernetes/runtime topology, stateful service choices, IaC, probes, scaling, installation qualification, upgrades and rollback.

# 2. Actors / Components

- Platform Engineer
- DevOps/SRE
- Installer
- Customer IT
- Security
- DBA
- Release Engineer
- Validation

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| DEP-FR-001 | Deployment profiles | Support AWS, Azure, private cloud/on-prem Kubernetes and controlled VM/container profile without vendor-specific domain code. | Cloud-neutral. |
| DEP-FR-002 | Dedicated customer deployment | Baseline production uses dedicated customer deployment/isolation; multi-tenant shared deployment requires separate architecture approval. | Enterprise. |
| DEP-FR-003 | Environment separation | dev/test/validation/staging/prod logically separated with distinct secrets/data/endpoints. | SDLC. |
| DEP-FR-004 | IaC | Infrastructure defined in version-controlled Terraform/OpenTofu/Helm/Kustomize or approved equivalents. | Reproducible. |
| DEP-FR-005 | Immutable images | Services deployed from signed immutable image digest/release. | Supply-chain. |
| DEP-FR-006 | Configuration | Environment config separated from code; GxP/security config version controlled and approved as required. | Change control. |
| DEP-FR-007 | Kubernetes namespaces | Separate platform/GxP/integration/observability or equivalent boundaries with service accounts/network policy. | Isolation. |
| DEP-FR-008 | Stateless services | Frappe/GxP APIs/workers run as stateless horizontally scalable deployments where architecture permits. | Scale. |
| DEP-FR-009 | Stateful services | Managed services preferred where suitable; self-hosted stateful components use operators/StatefulSets/VMs with tested persistence/backup. | Reliability. |
| DEP-FR-010 | Persistent volumes | PVC/storage class performance/durability/retention explicitly configured; PVC retention not backup. | Storage. |
| DEP-FR-011 | Ingress | TLS ingress/API gateway with WAF/rate limits as deployment requires; admin endpoints segregated. | Security. |
| DEP-FR-012 | Service discovery | Internal DNS/service names stable and environment-scoped. | Runtime. |
| DEP-FR-013 | Secrets | External secret manager/CSI/operator or controlled equivalent; no plaintext Kubernetes Secret manifests in repo. | Security. |
| DEP-FR-014 | PKI | Service/Edge certificates provisioned through documented CA/KMS workflow. | Identity. |
| DEP-FR-015 | Database endpoints | Managed/private endpoints or internal-only services; no public DB. | Security. |
| DEP-FR-016 | Object store | Provider abstraction maps S3/Azure/on-prem endpoints and WORM/immutability capabilities. | Portability. |
| DEP-FR-017 | NATS | NATS cluster/service profile pins version, storage, replicas, TLS/auth, monitoring and backup/config. | Messaging. |
| DEP-FR-018 | Temporal | Temporal Cloud/self-hosted profile with namespace/auth/persistence/worker config. | Orchestration. |
| DEP-FR-019 | Redis/search | Optional deployment with HA/persistence according to cache/search role; service can degrade if unavailable. | Read layer. |
| DEP-FR-020 | Resource requests/limits | Kubernetes workloads define requests/limits based on load tests; avoid arbitrary tiny defaults. | Scheduling. |
| DEP-FR-021 | Probes | Startup/readiness/liveness probes are service-semantic; readiness fails when dependency needed to serve safely is unavailable. | Correct routing. |
| DEP-FR-022 | Graceful shutdown | APIs/workers drain requests/jobs/outbox leases before termination within configured grace. | Safe rollout. |
| DEP-FR-023 | Pod disruption | PDB/topology spread/anti-affinity used where availability warrants. | Resilience. |
| DEP-FR-024 | Autoscaling | Stateless workers/API HPA/KEDA or equivalent uses safe metrics and max bounds; DB connections considered. | Scale. |
| DEP-FR-025 | Rolling deploy | Rolling/canary/blue-green strategy per service risk; DB migrations backward compatible across rollout window. | Availability. |
| DEP-FR-026 | Rollback | Application rollback does not blindly reverse incompatible DB migration; migration compatibility plan explicit. | Safe release. |
| DEP-FR-027 | On-prem install | Air-gapped/private registry/offline package mode supported for enterprise plants where required. | Deployment. |
| DEP-FR-028 | On-prem prerequisites | CPU/RAM/storage/network/NTP/DNS/PKI/backup prerequisites machine-checkable before install. | Successful setup. |
| DEP-FR-029 | Installation validation | Post-install automated health/security/data/queue/storage/auth checks produce evidence report. | Qualification aid. |
| DEP-FR-030 | Upgrade | Upgrade preflight, backup, migration, deployment, smoke tests, rollback decision and validation evidence. | Controlled change. |
| DEP-FR-031 | Infrastructure drift | Detect IaC/config drift in production and alert/require reconciliation. | Validated state. |
| DEP-FR-032 | Feature flags | Runtime flags versioned/scoped; GxP-affecting flag cannot silently change regulated behavior outside change/release controls. | Safe config. |
| DEP-FR-033 | Time sync | All hosts/nodes use approved UTC/NTP/PTP strategy and monitor offset. | Chronology. |
| DEP-FR-034 | Certificate/DNS expiry | Monitor certificates/domains/dependencies before expiry. | Availability. |
| DEP-FR-035 | No single-node assumption | Production reference can scale beyond one host; on-prem compact profile explicitly documents reduced HA. | Commercial scalability. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| validateDeploymentPrerequisites() | Installer/CI | deployment profile; discovered infrastructure | Profile version approved | Checks versions/resources/storage/network/DNS/NTP/PKI/backup/ports | PrerequisiteReport | DEPLOYMENT_PREREQUISITE_FAILED |
| renderInfrastructurePlan() | IaC pipeline | customer/environment profile; versions; sizing | Inputs approved; modules pinned | Renders plan/manifests, no production apply yet | InfrastructurePlan | InfrastructurePlanGenerated |
| applyInfrastructurePlan() | Authorized deploy pipeline | signed plan/artifacts; environment | Change/release approved; credentials scoped | Applies IaC/manifests; records revisions/digests | DeploymentResult | InfrastructureApplied |
| runPostInstallQualificationChecks() | Installer/Validation | environment; check profile | Core services deployed | Tests identity, TLS, DB/object, NATS, Temporal, backups, clocks, network policies, version endpoints | InstallationCheckReport | InstallationChecksCompleted |
| performRollingUpgrade() | Release pipeline | current/new release; migration plan; rollout strategy | Backup/preflight/security gate passed | Runs migrations/deploys compatible versions/drains workers/smoke tests | UpgradeResult | PlatformUpgraded |
| detectInfrastructureDrift() | Scheduled/CI | declared IaC state; observed resources | Read permission | Compares relevant configuration, reports unauthorized drift | DriftReport | InfrastructureDriftDetected |
| scaleService() | Autoscaler/operator | service; target replicas/capacity trigger | Bounds/DB pool capacity policy | Adjusts stateless worker/API capacity; records operational change | ScaleResult | ServiceScaled |
| drainWorkerSafely() | Deployment lifecycle | worker instance; grace deadline | Worker healthy enough to drain | Stops new claims, finishes/releases leases, checkpoints and exits | DrainResult | WorkerDrained |


# 5. State / Runtime / Ownership Model

```text
SOURCE + SIGNED ARTIFACTS + IaC
          ↓
DEPLOYMENT PROFILE
  ├ AWS
  ├ Azure
  └ On-Prem/Private Cloud
          ↓
PRECHECK
          ↓
INFRA APPLY / INSTALL
          ↓
DB/OBJECT/NATS/TEMPORAL
          ↓
APP/API/WORKERS/FRAPPE
          ↓
POST-INSTALL SECURITY/GxP CHECKS
          ↓
READY

UPGRADE: PRECHECK → BACKUP → MIGRATE → ROLL → SMOKE → ACCEPT/ROLLBACK

```

# 6. Data / Configuration Model

## `deployment_profile`
- provider/environment/customer
- release versions
- region/site topology
- service sizing
- managed/self-hosted selections
- network/security profile
- storage classes
- backup/DR profile
- external endpoints
- certificate/secret profiles

## Reference namespaces/logical zones
```text
ingress
frappe
gxp
integration
edge-services (central components)
messaging
orchestration
observability
security
```

## On-prem compact profile

May co-locate selected services on fewer worker nodes for cost, but:
- authoritative DB/evidence remain protected;
- backups externalized;
- resource reservations documented;
- reduced HA explicitly accepted.


# 7. APIs / Internal Interfaces

- `CI/CD/IaC interfaces`
- `Deployment health/version endpoints`
- `Installer CLI`
- `Upgrade/rollback automation`

# 8. UI / Operations Screens

1. Deployment Inventory
2. Version Matrix
3. Install Preflight
4. Upgrade Dashboard
5. Drift
6. Capacity/Autoscaling
7. Post-Install Qualification

# 9. Events / Operational Signals

- `DeploymentPrerequisiteFailed`
- `InfrastructureApplied`
- `InstallationChecksCompleted`
- `InfrastructureDriftDetected`
- `PlatformUpgraded`
- `RollbackInitiated`
- `CertificateExpiryWarning`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/
services/platform/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/
packages/data-contracts/
validation/infrastructure/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/
tests/infrastructure/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/
docs/runbooks/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/
```

# 12. Mandatory Test Catalogue

- fresh cloud install
- air-gapped on-prem install
- NTP missing preflight
- PVC lost pod reschedule
- rolling API upgrade
- worker drains outbox
- DB migration backward compatibility
- failed smoke rollback
- IaC drift

# 13. Acceptance Criteria

A new customer environment can be created from documented IaC/profile and produce a repeatable installation-check report without hand-configuring hidden production dependencies.

# 14. Claude Code / Codex Prohibitions

- Never depend on Kubernetes PVC as backup.
- Never deploy unsigned/unversioned image.
- Never place production secrets in Helm values committed to Git.
- Never run destructive DB rollback because application image rolled back.


