# 32 — Validation Evidence Index

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Where each class of objective evidence lives and how it is protected.

---

| Evidence class | Produced by | Location | Immutability | Retention |
|---|---|---|---|---|
| Requirement traceability | Phase-0 + each WP | `docs/generated/29_VALIDATION_TRACEABILITY_MASTER.csv` | versioned in git | RC-VALIDATION |
| Engineering test results | CI | `validation/evidence/engineering/<release>` | signed CI artefact | RC-VALIDATION |
| IQ evidence | Deployment | `validation/evidence/iq/<environment>` | immutable object store | RC-VALIDATION |
| OQ evidence | Qualification execution | `validation/evidence/oq/<release>` | immutable, failures retained | RC-VALIDATION |
| PQ/UAT evidence | Customer execution | `validation/evidence/pq/<customer>/<release>` | immutable | RC-VALIDATION |
| Part 11 evidence | Doc 88 protocols | `validation/evidence/part11/<release>` | immutable | RC-VALIDATION |
| Security qualification | Doc 92 | `validation/security/<release>` | immutable | RC-SECURITY + RC-VALIDATION |
| DR/restore drills | Doc 91 | `validation/evidence/dr/<date>` | immutable | RC-VALIDATION |
| Performance qualification | Doc 93 | `validation/evidence/performance/<release>` | immutable | RC-VALIDATION |
| Migration/cutover | Doc 87 | `validation/evidence/migration/<cutover>` | immutable + reconciliation | RC-VALIDATION |
| Validation exceptions | Doc 94 | `validation/evidence/exceptions` | immutable, never edited to pass | RC-VALIDATION |
| VSR & release authorization | Doc 95 | `validation/evidence/vsr/<release>` | signed | RC-VALIDATION |
| SBOM & signatures | CI (Doc 104) | release artefact registry | signed, hash-verified | RC-VALIDATION |

**Rule:** a failed test execution is evidence. It is never deleted, re-run over, or edited into a pass.
