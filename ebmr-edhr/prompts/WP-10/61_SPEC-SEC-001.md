# Claude Code prompt — WP-10 / Document 61: Security Architecture, Threat Model & Control Framework

TASK:
Implement the Security Architecture, Threat Model & Control Framework module (SPEC-SEC-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_61_Security_Architecture_Threat_Model_Control_Framework_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: SEC-THR-001..028 (28)
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
contracts/openapi/spec-sec-001.yaml
contracts/events/spec-sec-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-sec-001/
```

REQUIREMENTS TO IMPLEMENT (28):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| SEC-THR-001 | Security architecture register | Maintain system security architecture, trust zones, assets, actors, data classifications, entry points and security owners. | Visible security design. |
| SEC-THR-002 | Threat model lifecycle | Threat model created at architecture baseline and updated for new modules, integrations, deployment modes and material changes. | Continuous risk review. |
| SEC-THR-003 | Threat methodology | Use STRIDE or equivalent controlled methodology with asset/abuse-case mapping; methodology version retained. | Repeatable. |
| SEC-THR-004 | Asset catalogue | Classify GxP records, credentials, signatures, audit, source evidence, PII, configuration, code/artifacts and keys. | Protection based on value. |
| SEC-THR-005 | Trust boundaries | Explicit boundaries between browser, Frappe, GxP services, databases, Keycloak/IdP, Edge, OT network, integrations, object store and admin plane. | No implicit trust. |
| SEC-THR-006 | Abuse cases | Model account takeover, privilege escalation, signature fraud, audit tampering, data exfiltration, ransomware, API abuse, insider misuse, malicious integration, Edge compromise and supply-chain compromise. | Realistic adversary paths. |
| SEC-THR-007 | GxP integrity threats | Explicitly model unauthorized mutation, historical overwrite, duplicate/replayed command, stale version, failed-result deletion and audit-chain tampering. | Regulated integrity. |
| SEC-THR-008 | Availability threats | Model DoS, queue exhaustion, database outage, object-store outage, IdP outage, Edge outage and network segmentation. | Operational resilience. |
| SEC-THR-009 | Privacy threats | Model overexposure of complaint/patient/reporter/personnel data and export/search leakage. | Confidentiality. |
| SEC-THR-010 | OT threats | Model compromised PLC/SCADA/Edge source, forged telemetry, bad clock, protocol abuse and unauthorized machine command. | Factory boundary. |
| SEC-THR-011 | Integration threats | Model SSRF, unsafe third-party response consumption, compromised ERP/LIMS endpoint and replayed webhook. | External trust. |
| SEC-THR-012 | Tenant/site threats | Model cross-tenant and cross-site object access, cache leakage, search leakage and background-job scope errors. | Isolation. |
| SEC-THR-013 | Control mapping | Each identified threat maps preventive/detective/recovery controls and verification tests. | Actionable. |
| SEC-THR-014 | Risk rating | Use approved security-risk model with impact/likelihood/exposure and residual-risk decision. | Prioritized. |
| SEC-THR-015 | Security acceptance | High/critical residual risk requires Security owner plus Quality/Business acceptance where GxP impact exists. | Governed. |
| SEC-THR-016 | Security requirements | Threat mitigations generate stable security requirement IDs and tests. | Traceability. |
| SEC-THR-017 | Security ADR | Material security tradeoff documented in ADR with threat/risk/control impact. | Explainable design. |
| SEC-THR-018 | Secure defaults | Default deployment minimizes exposed services, uses TLS, denies generic admin access, disables machine write and requires strong auth. | Secure-by-default. |
| SEC-THR-019 | Attack surface inventory | Maintain deployed endpoints, ports, APIs, admin interfaces, integrations and versions. | Asset awareness. |
| SEC-THR-020 | Dependency boundary | Third-party library/service risk included in threat model where compromise affects regulated state. | Supply-chain aware. |
| SEC-THR-021 | Customer configuration threat review | Security-impacting tenant/customer configuration has safe defaults and validation. | No insecure customization. |
| SEC-THR-022 | Security control ownership | Every security control has implementation owner, evidence source and test owner. | Accountability. |
| SEC-THR-023 | Exception process | Security exception is time-bounded, risk-assessed, approved and tracked to remediation. | No permanent bypass. |
| SEC-THR-024 | Threat review trigger | Trigger on new external endpoint, auth mode, machine command, new data class, new deployment mode, major library/runtime or architectural change. | Change-sensitive. |
| SEC-THR-025 | Security profile | Cloud, private cloud and on-prem deployments receive profile-specific threat/control baselines. | Deployment-aware. |
| SEC-THR-026 | Control effectiveness | Security monitoring/pen test/incidents can update control effectiveness and reopen threats. | Feedback loop. |
| SEC-THR-027 | Inspection evidence | Threat/control/risk/exception history exportable for enterprise customer assessment. | Customer assurance. |
| SEC-THR-028 | No checklist-only security | Security framework mapping supplements—not replaces—system-specific threat modeling. | Meaningful design. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createThreatModelVersion() | Security Architect | system_version; methodology_version; scope; assets; boundaries | ThreatModelDraft | ThreatModelDraftCreated; THREAT_SCOPE_INVALID |
| registerThreat() | Architect/Engineer | threat_model_id; asset/boundary; threat_type; abuse_case; evidence | ThreatRecord | ThreatRegistered |
| mapSecurityControl() | Security Architect | threat_id; control_id; preventive/detective/recovery; implementation refs | ThreatControlMapping | SecurityControlMapped |
| calculateSecurityRisk() | Security Risk Service | threat_id; impact inputs; likelihood inputs; methodology | SecurityRiskAssessment | SecurityRiskCalculated |
| acceptResidualSecurityRisk() | Security/Quality/Business approver | risk_id; rationale; expiry/review date; signatures | SecurityRiskAcceptance | ResidualSecurityRiskAccepted |
| openSecurityException() | Security owner | control/requirement; reason; compensating controls; expiry | SecurityException | SecurityExceptionOpened |
| triggerThreatModelReview() | Change/SDLC/event | change_id; affected modules; trigger type | ThreatReviewTask | ThreatModelReviewRequired |
| generateSecurityControlMatrix() | Validation/Security | threat model/version; deployment profile | SecurityControlMatrix | SecurityControlMatrixGenerated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `security_threat_model_version` | 7 | PostgreSQL (GxP Core, authoritative) |
| `security_threat` | 6 | PostgreSQL (GxP Core, authoritative) |
| `security_control` | 6 | PostgreSQL (GxP Core, authoritative) |
| `security_exception` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /security/v1/threat-models` | yes | — |
| `POST /security/v1/threats` | yes | — |
| `POST /security/v1/threats/{id}/controls` | yes | — |
| `POST /security/v1/risks/{id}/accept` | yes | — |
| `POST /security/v1/exceptions` | yes | — |
| `GET /security/v1/control-matrix` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ThreatModelDraftCreated` | SPEC-SEC-001 | event_id |
| `ThreatRegistered` | SPEC-SEC-001 | event_id |
| `SecurityControlMapped` | SPEC-SEC-001 | event_id |
| `ResidualSecurityRiskAccepted` | SPEC-SEC-001 | event_id |
| `SecurityExceptionOpened` | SPEC-SEC-001 | event_id |
| `ThreatModelReviewRequired` | SPEC-SEC-001 | event_id |

UI SURFACES:
- Security Architecture
- Threat Model
- Assets/Trust Boundaries
- Threat Register
- Control Catalogue
- Residual Risk
- Exceptions
- Control/Test Matrix

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
- cross-tenant abuse case
- signature fraud threat
- audit tamper threat
- Edge compromise
- SSRF integration threat
- critical residual risk approval
- expired exception
- change-triggered review
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-10/Document_61_SPEC-SEC-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-SEC-001/<test_case_id>/`.
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
