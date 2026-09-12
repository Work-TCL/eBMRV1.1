# Phase 4 — WP-05 remainder: deviation → Change Control / Training FK link (SG-060)

**Date:** 2026-09-12
**Branch:** `wp20-phase4-wp05-deviation-fk` (based on `main` at the merge of PR #16's WP-03 yield-supersede work)
**Scope:** the "no real entity to link to" half of SG-060 (Document 26, DEV-FR-014/015), chosen after a
research pass across WP-05's 12 documents found this was the cleanest, smallest buildable item.

---

## 0. Scoping investigation before building anything

A research pass across Documents 26-37 (Deviation, CAPA, NCR, Change Control, Document Control,
Training, SCAR, Risk, Internal Audit, Complaint, Field Action, Quality Metrics — 257 requirements) found
the module structure is one `qms` package with per-document command/model/router file sets, all
genuinely built with real DDL and passing test suites (not vaporware). Most of the 44 recorded gaps
(SG-059..SG-108) are correctly blocked on a real missing decision — a numeric threshold nowhere in the
baseline (SG-087 training attempts, SG-099 risk-escalation authority), a security-architecture call
(SG-104 complainant PII redaction), a live external integration (SG-105 ERP/WMS/CRM), or nine
undefined quality-metric formulas (SG-107) — correctly left open.

SG-060 stood out as stale in a specific way: it says neither a Change Control nor a
training/retraining-action entity exists in this codebase "to link to." That was true when SG-060 was
filed (2026-08-24), but both entities were built in later WP-05 passes the same day/week
(`qms.change_control`, `qms.training_assignment`) — `deviation_record`'s own `change_control_required`/
`training_required` flags were simply never revisited to add the FK once the target tables existed. The
same shape repeats on `ncr_record`/`complaint_record`/`field_action`'s own `capa_required` flags (pointing
at `qms.capa_record`, also already real) — left as a same-shaped fast-follow, not attempted this pass to
keep the change reviewable.

## 1. What was built

Added `change_control_id: uuid.UUID | None` (FK → `qms.change_control.id`) and
`training_assignment_id: uuid.UUID | None` (FK → `qms.training_assignment.id`) to `DeviationRecord`
(`app/modules/qms/models.py`) — migration `0102_deviation_change_training_fk`, additive only (existing
`change_control_required`/`change_control_rationale`/`training_required`/`training_rationale` columns
untouched).

`DispositionCommand` (`app/modules/qms/commands.py`) accepts both fields optionally; when supplied,
`disposition_deviation()` validates the referenced row actually exists (`session.get(...)`, `NotFoundError`
otherwise) before storing it — the same shape as SCAR's `supplier_id` FK-check precedent already used
elsewhere in this module family. No new endpoint: Document 26's existing `POST
/qms/v1/deviations/{id}/disposition` carries the new fields.

**Deliberately not built:** a way to link a Change Control/Training Assignment created *after* disposition
already committed (this pass only wires the one-shot, disposition-time case — a customer whose workflow
always creates the linked record afterward would need a follow-up "link" command, not attempted here to
avoid scope creep on top of the FK's originally-recorded question); and the identical fast-follow on
NCR/Complaint/Field Action's own `capa_required` flags.

## 2. Contract

`contracts/openapi/spec-qms-001.yaml` — `change_control_id`/`training_assignment_id` added to
`DispositionCommand` (`additionalProperties: false`, so required). `tooling/contracts/validate.py
--baseline` PASS.

## 3. Updated SPEC_GAP

**SG-060** — moved to `PARTIALLY_RESOLVED`. The FK half is closed for `deviation_record`; the
NCR/Complaint/Field Action `capa_required`→`capa_record` fast-follow and post-disposition linking remain
open, recorded rather than silently assumed done.

## 4. Test evidence

`tests/test_qms_deviation.py` grew from 26 to 28 tests, **28/28 passed**: happy-path linking both a
`ChangeControl` and a `TrainingAssignment` at disposition time, and rejecting an unknown
`change_control_id` with `NOT_FOUND`.

## 5. Traceability / build-status / test-case updates

- `docs/generated/18_SPEC_GAPS.md` — SG-060 description + resolution_document + status updated.
- `traceability/TRACEABILITY_MASTER.csv` — TR-02979/TR-02980 (DEV-FR-014/015) moved
  `NOT_STARTED`/`BLOCKED` → `CODE_COMPLETE`/`VERIFIED`, gap_reference updated to describe the real FK.
- `test-cases/WP-05/Document_26_SPEC-QMS-001_TEST_CASES.md` + `test-cases/TEST_CASE_LIBRARY.csv` —
  TC-026-014-01/015-01 moved `NOT_STARTED` → `PASS` with real evidence citations.
- `status/build-status.json` — SPEC-QMS-001 requirements_state (DEV-FR-014/015 → VERIFIED), test_pass
  31→33, test_blocked 28→26, new stage_history entry; `tooling/status/rollup.py` re-run.
