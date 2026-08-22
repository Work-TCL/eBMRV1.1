# Claude Code prompt — WP-10 / Document 63: Privileged Access, Support Access, Break-Glass & Administrative Security

TASK:
Implement the Privileged Access, Support Access, Break-Glass & Administrative Security module (SPEC-SEC-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_63_Privileged_Support_BreakGlass_Admin_Security_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: PAM-FR-001..026 (26)
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
- `platform/security` and its tests
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
platform/security/src/            # domain services, command handlers, repositories
platform/security/migrations/     # owned entities only
platform/security/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-sec-003.yaml
contracts/events/spec-sec-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-sec-003/
```

REQUIREMENTS TO IMPLEMENT (26):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| PAM-FR-001 | Privileged role catalogue | Define platform admin, security admin, DB admin, infrastructure admin, support engineer, integration admin and customer admin separately. | Role separation. |
| PAM-FR-002 | Admin not Quality | Privileged technical role never implies production/QC/QA/release/signature authority. | SoD. |
| PAM-FR-003 | Named accounts | Privileged actions require named human account; shared admin accounts prohibited. | Attribution. |
| PAM-FR-004 | MFA | Privileged interactive access requires MFA. | Strong admin auth. |
| PAM-FR-005 | JIT access | Support just-in-time elevated access with ticket/reason/scope/start/expiry and approver. | Least privilege. |
| PAM-FR-006 | Support access | Vendor/support access disabled by default and enabled per customer/site/time window. | Customer control. |
| PAM-FR-007 | Support purpose | Support session has case/ticket, reason, customer approval where required and explicit resource scope. | Purpose limitation. |
| PAM-FR-008 | Read-only default | Support role defaults read-only diagnostics; mutation requires separately approved privileged change path. | Safe support. |
| PAM-FR-009 | Production shell | Interactive shell/SSH/kubectl access to production minimized and controlled by JIT/bastion/PAM pattern. | Reduced exposure. |
| PAM-FR-010 | Database access | Direct production DB access restricted; GxP data repair uses controlled repair commands, not ad-hoc UPDATE. | Data integrity. |
| PAM-FR-011 | Break-glass | Emergency account/path is disabled/sealed or tightly monitored, requires explicit reason and immediate post-use review. | Emergency resilience. |
| PAM-FR-012 | Break-glass scope | Break-glass does not grant electronic-signature or QA release rights. | GxP boundary. |
| PAM-FR-013 | Session recording | Privileged shell/admin session commands/activity recorded where deployment permits; database diagnostic queries logged where feasible. | Forensics. |
| PAM-FR-014 | Clipboard/download restriction | Support export/download of sensitive data limited and audited. | Data protection. |
| PAM-FR-015 | No impersonation | Support cannot impersonate end user to create GxP actions/signatures. | Integrity. |
| PAM-FR-016 | Approval separation | Requester cannot approve own privileged elevation except emergency path requiring retrospective review. | SoD. |
| PAM-FR-017 | Time bound | Elevation expires automatically; no permanent hidden grants. | Least privilege. |
| PAM-FR-018 | Command allowlist | High-risk admin operations exposed as controlled commands with validation/audit rather than arbitrary DB/scripts. | Safe operations. |
| PAM-FR-019 | Config changes | Security/infra production configuration changes link Change Control where GxP-impacting. | Validated state. |
| PAM-FR-020 | Customer data access | Vendor staff tenant access requires explicit tenant scope and support entitlement. | Isolation. |
| PAM-FR-021 | Secrets access | Viewing raw production secrets is restricted and exceptional; prefer delegated operations without secret disclosure. | Credential hygiene. |
| PAM-FR-022 | Admin API | Administrative APIs separate namespace/scopes/rate limits and not exposed publicly unless required. | Attack surface. |
| PAM-FR-023 | Activity monitoring | Privileged events produce high-signal telemetry and alerts for unusual scope/time/actions. | Detection. |
| PAM-FR-024 | Periodic review | Privileged assignments and support entitlements reviewed periodically. | Governance. |
| PAM-FR-025 | Offboarding | Termination/vendor access removal immediately revokes sessions/keys/JIT grants. | Lifecycle. |
| PAM-FR-026 | Emergency repair evidence | Any emergency technical repair records original issue, command, before/after hashes, approver and linked deviation/change/security incident. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| requestPrivilegedAccess() | Admin/Support user | requested_role; tenant/site/resources; reason; ticket; duration | PrivilegedAccessRequest | PrivilegedAccessRequested |
| approvePrivilegedAccess() | Authorized approver | request_id; decision; comments | PrivilegedGrant | PrivilegedAccessGranted |
| evaluatePrivilegedGrant() | Admin middleware | subject; operation; resource; current time | PrivilegedDecision | PRIVILEGED_ACCESS_DENIED |
| openSupportSession() | Support portal | grant_id; customer tenant; support case | SupportSession | SupportSessionOpened |
| executeControlledAdminCommand() | Admin UI/CLI | command_code; parameters; grant; reason | AdminCommandReceipt | AdminCommandExecuted; ADMIN_COMMAND_NOT_ALLOWED |
| activateBreakGlass() | Emergency operator | emergency identity/path; incident ID; reason | BreakGlassSession | BreakGlassActivated |
| closePrivilegedSession() | User/system expiry | session_id; outcome | CloseReceipt | PrivilegedSessionClosed |
| reviewPrivilegedSession() | Security reviewer | session_id; evidence; findings | PrivilegedReview | PrivilegedSessionReviewed |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `privileged_access_request` | 9 | PostgreSQL (GxP Core, authoritative) |
| `privileged_grant` | 5 | PostgreSQL (GxP Core, authoritative) |
| `privileged_session` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /security/v1/privileged-access/requests` | yes | — |
| `POST /security/v1/privileged-access/requests/{id}/approve` | yes | policy lookup (Doc 106) |
| `POST /security/v1/support-sessions` | yes | — |
| `POST /security/v1/admin-commands/{code}:execute` | yes | — |
| `POST /security/v1/break-glass` | yes | — |
| `POST /security/v1/privileged-sessions/{id}/close` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `PrivilegedAccessRequested` | SPEC-SEC-003 | event_id |
| `PrivilegedAccessGranted` | SPEC-SEC-003 | event_id |
| `SupportSessionOpened` | SPEC-SEC-003 | event_id |
| `AdminCommandExecuted` | SPEC-SEC-003 | event_id |
| `BreakGlassActivated` | SPEC-SEC-003 | event_id |
| `PrivilegedSessionClosed` | SPEC-SEC-003 | event_id |
| `PrivilegedSessionReviewed` | SPEC-SEC-003 | event_id |

UI SURFACES:
- Privileged Access Requests
- Active Grants
- Support Sessions
- Controlled Admin Commands
- Break-Glass
- Privileged Session Review
- Privileged Role Review

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies.
- Security subsystem outage must not silently downgrade protection.
- Retryable infrastructure failures use bounded retry/backoff.
- Security-control bypass requires a separate controlled emergency path, not a hidden fallback.
- Recovery actions are themselves logged and reviewable.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- self-approval denied
- grant expiry during session
- support cross-tenant access denied
- DB UPDATE attempt absent from allowed tools
- break-glass cannot sign QA release
- admin command parameter validation
- terminated support user access revoked
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-10/Document_63_SPEC-SEC-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-SEC-003/<test_case_id>/`.
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
