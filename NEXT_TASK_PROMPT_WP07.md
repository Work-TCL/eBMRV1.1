# Next development prompt — WP-07 completion: Enterprise Integrations (Documents 48-53)

## STATUS NOTE — written 2026-08-29

This file is a coordination brief for a **new, separate Claude Code chat session** working on the same
`eBMR-new` repository as at least one other active session. Read this file in full before doing anything.

**Another session may still be active on WP-05 QMS** (`app/modules/qms/`, `tests/test_qms_*.py`) and a
third session may be starting WP-08 DDCP (`app/modules/ddcp/`, see `NEXT_TASK_PROMPT_WP08.md`) — check
`ps -ef | grep pytest` before running your own test suite against the shared `ebmr_new_gxp_test`
database, and coordinate with any peer session found via the `ListAgents`/`SendMessage` tools rather than
guessing at timing. Never `pkill` a running pytest mid-run — the `clean_database` fixture's truncation can
leave the DB half-seeded for whoever runs next. This repo's shared-test-DB contention is a real, recurring
cost — plan for it up front.

## Correcting an earlier claim — WP-07 is NOT complete

An earlier turn in a different chat this same day stated WP-07 was "already fully built and contracted."
That was **wrong** on the implementation side (right only on the contract/API side — see below) and was
corrected once `status/BUILD_STATUS.md` was actually checked. The real state, verified 2026-08-29:

```
WP-07 | Enterprise Integrations | 0/6 | IN_DEVELOPMENT | WP-01, WP-04
```

| Doc | Spec | Reqs | Verified | Tests | Pass | Fail | Blocked |
|---|---|---|---|---|---|---|---|
| 48 | ERP-001 (Architecture/provider contract) | 30 | 0 | 120 | 87 | 0 | 25 |
| 49 | ERP-002 (ERPNext adapter) | 24 | 0 | 98 | 61 | 0 | 11 |
| 50 | ERP-003 (SAP S/4HANA adapter) | 25 | 0 | 76 | 43 | 0 | 16 |
| 51 | ERP-004 (Oracle Fusion/Dynamics 365/custom) | 24 | 0 | 84 | 40 | 0 | 21 |
| 52 | ERP-005 (Master data sync/mapping/reconciliation) | 28 | 0 | 98 | 65 | 0 | 19 |
| 53 | ERP-006 (Error handling/retry/idempotency/reconciliation) | 30 | 0 | 100 | 72 | 0 | 22 |
| **Total** | | **161** | **0** | **576** | **368** | **0** | **114** |

**368 tests genuinely pass, 0 fail. 114 are BLOCKED. 0 requirements are marked VERIFIED. Stage is
IN_DEVELOPMENT, not CODE_COMPLETE.** Real implementation exists — `app/modules/erp/` (`models.py`,
`commands.py`, `provider.py`, `reliability.py`, `adapters/{base,erpnext,sap,oracle_fusion,dynamics365,
generic}.py`) plus `app/modules/lims_integration/` and `app/modules/machine_integration/` — and the
**contract side is genuinely done**: `tooling/contracts/validate.py --strict-coverage` confirms every
implemented HTTP operation across all three modules has a committed, exact-coverage OpenAPI contract
(`spec-erp-006.yaml`, `spec-edge-005.yaml`). What remains is closing the implementation gap behind the 114
blocked test cases.

## Why the 114 cases are blocked — read the SPEC_GAPs first, they already explain almost everything

`docs/generated/18_SPEC_GAPS.md` **SG-121 through SG-126** (search for `spec_gap_id: SG-12[1-6]`) document
this in detail — read all six before writing code, they will save you from re-deriving conclusions that
are already on record:

- **SG-121** — no Document 112 schema existed for any WP-07 entity; a provisional schema was authored
  under ADR-0009 (`erp` PostgreSQL schema, 10 tables: `erp_instances`, `erp_external_mappings`,
  `erp_mapping_conflicts`, `erp_sync_checkpoints`, `integration_commands`, `integration_command_attempts`,
  `integration_inbound_events`, `integration_reconciliation_runs`, `integration_reconciliation_differences`,
  `integration_circuit_breakers`). `status: OPEN`, `blocking: false` — usable now, may need a follow-up
  migration once a human amends Document 112.
