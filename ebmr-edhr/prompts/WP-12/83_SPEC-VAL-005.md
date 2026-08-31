# Claude Code prompt — WP-12 / Document 83: Installation Qualification (IQ) & Installed Baseline Verification

TASK:
Implement the Installation Qualification (IQ) & Installed Baseline Verification module (SPEC-VAL-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_83_Installation_Qualification_IQ_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: IQ-FR-001..021 (21)
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
contracts/openapi/spec-val-005.yaml
contracts/events/spec-val-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-005/
```

REQUIREMENTS TO IMPLEMENT (21):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| IQ-FR-001 | Installation scope | Identify installed components, versions, environment topology and responsibilities. | Known installation. |
| IQ-FR-002 | Prerequisites | Verify OS/K8s/runtime/network/DNS/NTP/storage/DB/object/PKI/backups. | Ready environment. |
| IQ-FR-003 | Artifact identity | Verify deployed image/package digest/signature matches approved release. | Correct software. |
| IQ-FR-004 | SBOM/provenance | Reference approved SBOM/build provenance. | Supply-chain. |
| IQ-FR-005 | Configuration baseline | Capture environment/config/feature flags without secret values. | Reproducibility. |
| IQ-FR-006 | Secret/certs | Verify required secret references/cert validity/scope. | Security. |
| IQ-FR-007 | DB/schema | Verify PostgreSQL/MariaDB versions/migrations/schemas. | Persistence. |
| IQ-FR-008 | Object store | Verify encryption/immutability/access/evidence operations. | Evidence. |
| IQ-FR-009 | NATS/Temporal | Verify version/config/auth/storage/namespace. | Platform. |
| IQ-FR-010 | Frappe site | Verify Frappe app/site/migrations. | UI. |
| IQ-FR-011 | Network controls | Verify required and forbidden network paths. | Security. |
| IQ-FR-012 | Time sync | Verify UTC/NTP within approved threshold. | Chronology. |
| IQ-FR-013 | Backup config | Verify backup/PITR/key/monitoring configuration exists. | Recovery. |
| IQ-FR-014 | Observability | Verify critical metrics/logs/alerts registered. | Operations. |
| IQ-FR-015 | Host inventory | Capture nodes/specs/ownership. | Trace. |
| IQ-FR-016 | External endpoints | Verify IdP/ERP/LIMS/Edge endpoint/trust configs in scope. | Integration. |
| IQ-FR-017 | Environment segregation | Verify validation/prod data/secrets/endpoints not mixed. | SDLC. |
| IQ-FR-018 | Exceptions | Mismatches become validation deviations before IQ completion. | No silent variance. |
| IQ-FR-019 | Delta IQ | Upgrade/rebuild supports risk-based delta/full IQ. | Lifecycle. |
| IQ-FR-020 | Automated IQ | Controlled install/preflight automation may generate primary evidence. | Efficiency. |
| IQ-FR-021 | Approval | IQ requires reviewer approval and deviation disposition. | Gate. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createIQProtocol() | Validation/Installer | environment; release; deployment profile; component inventory | IQProtocol | IQProtocolCreated |
| captureInstalledInventory() | Qualification agent | environment | InstalledInventory | InstalledInventoryCaptured |
| verifyInstalledArtifact() | IQ executor | component; expected digest/signature/version | IQCheckResult | InstalledArtifactVerified/ARTIFACT_MISMATCH |
| verifyEnvironmentPrerequisites() | IQ executor | environment/profile | IQCheckSet | IQPrerequisitesVerified |
| completeIQExecution() | Validation executor | IQ run; results; deviations | IQResult | IQCompleted |
| approveIQ() | Validation/QA | IQ result; signature | ApprovedIQ | IQApproved |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `iq_protocol` | 2 | PostgreSQL (GxP Core, authoritative) |
| `iq_execution` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/iq/protocols` | yes | — |
| `POST /validation/v1/iq/executions` | yes | — |
| `POST /validation/v1/iq/executions/{id}/complete` | yes | — |
| `POST /validation/v1/iq/executions/{id}/approve` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (4):
| Event type | Producer | Dedupe key |
|---|---|---|
| `InstalledInventoryCaptured` | SPEC-VAL-005 | event_id |
| `IQPrerequisitesVerified` | SPEC-VAL-005 | event_id |
| `IQCompleted` | SPEC-VAL-005 | event_id |
| `IQApproved` | SPEC-VAL-005 | event_id |

UI SURFACES:
- IQ Protocol
- Installed Inventory
- Prerequisite Checks
- IQ Deviations
- IQ Approval

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
- wrong image digest
- unsupported DB version
- NTP missing
- backup absent
- cert expired
- forbidden path open
- validation endpoint points to prod ERP
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-12/Document_83_SPEC-VAL-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-005/<test_case_id>/`.
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
