# Claude Code prompt — WP-01 / Document 06: Record Version Vault, Locking, Amendment & Controlled Correction

TASK:
Implement the Record Version Vault, Locking, Amendment & Controlled Correction module (SPEC-GXP-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_06_Record_Version_Vault_Locking_Amendment_Correction_Specification_v1_1_IMPLEMENTATION_READY.md`
- Requirement IDs: VLT-FR-001..030 (30)
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

- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `services/gxp-api/src/modules/vault` and its tests
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
services/gxp-api/src/modules/vault/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/vault/migrations/     # owned entities only
services/gxp-api/src/modules/vault/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-gxp-004.yaml
contracts/events/spec-gxp-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-gxp-004/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| VLT-FR-001 | Immutable released version | Every released master, specification, controlled document snapshot and regulated final record receives immutable vault version ID. | Released content cannot be edited in place. |
| VLT-FR-002 | Canonical snapshot | Vault stores canonical structured representation sufficient to reproduce content/meaning independent of mutable Frappe master. | Changing Frappe draft does not change vault object. |
| VLT-FR-003 | Cryptographic digest | Calculate and store algorithm + digest over canonical representation and evidence manifest. | Integrity test reproducible. |
| VLT-FR-004 | Release metadata | Store object type, business ID, version, status, effective dates, release reason, authors/approvers/signatures and software/schema versions. | Full release context retained. |
| VLT-FR-005 | Evidence manifest | Link immutable file/evidence IDs, hashes, media types and versions used by released object. | Attachments cannot silently swap. |
| VLT-FR-006 | Batch issue snapshot | At batch/device work issuance, freeze exact released recipe/specification/material/equipment/rule references required for that execution. | Later master change cannot rewrite active/history. |
| VLT-FR-007 | Snapshot dependency closure | Snapshot captures exact IDs/versions/hashes of dependent released objects rather than only business names. | Dependency reproducible. |
| VLT-FR-008 | Effective dating | Released versions have controlled effective-from/effective-to/obsolete lifecycle; selection engine prevents unauthorized obsolete/future use. | Batch issue chooses eligible version. |
| VLT-FR-009 | Supersession | New approved version supersedes prior for future use but never deletes prior version or its historical references. | Old batches still resolve old version. |
| VLT-FR-010 | Controlled correction | Corrections to regulated completed/released records create amendment/superseding version referencing original, reason, authority, signatures and changed fields. | Original remains visible. |
| VLT-FR-011 | Correction eligibility | Policy defines which record states/types permit correction, who may initiate/approve, and whether downstream impact assessment is required. | Unauthorized correction blocked. |
| VLT-FR-012 | No silent overwrite | Any attempt to overwrite a vault object/version through application API is rejected. | Immutability negative test. |
| VLT-FR-013 | Void/cancel semantics | Where a record must be voided/cancelled, retain original and add controlled status/event/reason rather than physical deletion. | Voided history remains. |
| VLT-FR-014 | Signature binding | Signatures reference exact vault version/hash or pre-commit canonical target that becomes exact resulting version. | Signature cannot float to new content. |
| VLT-FR-015 | Audit linkage | Version creation/release/supersession/correction is represented in Audit Ledger. | Vault history and audit reconcile. |
| VLT-FR-016 | Inspection retrieval | Authorized user can retrieve any historical version plus relationships, signatures, audit and evidence manifest. | Historical record is readable. |
| VLT-FR-017 | Deterministic export | Export service can regenerate human-readable representation from stored authoritative version using controlled renderer/version or preserve signed release export. | Meaning remains available after upgrade. |
| VLT-FR-018 | Schema evolution | Older canonical schema versions remain readable. Migrations never rewrite historical semantic content without controlled migration provenance. | Old records survive software upgrade. |
| VLT-FR-019 | Retention class | Each object gets retention class based on profile/record type/customer policy; no normal application deletion. | Retention auditable. |
| VLT-FR-020 | Legal/quality hold | Hold prevents disposal/archival transitions and is itself controlled/audited. | Hold honored. |
| VLT-FR-021 | Archive tiering | Move old vault objects/evidence to archival storage only if integrity, retrieval and meaning are preserved. | Archive retrieval qualified. |
| VLT-FR-022 | WORM-capable evidence | Released file packages/checkpoints may use object-storage retention lock/WORM where deployment supports it. | Infrastructure immutability can be verified. |
| VLT-FR-023 | Version numbering | Use immutable internal version IDs plus human/business version labels; never rely only on editable semantic label. | Duplicate labels cannot confuse history. |
| VLT-FR-024 | Content addressing | Evidence objects may be deduplicated by digest while preserving record-specific manifest references and retention. | No cross-record mutation. |
| VLT-FR-025 | Cross-constituent snapshot | DDCP snapshot can bind exact drug constituent version, device constituent version, compatibility version and final assembly/release rules. | Final DDCP scope reproducible. |
| VLT-FR-026 | Migration provenance | Imported historical versions are flagged migrated, with source system, source ID, extraction checksum and migration batch. | Native vs migrated distinguishable. |
| VLT-FR-027 | Restore verification | Backup restore checks version counts, hashes, evidence manifests, signatures and audit relationships. | Restored vault trustworthy. |
| VLT-FR-028 | Access control | Draft authorship access does not imply released-vault write access; runtime exposes read plus controlled release/correction commands only. | Least privilege. |
| VLT-FR-029 | Reference integrity | Foreign references to released version use immutable identifiers and DB constraints/service validation; no dangling reference on normal operation. | Batch can always resolve snapshot. |
| VLT-FR-030 | Disposition package | Final release/closure creates or references a complete immutable record package suitable for regulatory export and long-term retrieval. | Release package complete. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (5 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `vault_object` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `vault_evidence_manifest` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `gxp_vault_object` | 19 | PostgreSQL (GxP Core, authoritative) |
| `gxp_vault_evidence` | 7 | PostgreSQL (GxP Core, authoritative) |
| `gxp_record_correction` | 12 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /vault/v1/masters/{type}/{businessId}/release` | yes | policy lookup (Doc 106) |
| `GET /vault/v1/objects/{objectId}` | no | — |
| `GET /vault/v1/objects/{objectId}/integrity` | no | — |
| `POST /vault/v1/objects/{objectId}/corrections` | yes | — |
| `POST /vault/v1/corrections/{id}/complete` | yes | — |
| `GET /vault/v1/business/{type}/{businessId}/versions` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- View Historical Version
- Request Correction
- Impact Assessment
- Compare Old vs Proposed
- Signature/Approval
- Corrected Version History

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
- released object write attempt
- master version supersession
- batch snapshot after master changes
- attachment swap attempt
- correction old/new
- void/cancel
- signature remains on old version
- new signature on amendment
- effective-date selection
- obsolete-version issue attempt
- schema upgrade readability
- backup/restore hashes
- archive/retrieve
- DDCP constituent snapshot
- migration provenance
- happy path
- authorization denial
- validation failure
- stale/concurrent write
- duplicate/replay where applicable
- dependency outage
- restart/recovery
- data integrity
- audit verification
- signature verification where applicable
- field order changes produce same hash
- semantic value change produces different hash
- equivalent decimal formatting normalized
- timestamps normalized
- array order behavior defined by field semantics
- null vs missing behavior defined
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-01/Document_06_SPEC-GXP-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-GXP-004/<test_case_id>/`.
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
