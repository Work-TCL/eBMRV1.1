# Claude Code prompt — WP-06 / Document 46: Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration

TASK:
Implement the Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration module (SPEC-EDGE-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_46_Barcode_Scanner_Balance_Printer_Tester_Peripheral_Integration_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: PER-FR-001..025 (25)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **HIGHER-PROCESS-RISK** → scripted tests, independent review, mandatory negative and failure evidence

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- WP-00 foundations exist (contracts tooling, guardrails, CI gates).
- WP-01 GxP Core is available (mutation, policy, signature, audit, vault, rules).
- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `edge` and its tests
- `contracts/` entries owned by this module
- migrations for entities owned by this module
- Frappe UI surfaces for this module in `apps/ebmr_frappe/`

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

FILES TO CREATE/MODIFY:
```text
edge/src/            # domain services, command handlers, repositories
edge/migrations/     # owned entities only
edge/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-edge-004.yaml
contracts/events/spec-edge-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-edge-004/
```

REQUIREMENTS TO IMPLEMENT (25):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| PER-FR-001 | Peripheral registry | Barcode scanners, balances, printers, testers, cameras/vision and other peripherals have registered identity and site/station assignment. | Attributable source. |
| PER-FR-002 | Station profile | Define station/workcell allowed device types and intended operations. | Correct device use. |
| PER-FR-003 | Barcode scanner | Support keyboard wedge only for noncritical/simple cases; preferred explicit scanner SDK/serial/HID service with source identity. | Source clarity. |
| PER-FR-004 | Barcode parsing | Versioned barcode parser supports GS1/UDI/custom/internal labels; raw scan retained. | Deterministic parsing. |
| PER-FR-005 | Scan validation | Server/domain validates scanned business object against expected material/product/lot/serial/location/action. | No trust in text. |
| PER-FR-006 | Duplicate scan | Debounce/duplicate handling does not suppress legitimate repeated actions; operation context determines idempotency. | Safe UX. |
| PER-FR-007 | Balance integration | Registered balance delivers value, unit, stable flag, device time/status and calibration identity. | Weighing evidence. |
| PER-FR-008 | Stable reading | Device/adapter-specific stable criteria must be released/configured; UI cannot accept transient value as stable. | Accuracy. |
| PER-FR-009 | Balance tare | Tare operation/status captured when workflow requires; software distinguishes gross/tare/net. | Reproducibility. |
| PER-FR-010 | Manual fallback | Manual weight/result only if workflow policy permits and reason/verifier requirements met. | Controlled fallback. |
| PER-FR-011 | Label printer | Print request uses exact released template/artwork, variable data and printer identity. | Controlled labeling. |
| PER-FR-012 | Print acknowledgement | Where printer supports it, capture job/print status; lack of status does not fabricate successful physical application. | Boundary. |
| PER-FR-013 | Reprint | Reprint is a new controlled print action with reason/counter. | Trace. |
| PER-FR-014 | Tester integration | Functional/device testers return test ID, unit/serial, method/program version, values, result, raw evidence and tester identity. | eDHR evidence. |
| PER-FR-015 | Vision system | Capture inspected unit/lot, recipe/model version, defect classification, image/evidence ref and system confidence if used. | Inspection trace. |
| PER-FR-016 | AI/vision decision | Automated pass/fail only if validated approved model/rule; otherwise advisory result requiring operator/QA decision. | Controlled AI. |
| PER-FR-017 | File-producing instrument | Import original file/export with checksum and parse result through versioned adapter. | Data integrity. |
| PER-FR-018 | Peripheral eligibility | Calibration/qualification/maintenance status checked through Equipment module before regulated use. | Valid equipment. |
| PER-FR-019 | Station lock | Critical workflow binds expected station/peripheral so another nearby device cannot submit without authorization. | Context. |
| PER-FR-020 | Hot-plug/reconnect | Reconnect preserves device identity and generates session boundary. | Resilience. |
| PER-FR-021 | Device substitution | Replacement device requires eligibility and station policy; no hidden substitution. | Trace. |
| PER-FR-022 | Local UI | Operator sees device connected/eligible/stable/source status before action. | Transparency. |
| PER-FR-023 | Raw input preservation | Raw scan/weight/test payload retained or hashed/evidenced where required. | Auditability. |
| PER-FR-024 | Security | USB/serial/network device access restricted to gateway service; arbitrary removable-storage use prohibited by deployment hardening. | Security. |
| PER-FR-025 | Simulation | Peripheral simulators available for CI and validation. | Testability. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| captureBarcodeScan() | Scanner adapter | raw_scan; scanner_id; station_id; timestamp | ScanObservation{raw,parsed,parser_version} | BarcodeScanned; BARCODE_PARSE_FAILED |
| validateScanForAction() | UI/domain action | ScanObservation; expected_entity_type; action_context | ScanValidationResult | WRONG_MATERIAL/WRONG_LOT/WRONG_SERIAL/LOCATION_MISMATCH |
| readStableWeight() | Dispensing UI | balance_id; timeout_ms; expected_uom | StableWeightReading | READING_UNSTABLE/BALANCE_INELIGIBLE |
| recordTare() | Dispensing workflow | balance_id; tare_context | TareReceipt | TARE_FAILED |
| submitManualWeight() | Operator UI | value; uom; reason; verifier/signature if required | ManualWeightResult | MANUAL_FALLBACK_NOT_ALLOWED |
| createPrintJob() | Packaging/dispensing module | template_version; variable_data; printer_id; copies | PrintJobReceipt | LABEL_TEMPLATE_INVALID/PRINTER_INELIGIBLE |
| reprintLabel() | Authorized UI | original_print_job_id; reason | PrintJobReceipt | REPRINT_REASON_REQUIRED |
| ingestTesterResult() | Tester adapter | tester payload; tester_id; program_version; unit/serial | CanonicalTesterResult | TESTER_PROGRAM_MISMATCH/UNIT_ID_MISMATCH |
| ingestVisionResult() | Vision adapter | inspection payload; model/recipe version; image refs | VisionInspectionResult | VISION_MODEL_UNAPPROVED |
| registerPeripheralSession() | Gateway runtime | device_id; station_id; connection metadata | PeripheralSession | DEVICE_NOT_REGISTERED/STATION_NOT_ALLOWED |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- <ScannerStatus />
- <ScanInputAction />
- <BalanceStatus />
- <LiveStableWeight />
- <ControlledPrintAction />
- <TesterResultPanel />
- <VisionEvidencePanel />

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Fail closed on any compliance-critical dependency outage; no degraded-mode commit.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- derive from the requirement table above
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_46_SPEC-EDGE-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EDGE-004/<test_case_id>/`.
- A failed case is evidence: never delete it, re-run over it, or edit the expected result to make it pass.
  Raise a defect, record the reference, re-execute as a new dated execution.

TRACEABILITY & STATUS (mandatory at the end of this prompt):
- Update `traceability/TRACEABILITY_MASTER.csv` for every requirement you touched: `build_stage`,
  `verification_state`, `test_case_ids`, `evidence_location`.
- Update `status/build-status.json`: set this module's `stage`, append to `stage_history`, set
  `requirements_state` per requirement, and set `test_pass` / `test_fail` / `test_blocked` from the
  actual recorded results.
- You may only set stages you can evidence, up to and including CODE_COMPLETE and the test states.
  `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans, never by you.
- Run `python tooling/status/rollup.py` and include the printed summary in your completion report.

VALIDATION / TRACEABILITY:
- update `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` and `29_VALIDATION_TRACEABILITY_MASTER.csv`
- state IQ/OQ/PQ impact; HIGHER-PROCESS-RISK functions need retained objective evidence
- Part 11 impact where signatures are involved (Document 88)

ACCEPTANCE CRITERIA:
- every requirement above implemented, traced and tested
- all listed tests executed with real results
- no architecture guardrail violation
- contracts committed before implementation and compatible

SPEC_GAP RULE:
Do not guess regulated behaviour. Append unresolved decisions to `docs/generated/18_SPEC_GAPS.md`
with affected requirements, risk, options and blocking status, then continue only on unaffected work.

BEFORE COMPLETION:
Run lint, typecheck, unit, contract, integration and guardrail checks. Report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; **test cases executed with PASS/FAIL/BLOCKED counts and
the case ids of every failure**; validation impact; **traceability and status files updated (include the
rollup summary)**; unresolved SPEC_GAPs; known limitations.
