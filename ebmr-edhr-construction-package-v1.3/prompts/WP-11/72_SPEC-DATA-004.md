# Claude Code prompt — WP-11 / Document 72: Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle

TASK:
Implement the Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle module (SPEC-DATA-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_72_Immutable_Evidence_Object_Storage_WORM_Archive_File_Lifecycle_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: OBJ-FR-001..030 (30)
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
- `infrastructure` and its tests
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
infrastructure/src/            # domain services, command handlers, repositories
infrastructure/migrations/     # owned entities only
infrastructure/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-data-004.yaml
contracts/events/spec-data-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-004/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| OBJ-FR-001 | Evidence object abstraction | Support S3-compatible, Azure Blob and on-prem object storage through one EvidenceStore provider. | Cloud-neutral. |
| OBJ-FR-002 | Content addressing | Evidence object identified by generated immutable evidence ID plus SHA-256/approved digest; optional content-addressed path. | Integrity. |
| OBJ-FR-003 | Upload staging | Upload enters STAGED/QUARANTINE until checksum/type/security validation completes. | Safe ingestion. |
| OBJ-FR-004 | Immutable promotion | Validated evidence promoted/finalized into immutable object key/version; overwrite prohibited. | History. |
| OBJ-FR-005 | Metadata authority | PostgreSQL stores evidence metadata, ownership, hash, size, MIME, source, retention, legal hold and object version/reference. | Searchable control. |
| OBJ-FR-006 | WORM/immutability | Release/archive profile supports Object Lock/immutability policy or equivalent on-prem retention lock. | Tamper resistance. |
| OBJ-FR-007 | Retention mode | Governance/compliance/provider-specific retention mode selected by deployment and legal requirements; config protected. | Controlled storage. |
| OBJ-FR-008 | Evidence manifest | Regulated record/release package references immutable manifest of evidence IDs/hashes/versions. | Inspection. |
| OBJ-FR-009 | Large raw evidence | Machine files, images, PDFs, instrument exports, reports and cycle evidence stored without loading into DB blob columns. | Scale. |
| OBJ-FR-010 | Multipart upload | Large files use resumable/multipart upload with final whole-object integrity verification. | Reliability. |
| OBJ-FR-011 | Pre-signed URL | Temporary upload/download URLs can be issued only after authorization and short expiry; URL alone not permanent authority. | Secure transfer. |
| OBJ-FR-012 | Download authorization | Service validates subject/resource/evidence access before generating download token. | Confidentiality. |
| OBJ-FR-013 | Encryption | Provider at-rest encryption with customer/dedicated keys where profile requires; TLS in transit. | Security. |
| OBJ-FR-014 | Malware/quarantine | Externally uploaded files scanned/quarantined before ordinary access where applicable. | Security. |
| OBJ-FR-015 | Type validation | MIME/extension/content signature/size policies validated; filenames treated as metadata only. | Upload safety. |
| OBJ-FR-016 | Hash verification | Hash verified at ingest, copy/archive, restore and optionally periodic integrity scans. | Integrity. |
| OBJ-FR-017 | No in-place edit | Corrected document/file creates new evidence object/version and relationship; original retained. | History. |
| OBJ-FR-018 | Legal hold | Hold prevents normal expiry/delete regardless of retention schedule. | Governance. |
| OBJ-FR-019 | Retention expiration | Purge eligibility determined by Records service + holds + reference policy, not bucket lifecycle alone. | Controlled deletion. |
| OBJ-FR-020 | Lifecycle tiers | Archive/cold tiers allowed if retrieval SLA/validation/immutability requirements met. | Cost control. |
| OBJ-FR-021 | Cross-region/site replication | Optional replication configured per deployment/DR profile; replica integrity monitored. | DR. |
| OBJ-FR-022 | Backup distinction | Replication/versioning is not backup; backup/restore strategy explicitly tested. | Resilience. |
| OBJ-FR-023 | Missing object | Broken evidence metadata→object relation triggers critical integrity event and release/inspection blocker where relevant. | Fail safe. |
| OBJ-FR-024 | Orphan detection | Unreferenced objects/staged uploads detected and handled via controlled cleanup policies. | Hygiene. |
| OBJ-FR-025 | Evidence provenance | Store producer, source device/system, uploaded actor/service, timestamps and source hash where supplied. | Traceability. |
| OBJ-FR-026 | Rendering | Generated PDFs/renditions are separate evidence objects linked to canonical data/version and renderer version. | Reproducibility. |
| OBJ-FR-027 | Export package | Inspection export creates manifest, files, hashes and metadata without changing source evidence. | Portable evidence. |
| OBJ-FR-028 | Restore validation | Restored archive verifies object count/manifests/hashes and sampled retrieval before healthy. | DR assurance. |
| OBJ-FR-029 | Provider migration | Storage-provider migration uses manifest/hash copy verification and retains old location until acceptance. | Cloud portability. |
| OBJ-FR-030 | No bucket browsing | Users/apps do not receive broad bucket listing credentials; access is resource-scoped. | Least privilege. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| stageEvidenceUpload() | UI/Edge/Integration | owner context; filename; MIME; size; expected hash? | EvidenceUploadSession | EvidenceUploadStaged; EVIDENCE_UPLOAD_DENIED |
| finalizeEvidenceUpload() | Upload callback/service | evidence_id; provider object/version; calculated hash; size | EvidenceRef | EvidenceFinalized; EVIDENCE_HASH_MISMATCH |
| createEvidenceManifest() | Vault/Release/Export | owner record/version; evidence refs; manifest type | EvidenceManifestRef | EvidenceManifestCreated |
| authorizeEvidenceDownload() | Download API | AuthContext; evidence_id; purpose | EvidenceDownloadGrant | EVIDENCE_ACCESS_DENIED |
| verifyEvidenceIntegrity() | Scheduled/restore/inspection | evidence scope; sampling/full mode | EvidenceIntegrityReport | EVIDENCE_MISSING/EVIDENCE_HASH_MISMATCH |
| applyEvidenceLegalHold() | Records/Legal | evidence scope; hold_id; reason | HoldReceipt | EvidenceLegalHoldApplied |
| purgeExpiredEvidence() | Retention worker | eligibility set; policy version | PurgeReport | EVIDENCE_PURGE_BLOCKED |
| migrateEvidenceProvider() | Migration tool | source provider; target provider; manifest scope | ProviderMigrationReport | EvidenceProviderMigrated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `evidence_object` | 16 | Object store (WORM evidence) + PostgreSQL metadata |
| `evidence_manifest` | 5 | Object store (WORM evidence) + PostgreSQL metadata |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /evidence/v1/uploads` | yes | — |
| `POST /evidence/v1/{id}:finalize` | yes | — |
| `GET /evidence/v1/{id}/download` | no | — |
| `POST /evidence/v1/manifests` | yes | — |
| `POST /evidence/v1/{id}/legal-holds` | yes | — |
| `POST /evidence/v1/integrity-checks` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `EvidenceUploadStaged` | SPEC-DATA-004 | event_id |
| `EvidenceFinalized` | SPEC-DATA-004 | event_id |
| `EvidenceHashMismatch` | SPEC-DATA-004 | event_id |
| `EvidenceMissing` | SPEC-DATA-004 | event_id |
| `EvidenceLegalHoldApplied` | SPEC-DATA-004 | event_id |
| `EvidencePurged` | SPEC-DATA-004 | event_id |
| `EvidenceProviderMigrated` | SPEC-DATA-004 | event_id |

UI SURFACES:
- Evidence Browser (authorized metadata)
- Upload/Quarantine
- Integrity Status
- Retention/Hold
- Archive Tier
- Evidence Manifest
- Provider Migration

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- hash mismatch on upload
- malware quarantine
- overwritten provider object detected
- legal hold blocks lifecycle deletion
- cold archive restore
- missing object
- provider migration hash reconciliation
- presigned URL expiry
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_72_SPEC-DATA-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-004/<test_case_id>/`.
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
