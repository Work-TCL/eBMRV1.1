# US eBMR / eDHR Regulated Manufacturing Platform
## Document 108 — Record Retention, Archival, Legal Hold & Disposal Baseline — v1.0 APPROVED

**Specification ID:** SPEC-DATA-011
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Head of Quality, Regulatory Affairs and Legal
**Closes:** SG-005
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Document 06 (Vault, VLT-FR-019/021/022), Document 72 (evidence/WORM), Document 60 (PMO-FR-025..028), Document 05 (audit), Document 69 (data ownership), Document 76 (backup/DR)

---

# 0. Why this document exists

Document 06 requires every vault object to carry a **retention class**. Document 60 requires the **longest applicable** retention for combination-product postmarket records, prohibits retrospective shortening and requires legal hold. No document assigns concrete durations, trigger events or disposal authority. Retention cannot be guessed: early destruction of a regulated record is irreversible, and over-retention of postmarket patient data creates privacy exposure.

# 1. Objective and non-goals

**Objective.** Define retention classes, their trigger events and duration rules, the legal-hold model, the archival tiering rules and the controlled disposal process.

**Non-goals.** This document does not set a single global number. Durations are rule-based and depend on product profile, market and record class. It does not replace the customer's records-management procedure; it provides the engine and a defensible default.

# 2. Principles

| # | Principle |
|---|---|
| R1 | Retention is computed from a **trigger event + rule**, never from record creation date alone. |
| R2 | Where several regimes apply to one record, the **longest** applicable retention wins (Document 60 PMO-FR-025). |
| R3 | A later rule change can **extend** retention; it can never retrospectively shorten it (PMO-FR-027). |
| R4 | Nothing is ever purged automatically. Disposal requires an authorized, signed disposal decision. |
| R5 | Legal or regulatory hold suspends every disposal path and is itself an audited, signed action. |
| R6 | Audit trails and signatures inherit the retention of the record they describe (§11.10(e)). |
| R7 | Archival may change storage tier only if integrity, retrievability and meaning are preserved (VLT-FR-021). |
| R8 | Personal data in postmarket records is minimised and pseudonymised once reporting obligations end (PMS-FR-029). |

# 3. Retention classes (PROPOSED defaults)

Durations below are the **platform defaults**; each is configurable per tenant and per product profile, and each cites the predicate-rule basis that motivated it. The customer's Quality and Regulatory functions remain responsible for confirming the applicable regime for their products and markets.

| Class | Applies to | Trigger event | Default duration | Predicate-rule basis |
|---|---|---|---|---|
| RC-BATCH-DRUG | Batch/production and control records for drug products | Batch expiration date | expiry + 1 year | 21 CFR §211.180(a) |
| RC-BATCH-DRUG-NOEXP | OTC drug products without expiration dating | Distribution date | distribution + 3 years | 21 CFR §211.180(a) |
| RC-DHR-DEVICE | Device history records, device master record snapshots | Release for commercial distribution | expected device life, minimum 2 years | 21 CFR §820.180(b) / QMSR |
| RC-DDCP | Combination-product records containing both constituents | Latest applicable trigger among constituent rules | max(RC-BATCH-DRUG, RC-DHR-DEVICE) | 21 CFR Part 4 longest-applicable principle |
| RC-COMPLAINT | Complaint files | Complaint closure | aligned to RC-DHR-DEVICE for the device involved | §820.198 with §820.180(b) retention |
| RC-MDR | Medical device report event files | Date of the event | 2 years or expected device life, whichever is greater | 21 CFR §803.18 |
| RC-806 | Correction/removal records (reportable and §806.20 non-reportable) | Record creation | expected device life + 2 years | 21 CFR §806.20 |
| RC-AEMS | Drug/biologic adverse experience records | Report submission | per applicable postmarket reporting regime; default aligned to RC-BATCH-DRUG | Part 314/600 postmarket reporting |
| RC-QMS | Deviation, CAPA, NC, change, SCAR, risk, audit records | Record closure | longest retention of any record it impacts, minimum 6 years | quality-system recordkeeping expectations |
| RC-TRAINING | Training and qualification records | Employment end or record supersession | longest batch retention the person contributed to | §211.25 / §820.25 |
| RC-EQUIPMENT | Calibration, qualification, maintenance, cleaning records | Equipment retirement | equipment life + longest batch retention it touched | §211.67/§211.68 |
| RC-VALIDATION | Validation protocols, evidence, VSR, qualification records | System retirement | system life + 5 years | CSA/validated-state maintenance (Doc 96) |
| RC-AUDITTRAIL | Audit events, signature records, record versions | Parent record's disposal eligibility | equal to the parent record class | 21 CFR §11.10(e) |
| RC-SECURITY | Security logs, access reviews, incident records | Event date | 1 year online + 6 years archive (configurable) | Document 67 policy; customer security programme |
| RC-PII-PM | Patient/reporter identifiers inside postmarket records | End of applicable reporting obligation | pseudonymise; retain minimum necessary linkage | PMS-FR-029 minimum-necessary |

# 4. Data model

## `retention_class`
```text
id uuid PK, tenant_id uuid, code varchar(40) NOT NULL, description text,
trigger_event varchar(80) NOT NULL, duration_rule jsonb NOT NULL,
predicate_basis text NOT NULL, longest_applicable boolean NOT NULL DEFAULT true,
policy_source varchar(30) NOT NULL, effective_from timestamptz, effective_to timestamptz,
version bigint NOT NULL
```