- **SG-122** — Document 106 has zero signature-policy rows for any WP-07 action; resolved to
  `signature_required=False` for `approve_mapping()`/`resolve_master_conflict()`/`register_erp_instance()`
  via `scripts/seed.py`'s `SIGNATURE_POLICY_FLOOR`. Same "no row = unsigned" precedent used everywhere
  else in this codebase — do not add a signature ceremony here without a real Document 106 row.
- **SG-123** — no numeric retry/backoff/circuit-breaker threshold exists in any baseline document;
  `app/modules/erp/reliability.py` ships conservative, fully-configurable-per-instance defaults (30s
  initial backoff, 2.0x multiplier, 3600s cap, ±20% jitter, 8 max attempts, circuit trips after 5
  consecutive failures in 10 min, half-opens after 60s). Reuse these, don't invent new numbers.
- **SG-124** — no auto-resolve tolerance exists for reconciliation differences; every difference is
  created `resolution_status=OPEN` and requires an explicit human `resolveReconciliationDifference()`
  call. **Do not implement an auto-resolve rule** without a released rule via the `rules` module
  (`RUL-FR-016` pattern) — a hardcoded tolerance is exactly the guessed regulated-precision behaviour
  AG-15 prohibits.
- **SG-125** — **cannot be closed by writing code.** No credentialed ERPNext/SAP/Oracle/Dynamics sandbox
  is reachable from this environment (a real Frappe+ERPNext bench exists at
  `/home/hepin/mydata/eBMR/apps/erpnext` but belongs to a different, unrelated project — provisioning
  credentials on it without explicit authorization is out of scope). Every adapter is real `httpx`-based
  code against each vendor's genuine documented API shape; every test runs against a local
  `httpx.MockTransport`. **Never claim a live vendor test occurred — this is CLAUDE.md §5 territory.**
  Test cases blocked for this reason stay blocked until a human provisions a real sandbox at an OQ/PQ
  stage; that is not this session's job.
- **SG-126** — the real scope map of what's built vs. not. This is your primary work list.

## The actual work: SG-126's "not built this pass" list, prioritized by blocked-case volume

Verified against `test-cases/TEST_CASE_LIBRARY.csv` (114 WP-07 rows with `status=BLOCKED`, grouped by the
real `actual_result` text already recorded on each row — read the exact row before touching a test case,
this summary is illustrative, not exhaustive):

