# Claude Code prompt — WP-10 / Document 64: Application, API, UI & Secure Runtime Engineering

TASK:
Implement the Application, API, UI & Secure Runtime Engineering module (SPEC-SEC-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_64_Application_API_UI_Secure_Runtime_Engineering_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: APPSEC-FR-001..030 (30)
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
contracts/openapi/spec-sec-004.yaml
contracts/events/spec-sec-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-sec-004/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| APPSEC-FR-001 | Server-side authorization | Every object/function/property mutation/read is authorized server-side; client-side visibility is not security. | BOLA/BFLA defense. |
| APPSEC-FR-002 | Object scope | Tenant/site/resource identifiers are derived/validated against AuthContext and Policy decision. | No IDOR. |
| APPSEC-FR-003 | Property authorization | Request DTO allowlists writable fields; mass-assignment to protected fields impossible. | Property-level security. |
| APPSEC-FR-004 | Input schemas | All API inputs validated by typed schema including length, ranges, enums, formats and unknown-property policy. | Injection/malformed defense. |
| APPSEC-FR-005 | Output minimization | Responses expose only required fields by role/context; sensitive fields omitted/masked. | Least disclosure. |
| APPSEC-FR-006 | SQL safety | Parameterized queries/ORM safe APIs only; no string-concatenated SQL from request data. | Injection defense. |
| APPSEC-FR-007 | Command injection | No shell command interpolation from untrusted input; use typed process APIs/allowlists where unavoidable. | RCE defense. |
| APPSEC-FR-008 | XSS | Frappe/UI escapes untrusted output; rich text sanitized with allowlist; no unsafe HTML rendering. | Browser protection. |
| APPSEC-FR-009 | CSRF | Cookie-authenticated browser mutations use robust CSRF protection/SameSite and origin controls; token APIs use appropriate model. | Request integrity. |
| APPSEC-FR-010 | CORS | CORS deny-by-default, allowlisted exact origins per deployment; credentials not wildcarded. | Cross-origin security. |
| APPSEC-FR-011 | SSRF | Outbound URL operations use allowlisted destinations/network egress controls; user-supplied URL cannot reach metadata/internal networks. | API7 defense. |
| APPSEC-FR-012 | File upload | Validate size/type/content policy, filename handling, malware scanning/quarantine where required, store outside executable paths. | Upload security. |
| APPSEC-FR-013 | Download authorization | Every attachment/evidence download rechecks object authorization; unguessable URL alone insufficient. | Data protection. |
| APPSEC-FR-014 | Rate limits | Authentication, exports, search, expensive reports, integrations and sensitive business flows have rate/resource limits. | Resource protection. |
| APPSEC-FR-015 | Pagination/bounds | List/search/report endpoints enforce result/time/size bounds. | DoS mitigation. |
| APPSEC-FR-016 | API inventory | All endpoints/version/deprecation/auth scopes documented in OpenAPI/inventory. | Asset management. |
| APPSEC-FR-017 | Debug exposure | Debug/admin/schema endpoints disabled or protected in production. | Misconfiguration defense. |
| APPSEC-FR-018 | Error responses | Client gets stable non-sensitive error; stack traces/internal secrets never exposed. | Information control. |
| APPSEC-FR-019 | Third-party API validation | Treat ERP/LIMS/IdP/Edge responses as untrusted; schema/size/status validation before consumption. | Unsafe API consumption defense. |
| APPSEC-FR-020 | Webhook validation | Authenticate/signature/mTLS as configured; replay/idempotency checks. | Inbound trust. |
| APPSEC-FR-021 | Export safety | CSV/spreadsheet export neutralizes formula injection where applicable and respects field permissions. | Office-client safety. |
| APPSEC-FR-022 | Template safety | No arbitrary template/code evaluation from customer-configured expressions; rules use constrained DSL. | RCE prevention. |
| APPSEC-FR-023 | Serialization | Avoid unsafe object deserialization; use explicit DTO schemas. | Code execution defense. |
| APPSEC-FR-024 | Secrets in URLs | Credentials/tokens/sensitive values not placed in URLs/query strings unless protocol unavoidably requires and mitigated. | Leak prevention. |
| APPSEC-FR-025 | Cookies | Secure, HttpOnly, SameSite cookies; session identifiers regenerated on auth privilege change as applicable. | Session defense. |
| APPSEC-FR-026 | Security headers | CSP, frame-ancestors/X-Frame controls, Referrer-Policy, MIME sniff protection and HSTS where appropriate. | Browser hardening. |
| APPSEC-FR-027 | API versioning | Deprecated insecure endpoint versions have removal plan/telemetry and cannot linger undocumented. | Attack surface. |
| APPSEC-FR-028 | Graph/relationship queries | Prevent unauthorized traversal through genealogy/search/report endpoints. | Indirect disclosure. |
| APPSEC-FR-029 | Bulk operations | Bulk mutations apply per-object authorization/business rules and bounded transaction behavior. | No batch bypass. |
| APPSEC-FR-030 | Security tests | ASVS/API Security requirements mapped to automated tests and penetration test scenarios. | Verification. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| authorizeObjectAccess() | API/service method | AuthContext; action; resource type/id; requested fields | AuthorizationDecision | ACCESS_DENIED |
| validateRequestSchema() | API middleware | operationId; request body/query/path | ValidatedRequest | REQUEST_SCHEMA_INVALID |
| sanitizeRichText() | UI/API input | html/text; sanitizer policy version | SanitizedContent | UNSAFE_CONTENT_REJECTED |
| validateOutboundDestination() | Integration/file fetch | URL/host/service ID; purpose | DestinationDecision | SSRF_DESTINATION_BLOCKED |
| validateFileUpload() | Upload endpoint | stream; filename; declared type; expected context | UploadReceipt | FILE_TYPE_BLOCKED/MALWARE_DETECTED |
| protectSpreadsheetExport() | Export service | rows/columns; field metadata | SafeExportDataset | none |
| enforceRateLimit() | Gateway/middleware | subject/client/IP/operation; cost | RateLimitDecision | RATE_LIMITED |
| verifyWebhook() | Inbound integration | headers/cert/body; provider profile | VerifiedWebhook | WEBHOOK_AUTH_FAILED/REPLAY_DETECTED |
| mapSafeErrorResponse() | API exception handler | internal error; correlation ID | PublicError | none |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `api_security_policy` | 6 | PostgreSQL (GxP Core, authoritative) |
| `outbound_destination` | 5 | PostgreSQL (GxP Core, authoritative) |
| `webhook_profile` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (3):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /security/v1/outbound-destinations` | yes | — |
| `POST /security/v1/webhook-profiles` | yes | — |
| `GET /security/v1/api-inventory` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `APIAccessDenied` | SPEC-SEC-004 | event_id |
| `RateLimitTriggered` | SPEC-SEC-004 | event_id |
| `SSRFBlocked` | SPEC-SEC-004 | event_id |
| `MaliciousUploadDetected` | SPEC-SEC-004 | event_id |
| `WebhookReplayDetected` | SPEC-SEC-004 | event_id |
| `DeprecatedAPIUsed` | SPEC-SEC-004 | event_id |

UI SURFACES:
- API Security Inventory
- Rate-Limit Policies
- Outbound Destination Registry
- Webhook Profiles
- File Quarantine
- Security Test Coverage

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
- BOLA cross-tenant ID
- mass assignment state/role field
- SQL injection payload
- stored XSS
- CSRF mutation
- SSRF metadata IP
- oversized upload
- malware file
- CSV formula injection
- third-party API malformed payload
- bulk auth bypass
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-10/Document_64_SPEC-SEC-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-SEC-004/<test_case_id>/`.
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
