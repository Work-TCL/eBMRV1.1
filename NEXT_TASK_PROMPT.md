# Next development prompt — SG-138 (engineering half): QMS signature-challenge endpoints

Continue development on the eBMR/eDHR regulated manufacturing platform at `/home/hepin/mydata/eBMR-new`,
following the project's CLAUDE.md contract exactly (source-of-truth precedence, the regulated mutation
path, SPEC_GAP discipline, no fabricated evidence, WP-00..WP-14 execution order).

## STATUS NOTE — re-verified 2026-08-29 04:10, this task is still open and still the right one

**Heads up: other Claude Code sessions are active on this same repo right now** (confirmed via `ps -ef`
at the time of this refresh — 3 concurrent processes, one mid-`pytest` run against `test_edge_flow.py`,
`test_erp_flow.py`, `test_iam_admin.py`, `test_lims_integration.py`, `test_machine_integration_flow.py`,
`test_policy_engine.py`, `test_qc_oos.py`, `test_qc.py`, `test_qc_uom.py`, `test_supplier_quality.py`,
`test_contract_conformance.py`). That work is a **contract-hygiene sweep** (CR-013, see below) plus its
own regression verification — it does not touch `app/modules/qms/`, `contracts/openapi/spec-qms-*`
(doesn't exist yet), or anything else this task needs, so there is no collision. Do not start a second
concurrent `pytest` run against `ebmr_new_gxp_test` while that session's run is in flight — the autouse
`clean_database` fixture will race it (see OPERATIONAL NOTES).

This prompt was originally written 2026-08-27. Since then, other sessions have:

- CR-001..CR-003 (2026-08-27): WP-01 GxP Core contract slice (Docs 03/04/05/06/08), Document 110
  precision/rounding/UOM enforcement (closed SG-143), UOM/conversion authoring command surface
  (SG-146 authoring half).
- CR-004..CR-007 (2026-08-27): WP-02 contract slice — Docs 09-12 (`spec-ebmr-000`..`003`: Product
  Master, Master Recipe/MMR, Batch Execution Engine, eDHR).
- CR-008..CR-012 (2026-08-27 through 2026-08-29 03:41): WP-03 contract slice — Docs 13-17
  (`spec-ebmr-004`..`008`: Genealogy, QA Review, Release/Disposition, Packaging, Yield/Reconciliation).
  Contract-validation baseline held at 107 findings throughout all 12 change records.
- SG-146 (UOM authoring/expand step) is now **fully resolved** for all 8 affected modules (`batch`,
  `batch_execution`, `genealogy`, `recipe_master`, `product_master`, `yield_reconciliation`, `qc`,
  `material` — 24 free-text UOM columns across 24 tables all dual-write a `*_uom_id` FK now). The
  contract step (dropping the free-text columns) is explicitly not due yet (MIG-FR-004 needs two
  releases of runway) — do not attempt it.
- CR-013 (2026-08-29, ~03:55-04:06): a **contract-hygiene sweep** over the 8 pre-existing contract files
  that predated the WP-02/WP-03 work (`spec-mat-001`, `spec-qc-001/2/3`, `spec-iam-001`, `spec-erp-006`,
  `spec-edge-001/005`) — fixed a YAML parse bug, path-parameter casing bugs, ~84 missing
  `x-requirement-ids`, and 2 genuinely uncontracted `GET /suppliers/v1*` operations.
  `tooling/contracts/validate.py` now reports **`PASS  no contract conformance violations found`** —
  the long-tracked "107 findings" baseline is fully zeroed, not just held flat. A regression pytest run
  for the touched modules was in flight as of this refresh (see the heads-up above) — its result isn't
  yet known to this prompt; don't assume it passed or failed, check `/tmp/ebmr_wp04_verify.log` or
  re-run if you need that number.

**None of that touched WP-05 QMS or signatures.** Verified directly against the code just now
(`grep -rn 'signature-challenges' services/gxp-api/app/modules/qms/*.py` → zero matches; every QMS
router file's last modification is still 2026-08-20/21). **This task — SG-138's engineering half — is
exactly as described below and is still completely unstarted.** The reference pattern (`batch`
module's `POST /{batch_id}/signature-challenges`) and the 12-module `record_type="..."` mapping table
below were both re-verified against the current code for this refresh and are accurate as of now.
Also re-confirmed by parsing every one of the 146 entries in `18_SPEC_GAPS.md` for
`blocking: true` + `status: OPEN`: **SG-138 is the only such gap in the entire register right now** —
the clean single highest-priority, unblocked, buildable item project-wide.

## CONTEXT — repo layout (confirmed, don't re-derive)

- `ebmr-edhr/` is the CURRENT, authoritative doc tree — specs, docs/generated/, test-cases/,
  traceability/, status/, work-packages/, prompts/. ALL deliverable updates go here. **It is untracked
  by git.**
- `ebmr-edhr-construction-package-v1.3/` is a STALE older snapshot that IS git-tracked. Git tracking is
  an anti-signal here — do not treat it as authoritative and do not write to it.
- Neither doc tree contains code. The one real codebase is `services/gxp-api/`.
- `contracts/openapi/` (repo root) now holds 22 committed contract files spanning WP-00/IAM, WP-01 GxP
  Core, WP-02 (Docs 09-12), WP-03 (Docs 13-17), and partial WP-04 (`spec-mat-001`, `spec-qc-001/2/3`)
  and WP-06/07 (`spec-edge-001/005`, `spec-erp-006`). **WP-05 QMS has zero contract files** — none of
  the twelve QMS record types is contracted yet. That's a separate, later gap; this task does not touch
  `contracts/openapi/` (see SCOPE below — the WP-05 API_CATALOGUE/contract question is explicitly
  deferred, not silently skipped).

## THE TASK

Close the **buildable half of SG-138 (blocking)**: give all twelve WP-05 QMS modules a
`POST .../signature-challenges` endpoint, the same ceremony-entry-point pattern every other signing
module in the codebase already exposes (batch, material, equipment, yield_reconciliation, edge,
machine_integration, lims_integration, qc, supplier_quality).

### Why this is buildable right now, not blocked

SG-138 has two independent halves:
1. **Policy data** — no WP-05 QMS record type is seeded in `SIGNATURE_POLICY_FLOOR`
   (`services/gxp-api/scripts/seed.py`), so `resolve_signature_requirement()` fails closed with
   `SIGNATURE_POLICY_UNRESOLVED` for all 26 (record_type, action) pairs. This is a regulated decision
   (signature meaning, signer role, independence, reason-required) reserved to Head of Quality +
   Regulatory Affairs per CLAUDE.md §4 — **do not invent these rows.**
2. **Ceremony entry point** — none of the twelve QMS routers exposes an endpoint to *obtain* a
   `challenge_id` in the first place. This is ordinary engineering, has zero regulated content of its
   own (it doesn't decide meaning/signer/independence — it just resolves policy and creates a challenge,
   exactly like every other module's endpoint already does), and is entirely unblocked by (1) being
   missing. Build this half. It will legitimately return `SIGNATURE_POLICY_UNRESOLVED` until someone
   supplies the policy rows — that's correct fail-closed behaviour, not a bug to work around.

## WHAT ALREADY EXISTS (re-verified 2026-08-29 — don't re-derive)

- Every one of the twelve QMS command files already calls
  `signature_service.resolve_signature_requirement(session, record_type=..., action=...)` at the point
  of a decision-bearing transition, and already calls `signature_service.consume_challenge()` /
  `signature_service.sign()` to close the ceremony. **The command-layer half of the pattern is complete
  and correct.** What's missing is purely the router-level step that creates the challenge the client
  presents back to these commands.
- Every QMS command file already has its own private `_record_hash(record) -> str` helper, used
  internally when consuming a challenge. Reuse these directly — do not write a second hashing scheme.
- The reference pattern to copy is `services/gxp-api/app/modules/batch/router.py` — its
  `SignatureChallengeRequest` model + `POST /{batch_id}/signature-challenges` handler (`action` field
  drives which record_type/meaning to resolve; loads the record, calls
  `resolve_signature_requirement(session, record_type=..., action=...)`, falls back through the
  resolved policy's `meaning`, then calls `create_challenge(session, user_id=actor.user_id,
  record_type=..., record_id=..., record_version=..., record_hash=..., meaning=...)` from
  `app.modules.signature.service`, and returns `{"challenge_id": ..., "meaning": ...,
  "expires_at": ...}`). Confirmed byte-for-byte still matching this description on 2026-08-29.
- `signature_service.create_challenge()` signature (in `app/modules/signature/service.py`):
  `(session, *, user_id, record_type, record_id, record_version, record_hash, meaning) -> SignatureChallenge`.

### The exact 12 (router file → record_type → actions → hash helper) mapping, re-confirmed 2026-08-29

Re-verified via `grep -rn 'record_type="' app/modules/qms/*.py` immediately before writing this — exact
match to the table below, no drift since 2026-08-27.

| Router file | `record_type` literal | Actions needing a challenge | `_record_hash` source |
|---|---|---|---|
| `qms/router.py` | `deviation_record` | disposition, close | `qms/commands.py:_record_hash` |
| `qms/capa_router.py` | `capa_record` | close | `qms/capa_commands.py:_record_hash` |
| `qms/ncr_router.py` | `nonconformance_record` | disposition, verify, close | `qms/ncr_commands.py:_record_hash` |
| `qms/change_router.py` | `change_control` | approve, verify, close | `qms/change_commands.py:_record_hash` |
| `qms/complaint_router.py` | `complaint_record` | reportability, close | `qms/complaint_commands.py:_record_hash` |
| `qms/scar_router.py` | `scar_record` | review, close | `qms/scar_commands.py:_record_hash` |
| `qms/field_action_router.py` | `field_action` | reportability, approve, close | `qms/field_action_commands.py:_record_hash` |
| `qms/internal_audit_router.py` | `internal_audit` | start, close | `qms/internal_audit_commands.py:_record_hash` |
| `qms/internal_audit_router.py` (finding sub-resource) | `audit_finding` | verify | same file, second `_record_hash` |
| `qms/document_router.py` | `controlled_document_version` | release | `qms/document_commands.py:_record_hash` |
| `qms/risk_router.py` | `risk_record` | review | `qms/risk_commands.py:_record_hash` |
| `qms/training_router.py` | `training_assignment` | create, complete, assess | `qms/training_commands.py:_record_hash` |
| `qms/quality_metrics_router.py` | `quality_metric_definition` | release | `qms/quality_metrics_commands.py:_record_hash` |
| `qms/quality_metrics_router.py` (snapshot sub-resource) | `quality_metric_snapshot` | management_review | same file, same/second `_record_hash` |

## SCOPE THIS TASK

1. **Design one shared pattern, don't hand-roll twelve.** All twelve endpoints have the identical shape:
   resolve policy for `(record_type, action)` → load the record → determine `meaning` (from the resolved
   policy, mirroring batch's `policy.meaning` fallback) → `create_challenge()` → return the receipt. A
   single helper (e.g. `app/modules/qms/signature_support.py` with a shared `SignatureChallengeRequest`
   model and a `create_qms_signature_challenge()` function parameterized by record_type/loader/hash-fn) is
   almost certainly better than duplicating the ~25-line block twelve times — same DRY judgment call the
   `material` module's `uom_backfill.py` made for its thirteen tables (see SG-146). Use your judgment; the
   project's own precedent favors the shared helper.
2. **Add the endpoint to each of the twelve routers**, following the mapping table above. Where a router
   has two record types (internal_audit/audit_finding; quality_metric_definition/quality_metric_snapshot),
   either one endpoint with an `action`-driven record_type resolution (like batch's single endpoint
   handling `complete_step`/`review`/`release`) or two endpoints — match whatever is more consistent with
   how that router already structures its other endpoints.
3. **Do not seed policy rows.** Do not add QMS record types to `SIGNATURE_POLICY_FLOOR`. Do not guess a
   `meaning` string, signer role, independence flag or reason-required flag for any of the 26 pairs — the
   endpoint should resolve policy from data and surface `SIGNATURE_POLICY_UNRESOLVED` exactly as batch's
   equivalent endpoint would if batch's own policy row were deleted. That failure is the correct,
   evidenced behaviour to test for.
4. **No migration needed.** This is router/service code only — no new tables or columns.
5. **Update SG-138**: do not close it (the policy-data half is still genuinely open and still needs Head
   of Quality + Regulatory Affairs). Add a note to its entry recording that the "no signature-challenges
   endpoint" defect is resolved, keep `blocking: true`, and keep `status: OPEN`. Update `resolution_document`
   to name what you built.
6. **Do not start a WP-05 OpenAPI contract file.** `contracts/openapi/` has no QMS contract yet; adding
   one is a separate, larger slice (12 modules, same shape as the WP-02/WP-03 work) that deserves its own
   task, not a byproduct of this one. If you touch `docs/generated/06_API_CATALOGUE.yaml` at all, only add
   the 12 new path entries at the summary level it already uses elsewhere for uncontracted operations —
   don't invent field-level schemas there either.

## TESTS

- For each of the twelve endpoints, write at minimum: (a) `SIGNATURE_POLICY_UNRESOLVED` when no policy
  row exists (the current, expected state — this should PASS against today's seed data), (b) 404/not-found
  on a bad record id, (c) once you can seed a policy row inside a test fixture only (not in
  `scripts/seed.py`), a full create-challenge → consume → sign round trip proving the wiring is real, not
  just a stub returning 200. Test-fixture-only policy rows are fine — they exercise the code path without
  making a production regulatory decision.
- Execute the pre-written test-case books for Docs 26-37 (`test-cases/WP-05/Document_NN_*_TEST_CASES.md`)
  where a case exists for a signature-challenge or ceremony behaviour; do not invent a parallel set.
  Blocked counts as of the 2026-08-27 handover (verify per case yourself before trusting — not
  re-measured for this refresh since no QMS code changed in between): Doc 26 (deviation) 28/73, Doc 27
  (CAPA) 19/61, Doc 28 (NCR) 35/65, Doc 29 (change) 21/61, Doc 30 (document) 39/52, Doc 31 (training)
  30/43, Doc 32 (risk) 20/26, Doc 33 (SCAR) 18/26, Doc 34 (internal audit) 32/36, Doc 35 (complaint)
  29/39, Doc 36 (field action) 18/32, Doc 37 (quality metrics) 25/43.
- Get a fresh real regression count yourself — don't reuse any number from a prior handover. Per
  [[project-ebmr-new-test-suite-state]]-type experience on this project, the pytest suite has known
  fixture-isolation races unrelated to your change; run one untouched-module test file as a control
  before attributing any failure to your own work (see OPERATIONAL NOTES).

## OPERATIONAL NOTES (learned on this project — save yourself the rediscovery)

- Run Python as `su -s /bin/bash frappe -c "cd /home/hepin/mydata/eBMR-new/services/gxp-api && ..."`.
  You are root but the project must stay `frappe`-owned — `chown -R frappe:frappe` everything you write.
  **Always include the `cd` inside the `su -c` string**; the Bash tool's cwd does not carry into `su`.
- Test DB env vars do NOT persist across Bash calls. Re-export inline every time:
  `GXP_TEST_DB_APP_PW='<pw>' GXP_TEST_DB_MIGRATOR_PW='<pw>' .venv/bin/python -m pytest ...`
  (values are in `services/gxp-api/.env`'s `GXP_DATABASE_URL` / `GXP_MIGRATION_DATABASE_URL`).
- **NEVER run two pytest sessions against `ebmr_new_gxp_test` at once** — the autouse `clean_database`
  fixture truncates tables and a concurrent run destroys the other's fixtures. Another Claude Code session
  may be using that database; check before a long run.
- The pytest suite is slow by construction (~8s/test, truncates 173 tables each time) and has known
  fixture-isolation races independent of any code change (duplicate-key on `sites_code_key`, FK
  violations, deadlocks) — before attributing a failure to your change, run a file you didn't touch as a
  control. Redirect long runs to a file and poll; never `pkill` mid-run (leaves half-seeded reference
  data that masks the real cause on the next run).
- `ruff` is NOT installed in the venv.
- `tooling/status/rollup.py` **derives** `requirements_state` from `TEST_CASE_LIBRARY.csv` and writes
  `build-status.json` back. It maps a case status of `FAIL` to requirement state `BLOCKED`, not `FAILED`.
  Manual edits to `requirements_state` are overwritten — set case results and let rollup do the rest.
  `test_cases`, `stage`, `blockers` and `open_defects` are NOT derived and must be set by hand.
- `TEST_CASE_LIBRARY.csv` has 1,092 duplicate-id rows across a handful of documents (not confirmed to
  include Docs 26-37 — re-check before trusting counts if you touch those rows).
- Before writing a SPEC_GAP that says "X doesn't exist," grep `app/modules/` and check
  `ebmr-edhr/status/build-status.json` — an inaccurate "doesn't exist" gap has been written before.
  `status/build-status.json`'s `code_location` fields for Docs 5, 7, 22 and 26-37 correctly point at
  `services/gxp-api/app/modules/qms`, `.../audit`, `.../policy`, `.../material` (fixed 2026-08-27).

## DELIVERABLES — update on THIS task, not at the end of the project

- `services/gxp-api/app/modules/qms/*router*.py` (all twelve, plus any new shared helper module)
- `services/gxp-api/tests/` — new signature-challenge tests per module
- `ebmr-edhr/docs/generated/18_SPEC_GAPS.md` — update SG-138's narrative and `resolution_document`,
  keep `blocking: true` / `status: OPEN`
- `ebmr-edhr/test-cases/WP-05/` + `TEST_CASE_LIBRARY.csv`, `traceability/TRACEABILITY_MASTER.csv`,
  `status/build-status.json` for Docs 26-37, then run `python ebmr-edhr/tooling/status/rollup.py`

## REPORT

Deliver the 12-point completion report CLAUDE.md §6 requires. Include the real `rollup.py` summary line
and real PASS/FAIL/BLOCKED counts from actual runs — never a fabricated or predicted result. A failed case
is evidence and stays.

---

## Alternatives considered (if you'd rather redirect)

- **SG-013 — continue the contract-first slice into WP-04's remaining modules.** WP-02/WP-03 are now
  fully committed (22 contract files total). WP-04 has `spec-mat-001` (material) and `spec-qc-001/2/3`
  (QC) already, but Document 18 (supplier quality/ASL), Document 19/20 (procurement), and Document 22
  (consumption/return/adjustment/destruction/reconciliation) are not yet contracted, nor is Document 24
  (LIMS integration, WP-07-adjacent). Mechanical and well-precedented now that 5 reference contract
  files exist across 3 different work packages, but it's a large, repetitive slice and doesn't move a
  `blocking: true` gap the way SG-138 does.
- **SG-138's own contract half** — once this task's endpoints exist, a WP-05 `spec-qms-*.yaml` contract
  slice (12 modules) becomes buildable using the exact same pattern as WP-02/WP-03. Deliberately
  sequenced after this task, not combined with it (see SCOPE point 6).
- **SG-144 — close `SimulateRuleRequest`'s open payload** (`extra="forbid"` missing). Small, one-file,
  low-value relative to the above; pick this up opportunistically if you're already in
  `app/modules/rules/`.
