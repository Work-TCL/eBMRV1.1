# Next development prompt — WP-08: DDCP Product Profiles (Documents 54-57)

## STATUS NOTE — written 2026-08-29, end of the WP-06/IAM/legacy contract session

This file is a coordination brief for a **new, separate Claude Code chat session** working on the same
`eBMR-new` repository as at least one other active session. Read this file in full before doing anything.

**Another session is actively working WP-05 QMS** (SG-138's engineering half — signature-challenge
endpoints across the 12 QMS modules — followed by the WP-05 `spec-qms-*.yaml` contract slice once that
finishes). It runs `pytest` against the shared test database (`ebmr_new_gxp_test`) frequently and for long
stretches (20-30 min runs are normal). **Do not touch anything under `app/modules/qms/` or the QMS test
files (`tests/test_qms_*.py`), and do not assume the test database is idle** — check `ps -ef | grep
pytest` before running your own test suite, and if you find a collision mid-run, coordinate before
retrying (see "Test database coordination" below). This is the same shared-DB contention pattern that
cost real time in the session that wrote this file — plan for it up front instead of discovering it.

## What is already done (verified 2026-08-29, do not re-verify from scratch — trust this, spot-check if in doubt)

- **WP-00 through WP-04, WP-06, WP-07 are contract-complete.** `tooling/contracts/validate.py
  --strict-coverage` (run inside the `services/gxp-api/.venv` — the plain interpreter can't import
  FastAPI) confirms: 32 contract files committed, 329 operations, **0 conformance violations**, and the
  **entire remaining 123-operation backlog is WP-05 QMS** (`/qms/v1/*`, `/documents/v1/*`,
  `/effectiveness/v1/*`, `/training/v1/*`, `/quality-metrics/v1/*`). Every other implemented module in
  this codebase has a committed, exact-coverage OpenAPI contract.
- **WP-08 (this task) and WP-09+ have zero implementation.** No `app/modules/ddcp` directory exists.
  `services/gxp-api/app/modules/` currently has no code for Documents 54-60+. This is a genuine
  build-from-scratch task, not a "write the missing contract for existing code" task like most of this
  session's prior work.
- WP-08's own stated preconditions (`work-packages/WP-08/CLAUDE_CODE_PROMPT.md`: "WP-02, WP-03, WP-06
  accepted") are satisfied on the code-complete/contract level as of this session; `REVIEWED`/`QUALIFIED`
  human sign-off is a separate step this file does not claim.

## Why WP-08 next

Per `CLAUDE.md` §7's work-package order, WP-05 (claimed, in progress elsewhere) comes before WP-06
(now done). WP-07 (enterprise integrations, Documents 48-53) turned out to already be fully built and
contracted from an earlier phase — nothing left there. WP-08 is the next work package with real,
available, un-owned scope, and its preconditions are met.

## TASK

Implement WP-08 (Prefilled syringe, autoinjector/pen, inhalation MDI/DPI and drug-eluting device
execution profiles) covering **Documents 54, 55, 56, 57** — 120 requirements total. Full detail already
exists in this repo; **do not re-derive it, read it**:

- `work-packages/WP-08/CLAUDE_CODE_PROMPT.md` — the work-package-level brief (scope, architecture
  constraints, allowed/forbidden paths, acceptance criteria, completion-report format). Read this first.
- `work-packages/WP-08/01_SCOPE_AND_REQUIREMENTS.md` through `13_TRACEABILITY_AND_STATUS.md` — supporting
  detail (dependencies, function contracts, data model, API/event contracts, UI workflows, security,
  implementation sequence, test plan, validation impact, acceptance checklist, SPEC_GAPs already on file,
  traceability instructions).
- `prompts/WP-08/54_SPEC-DDCP-001.md` — Document 54, Prefilled Syringe & Injectable DDCP (PFS-FR-001..030)
- `prompts/WP-08/55_SPEC-DDCP-002.md` — Document 55 (requirement prefix in that file)
- `prompts/WP-08/56_SPEC-DDCP-003.md` — Document 56 (requirement prefix in that file)
- `prompts/WP-08/57_SPEC-DDCP-004.md` — Document 57 (requirement prefix in that file)

**Execution order: 54 → 55 → 56 → 57**, exactly as `work-packages/WP-08/08_IMPLEMENTATION_SEQUENCE.md`
and each sub-prompt's own numbering imply. Each sub-prompt is a complete, self-contained spec (source
document, requirement table, function catalogue, data model, API list, events, UI surfaces, security,
failure/recovery, migrations, tests, completion-report format) — follow it as written, the same way this
session followed `prompts/WP-06/38-42_SPEC-EQP-*.md` document-by-document.

## Contract-first — the one thing to get right before writing any implementation code

Unlike most of this session's work (which contracted already-implemented modules), **WP-08 starts from
zero code**. Its own preconditions say "Contracts for this module are committed before implementation
(Document 113)" — meaning `contracts/openapi/spec-ddcp-001.yaml` (and 002/003/004) should exist and pass
`tooling/contracts/validate.py` **before** `app/modules/ddcp/` is written, not after. This inverts the
"contract the code that exists" discipline used throughout the rest of this codebase — here you are
authoring the contract from the specification's own declared API list (§6 of each sub-prompt) since there
is no implementation yet to contract from instead. Once code exists, re-verify the contract still matches
what got built (specs and implementations commonly diverge in this codebase — see any `spec-eqp-*.yaml`
or `spec-mat-*.yaml` description for the established pattern of documenting where they do) and correct
the contract to match reality, the same discipline every other module in this repo follows.

