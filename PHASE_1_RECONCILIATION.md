# Phase 1 — Status / Traceability Reconciliation + Test Baseline

**Date:** 2026-09-09
**Goal:** make `status/build-status.json` and the traceability records reflect the code that actually
exists, and establish a real backend-test baseline.

---

## 1. What was corrected

### WP-11 (Data / Infrastructure / DR / SRE — Docs 69–78)

Tracked as `NOT_STARTED` with a placeholder `code_location: "infrastructure"`. **9 of 10 modules have
real code + tests** in `services/gxp-api/app/modules/` and were moved to `IN_DEVELOPMENT` with the true
path:

| Doc | Module | Was | Now | Code location | Tests |
|---|---|---|---|---|---|
| 69 | SPEC-DATA-001 (Data ownership / lineage) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/dataops` (7 files, 4 endpoints) | `test_data_ownership.py` |
| 70 | SPEC-DATA-002 (PG schema / partitioning / concurrency) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/dbops` (6 files) | `test_dbops_pg_architecture.py` |
| 71 | SPEC-DATA-003 (Frappe/MariaDB projection) | NOT_STARTED | **NOT_STARTED** — reqs → `DEFERRED` | *not built by design* | — |
| 72 | SPEC-DATA-004 (Immutable evidence / WORM) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/evidence` (5 files, 6 endpoints) | `test_evidence_lifecycle.py` |
| 73 | SPEC-DATA-005 (NATS / outbox) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/eventbus` (8 files) — **interim stand-in, ADR-0011 / SG-183** | `test_eventbus_outbox_consumer.py` |
| 74 | SPEC-DATA-006 (Temporal) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/workflowops` (4 files) — **interim stand-in, ADR-0011 / SG-183** | `test_workflowops.py` |
| 75 | SPEC-DATA-007 (Caching / search / read models) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/readmodels` (6 files, 5 endpoints) | `test_readmodels_cache_search.py` |
| 76 | SPEC-DATA-008 (Backup / restore / PITR / DR) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/disaster_recovery` (7 files, 3 endpoints) | `test_disaster_recovery.py` |
| 77 | SPEC-DATA-009 (Cloud-neutral K8s / on-prem deploy) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/deployment` (3 files) | `test_deployment.py` |
| 78 | SPEC-DATA-010 (Performance / capacity / SLO / SRE) | NOT_STARTED | IN_DEVELOPMENT | `app/modules/sre` (5 files) | `test_sre_slo_capacity.py` |

**Doc 71** is deliberately not built — ADR-0010 makes the Next.js `frontend/` the UI of record, so the
Frappe/MariaDB projection tier does not exist. Its 28 requirements were reclassified `NOT_STARTED →
DEFERRED` with blocker `SG-182` (Document 71 rework/descope).

A top-level `reconciliation_note` was added to `build-status.json`, and `rollup.py` was re-run.
**`modules_started` went 83 → 92.**

### WP-12 / WP-13 / WP-14 — no correction needed

These modules were **already** `IN_DEVELOPMENT` with the correct `code_location`
(`app/modules/validation`, `app/modules/ai_governance`). Their "0 requirements verified" is **accurate,
not a tracking error** — the qualification test cases in `TEST_CASE_LIBRARY.csv` (980 / 181 / 192 rows
respectively) have simply never been executed. Executing them is Phase 6 (WP-12 validation), not a
bookkeeping fix. The code is substantial:

| WP | Module(s) | Endpoints | Tests |
|---|---|---|---|
| WP-12 | `app/modules/validation/` (Docs 79–96) | 86 | `test_validation_wp12_part1–4.py` |
| WP-13 | `app/modules/ai_governance/` (Doc 105) | 24 | `test_ai_governance.py` |
| WP-14 | `app/modules/validation/router_wp14.py` (Docs 85/87/95) | 20 | `test_validation_wp14_part1–3.py` |

### WP-06 edge Docs 44 / 45 / 46 — confirmed genuinely not started

`SPEC-EDGE-002` (industrial device protocol drivers), `SPEC-EDGE-003` (store/forward offline buffering),
`SPEC-EDGE-004` (barcode/scanner/balance/printer peripherals) have **no code** — `app/modules/edge`
covers Doc 43 only, `app/modules/machine_integration` covers Doc 47. Their requirements are already
`DEFERRED`, which is now formally correct: these are out of the M1 scope (ADR-0012). No change.

