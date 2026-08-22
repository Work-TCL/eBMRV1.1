# Document Patch List

**Status:** Proposed patches to the controlled baseline / Ready for Review
**Source of decisions:** Document 115 (SG-001, SG-002, SG-003, SG-020)

Each patch is an exact, reviewable edit to an existing controlled document. Apply through the normal
document change control process; do not edit specifications in place without a change record.

| # | Document | Change type | Find | Replace | Scope | Closes |
|---|---|---|---|---|---|---|
| P-01 | Document 91 | Requirement re-namespace | `DRV-FR-` | `DRQ-FR-` | whole document + cross references | SG-001 |
| P-02 | Document 104 | Requirement re-namespace | `DEP-FR-` | `DPM-FR-` | whole document + cross references | SG-002 |
| P-03 | Document 69 | Event ownership note | `` `ProjectionStaleDetected` `` | `` `ProjectionStaleDetected` — contract owned by Document 78 `` | events section | SG-003 |
| P-04 | Document 71 | Event ownership note | `` `ProjectionStaleDetected` `` | `` `ProjectionStaleDetected` — contract owned by Document 78 `` | events section | SG-003 |
| P-05 | Document 73 | Event ownership note | `` `OutboxLagExceeded` `` | `` `OutboxLagExceeded` — contract owned by Document 78 `` | events section | SG-003 |
| P-06 | Document 75 | Event ownership note | `` `ProjectionLagExceeded` `` | `` `ProjectionLagExceeded` — contract owned by Document 78 `` | events section | SG-003 |
| P-07 | Document 05 | Section addition | — | new `# Acceptance Gate` section (text in Document 115 §5) | before the regulatory basis section | SG-020 |

## Cross-reference updates required after P-01 and P-02

| Artefact | Update |
|---|---|
| `docs/generated/01_REQUIREMENT_REGISTRY.csv` | regenerate |
| `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` | regenerate |
| `docs/generated/29_VALIDATION_TRACEABILITY_MASTER.csv` | regenerate |
| Documents 76, 86 | check any `DRV-FR` reference intended for Document 91 |
| Documents 68, 103 | check any `DEP-FR` reference intended for Document 104 |

## Alias table (retain for one revision)

| Old identifier | Document | New identifier |
|---|---|---|
| DRV-FR-001 | 91 | DRQ-FR-001 |
| DRV-FR-002 | 91 | DRQ-FR-002 |
| DRV-FR-003 | 91 | DRQ-FR-003 |
| DRV-FR-004 | 91 | DRQ-FR-004 |
| DRV-FR-005 | 91 | DRQ-FR-005 |
| DRV-FR-006 | 91 | DRQ-FR-006 |
| DRV-FR-007 | 91 | DRQ-FR-007 |
| DRV-FR-008 | 91 | DRQ-FR-008 |
| DRV-FR-009 | 91 | DRQ-FR-009 |
| DRV-FR-010 | 91 | DRQ-FR-010 |
| DRV-FR-011 | 91 | DRQ-FR-011 |
| DRV-FR-012 | 91 | DRQ-FR-012 |
| DRV-FR-013 | 91 | DRQ-FR-013 |
| DRV-FR-014 | 91 | DRQ-FR-014 |
| DRV-FR-015 | 91 | DRQ-FR-015 |
| DRV-FR-016 | 91 | DRQ-FR-016 |
| DRV-FR-017 | 91 | DRQ-FR-017 |
| DRV-FR-018 | 91 | DRQ-FR-018 |
| DRV-FR-019 | 91 | DRQ-FR-019 |
| DRV-FR-020 | 91 | DRQ-FR-020 |
| DRV-FR-021 | 91 | DRQ-FR-021 |
| DRV-FR-022 | 91 | DRQ-FR-022 |
| DEP-FR-001 | 104 | DPM-FR-001 |
| DEP-FR-002 | 104 | DPM-FR-002 |
| DEP-FR-003 | 104 | DPM-FR-003 |
| DEP-FR-004 | 104 | DPM-FR-004 |
| DEP-FR-005 | 104 | DPM-FR-005 |
| DEP-FR-006 | 104 | DPM-FR-006 |
| DEP-FR-007 | 104 | DPM-FR-007 |
| DEP-FR-008 | 104 | DPM-FR-008 |
| DEP-FR-009 | 104 | DPM-FR-009 |
| DEP-FR-010 | 104 | DPM-FR-010 |
| DEP-FR-011 | 104 | DPM-FR-011 |
| DEP-FR-012 | 104 | DPM-FR-012 |
| DEP-FR-013 | 104 | DPM-FR-013 |
| DEP-FR-014 | 104 | DPM-FR-014 |
| DEP-FR-015 | 104 | DPM-FR-015 |
| DEP-FR-016 | 104 | DPM-FR-016 |
| DEP-FR-017 | 104 | DPM-FR-017 |
| DEP-FR-018 | 104 | DPM-FR-018 |
| DEP-FR-019 | 104 | DPM-FR-019 |
| DEP-FR-020 | 104 | DPM-FR-020 |
| DEP-FR-021 | 104 | DPM-FR-021 |
| DEP-FR-022 | 104 | DPM-FR-022 |
| DEP-FR-023 | 104 | DPM-FR-023 |
| DEP-FR-024 | 104 | DPM-FR-024 |
| DEP-FR-025 | 104 | DPM-FR-025 |
| DEP-FR-026 | 104 | DPM-FR-026 |
| DEP-FR-027 | 104 | DPM-FR-027 |
| DEP-FR-028 | 104 | DPM-FR-028 |
| DEP-FR-029 | 104 | DPM-FR-029 |
| DEP-FR-030 | 104 | DPM-FR-030 |
| DEP-FR-031 | 104 | DPM-FR-031 |
| DEP-FR-032 | 104 | DPM-FR-032 |
| DEP-FR-033 | 104 | DPM-FR-033 |
| DEP-FR-034 | 104 | DPM-FR-034 |
| DEP-FR-035 | 104 | DPM-FR-035 |