## Patterns already established elsewhere in this codebase — reuse them, don't reinvent

Read a couple of the more recently-built modules before starting, to match idiom:
`app/modules/equipment/` (5 sub-documents in one module directory — DDCP's 4 documents may fit the same
shape) and `app/modules/material/`. Reusable precedents you will very likely need:

- **Mutation Gateway pattern**: `check_idempotency` → domain mutation → `write_audit_event` +
  `write_outbox_event` + `record_command_receipt` in one transaction → `MutationReceipt`. Every mutating
  command in this codebase follows this exact shape (see any `commands.py` file).
- **Signature ceremony**: `signature_service.resolve_signature_requirement(record_type=..., action=...)`
  → if `signature_required`, verify fresh password reauth → `consume_challenge` → `sign`. "No Document 106
  row = unsigned" is the standing precedent — never invent a signature requirement not in the approved
  Document 106 policy set; if one seems needed and isn't there, raise a SPEC_GAP and continue unsigned.
- **"Captured, not enforced" reference fields**: when a spec names an entity/field this codebase's frozen
  data model doesn't have a master table for, capture it as an unenforced UUID/string field with a comment
  explaining why (see `equipment_class_id` in `app/modules/equipment/models.py` for the canonical example)
  — never invent a 5th/6th entity beyond what the document's own data-model table declares.
  DDCP's spec function catalogue mentions constituent/process-stage config, aseptic-intervention linkage
  and functional-test results — check the 9-entity data model in `prompts/WP-08/54_SPEC-DDCP-001.md`
  before assuming any of these need their own table.
- **UOM dual-write (SG-146 precedent)**: any quantity-carrying entity should best-effort resolve free-text
  UOM against `rules.gxp_uom` via a `_resolve_uom_id()` helper that returns `None` on `UomUnknownError`
  rather than failing the write (see `app/modules/equipment/commands.py` or `material/commands.py` for
  the exact helper shape).
- **Decimal-only quantities**: never a binary float for a regulated quantity (DATA-FR-019) — `Decimal` in
  Python, `Numeric` in the ORM, decimal strings over the wire.
- **Cross-module reads, not writes**: DDCP will almost certainly need to read batch/equipment/aseptic/EM/
  sterilization state (the function catalogue references bulk release, sterile status, EM, filter
  integrity, aseptic interventions). Call the owning module's existing query functions directly (e.g.
  `equipment_commands.get_eligibility`, `em_commands.get_area_readiness`,
  `sterilization_commands.get_item_status` — all already built and importable) rather than duplicating
  their logic or writing to their tables (AG-05/AG-06). This is exactly the pattern
  `aseptic_commands._compute_readiness` uses for Document 40 — read it for a concrete example of composing
  four other modules' reads into one readiness check.

## Test database coordination

Before running any `pytest` against `ebmr_new_gxp_test`:
1. `ps -ef | grep -i pytest` — if the QMS session's tests are running, wait or pick a small/short test
   subset and time it around their run.
2. If you have access to the `ListAgents`/`SendMessage` tools, you can message the peer session directly
   (as this session did) rather than guessing at timing — a short "I'm about to run tests/test_X.py, is
   the DB free for ~N minutes?" costs less than a contaminated run.
3. Never `pkill` a running pytest mid-run (even your own) — the `clean_database` fixture's truncation can
   leave the shared DB half-seeded for whoever runs next. Let it finish, then treat only genuinely
   uncontaminated runs as evidence (see CLAUDE.md §5 — never report a contaminated run as real evidence
   either way).

## Standing project rules (from CLAUDE.md — do not skip these)

- `specs/` is read-only. Never edit it.
- Never invent regulated behaviour (signature requirements, SoD, retention, precision, authorization,
  audit/vault semantics, release decisions). Missing decision → append a SPEC_GAP entry to
  `docs/generated/18_SPEC_GAPS.md` (state affected requirements, risk, options, blocking yes/no) and
  continue on unaffected work.
- Never fabricate a test run, scan result, coverage number or signature. A failed test is evidence — never
  delete it, re-run over it, or edit the expected result to pass.
- Update `traceability/TRACEABILITY_MASTER.csv` and `status/build-status.json` as you go (not only at the
  end), and run `python tooling/status/rollup.py` before your completion report.
- Run Python via `su -s /bin/bash frappe -c "cd services/gxp-api && ..."`; `chown frappe:frappe` anything
  you create as another user.
- Before declaring the task complete, deliver the full CLAUDE.md §6 twelve-point completion report:
  requirement IDs implemented; functions created/changed; files changed; migrations; API/event contract
  changes; dependency/licence changes; security impact; test cases executed (PASS/FAIL/BLOCKED + failure
  ids); validation/change impact; traceability/status updated (include the `rollup.py` summary line);
  unresolved SPEC_GAPs; known limitations.

## Suggested opening move for the new session

1. Read this file in full (done, if you're reading this).
2. Read `work-packages/WP-08/CLAUDE_CODE_PROMPT.md` in full.
3. Read `prompts/WP-08/54_SPEC-DDCP-001.md` in full.
4. Skim `app/modules/equipment/models.py` + `commands.py` (Document 38) and
   `app/modules/equipment/aseptic_commands.py` (Document 40) for 10 minutes to internalize this
   codebase's idiom before writing anything new.
5. Write `contracts/openapi/spec-ddcp-001.yaml` from Document 54's declared API list, validate it with
   `tooling/contracts/validate.py`, then implement `app/modules/ddcp/` (models, commands, router) for
   Document 54 end to end (including tests) before moving to Document 55.
