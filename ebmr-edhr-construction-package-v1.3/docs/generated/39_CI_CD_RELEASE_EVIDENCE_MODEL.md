# 39 — CI/CD & Release Evidence Model

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Pipeline stages, gates and evidence produced at each step (Document 103/68/104/95).

---

```text
PR
 ├ lint / typecheck / unit
 ├ contract schema lint + compatibility check
 ├ architecture guardrail checks (34_ARCHITECTURE_GUARDRAIL_MATRIX.md)
 ├ migration safety check
 ├ SAST / secret scan / dependency (SCA) / licence check
 ├ requirement-ID uniqueness + single-producer checks (Doc 115)
 └ traceability update check (requirement ↔ test)
merge to main
 ├ integration + E2E
 ├ container build (build once)
 ├ SBOM generation
 ├ IaC + container scan
 └ artefact signing
release candidate
 ├ full engineering test suite
 ├ performance smoke against SLO classes
 ├ migration matrix execution on a restored copy
 ├ validation impact assessment
 └ release manifest (artefact hashes, SBOM, contracts, migrations, requirements)
validated release authorization (Doc 95)
 ├ qualification evidence complete (IQ/OQ/PQ as applicable)
 ├ open validation exceptions assessed (Doc 94)
 └ signed authorization
deployment
 ├ environment fingerprint verification
 ├ post-deployment checks
 └ rollback plan verified
```

| Gate | Blocking condition | Evidence produced |
|---|---|---|
| PR gate | any lint/type/unit/guardrail/contract failure | CI run record + logs |
| Security gate | critical SAST/SCA/secret/IaC finding | scan reports |
| Licence gate | unknown or prohibited licence (Doc 104) | SBOM + licence report |
| Migration gate | unsafe lock or missing rollback | migration plan + dry-run result |
| Contract gate | breaking change without version bump | compatibility diff |
| Traceability gate | requirement without a test or test without a requirement | traceability delta |
| Release gate | missing qualification evidence or unresolved blocking exception | release manifest |
| Deployment gate | fingerprint mismatch with the authorized release | deployment record |

**Rule:** production cannot deploy an unvalidated or fingerprint-mismatched regulated configuration. Never fabricate a test run, scan result or validation record.
