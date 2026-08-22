# 35 — Repository Ownership & Release Map

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Ownership, branch protection, mandatory checks and release artefacts per component (Document 99/103).

---

| Component | Path | Business owner | Code owner | Security/QA owner | Branch protection | Mandatory checks | Release artefact | Versioning |
|---|---|---|---|---|---|---|---|---|
| GxP Core API | services/gxp-api | Product Owner | GxP Core Lead | Security Officer + Validation Lead | protected main, 2 reviews, no force push | lint, typecheck, unit, contract, guardrail, migration, security | signed container image | semver + release tag |
| Temporal workers | services/workers | Product Owner | GxP Core Lead | Validation Lead | protected main | unit, integration, workflow replay | signed container image | semver |
| Platform services | services/platform | Product Owner | SRE Lead | Security Officer | protected main | unit, integration, SLO checks | signed container image | semver |
| Security services | services/security | Security Officer | Security Lead | Security Officer | protected main, security review required | SAST, secrets, unit, integration | signed container image | semver |
| Integration gateway | services/integration-gateway | Integration Owner | Integration Lead | Security Officer | protected main | contract, adapter, reconciliation tests | signed container image | semver |
| AI gateway | services/ai-gateway | Product Owner | AI Lead | Head of Quality + Security Officer | protected main, governance review | eval set, security tests, authority-boundary tests | signed container image | semver |
| Frappe app | apps/ebmr_frappe | Product Owner | Application Lead | Validation Lead | protected main | lint, unit, projection tests, no-core-edit guardrail | versioned app package | semver |
| Edge | edge | OT Owner | Edge Lead | Security Officer | protected main | driver, buffering, replay, security tests | signed edge bundle | semver |
| Contracts | contracts | Platform Architect | Contract Owner | Validation Lead | protected, contract review required | schema lint, compatibility check | published schema package | schema_version |
| Infrastructure | infrastructure | SRE Lead | SRE Lead | Security Officer | protected main | IaC scan, policy check, plan review | IaC release | semver |
| Validation | validation | Validation Lead | Validation Lead | Head of Quality | protected, QA review required | evidence integrity check | validation package | release-bound |
| Specs | specs | Specification Owner | Specification Owner | Head of Quality | read-only to agents; change control required | uniqueness + conformance checks | controlled baseline | document version |

## Branching (Document 99)
- `main` is always releasable and protected.
- Short-lived `feat/WP-XX-*` branches; squash merge with the work-package reference.
- Release branches `release/x.y` for supported validated versions.
- Hotfix `hotfix/x.y.z` from the release branch with the same gates and a validation impact record.
- No direct commits to `main` or a release branch.
