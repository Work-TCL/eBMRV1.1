# Claude Code prompt — WP-10 / Document 67: Security Logging, Monitoring, Incident Response & Forensic Evidence

TASK:
Implement the Security Logging, Monitoring, Incident Response & Forensic Evidence module (SPEC-SEC-007) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_67_Security_Logging_Monitoring_Incident_Response_Forensics_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: MON-FR-001..030 (30)
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
contracts/openapi/spec-sec-007.yaml
contracts/events/spec-sec-007/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-sec-007/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| MON-FR-001 | Security event taxonomy | Define authentication, authorization, privileged, admin, config, secret/key, API abuse, integration, malware, integrity, network and data-access security events. | Consistent detection. |
| MON-FR-002 | Separate audit vs security logs | GxP audit ledger remains regulatory mutation history; security telemetry is separate but cross-correlated. | Correct evidence. |
| MON-FR-003 | Structured logging | Security logs include event code, UTC time, subject/service, tenant/site, source, target, result, correlation and severity. | Machine usable. |
| MON-FR-004 | Sensitive redaction | Logs exclude secrets/tokens/passwords/private keys and minimize PII/regulated content. | Safe telemetry. |
| MON-FR-005 | Central collection | App/services/Edge/IdP/infrastructure forward security telemetry to central SIEM/log platform where deployment supports. | Visibility. |
| MON-FR-006 | Tamper resistance | Security logs centrally retained with restricted delete/admin roles; critical log source loss alerts. | Evidence. |
| MON-FR-007 | Clock | All sources use synchronized UTC and carry clock-health metadata for Edge/OT. | Timeline. |
| MON-FR-008 | Detection rules | Versioned alerts for brute force, impossible/abnormal access, privilege elevation, break-glass, denied cross-tenant, hash conflict, unusual export, cert/secret issues and service anomalies. | Detection. |
| MON-FR-009 | Rate anomaly | Detect repeated BOLA/authorization denials, scan patterns, resource abuse and API enumeration. | API security. |
| MON-FR-010 | Data-integrity alert | Audit hash/checkpoint, event-id payload conflict, unexpected DB mutation or evidence hash mismatch becomes critical security/quality event. | GxP integrity. |
| MON-FR-011 | Edge security | Gateway cert misuse, config-signature failure, clock anomaly, buffer integrity failure and command denial visible centrally. | OT visibility. |
| MON-FR-012 | Incident register | Formal security incident with severity, scope, owner, affected tenants/sites, data/GxP impact and timeline. | Managed response. |
| MON-FR-013 | Incident states | Detected → Triage → Contain → Investigate → Eradicate/Recover → GxP/Data Impact → Close/Postmortem. | Explicit. |
| MON-FR-014 | Evidence preservation | Forensic snapshot/log/evidence collection uses immutable refs/hashes and chain-of-custody metadata. | Investigation. |
| MON-FR-015 | Containment actions | Revoke sessions/certs/secrets, isolate service/gateway, block integration, freeze account or disable feature through controlled commands. | Rapid response. |
| MON-FR-016 | GxP impact assessment | Incident affecting regulated data/system may create deviation/change/CAPA/validation impact through QMS. | Quality integration. |
| MON-FR-017 | Data breach assessment hook | Privacy/security incident can create legal/privacy assessment task without software autonomously making notification determination. | Governance. |
| MON-FR-018 | Ransomware | Incident playbook supports isolation, credential rotation, immutable backup assessment and restoration decision. | Resilience. |
| MON-FR-019 | Customer notification | Enterprise/customer security notification tasks tracked under contractual/regulatory policy. | Accountability. |
| MON-FR-020 | Incident communications | Internal/external communications versioned and approved where material. | Controlled. |
| MON-FR-021 | Postmortem | Root cause, control failure, corrective actions and lessons linked CAPA/Change/security backlog. | Improvement. |
| MON-FR-022 | Detection validation | Security rules tested with synthetic events and periodic control checks. | No dead alerts. |
| MON-FR-023 | Retention | Security telemetry retention configurable; incident evidence/regulated-impact evidence retained per applicable investigation policy. | Evidence. |
| MON-FR-024 | Access | Security logs restricted; support/customer views scoped to tenant/site and role. | Confidentiality. |
| MON-FR-025 | Export | Incident timeline/evidence package exportable without exposing unrelated tenant data. | Forensics. |
| MON-FR-026 | Alert fatigue | Detection rules have severity, dedup/suppression windows and tuning history; suppression cannot hide critical integrity alerts silently. | Operable. |
| MON-FR-027 | Health | Monitor log-ingestion lag/source silence/SIEM forwarding failure. | Telemetry assurance. |
| MON-FR-028 | Metrics | MTTD/MTTR, alert volume, false positives, privileged events, integrity events and unresolved security findings. | Management. |
| MON-FR-029 | No auto-delete | Incident closure never deletes security events/source evidence. | History. |
| MON-FR-030 | Security/QMS linkage | Security incident IDs can be referenced by deviation/CAPA/change and vice versa without duplicating evidence. | Integrated. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| emitSecurityEvent() | Any service/Edge/security control | event_code; subject; tenant/site; target; result; correlation; metadata | SecurityEventReceipt | SecurityEventEmitted |
| evaluateDetectionRules() | SIEM/detection worker | security events; rule versions; window | SecurityAlert[] | SecurityAlertRaised |
| openSecurityIncident() | Security analyst/critical rule | alert/evidence refs; severity; affected scope | SecurityIncident | SecurityIncidentOpened |
| executeIncidentContainment() | Incident commander | incident_id; containment command; target; approval if required | ContainmentReceipt | IncidentContainmentExecuted |
| preserveForensicEvidence() | Incident responder | source/path/object/log range; acquisition metadata | ForensicEvidenceRef | ForensicEvidencePreserved |
| assessGxPIncidentImpact() | Security + QA | incident_id; affected systems/time/data; evidence | GxPIncidentImpact | SecurityGxPImpactAssessed |
| closeSecurityIncident() | Incident owner/approver | incident_id; root cause; actions; residual risk | IncidentClosure | SecurityIncidentClosed |
| testDetectionRule() | Security engineering/CI | rule_id; synthetic event set | DetectionTestResult | DetectionRuleTested |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `security_incident` | 9 | PostgreSQL (GxP Core, authoritative) |
| `forensic_evidence` | 4 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (5):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /security/v1/incidents` | yes | — |
| `POST /security/v1/incidents/{id}/containment` | yes | — |
| `POST /security/v1/incidents/{id}/evidence` | yes | — |
| `POST /security/v1/incidents/{id}/gxp-impact` | yes | — |
| `POST /security/v1/incidents/{id}/close` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `SecurityAlertRaised` | SPEC-SEC-007 | event_id |
| `SecurityIncidentOpened` | SPEC-SEC-007 | event_id |
| `IncidentContainmentExecuted` | SPEC-SEC-007 | event_id |
| `ForensicEvidencePreserved` | SPEC-SEC-007 | event_id |
| `SecurityGxPImpactAssessed` | SPEC-SEC-007 | event_id |
| `SecurityIncidentClosed` | SPEC-SEC-007 | event_id |

UI SURFACES:
- Security Alerts
- Incident Queue
- Incident Timeline
- Containment Actions
- Forensic Evidence
- GxP Impact
- Detection Rules
- Telemetry Health
- Metrics

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
- credential stuffing alert
- cross-tenant denial burst
- break-glass alert
- audit hash failure
- Edge buffer hash mismatch
- log source silent
- ransomware tabletop
- session revocation containment
- forensic chain-of-custody
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-10/Document_67_SPEC-SEC-007_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-SEC-007/<test_case_id>/`.
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