## `record_retention_assignment`
```text
id uuid PK, tenant_id uuid, record_class varchar(80), record_id uuid, record_version bigint,
retention_class_code varchar(40) NOT NULL, applicable_regimes jsonb NOT NULL,
trigger_event_at timestamptz NULL, computed_disposal_eligible_at timestamptz NULL,
selected_rule varchar(80) NOT NULL, rule_version bigint NOT NULL,
state varchar(30) NOT NULL,   -- ACTIVE | HOLD | DISPOSAL_ELIGIBLE | DISPOSAL_APPROVED | DISPOSED
version bigint NOT NULL
```
Indexes: `(tenant_id, state, computed_disposal_eligible_at)`, `(record_class, record_id)`.

## `legal_hold`
```text
id uuid PK, tenant_id uuid, hold_reference varchar(120) NOT NULL, reason text NOT NULL,
scope jsonb NOT NULL,           -- product/lot/site/date-range/record-class selectors
requested_by uuid, approved_by uuid, approval_signature_id uuid,
placed_at timestamptz, released_at timestamptz NULL, released_signature_id uuid NULL,
state varchar(20) NOT NULL, version bigint NOT NULL
```

## `disposal_decision`
```text
id uuid PK, tenant_id uuid, scope jsonb NOT NULL, record_count integer NOT NULL,
manifest_digest varchar(128) NOT NULL,     -- immutable list of what is being disposed
approved_by uuid, approval_signature_id uuid, executed_at timestamptz NULL,
execution_evidence_id uuid NULL, state varchar(30) NOT NULL, version bigint NOT NULL
```

# 5. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| RET-FR-001 | Class assignment at creation | Every regulated record and vault object receives a retention class at creation; unassigned is impossible. | Negative test: creation without class fails. |
| RET-FR-002 | Multi-regime evaluation | All applicable regimes are stored; the longest is selected and the selection is recorded. | Selection reproducible. |
| RET-FR-003 | Trigger capture | Trigger events (expiry, distribution, closure, retirement, event date) are captured when they occur and recompute eligibility. | Eligibility recalculated and audited. |
| RET-FR-004 | No retrospective shortening | A rule change may only extend the disposal-eligible date of existing records. | Negative test passes. |
| RET-FR-005 | No automatic purge | Disposal requires an approved, signed disposal decision with an immutable manifest. | No scheduled delete job exists. |
| RET-FR-006 | Legal hold | An authorized hold suspends disposal for its scope and cannot be bypassed by any application path. | Held record cannot be disposed. |
| RET-FR-007 | Hold release | Hold release is a separate signed action preserving the original hold evidence. | History preserved. |
| RET-FR-008 | Audit/signature inheritance | Audit events, signatures and record versions inherit the parent record's class. | Orphan retention impossible. |
| RET-FR-009 | Archival integrity | Tier migration preserves digest, manifest, retrievability and rendering; verified after migration. | Post-migration verification evidence. |
| RET-FR-010 | WORM/retention lock | Where the deployment supports object-lock, evidence objects are written with a retention lock at least equal to the computed period. | Lock verified. |
| RET-FR-011 | Privacy minimisation | Postmarket personal identifiers are pseudonymised once obligations end while preserving case linkage. | Privacy test passes. |
| RET-FR-012 | Disposal evidence | Disposal execution produces immutable evidence (manifest digest, approver, time, counts) retained beyond the disposed records. | Inspection can prove lawful disposal. |
| RET-FR-013 | Restore consistency | Restore from backup re-applies retention state and holds; a restore cannot resurrect a lawfully disposed record. | Restore test passes. |
| RET-FR-014 | Reporting | Retention dashboard shows records by class, eligibility, holds and pending disposal decisions. | Reproducible report. |

# 6. Stable error codes

`RETENTION_CLASS_REQUIRED`, `RETENTION_RULE_UNRESOLVED`, `RETENTION_SHORTENING_PROHIBITED`,
`LEGAL_HOLD_ACTIVE`, `DISPOSAL_NOT_APPROVED`, `DISPOSAL_MANIFEST_MISMATCH`, `ARCHIVE_INTEGRITY_FAILED`,
`WORM_LOCK_UNAVAILABLE`.

# 7. Test catalogue

1. Every retention class: trigger occurs → eligibility computed correctly.
2. Multi-regime record (DDCP) selects the longest rule and records the selection.
3. Rule change attempts to shorten an existing record → rejected.
4. Disposal attempt without approved decision → rejected.
5. Disposal attempt on held records → rejected.
6. Hold placement/release preserves both signatures and evidence.
7. Archive tier migration → digest and rendering verified after move.
8. WORM lock applied and verified; early delete attempt fails at storage layer.
9. Audit events inherit class; orphan audit retention impossible.
10. Restore after disposal does not resurrect disposed records.
11. Pseudonymisation preserves case linkage and blocks re-identification through normal paths.
12. Retention dashboard counts reconcile with the record store.

# 8. Validation impact

Retention and disposal are data-integrity controls: qualification evidence per Document 89, DR/restore interaction per Document 91, and periodic review per Document 96. Any change to a class duration is a revalidation trigger.

# 9. Acceptance criteria

1. No regulated record can exist without a retention assignment.
2. Longest-applicable selection demonstrated for a DDCP record.
3. No code path deletes a regulated record without an approved disposal decision.
4. All §7 tests pass.

# 10. Claude Code / Codex prohibitions

- Do not write a scheduled job that deletes regulated data.
- Do not implement `DELETE` on audit, signature, vault or evidence tables.
- Do not hardcode a duration in a service; read the retention rule.
- Do not shorten retention to simplify a test fixture.

# 11. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Head of Quality |  |  |  |  |
| Regulatory Affairs |  |  |  |  |
| Legal |  |  |  |  |
