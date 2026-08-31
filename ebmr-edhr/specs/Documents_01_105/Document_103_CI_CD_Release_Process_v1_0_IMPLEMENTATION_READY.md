# US eBMR / eDHR Regulated Manufacturing Platform
## Document 103 — CI/CD & Release Process — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ENG-007  
**Parent Documents:** Documents 01–96  
**Primary Dependencies:** Documents 61–96, 97–102, 104  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This document is a normative engineering-control source for Claude Code/Codex and human developers.

Every implementation must preserve:
- stable requirement IDs;
- explicit function input/output/error contracts;
- authorization/SoD/signature behavior;
- data owner and transaction boundaries;
- API/event schema and compatibility;
- validation/test evidence;
- security/dependency/license controls;
- actual rather than claimed CI/release evidence.

Where regulated behavior is not specified, create a `SPEC_GAP` and block the guess.

# Cross-Document Non-Negotiables

- Frappe/ERPNext core remains unmodified.
- GxP-authoritative writes flow through proprietary services/Mutation Gateway.
- No generic CRUD of released regulated records.
- No signature, authorization, audit, retention, data-owner or validation bypass.
- PostgreSQL is GxP authority; MariaDB/read models/cache/search/message/orchestration are not competing sources of truth.
- Transactional outbox/idempotent consumers are used where specified.
- Production release must match approved validated release authorization.
- AI remains advisory unless a future explicitly approved controlled specification authorizes a different risk class.

# 1. Objective

Define automated build, security/test gates, immutable packaging, release evidence, validated production authorization, deployment and rollback.

# 2. Actors / Components

- Developer
- CI System
- Release Engineer
- Security
- Validation/QA
- SRE
- Deployment Platform
- Claude Code/Codex

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| CICD-FR-001 | Pipeline as code | Build/test/release/deploy workflows version controlled and reviewed. | Reproducibility. |
| CICD-FR-002 | Trusted runners | Production signing/deploy jobs run on trusted hardened runners; untrusted PR code cannot access production secrets. | Supply-chain. |
| CICD-FR-003 | Lockfile builds | Dependencies installed from locked/pinned sources; unexpected lock change visible. | Reproducibility. |
| CICD-FR-004 | Build once | Release artifact built once, immutable, promoted across environments by digest rather than rebuilt. | Artifact identity. |
| CICD-FR-005 | Source provenance | Artifact links source commit, workflow version, builder, dependencies/SBOM and test evidence. | Traceability. |
| CICD-FR-006 | Lint/type gate | Coding/type/architecture checks mandatory. | Quality. |
| CICD-FR-007 | Test gate | Risk-derived required engineering test suites must pass/approved exception. | Quality. |
| CICD-FR-008 | Secret scan | Secret/private-key/token scanning before merge/release. | Security. |
| CICD-FR-009 | SAST | Static security analysis with policy thresholds and reviewed suppressions. | Security. |
| CICD-FR-010 | SCA | Dependency vulnerability/license scan linked Document104. | Supply chain. |
| CICD-FR-011 | IaC scan | Infrastructure/config manifests checked for security/misconfiguration. | Infrastructure. |
| CICD-FR-012 | Container scan | Image/base/package scan after build. | Runtime security. |
| CICD-FR-013 | SBOM | Release SBOM generated and stored with artifact. | Inventory. |
| CICD-FR-014 | Artifact signing | Approved artifact/images/attestations signed after release gates. | Provenance. |
| CICD-FR-015 | Contract gate | OpenAPI/AsyncAPI compatibility tests block unplanned breaking change. | Integration. |
| CICD-FR-016 | Migration gate | Migrations static-analyzed, dry-run/reconciled against supported previous versions. | Upgrade safety. |
| CICD-FR-017 | Validation impact gate | Changed higher-risk requirements/functions produce validation/change impact before production authorization. | Validated state. |
| CICD-FR-018 | Release candidate | Candidate freezes exact source/artifact/contracts/migrations/config baseline. | Controlled release. |
| CICD-FR-019 | Release notes | Generated/reviewed notes include features, fixes, migrations, compatibility, security/known limitations, validation impact. | Customer readiness. |
| CICD-FR-020 | Approval | Release approval roles distinct from author where policy requires. | SoD. |
| CICD-FR-021 | Validated release authorization | Regulated production deploy requires Document95 authorization matching artifact/config fingerprint. | Compliance gate. |
| CICD-FR-022 | Environment promotion | Same artifact digest promoted dev/test/validation/staging/prod; environment config externalized. | Consistency. |
| CICD-FR-023 | Predeploy check | Backup/PITR, migration readiness, capacity, secrets/certs, dependency health and change window checked. | Safe deployment. |
| CICD-FR-024 | Deployment strategy | Rolling/canary/blue-green selected by service risk; migrations remain compatible. | Availability. |
| CICD-FR-025 | Smoke checks | Postdeploy health/auth/db/object/NATS/Temporal/GxP smoke checks required. | Safe rollout. |
| CICD-FR-026 | Rollback | Rollback uses signed prior artifact and compatibility plan; DB state handled separately. | Recovery. |
| CICD-FR-027 | Automatic abort | Critical smoke/integrity/security/migration failure stops rollout. | Fail closed. |
| CICD-FR-028 | Hotfix process | Expedited path keeps security/test/validation/approval evidence appropriate to risk. | Emergency control. |
| CICD-FR-029 | Release manifest | One immutable manifest contains artifact digests, source, SBOM, contracts, migrations, tests, scans, validation authorization. | Due diligence. |
| CICD-FR-030 | Evidence retention | CI/release evidence retained according to product/validation policy, not ephemeral CI logs only. | Inspection. |
| CICD-FR-031 | Deploy identity | Deployment records actor/service identity, environment, versions, start/end and outcome. | Attribution. |
| CICD-FR-032 | No manual drift | Manual production config/manifest changes detected and reconciled through IaC/change control. | Validated state. |
| CICD-FR-033 | Feature flags | GxP flags promoted as validated configuration; ordinary safe flags still inventoried. | Configuration. |
| CICD-FR-034 | Artifact verification | Cluster/admission/deployer verifies digest/signature/approved release before start. | Supply-chain. |
| CICD-FR-035 | Environment protections | Production workflow requires protected environment approvals/secrets. | Access control. |
| CICD-FR-036 | Release reproducibility | Given source/lock/toolchain, organization can regenerate equivalent artifact or explain nondeterminism. | Assurance. |

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB or artifact effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createReleaseCandidate() | Release pipeline | source commit; version; contract/migration/config refs | Main protected and required CI checks current | Freezes candidate metadata and artifact build inputs | ReleaseCandidate | ReleaseCandidateCreated |
| buildReleaseArtifact() | Trusted CI | release candidate; toolchain image | Dependencies locked; source clean | Builds containers/packages once and records digests/provenance | ReleaseArtifactSet | ReleaseArtifactsBuilt |
| runReleaseSecurityGates() | Trusted CI | artifacts; SBOM; source | Artifact immutable | Runs SAST/SCA/secret/IaC/container/provenance policy checks | ReleaseSecurityReport | ReleaseSecurityGatesCompleted |
| runMigrationCompatibilityMatrix() | CI | candidate migrations; supported source versions; representative snapshots | Migration plans present | Dry-runs upgrades and app/schema compatibility/reconciliation | MigrationMatrixReport | MigrationCompatibilityCompleted |
| assembleReleaseEvidenceManifest() | Release tooling | CI runs; SBOM; contracts; migrations; validation auth | Required evidence available | Creates canonical immutable release manifest/hash | ReleaseEvidenceManifest | ReleaseEvidenceManifestCreated |
| authorizeProductionPromotion() | Deployment gate | manifest; validated release authorization; target environment/config fingerprint | Approvals current | Verifies exact artifact/config and opens deployment | PromotionAuthorization | ProductionPromotionAuthorized |
| deployRelease() | Deployment system | authorization; artifact digests; strategy | Target prechecks pass | Deploys immutable artifact, records rollout status and smoke checks | DeploymentReceipt | ReleaseDeploymentStarted/Completed |
| executeControlledRollback() | Release/SRE | failed deployment; prior approved release; compatibility decision | Rollback authorized and DB compatibility understood | Promotes prior artifact or forward fix plan, preserving migration evidence | RollbackReceipt | ReleaseRollbackExecuted |
| generateReleaseNotes() | Release tooling | requirements/issues/contracts/migrations/security/validation changes | Candidate frozen | Builds reviewable customer/internal notes | ReleaseNotes | ReleaseNotesGenerated |

