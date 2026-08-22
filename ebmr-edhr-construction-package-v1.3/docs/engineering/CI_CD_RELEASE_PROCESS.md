# CI/CD & Release Process

**Derived from:** Document 103 (SPEC-ENG-007) — controlled source in `specs/`
**Purpose:** Pipeline, gates and release authorization.
**Requirements:** CICD-FR-001..036 (36)

> This file is the working engineering standard. The controlled source is Document 103; where the two
> differ, the specification wins and this file is corrected.

## Requirements

| ID | Requirement | Required behaviour | Acceptance intent |
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

## Enforcement

See `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`,
`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md` and `.github/workflows/ci.yml`.

## Tests

- untrusted PR cannot read prod secret
- build artifact promoted without rebuild
- breaking contract blocks
- migration previous-version dry run
- validated authorization mismatch blocks prod
- smoke fail aborts
- rollback after compatible schema
- hotfix retains evidence
