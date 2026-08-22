# Claude Code prompt — WP-01 / Document 07: Identity, Authorization, RBAC, Qualification & Segregation-of-Duties

TASK:
Implement the Identity, Authorization, RBAC, Qualification & Segregation-of-Duties module (SPEC-IAM-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_07_Identity_Authorization_RBAC_Qualification_SoD_Specification_v1_1_IMPLEMENTATION_READY.md`
- Requirement IDs: IAM-FR-001..032 (32)
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
- `services/gxp-api/src/modules/policy` and its tests
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
services/gxp-api/src/modules/policy/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/policy/migrations/     # owned entities only
services/gxp-api/src/modules/policy/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-iam-001.yaml
contracts/events/spec-iam-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-iam-001/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| IAM-FR-001 | Unique human identity | Each user has immutable internal subject mapping to enterprise identity; shared regulated accounts prohibited. | Two users cannot share signing identity. |
| IAM-FR-002 | External identity federation | Support OIDC/SAML through Keycloak-compatible boundary; customer Entra/Okta/AD or equivalent may be source. | Authentication provider replaceable. |
| IAM-FR-003 | Local identity fallback | On-prem deployments may use controlled local Keycloak identity where customer SSO unavailable, subject to equivalent policies. | No cloud IdP hard dependency. |
| IAM-FR-004 | User lifecycle | Provision, activate, suspend, disable, terminate and retain historical identity metadata. | Disabled user cannot act/sign. |
| IAM-FR-005 | Role catalogue | Reference roles grouped by Production, QA, QC, Warehouse, Procurement, Engineering, QMS, IT and Auditor. | Role names configurable but permissions controlled. |
| IAM-FR-006 | Permission actions | Permissions are action/resource based, not merely screen access: view, create-draft, execute, verify, approve, release, correct, administer, export, etc. | UI hiding not permission. |
| IAM-FR-007 | Tenant scope | Identity cannot access another customer environment/data. | Isolation negative test. |
| IAM-FR-008 | Site/area scope | User access can be limited to site, building, area/room/line and function where required. | Cross-site operation blocked. |
| IAM-FR-009 | Product/process scope | Authorization may restrict user to product family, process type or specialized operation. | Specialized task protected. |
| IAM-FR-010 | Qualification object | Model qualifications such as dispensing, sterile-area, aseptic operation, QA release, equipment use and specialized testing. | Qualification has status/effective/expiry. |
| IAM-FR-011 | Training gate | Required training/SOP curriculum status can be evaluated before execution/signing. | Expired training blocks configured action. |
| IAM-FR-012 | Equipment qualification authorization | User may require equipment-specific or class qualification before operating/verifying. | Execution gate server-side. |
| IAM-FR-013 | Signature entitlement | Only users with active electronic-signature entitlement and verified identity status may complete regulated signature challenges. | Role alone insufficient. |
| IAM-FR-014 | Segregation-of-duties policy | Support performer != verifier, author != approver, independent QA release, and configurable incompatible role/action combinations. | Same-user negative tests. |
| IAM-FR-015 | Dynamic SoD context | SoD evaluates record history, not only static role membership; e.g. user who performed step cannot verify same step. | History-aware decision. |
| IAM-FR-016 | Delegation of work | Tasks/approvals may be reassigned/delegated under controlled workflow, but electronic signature is never delegated. | New assignee signs self. |
| IAM-FR-017 | Temporary authorization | Time-limited authorization has reason, scope, start/end, approver and audit; auto-expires. | No permanent hidden elevation. |
| IAM-FR-018 | Break-glass access | Emergency access is explicitly invoked, MFA-protected, time-limited, reason-coded, heavily audited and independently reviewed. | Emergency use visible. |
| IAM-FR-019 | Privileged role separation | Application admin, Security admin, Identity admin, DB admin and infrastructure admin remain separate from product release authority. | Admin cannot release by privilege. |
| IAM-FR-020 | Vendor support access | Support access requires customer-approved/time-limited identity, scoped permissions and logging; no shared vendor root account. | Support access traceable. |
| IAM-FR-021 | Service accounts | Non-human identities have owner, purpose, scopes, credential/certificate lifecycle, rotation and no human signature capability. | Service identity inventory complete. |
| IAM-FR-022 | Device identities | Edge/instruments use registered non-human device identities/certificates separate from service/human users. | Machine evidence attributable. |
| IAM-FR-023 | Session controls | Configurable idle/absolute timeout, reauthentication rules and session revocation. Regulated signature still uses fresh step-up. | Stolen long session limited. |
| IAM-FR-024 | MFA | MFA required for privileged access and configured enterprise policies; signature authentication follows Document 04 assurance. | Privileged account cannot use password-only baseline. |
| IAM-FR-025 | Role assignment approval | High-risk role/entitlement assignment uses controlled approval and audit; assignment effective dates supported. | QA release role cannot self-assign. |
| IAM-FR-026 | Access review | Periodic report/review of active users, roles, sites, qualifications, service accounts and privileged access. | Review evidence exportable. |
| IAM-FR-027 | Joiner/mover/leaver | Identity changes synchronize through IdP/manual process while preserving immutable historical actor IDs. | Department change doesn't rewrite history. |
| IAM-FR-028 | Policy decision evidence | Authorization response contains allow/deny, policy version, evaluated subject/resource/action and reason codes. | Validation can prove why denied. |
| IAM-FR-029 | Least privilege defaults | New users/service accounts have no regulated privileges until explicitly assigned. | Default deny. |
| IAM-FR-030 | No client-side authority | Frappe permissions improve UX but GxP Policy Service independently enforces every authoritative regulated action. | API bypass fails. |
| IAM-FR-031 | Qualification override | Any permitted emergency qualification override requires dedicated policy, reason, authorized signer and quality-event/audit linkage. | No silent override. |
| IAM-FR-032 | Historical access | User/account deletion is avoided where history is required; deactivated identity remains referencable for old records/signatures. | Old actor resolves. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `iam_subject` | 12 | PostgreSQL (GxP Core, authoritative) |
| `iam_role_assignment` | 10 | PostgreSQL (GxP Core, authoritative) |
| `iam_qualification` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `iam_temporary_authorization` | 3 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (7):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /policy/v1/decisions` | yes | — |
| `GET /iam/v1/subjects/{id}/effective-authority` | no | — |
| `GET /iam/v1/subjects/{id}/qualifications` | no | — |
| `POST /iam/v1/temporary-authorizations` | yes | — |
| `POST /iam/v1/break-glass` | yes | — |
| `POST /iam/v1/access-reviews` | yes | — |
| `GET /iam/v1/access-reviews/{id}/report` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- User Directory Mapping
- Role Assignment
- Qualification Assignment
- Temporary Authorization
- Break-Glass Review
- Service Account Registry
- Device Identity Registry
- Access Review Dashboard

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
- user wrong site
- wrong role
- expired qualification
- missing training
- performer=verifier
- author=approver
- temporary role expiry
- break-glass
- disabled user
- role removed during active session
- service account human-signature attempt
- device identity acting as user
- admin release attempt
- support access expiry
- access review output
- customer SSO mapping
- IdP outage behavior
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
- Test case book: `test-cases/WP-01/Document_07_SPEC-IAM-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-IAM-001/<test_case_id>/`.
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
- action catalogue
- reference role-to-action matrix
- initial qualification catalogue
- SoD matrix
- Keycloak/Entra reference integration proof
- alignment with Electronic Signature policies
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