### WP-00 Docs 97–104 — confirmed mostly not started

Only `SPEC-ENG-005` (Doc 101, API/event contract standard) has partial code (`contracts/openapi/`,
`contracts/events/`, `tooling/contracts`, `tooling/events`). The WP-00 *deliverables* — CI/CD pipeline
(Doc 103), SBOM + licence register (Doc 104), coding-standard enforcement matrix (Doc 97), branching
standard (Doc 99) — do not exist. This is Phase 2 work; no reconciliation change.

---

## 2. Code inventory (whole platform, for reference)

| Layer | Count |
|---|---|
| Backend domain modules (`app/modules/`) | ~45 |
| Backend HTTP endpoints | 757 |
| Alembic migrations (head `a6d525b2d585` / `0093`) | 93 |
| Backend pytest tests | 1 159 |
| Frontend pages (`frontend/src/app/**/page.tsx`) | 72 |
| Frontend automated tests | **0** (a UI test layer is a WP-00 / WP-12 deliverable per ADR-0010) |

**Overall after reconciliation:** 92 / 103 modules started · 0 released · 763 / 2 965 requirements
verified · 2 504 / 9 150 test cases executed (all figures from `TEST_CASE_LIBRARY.csv` via `rollup.py`).

---

## 3. Backend test baseline

**Test database:** `ebmr_new_gxp_test` on the shared PostgreSQL 14 instance (port 5432).
`alembic_version = a6d525b2d585` — **at code head, no drift.** Roles `ebmr_new_gxp_app` /
`ebmr_new_migrator`; passwords in `services/gxp-api/.env` (exported as `GXP_TEST_DB_APP_PW` /
`GXP_TEST_DB_MIGRATOR_PW` for the run).

**Run:** `pytest -q -p no:randomly -rf --tb=line` as the `frappe` user, 1 159 tests collected,
completed in **2 h 20 m** (2026-09-09).

| Result | Count | % |
|---|---|---|
| **PASS** | **968** | **83.5 %** |
| FAIL | 191 | 16.5 % |
| ERROR | 0 | — |
| SKIP / XFAIL | 0 | — |

### Failure triage — ~183 of 191 are environmental, not code defects

| Bucket | Count | Cause | Type |
|---|---|---|---|
| **A** | ~122 | `sqlalchemy ProgrammingError: UndefinedColumnError` — `ddcp_profile_version.product_version_id` (migration **0089**) and `material_lots.supplier_id` (migration **0084**) do not exist in `ebmr_new_gxp_test` | **Stale test DB** |
| **B** | ~22 | `NotFoundError: Batch not found` in `ddcp/*commands.py` — downstream of bucket A (profile create fails → no batch context); some may also touch the SG-173 dual batch store | **Stale test DB / SG-173** |
| **C** | ~35 | `SignaturePolicyUnresolvedError` in `test_validation_wp12_part1–4` / `test_validation_wp14_part1–3` | **Open gap SG-172 / SG-167 / SG-170** — not a defect |
| **D** | 8 | genuine individual failures — see below | **Real** |
| **E** | ~4 | `AssertionError` / misc downstream of A–C | mixed |

**Bucket C is not fixable in Phase 1.** `app/modules/validation/signature_support.py` states it
"deliberately does NOT seed Document 106 policy rows... `SignaturePolicyUnresolvedError` ... is the
correct, evidenced behaviour for every one of these pairs until Head of Quality + Regulatory Affairs
supply Document 106 rows." `SIGNATURE_POLICY_FLOOR` in `scripts/seed.py` has **zero** validation-platform
rows, and neither does the conftest `seeded` fixture. These 35 tests are the open **SG-172** policy-data
gap surfacing as red — the same class as the 2 269 library test cases marked `BLOCKED`. They should be
reclassified `BLOCKED (SG-172)`, not counted as regressions. Closing them needs the Quality/Regulatory
sign-off already listed in `PHASE_0_DECISIONS.md §3`, and WP-12 validation execution is Phase 6 per
ADR-0012.

**Root cause of buckets A/B — confirmed by direct schema comparison:**