# 5. Reference Pipeline

```text
PR
 ↓
format/lint/type/architecture
 ↓
unit/property/API/contract/integration tests
 ↓
secret + SAST + SCA/license + IaC checks
 ↓
merge protected main
 ↓
RELEASE CANDIDATE
 ↓
build ONCE → artifact digests
 ↓
SBOM + container scan + provenance
 ↓
migration compatibility matrix
 ↓
security/performance/validation gates as required
 ↓
release evidence manifest
 ↓
human/Quality release authorization
 ↓
promote exact artifact by digest
 ↓
post-deploy verification
```


# 6. Release Manifest Schema

```yaml
release:
source_commit:
release_tag:
artifacts:
sbom_ref:
provenance_ref:
contract_catalogue_ref:
migration_manifest_ref:
test_run_refs: []
security_scan_refs: []
validation_summary_ref:
validated_release_authorization_ref:
known_limitations: []
```


# 7. Hotfix Rules

A hotfix may shorten scheduling but not erase:
- source/PR;
- code/security scans;
- targeted test evidence;
- migration analysis if schema affected;
- validation/change impact;
- release manifest;
- authorized promotion;
- forward merge into main.

# 8. Rollback Decision Matrix

Rollback may be safe when:
- application artifact changes only and schema backward compatible;
- previous artifact remains supported and signed.

Rollback is not automatically safe when:
- destructive/contracted schema migration ran;
- data transform semantics changed;
- external side effects occurred;
- event/API version consumers already changed.

In those cases use forward fix or documented recovery plan.

# 9. Mandatory Test / Enforcement Catalogue

- untrusted PR cannot read prod secret
- build artifact promoted without rebuild
- breaking contract blocks
- migration previous-version dry run
- validated authorization mismatch blocks prod
- smoke fail aborts
- rollback after compatible schema
- hotfix retains evidence

# 10. Acceptance Criteria

Every production deployment can be reconstructed from source commit through tests, scans, SBOM, migration/contract evidence, validation authorization and exact signed artifact digest.

# 11. Claude Code / Codex Prohibitions

- Never rebuild artifact separately for production.
- Never deploy from developer workstation.
- Never bypass validation authorization with CI administrator permission.
- Never roll back application without assessing database/data compatibility.
