# Claude Code prompt — WP-10 / Document 62: Identity Federation, SSO, MFA, Sessions & Service Identities

TASK:
Implement the Identity Federation, SSO, MFA, Sessions & Service Identities module (SPEC-SEC-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_62_Identity_Federation_SSO_MFA_Sessions_Service_Identities_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: IAMSEC-FR-001..026 (26)
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
contracts/openapi/spec-sec-002.yaml
contracts/events/spec-sec-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-sec-002/
```

REQUIREMENTS TO IMPLEMENT (26):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| IAMSEC-FR-001 | Federated identity | Support OIDC and SAML federation through Keycloak-compatible identity boundary; direct app password store is fallback only for approved isolated deployments. | Enterprise SSO. |
| IAMSEC-FR-002 | Local fallback IdP | On-prem/private deployments can use locally managed Keycloak-compatible realm when customer IdP unavailable. | Deployment flexibility. |
| IAMSEC-FR-003 | MFA policy | MFA requirements configurable by user risk/role/context; privileged users require MFA. | Strong auth. |
| IAMSEC-FR-004 | MFA methods | Support WebAuthn/passkeys/security keys and approved TOTP/IdP MFA methods; weak factors configurable as disallowed. | Phishing resistance. |
| IAMSEC-FR-005 | SSO session | Application accepts short-lived identity tokens/session assertions and validates issuer/audience/signature/expiry/nonce/state. | Token integrity. |
| IAMSEC-FR-006 | Session binding | Session binds tenant/user/authentication context and cannot change tenant/site silently. | Scope integrity. |
| IAMSEC-FR-007 | Session timeout | Idle and absolute session lifetimes configurable by deployment/profile; sensitive contexts shorter. | Least exposure. |
| IAMSEC-FR-008 | Reauthentication | Sensitive security/admin operations may require fresh authentication independently of Part 11 signing. | Step-up. |
| IAMSEC-FR-009 | Part 11 separation | Regulated signature ceremony always uses Document 04; normal MFA/session is never reused automatically as signature proof. | Correct semantics. |
| IAMSEC-FR-010 | Token revocation | Disabled user/critical risk/session logout/revocation invalidates or rapidly expires app access. | Lifecycle. |
| IAMSEC-FR-011 | Group/claim mapping | External groups/claims map through controlled identity mapping; external IdP does not directly assign unrestricted GxP permission. | Policy boundary. |
| IAMSEC-FR-012 | Provisioning | SCIM or controlled directory sync may provision identity metadata; authorization remains controlled in platform. | Enterprise lifecycle. |
| IAMSEC-FR-013 | Joiner/mover/leaver | Identity lifecycle integrates Document 07 role/qualification lifecycle and security session revocation. | Timely access removal. |
| IAMSEC-FR-014 | Service identity | Services use workload identities/client credentials/mTLS certificates; no shared human accounts. | Machine attribution. |
| IAMSEC-FR-015 | Device identity | Edge/connectors have distinct certificates/service principals and site scope. | Industrial identity. |
| IAMSEC-FR-016 | Credential storage | No plaintext user/service secrets in source/config/logs. | Secret hygiene. |
| IAMSEC-FR-017 | Authentication events | Success/failure/MFA/lockout/token/revocation events sent to security telemetry. | Detection. |
| IAMSEC-FR-018 | Brute-force defense | Rate-limit/lockout/risk response handled primarily at IdP and supported by application controls. | Abuse protection. |
| IAMSEC-FR-019 | Password fallback | If local passwords exist, enforce modern hashing and policy through IdP; application never implements custom password hashing. | Centralized auth. |
| IAMSEC-FR-020 | Account recovery | Recovery handled through controlled IdP/customer process; app support cannot reset identity secretly. | Identity proof. |
| IAMSEC-FR-021 | Impersonation | Human impersonation disabled by default; support troubleshooting uses controlled read-only/support-access model. | No hidden acting as user. |
| IAMSEC-FR-022 | Concurrent sessions | Configurable session/device visibility and admin/security ability to revoke sessions. | Account control. |
| IAMSEC-FR-023 | Risk context | Auth context may include MFA strength, device/trust/risk signals for policy decisions without embedding vendor-specific fields in domain. | Adaptive auth. |
| IAMSEC-FR-024 | Clock skew | Token validation uses bounded configured clock skew; large time anomalies fail/auth-alert. | Time integrity. |
| IAMSEC-FR-025 | Tenant discovery | Login flow never reveals sensitive tenant/customer existence beyond approved UX. | Information minimization. |
| IAMSEC-FR-026 | Identity audit | Identity mappings, federation changes, MFA policy and service-client changes versioned/audited. | Traceability. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| validateIdentityToken() | API gateway/session middleware | JWT/assertion; expected issuer/audience/tenant | AuthContext | AuthenticationSucceeded/Failed; TOKEN_INVALID |
| createApplicationSession() | Web login callback | AuthContext; browser/device metadata | ApplicationSession | SessionCreated |
| evaluateMFARequirement() | Login/admin action | user/role/context/risk | MFARequirement | MFARequired |
| revokeUserSessions() | Identity lifecycle/Security Admin | subject_id; reason | RevocationReceipt | UserSessionsRevoked |
| mapExternalIdentity() | Federation callback/provisioning | issuer; subject; claims | IdentityMapping | ExternalIdentityMapped |
| provisionServiceIdentity() | Security Admin/Deployment automation | service name; scopes; tenant/site; auth method | ServiceIdentity | ServiceIdentityProvisioned |
| validateServiceToken() | Service middleware | client token/cert; target audience | ServiceAuthContext | ServiceAuthenticationSucceeded |
| requireFreshAuthentication() | Sensitive admin operation | session_id; required_age/auth_strength | FreshAuthResult | FRESH_AUTH_REQUIRED |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `identity_provider_config` | 6 | PostgreSQL (GxP Core, authoritative) |
| `application_session` | 8 | PostgreSQL (GxP Core, authoritative) |
| `service_identity` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `GET /auth/login` | no | — |
| `GET /auth/callback` | no | — |
| `POST /auth/logout` | yes | — |
| `POST /security/v1/sessions/{id}/revoke` | yes | — |
| `POST /security/v1/service-identities` | yes | — |
| `POST /security/v1/identity-providers` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `AuthenticationSucceeded` | SPEC-SEC-002 | event_id |
| `AuthenticationFailed` | SPEC-SEC-002 | event_id |
| `MFARequired` | SPEC-SEC-002 | event_id |
| `SessionCreated` | SPEC-SEC-002 | event_id |
| `SessionRevoked` | SPEC-SEC-002 | event_id |
| `ExternalIdentityMapped` | SPEC-SEC-002 | event_id |
| `ServiceIdentityProvisioned` | SPEC-SEC-002 | event_id |

UI SURFACES:
- Identity Provider Config
- Active Sessions
- Service Identities
- Federation Mapping
- Authentication Policy
- Session Revocation

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
- wrong issuer
- wrong audience
- expired token
- clock skew
- MFA missing for privileged role
- disabled user existing session
- cross-tenant claim injection
- service token wrong audience
- certificate revoked
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-10/Document_62_SPEC-SEC-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-SEC-002/<test_case_id>/`.
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