| Object (migration) | `ebmr_new_gxp` (main, healthy) | `ebmr_new_gxp_test` |
|---|---|---|
| `alembic_version` | `a6d525b2d585` (head / 0093) | `a6d525b2d585` (head / 0093) |
| `material_lots.supplier_id` (0084) | ✅ present | ❌ **missing** |
| `gxp_batch_step.required_role_code` (0086) | ✅ | ✅ |
| `ddcp_profile_version.product_version_id` (0089) | ✅ present | ❌ **missing** |
| `gxp_step_result` (0092) | ✅ | ✅ |

The test DB is **stamped at head but is missing migrations 0084 and 0089** (scattered — 0086 and 0092
between them did land). This is the drift pattern noted in project memory ("test DB's `alembic_version`
can be stale vs. its real schema"). It is a **test-environment defect, not 183 code bugs** — the healthy
main DB proves `alembic upgrade head` produces the correct schema. Corrected pass rate after a clean
test-DB rebuild is expected to be ~97 %+, consistent with the per-module results earlier sessions
recorded.

### Bucket D — the 8 genuine failures to investigate

| Test | Cause | Likely tie |
|---|---|---|
| `test_contract_conformance.py::test_wp01_contracts_cover_every_implemented_wp01_operation` | `AssertionError: implemented but not committed` | **SG-013** (known) — a WP-01 operation has no committed contract |
| `test_release_gate.py::test_disposition_blocked_by_a_released_eligibility_rule_that_fails` | assertion | **SG-143** (rules evaluator) |
| `test_release_gate.py::test_disposition_allowed_by_a_released_eligibility_rule_that_passes` | assertion | **SG-143** |
| `test_eventbus_outbox_consumer.py::test_outbox_event_carries_schema_version` | `AttributeError: 'NoneType' has no attribute 'schema_version'` | **SG-183** (eventbus stand-in) |
| `test_eventbus_outbox_consumer.py::test_claim_publish_mark_and_reject_double_mark` | `RuntimeError: coroutine raised StopIteration` | **SG-183** |
| `test_ai_governance.py::test_authorize_tool_call_read_tool_fails_closed_on_signature` | `AIToolNotAllowlistedError` | fixture/seed — triage |
| `test_crypto_secrets_pki.py::test_field_encryption_round_trip_and_wrong_key_context` | assertion | triage |
| `test_master_data_crud.py::test_material_edit_and_delete_guard` | assertion | possibly relates to the ADR-0013 `delete_site()` guard finding |

### Test-DB repair — DONE 2026-09-09

A full column/table diff between `ebmr_new_gxp` (healthy) and `ebmr_new_gxp_test` showed the drift was
**exactly two missing columns, nothing else** (tables identical, no extra objects). So a full rebuild was
unnecessary — a targeted repair applying migrations 0084 and 0089's DDL was sufficient:

```sql
ALTER TABLE materials.material_lots ADD COLUMN supplier_id uuid;
ALTER TABLE materials.material_lots ADD CONSTRAINT fk_material_lots_supplier_id
  FOREIGN KEY (supplier_id) REFERENCES ebmr.supplier(id);
ALTER TABLE ddcp.ddcp_profile_version ADD COLUMN product_version_id uuid;
ALTER TABLE ddcp.ddcp_profile_version ADD CONSTRAINT fk_ddcp_profile_version_product_version
  FOREIGN KEY (product_version_id) REFERENCES ebmr.gxp_product_version(id);
```

After: **`ebmr_new_gxp_test` column set is now identical to `ebmr_new_gxp`.** `alembic_version` already
read head, so no stamp change. The 23 affected files were re-run — results in the next section.

> **Follow-up for the environment owner:** the *main* `ebmr_new_gxp` DB is healthy, but the fact that the
> test DB reached "head" with 0084/0089 unapplied means a past `alembic upgrade` on it partially failed
> and was force-stamped. Worth a CI guard that runs `alembic upgrade head` on a fresh DB and diffs the
> resulting schema against the live one, so this can't recur silently.

### Re-run of the 23 affected files (post-repair) — 177 pass / 140 fail

The DB repair worked, but it **un-masked a second systematic problem**. Files that were pure
schema-drift now pass in full: `test_material_receipt_flow` (was 14 fail → 0), `test_material_uom`
(2 → 0), `test_release_gate` (2 → 0), `test_crypto_secrets_pki` (1 → 0), `test_master_data_crud`
(1 → 0). But the DDCP-family and material-inventory tests now fail with **`NotFoundError: Batch not
found`** instead of `UndefinedColumnError`.

**Root cause of the remaining ~100 failures = SG-173, exactly.**

- `app/modules/ddcp/commands.py` (and the injector / inhalation / coated-device command modules) do
  `from app.modules.batch_execution.models import Batch` → they query **`ebmr.gxp_batch`** (the
  authoritative store).
- `tests/test_ddcp_flow.py` (and the other DDCP + material flow tests) do
  `from app.modules.batch.models import Batch` and their `_create_batch()` helper inserts into
  **`ebmr.batches`** (the scaffold).
- The test hands the command a `batches.id` that has no row in `gxp_batch` → "Batch not found".

So the command layer has **already** been (partly) cut over to the authoritative store, but the test
fixtures were not. This is the precise failure ADR-0013's cutover (Phase 1 "repoint dependents",
Phase 3 "frontend consolidation" — and, it turns out, the test fixtures) resolves. **These ~100 are not
new defects — they are the SG-173 debt made visible, and concrete evidence for the Phase 0 priority.**

