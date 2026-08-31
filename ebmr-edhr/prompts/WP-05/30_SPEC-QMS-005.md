# Claude Code prompt — WP-05 / Document 30: Document Control

TASK:
Implement the Document Control module (SPEC-QMS-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_30_Document_Control_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DOC-FR-001..024 (24)
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
- `services/gxp-api/src/modules/qms` and its tests
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
services/gxp-api/src/modules/qms/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/qms/migrations/     # owned entities only
services/gxp-api/src/modules/qms/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-qms-005.yaml
contracts/events/spec-qms-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-005/
```

REQUIREMENTS TO IMPLEMENT (24):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DOC-FR-001 | Document master | Controlled document has immutable business identity, type, owner, department/site/profile and lifecycle. | Canonical identity. |
| DOC-FR-002 | Versioning | Each revision is separate version; released content immutable. | History. |
| DOC-FR-003 | Content storage | Store authoritative content/file in Vault/Evidence with hash and version. | Integrity. |
| DOC-FR-004 | Source/rendition | Differentiate editable source from released rendition/PDF where applicable. | Meaning preserved. |
| DOC-FR-005 | Review workflow | Technical/Quality/Regulatory reviewers based on document type. | Appropriate review. |
| DOC-FR-006 | Approval/e-signature | Controlled release requires policy-defined signatures. | Attributable. |
| DOC-FR-007 | Effective date | Version becomes usable only at approved effective date after prerequisites. | Controlled use. |
| DOC-FR-008 | Supersession | New effective version supersedes future use; historical records retain exact old version. | No drift. |
| DOC-FR-009 | Obsolete | Obsolete versions removed from normal current-use view but historically retrievable. | Prevent unintended use. |
| DOC-FR-010 | Controlled copy | Optional numbered controlled-copy issue/recipient/location/status. | Distribution control. |
| DOC-FR-011 | Uncontrolled copy marking | Print/download may be watermarked/marked uncontrolled per policy. | User awareness. |
| DOC-FR-012 | Periodic review | Review interval/due date with reminders/escalation. | Lifecycle. |
| DOC-FR-013 | Training impact | Release determines training assignment to roles/sites/users. | Training integrated. |
| DOC-FR-014 | Acknowledgment | Read-and-understand training is separate from approval signature. | Semantics. |
| DOC-FR-015 | Change link | Major revision may require Change Control. | Trace. |
| DOC-FR-016 | Relationships | Parent/child/reference links by exact version or explicit current-reference semantics. | Dependency clarity. |
| DOC-FR-017 | Forms/templates | Controlled forms and executable templates are versioned/released. | No uncontrolled forms. |
| DOC-FR-018 | External documents | Track external standards/guidance/customer specs with source/revision/applicability without unauthorized copying. | External control. |
| DOC-FR-019 | Access | Document-class/site/role access server-side. | Confidentiality. |
| DOC-FR-020 | Distribution audit | Audit controlled-copy generation/distribution where policy requires. | Evidence. |
| DOC-FR-021 | Retirement | Retire with reason/effective date/impact. | History. |
| DOC-FR-022 | Migration | Imported historical docs retain source/provenance; no fabricated approvals. | Integrity. |
| DOC-FR-023 | Search | Current/obsolete search by code/title/type/owner/site/effective date. | Usability. |
| DOC-FR-024 | Export | Revision/approval/effective/distribution history exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `controlled_document` | 8 | PostgreSQL (GxP Core, authoritative) |
| `controlled_document_version` | 11 | PostgreSQL (GxP Core, authoritative) |
| `controlled_copy` | 4 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (7):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /documents/v1/drafts` | yes | — |
| `POST /documents/v1/drafts/{id}/submit` | yes | — |
| `POST /documents/v1/drafts/{id}/release` | yes | policy lookup (Doc 106) |
| `POST /documents/v1/versions/{id}/make-effective` | yes | — |
| `POST /documents/v1/versions/{id}/obsolete` | yes | — |
| `POST /documents/v1/versions/{id}/controlled-copies` | yes | — |
| `GET /documents/v1/{code}/versions` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `DocumentVersionReleased` | SPEC-QMS-005 | event_id |
| `DocumentVersionEffective` | SPEC-QMS-005 | event_id |
| `DocumentVersionSuperseded` | SPEC-QMS-005 | event_id |
| `DocumentObsoleted` | SPEC-QMS-005 | event_id |
| `ControlledCopyIssued` | SPEC-QMS-005 | event_id |
| `DocumentPeriodicReviewDue` | SPEC-QMS-005 | event_id |

UI SURFACES:
- Document Library
- Document Editor/Upload
- Review/Approval
- Version Compare
- Effective/Obsolete
- Controlled Copies
- Periodic Review
- Training Impact
- Audit

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- DB unavailable: no regulated state transition.
- Signature/Policy unavailable: fail closed where required.
- Notification/outbox failures retry.
- Stale version rejects.
- Scheduled due/expiry jobs resume from persisted records.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- new SOP release
- future effective date
- obsolete old version
- historical batch opens old version
- controlled copy
- periodic review overdue
- training assignment
- unauthorized access
- migration
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_30_SPEC-QMS-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-005/<test_case_id>/`.
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
