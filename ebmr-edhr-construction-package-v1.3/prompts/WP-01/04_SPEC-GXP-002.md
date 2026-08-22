# Claude Code prompt — WP-01 / Document 04: 21 CFR Part 11 Electronic Signature

TASK:
Implement the 21 CFR Part 11 Electronic Signature module (SPEC-GXP-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_04_Part_11_Electronic_Signature_Specification_v1_1_IMPLEMENTATION_READY.md`
- Requirement IDs: SIG-FR-001..030 (30)
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
- `services/gxp-api/src/modules/signature` and its tests
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
services/gxp-api/src/modules/signature/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/signature/migrations/     # owned entities only
services/gxp-api/src/modules/signature/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-gxp-002.yaml
contracts/events/spec-gxp-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-gxp-002/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| SIG-FR-001 | Unique signer identity | Every electronic signature is linked to one immutable individual subject identifier. Display names may change historically, but signer subject cannot be reassigned. | Historical signature remains attributable after rename/deactivation. |
| SIG-FR-002 | Identity verification responsibility | Customer organization must have a controlled process to verify identity before granting electronic-signature authority; system stores status/evidence reference where configured. | Unverified identity cannot receive signing entitlement. |
| SIG-FR-003 | Signature meaning catalogue | Controlled meanings include Performed, Verified, Reviewed, Approved, Released, Rejected, Authored, Witnessed and customer-approved extensions. | Meaning is explicit in challenge, record and export. |
| SIG-FR-004 | Signature policy mapping | Record/action policy defines required meaning, signer role/qualification, number/order of signatures, independent signer restrictions and authentication assurance. | Client cannot alter required signer policy. |
| SIG-FR-005 | Challenge creation | Create server-side unique signature challenge containing challenge ID, signer subject, tenant/site, record ID, version/hash, action/meaning, nonce and expiry. | Challenge is unique and short-lived. |
| SIG-FR-006 | Fresh step-up authentication | Every regulated Part 11 signature in V1 requires fresh step-up authentication through configured IdP; normal existing session alone is insufficient. | Recorded authentication time/assurance meets configured policy. |
| SIG-FR-007 | Identification components | Non-biometric signature configuration must be validated to meet applicable §11.200 component controls. IdP policy must not silently downgrade required factors/components. | Configured test demonstrates required components. |
| SIG-FR-008 | Continuous-access policy | Although Part 11 distinguishes continuous sessions, V1 intentionally applies fresh step-up for every regulated signature as a stronger product baseline. | No session-only signing path exists. |
| SIG-FR-009 | Authentication context capture | Persist trusted IdP issuer, subject, authentication time, method/AMR, assurance/ACR where available, session reference and challenge reference. | Signature proves authentication event context. |
| SIG-FR-010 | Record/version/hash binding | Signature binds exact regulated record ID, version and cryptographic hash (or canonical immutable snapshot ID). | Signature invalid for modified/superseding version. |
| SIG-FR-011 | Command/action binding | Signature also binds intended action and meaning; an approval signature cannot be reused for release or correction. | Cross-action replay rejected. |
| SIG-FR-012 | Nonce/replay prevention | Nonce/challenge is single use. Repeated callback/token cannot create second signature. | Replay negative test passes. |
| SIG-FR-013 | Challenge expiry | Expired challenge cannot be completed; new challenge requires re-evaluation against current record state/version. | Expired challenge fails closed. |
| SIG-FR-014 | Changed-record invalidation | If record or command-relevant state changes after challenge creation, signature challenge is invalidated. | Stale signing rejected. |
| SIG-FR-015 | Signature manifestation | Signed record and human-readable export show printed name, execution date/time and signature meaning. | PDF/display test confirms manifestation. |
| SIG-FR-016 | Signature/record linking | Signature record is linked by immutable identifiers/hash so it cannot be excised, copied or transferred to another record by ordinary application means. | Copying signature ID to another record fails integrity checks. |
| SIG-FR-017 | Multiple signatures | Support performer/verifier, author/approver, QA reviewer/releaser and other ordered or independent signature chains. | Order and independence enforced server-side. |
| SIG-FR-018 | Segregation of duties | Policy may require signer != performer/author/previous signer; signer role and qualification checked at signature completion time. | Same-user prohibited scenario rejected. |
| SIG-FR-019 | Failed attempts | Failed step-up, expired challenge, wrong identity, denied policy and replay attempts do not create valid signature; security-relevant attempts are logged. | No orphan valid signature on failure. |
| SIG-FR-020 | User deactivation | Disabling signer prevents future signatures but does not invalidate historical legitimate signatures. | Historical exports remain valid. |
| SIG-FR-021 | Credential reset/recovery | Identity credential recovery is handled by IdP policy; product does not expose old credentials. High-risk recovery may suspend signing until customer process completes. | Recovered account policy testable. |
| SIG-FR-022 | No signature delegation | Users cannot delegate their electronic signature. Workflow delegation may reassign work but new assignee signs as self. | Delegated task preserves distinct signer. |
| SIG-FR-023 | Service account prohibition | Service/integration/device identity cannot create human Part 11 signature. | Service token rejected on human signature endpoint. |
| SIG-FR-024 | Biometric extensibility | Architecture may accept customer IdP biometric/WebAuthn assurance later, but the GxP Signature Service still creates the regulatory signature record. | Authentication technology does not replace GxP record. |
| SIG-FR-025 | Time source | Signature execution time is assigned server-side in UTC; local timezone is presentation metadata. | Browser clock manipulation has no effect. |
| SIG-FR-026 | Signer acknowledgement | UI clearly displays what is being signed, meaning, relevant record identity/version and any required statement before step-up. | User cannot sign ambiguous hidden target. |
| SIG-FR-027 | Signature receipt | Return signature_id, challenge_id, signer subject/name, time, meaning, record/version/hash and auth context reference. | Downstream transaction can reference exact signature. |
| SIG-FR-028 | Revocation/correction handling | A historical signature is never deleted. If signed record is superseded/corrected, old signature remains on old version; new version requires required new signatures. | Correction preserves prior signatures. |
| SIG-FR-029 | Customer Part 11 certification support | Provide configurable evidence/report supporting customer's §11.100 certification/governance responsibilities; software does not submit certification automatically unless separately designed. | Responsibility remains explicit. |
| SIG-FR-030 | Inspection/reporting | Authorized auditor can list all signatures for record/batch/user/time range and export manifestation plus linkage/integrity metadata. | Inspection query is reproducible. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `gxp_signature_challenge` | 19 | PostgreSQL (GxP Core, authoritative) |
| `gxp_signature` | 21 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (3):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /signature/v1/challenges` | yes | policy lookup (Doc 106) |
| `POST /signature/v1/challenges/{id}/verify` | yes | policy lookup (Doc 106) |
| `POST /signature/v1/signatures/{id}/consume` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- product/batch/document identity;
- exact action;
- signature meaning;
- relevant version;
- warning if data changed;
- required comment/reason;
- signer name.
- signed status;
- signer printed name;
- UTC/local display time;
- meaning;
- signature ID;
- resulting record version.
- action;
- record identity/version;
- summary fields;
- required reason/comment;
- signature policy.
- exact record target;
- exact action/meaning;
- signer identity;
- warning that signature is attributable;
- current record version;
- reason/comment if required.

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
| Condition | Result |
|---|---|
| Wrong user completes challenge | Reject |
| Record changed | Mark stale, require new challenge |
| Challenge expired | Reject |
| IdP unavailable | Signing unavailable; no bypass |
| Authentication succeeds but Mutation commit fails | Challenge/signature state must not create falsely completed business action; reconciliation required |
| Duplicate callback | Idempotent verification |
| User disabled before completion | Reject |
| Missing required SoD | Reject |

The final implementation shall ensure signature creation and signed business transition cannot become misleadingly inconsistent. Preferred approach: verified challenge is consumed by the authoritati

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- unique signer
- renamed signer history
- disabled signer
- wrong signer challenge
- fresh authentication required
- record changes before completion
- action/meaning mismatch
- challenge expiry
- replay
- duplicate callback
- performer/verifier SoD
- service account attempts signing
- manifestation in UI
- manifestation in PDF/export
- signature linked to exact old version after correction
- customer IdP outage
- auth method policy downgrade
- timezone/display
- history query
- backup/restore retains signature linkage
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
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-01/Document_04_SPEC-GXP-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-GXP-002/<test_case_id>/`.
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
- identity provider reference flow proven
- at least one Entra/Keycloak-style enterprise SSO flow tested
- signature challenge cryptographic/integrity design reviewed
- Record Vault canonical hash contract frozen
- SoD matrix reconciled with Document 07
- Part 11 assessment maps each signature control
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