| Bucket (post-repair) | ~count | Disposition |
|---|---|---|
| **SG-173** — DDCP/material tests use scaffold `batch`; commands use `batch_execution` | ~100 | Blocked on the ADR-0013 cutover (Phase 3). Fixture updates are part of that work. |
| **SG-172** — validation-platform signature policies not authored | ~36 | Blocked on Quality sign-off (`PHASE_0_DECISIONS.md §3`). Not a defect. |
| **Genuine backend defects** | **4** | Real backlog — see below |

### Genuine backend defect backlog (4)

| Test | Cause | Tie |
|---|---|---|
| `test_contract_conformance.py::test_wp01_contracts_cover_every_implemented_wp01_operation` | `AssertionError: implemented but not committed` | **SG-013** — a WP-01 operation has no committed contract (known/tracked) |
| `test_eventbus_outbox_consumer.py::test_outbox_event_carries_schema_version` | `AttributeError: 'NoneType' object has no attribute 'schema_version'` | **SG-183** — eventbus stand-in |
| `test_eventbus_outbox_consumer.py::test_claim_publish_mark_and_reject_double_mark` | `RuntimeError: coroutine raised StopIteration` | **SG-183** — eventbus stand-in |
| `test_ai_governance.py::test_authorize_tool_call_read_tool_fails_closed_on_signature` | `AIToolNotAllowlistedError` | triage — likely a test allowlist/seed issue |

### Corrected full-suite picture

| | Count |
|---|---|
| Baseline (pre-repair) | 968 pass / 191 fail |
| Recovered by the DB repair (pure schema-drift tests) | ~30 |
| **Solidly passing now** | **~998 / 1 159 (~86 %)** |
| Remaining — SG-173 dual store (test fixtures) | ~100 |
| Remaining — SG-172 validation signature policies (open gap) | ~36 |
| Remaining — genuine backend defects | 4 |

A clean full-suite re-run to confirm these exact numbers is worthwhile once the SG-173 fixture cutover
lands (otherwise it just re-measures the same ~100 known failures over another 2 h 20 m).

---

## 4. Traceability CSV

`traceability/TRACEABILITY_MASTER.csv` UI rows that reference `apps/ebmr_frappe/...` should be
re-pointed to `frontend/src/app/...` per ADR-0010. This is a mechanical sweep deferred to the same task
that adds the frontend traceability rows (Phase 5 entry) — it does not change any verification state and
is not M1-blocking.

---

## 5. Outcome

- `build-status.json` no longer under-reports WP-11 by 9 modules (`modules_started` 83 → 92).
- The remaining "0 verified" on WP-11/12/13/14 is **unexecuted qualification test cases**, not missing
  code — the correct input to Phase 6 planning.
- **Backend automated-test baseline: 968 / 1 159 pass (83.5 %), 0 errors** — then the test DB was
  repaired (missing migrations 0084 + 0089 applied) and the affected files re-run.
- **After repair: ~998 / 1 159 solidly passing (~86 %).** Of the remaining ~140: **~100 = SG-173**
  (DDCP/material test fixtures still use the scaffold `batch` module the command layer already left —
  fixed by the ADR-0013 cutover), **~36 = SG-172** (validation signature policies not authored — open
  Quality gap), **4 = genuine backend defects** (SG-013 ×1, SG-183 ×2, ai_governance ×1).
- **This run is direct evidence for the Phase 0 priorities**: the single biggest chunk of backend test
  failure is the SG-173 dual store.
