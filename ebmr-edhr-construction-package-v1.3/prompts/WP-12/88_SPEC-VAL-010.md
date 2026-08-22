# Claude Code prompt — WP-12 / Document 88: 21 CFR Part 11 Electronic Records & Electronic Signature Validation

TASK:
Implement the 21 CFR Part 11 Electronic Records & Electronic Signature Validation module (SPEC-VAL-010) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_88_21CFR_Part11_Electronic_Records_Signature_Validation_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: P11-FR-001..026 (26)
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
- `validation` and its tests
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
validation/src/            # domain services, command handlers, repositories
validation/migrations/     # owned entities only
validation/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-val-010.yaml
contracts/events/spec-val-010/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-010/
```

REQUIREMENTS TO IMPLEMENT (26):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| P11-FR-001 | Part 11 scope | Identify records/signatures relied upon electronically under predicate rules. | Scope. |
| P11-FR-002 | Accuracy/reliability | Verify intended functions create accurate/reliable records. | 11.10(a). |
| P11-FR-003 | Altered record discernment | Verify invalid/altered record detection. | 11.10(a). |
| P11-FR-004 | Human-readable copies | Verify accurate complete human-readable export. | 11.10(b). |
| P11-FR-005 | Electronic copies | Verify electronic export with required metadata. | 11.10(b). |
| P11-FR-006 | Retention/retrieval | Verify ready retrieval through retention/archive. | 11.10(c). |
| P11-FR-007 | Access | Verify authorized-only record/system access. | 11.10(d). |
| P11-FR-008 | Audit trail | Verify secure timestamped audit, prior values, retention/review. | 11.10(e). |
| P11-FR-009 | Operational checks | Verify sequencing prevents invalid workflow order. | 11.10(f). |
| P11-FR-010 | Authority checks | Verify role/qualification/SoD/signature authority. | 11.10(g). |
| P11-FR-011 | Device/source checks | Verify scanner/balance/Edge/device validity as applicable. | 11.10(h). |
| P11-FR-012 | Training | Verify relevant training/qualification controls. | 11.10(i). |
| P11-FR-013 | Signature accountability policy | Customer responsibility/evidence documented. | 11.10(j). |
| P11-FR-014 | Documentation controls | Verify controlled system documentation/access/change history. | 11.10(k). |
| P11-FR-015 | Signature manifestation | Verify signer printed name, time and meaning in display/export. | 11.50. |
| P11-FR-016 | Signature linking | Verify signature cannot be transferred to falsify another record by ordinary means. | 11.70. |
| P11-FR-017 | Unique identity | Verify unique signer mapping and identity verification responsibility. | 11.100. |
| P11-FR-018 | Signature components | Verify configured signing ceremony satisfies applicable controls. | 11.200. |
| P11-FR-019 | Version binding | Signature binds exact record/version/hash/action/meaning. | Platform control. |
| P11-FR-020 | Fresh step-up | V1 validates fresh step-up for every regulated signature per Document 04. | Stronger baseline. |
| P11-FR-021 | Failed signing | Expired challenge/stale version/replay/wrong signer fails. | Security. |
| P11-FR-022 | Correction | Signed/released correction creates new version, not edit. | Integrity. |
| P11-FR-023 | Clock | Signature/audit UTC consistency verified. | Chronology. |
| P11-FR-024 | Open systems | Additional controls assessed where deployment/use is open-system context. | Scope. |
| P11-FR-025 | Customer certification | §11.100 certification/support remains customer responsibility. | Responsibility. |
| P11-FR-026 | Control matrix | Every applicable control maps test/evidence/config/procedure. | Inspection. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createPart11Assessment() | Validation/Regulatory | record types; predicate rules; deployment/use | Part11Assessment | Part11AssessmentCreated |
| derivePart11TestSuite() | Validation | assessment; platform/customer config | Part11TestSuite | Part11TestSuiteDerived |
| verifySignatureManifestation() | Automated/manual test | signed record/export | ControlTestResult | SignatureManifestationVerified |
| verifySignatureRecordLink() | Validation | signature ID; record versions | ControlTestResult | SignatureRecordLinkVerified |
| verifyRecordCopyCompleteness() | Validation | record/version; export types | CopyVerification | ElectronicRecordCopyVerified |
| approvePart11Qualification() | QA/Validation | assessment/tests/deviations; signature | Part11Qualification | Part11QualificationApproved |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `part11_scope_assessment` | 6 | PostgreSQL (GxP Core, authoritative) |
| `part11_control_evidence` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (3):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/part11/assessments` | yes | — |
| `GET /validation/v1/part11/{id}/test-suite` | no | — |
| `POST /validation/v1/part11/{id}/approve` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (3):
| Event type | Producer | Dedupe key |
|---|---|---|
| `Part11AssessmentCreated` | SPEC-VAL-010 | event_id |
| `Part11TestSuiteDerived` | SPEC-VAL-010 | event_id |
| `Part11QualificationApproved` | SPEC-VAL-010 | event_id |

UI SURFACES:
- Part 11 Scope
- Control Matrix
- Record Copy Test
- Signature Validation
- Customer Responsibility
- Part 11 Package

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- unauthorized record access
- audit old/new
- wrong workflow order
- invalid scanner source
- signature manifestation
- signature reassociation denied
- expired challenge
- archive retrieval
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-12/Document_88_SPEC-VAL-010_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-010/<test_case_id>/`.
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
