# Phase 4 — WP-04 remainder: QC Method-master entity (SG-066)

**Date:** 2026-09-12
**Branch:** `wp17-phase4-wp04-qc-method-master` (based on `main` at `a90ea72`, the merge of PR #13's
WP-02 work)
**Scope:** the Method-master half of SG-066 (QC-FR-003/004, Document 23), chosen after correcting a
scoping error found while researching "WP-04 remainder: UOM conversion engine" (see §0 below).

---

## 0. Scope correction found before building anything

The Phase 4 gap-reconciliation summary produced before this branch claimed "UOM conversion engine: still
fully open, no conversion service exists anywhere in the codebase." This was wrong. Direct code inspection
found `rules.gxp_uom`/`rules.gxp_uom_conversion` with a full author/release command surface
(`app/modules/rules/uom_commands.py`) already built and resolved 2026-08-27 (SG-146), verified by
`tests/test_uom.py::test_uom_conversion_end_to_end_through_the_rules_evaluator`. What's actually still open
in that area is narrower and different: ~13 free-text `uom` columns across other tables that don't yet
validate against the controlled master (SG-146's own remaining expand-step items) — a cross-cutting
migration programme, not an engine build.

Re-scoped to the other genuinely-open QC-FR-004 item instead: a Method-master entity, which also turned up
a second correction — SG-066's own text claims Document 25 (OOS/OOT Management) isn't built, but direct
code inspection (`app/modules/qc/models.py:205`, `qc_result.oos_record_id` FK to `ebmr.oos_record.id`)
confirms it now is, built in a later pass than when SG-066 was written and never updated to reflect it.
Both corrections are recorded in SG-066's own resolution note rather than silently acted on.

## 1. What was built

**`QcMethodVersion`** (`app/modules/qc/models.py`, migration `dd78daa66970`) mirrors
`material_specification.MaterialSpecificationVersion`'s master+immutable-version split exactly —
`method_code`+`version_no` identity, `method_type` (compendial/internal/validated per QC-FR-003),
`validation_evidence_reference` (captured, unenforced — same precedent as `equipment_class_id`
elsewhere), `modification_reason` (required, VALIDATION_FAILED otherwise, on any version after the
first — QC-FR-004's own "reason" requirement), draft→released lifecycle through the generic Vault
surface. Full command surface (`create_qc_method_draft`/`release_qc_method_version`) + router
(`POST /qc/v1/methods/drafts`, `GET .../{method_code}/versions`, `GET .../{id}`,
`POST .../{id}/signature-challenges`, `POST .../drafts/{id}/release`), RBAC-gated with new
`qc_method.author`/`.release`/`.view` permissions — a deliberately stronger posture than this module's
own pre-existing convention of not RBAC-gating `qc_test_specification` drafts at all.

`qc_test_definition.method_version_id` is an additive, nullable FK (dual-written best-effort at
spec-authoring time, same MIG-FR-004 expand-step pattern already used for `uom_id`) — the existing
free-text `method_version` column is untouched.

Release correctly fails closed with `SIGNATURE_POLICY_UNRESOLVED`, since this is a brand-new record
type with no Document 106 policy row yet — new gap **SG-186**, not guessed, following the exact same
precedent as SG-035/138/167/181/185.

A real bug was caught and fixed before it shipped: the signature-challenge hash computed in the router
didn't match the hash `release_qc_method_version()` recomputes at consume time (a copy-paste mismatch
between this module's own `_record_hash(obj, field)` convention and a different 2-field pattern used
elsewhere) — would have made every release challenge fail with a false "record changed" rejection. Fixed
by using this module's own established convention consistently.

## 2. Contract

`spec-qc-001.yaml` — 5 new operations + 3 new schemas (`CreateQcMethodDraftCommand`,
`ReleaseQcMethodVersionCommand`, `QcMethodVersion`), `TestDefinitionInput` extended with
`method_version_id`. Required since `/qc/v1` is already contracted — `tooling/contracts/validate.py`
correctly flagged the 5 new undeclared operations before this fix.

## 3. New SPEC_GAP

**SG-186** — `qc_method_version/release` has no Document 106 signature policy row (class R, not
blocking). Correctly fails closed. Nearest analogue recorded for a future decision:
`qc_test_specification/release` (Document 106 row 58 — QA Approver/Batch Release role, independent).

## 4. Updated SPEC_GAP

**SG-066** — Method-master half PARTIALLY RESOLVED. Remaining open: `scope_type='material'` wiring
against SG-057's now-existing entity (small follow-on, not attempted), WP-06 instrument eligibility,
QC-FR-011 qualification-expiry, QC-FR-036/037 dashboard/export. The OOS/OOT sub-item was already resolved
elsewhere; this entry is corrected to say so.

## 5. Test-case evidence

TC-023-004-01/02 (QC-FR-004, the only two pre-written cases for this requirement) both **PASS** —
`tests/test_qc_method.py` (10/10 passed, new file), plus `test_qc.py`/`test_qc_oos.py`/`test_qc_uom.py`
(14/14) as an untouched-module control.
