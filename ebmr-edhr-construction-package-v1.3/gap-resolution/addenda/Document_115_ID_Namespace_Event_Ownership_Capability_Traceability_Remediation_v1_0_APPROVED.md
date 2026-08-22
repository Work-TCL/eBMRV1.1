# US eBMR / eDHR Regulated Manufacturing Platform
## Document 115 — Requirement ID Namespace, Event Ownership, Capability Traceability & Document Patches — v1.0 APPROVED

**Specification ID:** SPEC-ENG-011
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Specification Owner and Platform Architect
**Closes:** SG-001, SG-002, SG-003, SG-019, SG-020
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Documents 44, 91, 77, 104, 69, 71, 73, 75, 78, 05, 01, 81, 101

---

# 0. Scope

This document resolves defects in the existing baseline. Unlike Documents 106–114, which add missing decisions, this document **patches controlled documents**. Each patch is stated as an exact, reviewable edit.

# 1. SG-001 — `DRV-FR` namespace collision (Documents 44 and 91)

**Finding.** 22 identifiers (DRV-FR-001–DRV-FR-022) are used by both Document 44 (Industrial Device & Protocol Connectivity / Drivers) and Document 91 (Backup, Restore, PITR & DR Qualification).

**Decision (proposed).** Document 44 retains `DRV-FR` (driver is the natural referent). Document 91 is re-namespaced to **`DRQ-FR`** (Disaster Recovery Qualification).

**Patch — Document 91:**
```text
FIND    : DRV-FR-
REPLACE : DRQ-FR-
SCOPE   : whole document, including the functional requirement table, test catalogue and any cross references
```
**Downstream updates:** requirement registry, validation traceability master, test traceability matrix, and any Document 76/86/91 cross reference. A permanent alias table (`DRV-FR-nnn@Doc91 → DRQ-FR-nnn`) is retained for one revision so earlier reviews remain resolvable.

# 2. SG-002 — `DEP-FR` namespace collision (Documents 77 and 104)

**Finding.** 35 identifiers (DEP-FR-001–DEP-FR-035) are used by both Document 77 (Cloud-Neutral Deployment/Kubernetes) and Document 104 (SBOM / Third-Party License Management).

**Decision (proposed).** Document 77 retains `DEP-FR` (deployment). Document 104 is re-namespaced to **`DPM-FR`** (Dependency Management).

**Patch — Document 104:**
```text
FIND    : DEP-FR-
REPLACE : DPM-FR-
SCOPE   : whole document and cross references
```
**Downstream updates:** SBOM/licence register, CI release evidence model, Document 68 cross references, requirement and test traceability.

# 3. SG-003 — Event producer ambiguity

**Decision (proposed).** Operational-signal events are owned by the observability specification (Document 78). Detecting components emit their condition through the owning event; they do not declare their own duplicate type.

| Event | Declared in | Proposed single producer | Action for the other documents |
|---|---|---|---|
| `ProjectionStaleDetected` | Docs 69, 71 | **Document 78** (observability) | Docs 69/71 reference the Document 78 event; remove the local declaration |
| `OutboxLagExceeded` | Docs 73, 78 | **Document 78** | Doc 73 references it as a consumer/emitter of the Document 78 contract |
| `ProjectionLagExceeded` | Docs 75, 78 | **Document 78** | Doc 75 references it |

**Patch pattern (Documents 69, 71, 73, 75):**
```text
FIND    : - `<EventName>`
REPLACE : - `<EventName>` — contract owned by Document 78 (SPEC-DATA-010); emitted through the platform observability event contract
```

# 4. SG-019 — Document 01 capability traceability

**Finding.** Document 01 defines capability identifiers (C-* (69), CP-* (20), MAT-* (22), MD-* (25), PH-* (30), PM-* (10), QMS-* (18), SPEC-SEC-* (1), ST-* (20)) totalling 215 rows. Sampling shows most appear only inside Document 01, so the highest-precedence document has no forward trace into the implementing specifications.

**Decision (proposed).** Document 01 is **not** re-written (it is frozen). Instead a **capability coverage matrix** is created as a Phase-0 artefact:

```text
docs/generated/42_CAPABILITY_COVERAGE_MATRIX.csv
columns: capability_id, capability_name, source_section, implementing_document(s),
         implementing_requirement_ids, work_package, coverage_state, gap_reference
coverage_state ∈ COVERED | PARTIAL | NOT_COVERED | NOT_APPLICABLE_V1
```

Every `NOT_COVERED` row is either an implementation scope decision (recorded) or a new SPEC_GAP. The matrix is a Document 81 traceability input and a Document 95 VSR input.

# 5. SG-020 — Document 05 acceptance criteria

**Finding.** Document 05 (Immutable Audit Ledger) is the only module specification without an acceptance-criteria section, while being one of the highest-risk modules.

**Patch — Document 05, new section appended before the regulatory basis:**
```text
# Acceptance Gate

This specification is build-ready only when:
- audit events are written in the same transaction as every regulated state change, proven by failure injection;
- no application path can UPDATE or DELETE an audit event, proven by privilege-level negative tests;
- per-record-stream hash chaining and periodic signed checkpoints verify end to end;
- tamper attempts (row edit, out-of-order insert, checkpoint replay) are detected and alerted;
- audit review by exception returns complete, reproducible results for a defined record set;
- audit retention inherits the parent record class (Document 108) with no orphan retention;
- inspection export reproduces actor, UTC time, action, old/new values, reason, signature and rule/software versions.
```

# 6. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| REM-FR-001 | Unique requirement IDs | No requirement identifier resolves to more than one requirement across the baseline. | Automated uniqueness check passes. |
| REM-FR-002 | Alias retention | Re-namespaced identifiers keep a documented alias for one revision. | Historic review resolvable. |
| REM-FR-003 | Single event producer | Every event type has exactly one producing document and module. | Registry constraint enforced in CI. |
| REM-FR-004 | Capability coverage | Every Document 01 capability has a coverage state and, where covered, implementing requirement IDs. | Matrix complete. |
| REM-FR-005 | Acceptance completeness | Every module specification has an acceptance section. | Conformance check passes. |
| REM-FR-006 | Automated conformance | The uniqueness, single-producer and acceptance checks run in CI against `specs/`. | Regression prevented. |

# 7. Acceptance criteria

1. Uniqueness check reports zero colliding requirement identifiers.
2. Event registry reports exactly one producer per event type.
3. Capability coverage matrix generated with no unexplained `NOT_COVERED` rows.
4. Document 05 acceptance section present.
5. All checks run automatically in CI.

# 8. Claude Code / Codex prohibitions

- Do not silently renumber requirements in any other document.
- Do not resolve a collision by deleting one of the two requirement sets.
- Do not create a second producer for an existing event type.
- Do not mark a capability COVERED without implementing requirement IDs.

# 9. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Specification Owner |  |  |  |  |
| Platform Architect |  |  |  |  |