1. **Automated master-data sync pipeline (MDS-FR-004/005/008/023)** — `fetch_changes()` exists on every
   adapter but nothing calls it; only the human-driven `proposeMapping`/`approveMapping` surface is wired.
   No `stageInboundMasterRecords()`/`normalizeMasterRecord()`/`matchInternalEntity()` functions exist.
   Several blocked cases cite this directly ("fetch_changes() exists ... but no scheduled/triggered
   pipeline"). This is likely the single highest-value item — it's a real, buildable pipeline reusing the
   existing adapter/mapping infrastructure, not a new external dependency.
2. **Purchase Order read/create/update** — no PO command or endpoint exists at all (repeated across
   several blocked cases, e.g. "no PO read/create/update command or endpoint built this pass").
3. **Additional canonical operations declared but unimplemented** — `POST_RELEASE_AVAILABILITY`,
   `POST_RESERVATION` and similar are declared in `provider.py`'s `PROVIDER_OPERATIONS` capability list
   but have no adapter implementation behind them yet — check `provider.py` against each adapter's
   `SUPPORTED_OPERATIONS` for the full gap list.
4. **Lot/serial mapping** — no `lot`/`serial` `entity_type` or mapping path exists in the external-mapping
   model.
5. **File-based adapters (MULTI-FR-015)** — no SFTP/CSV/XML/EDI adapter exists; only the `httpx`-based
   REST/OData adapters were built. A genuinely separate adapter class from `HttpAdapterBase`.
6. **Deep per-vendor field mapping** (ENXT-FR-018 custom fields, SAP-FR-018 OData `$batch`, SAP-FR-023
   custom BAPI/RFC, MULTI-FR-014 SOAP/WSDL) — beyond the shared operation set every adapter currently
   implements.
7. **Response-status/body inspection** — at least one blocked case notes an adapter "treats any HTTP
   status < 300 as success; it does not inspect [the body for a vendor-specific soft-failure]" — a real,
   scoped bug/gap in existing adapter code, not a missing feature; fix this one directly.
8. **`retention_class` column** — none of the ten provisional `erp.*` tables from SG-121 has one; Document
   108's retention-classification requirement is uncoded for this module. A schema migration, not a new
   feature — follow the expand/migrate/contract discipline in `.claude/rules/08-database-migrations.md`.
9. **Compensation-command pattern** — no "compensation command tied to an authorized GxP correction" exists
   for reversing a previously-posted integration command.
10. **Secret-manager integration (ERP-ARC-028)** — `ErpInstance.auth_secret_ref` is used directly as a
    credential today; no secret-manager integration exists **anywhere in this codebase yet**. This is a
    platform-wide capability, not WP-07-scoped — raise a SPEC_GAP referencing SG-126 if you reach a
    requirement that needs it rather than building a one-off secret store for this module alone; check
    with the user before taking this on as it may be out of this task's reasonable scope.

Work through `test-cases/WP-07/Document_4{8,9}_*.md` and `Document_5{0,1,2,3}_*.md` (the same document
numbering as above), matching each `BLOCKED` row's `actual_result` text against the items above. Every
blocked case's `actual_result` field already states precisely why it's blocked — treat that as ground
truth over this summary if the two ever seem to disagree.

## Standing project rules (from CLAUDE.md — do not skip these)

- `specs/` is read-only. Never edit it.
- Never invent regulated behaviour. A missing decision → append a SPEC_GAP entry to
  `docs/generated/18_SPEC_GAPS.md` (affected requirements, risk, options, blocking yes/no) and continue on
  unaffected work. SG-121 through SG-126 are the existing entries for this module — extend them or add a
  new SG-12x if you resolve one or find a new gap; don't silently reinterpret an `OPEN` gap as closed.
- Never fabricate a test run, scan result, coverage number or signature — and **never claim a live
  ERPNext/SAP/Oracle/Dynamics call occurred** (SG-125). A failed test is evidence — never delete it,
  re-run over it, or edit the expected result to pass. A case that stays genuinely blocked (SG-125-class)
  stays `BLOCKED`, not silently marked `PASS`.
- Update `traceability/TRACEABILITY_MASTER.csv` and `status/build-status.json` as you go, and run
  `python tooling/status/rollup.py` before your completion report.
- Run Python via `su -s /bin/bash frappe -c "cd services/gxp-api && ..."`; `chown frappe:frappe` anything
  you create as another user.
- Deliver the full CLAUDE.md §6 twelve-point completion report before declaring done: requirement IDs
  implemented; functions created/changed; files changed; migrations; API/event contract changes
  (re-run `tooling/contracts/validate.py` and `--strict-coverage` if you add/change any endpoint —
  `spec-erp-006.yaml`/`spec-edge-005.yaml` currently have exact coverage, keep it that way); dependency/
  licence changes; security impact; test cases executed (PASS/FAIL/BLOCKED counts + failure/still-blocked
  ids, compared against the 87/61/43/40/65/72 pass / 0 fail / 25/11/16/21/19/22 blocked baseline above);
  validation/change impact; traceability/status updated (include the `rollup.py` summary line); unresolved
  SPEC_GAPs; known limitations.

## Suggested opening move for the new session

1. Read this file in full (done, if you're reading this).
2. Read SG-121 through SG-126 in `docs/generated/18_SPEC_GAPS.md` in full — do not skip this, it is the
   difference between real progress and re-deriving decisions already made and recorded.
3. Read `app/modules/erp/provider.py`, `commands.py` and one adapter (`adapters/erpnext.py`) to understand
   the existing architecture before adding to it.
4. Pull the exact 114 `BLOCKED` rows: `python3 -c "import csv; [print(r) for r in
   csv.DictReader(open('test-cases/TEST_CASE_LIBRARY.csv')) if r['work_package']=='WP-07' and
   r['status']=='BLOCKED']"` (or filter in your editor) — this is your real, ground-truth backlog, not the
   prioritized summary above.
5. Start with the automated master-data sync pipeline (item 1 above) — it's the highest-leverage single
   piece of missing work, reuses existing adapter/mapping code, and unblocks the largest cluster of
   related test cases across Documents 48/52/53.
