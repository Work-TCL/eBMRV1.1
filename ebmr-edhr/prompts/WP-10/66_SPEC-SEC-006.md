# Claude Code prompt — WP-10 / Document 66: Network, Tenant, Deployment Isolation & Zero-Trust Architecture

TASK:
Implement the Network, Tenant, Deployment Isolation & Zero-Trust Architecture module (SPEC-SEC-006) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_66_Network_Tenant_Deployment_Isolation_Zero_Trust_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: NET-FR-001..030 (30)
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
contracts/openapi/spec-sec-006.yaml
contracts/events/spec-sec-006/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-sec-006/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| NET-FR-001 | Deployment zones | Define ingress, app, GxP service, DB, integration, observability, admin and Edge/OT zones. | Layered architecture. |
| NET-FR-002 | Default deny | Network policies/firewalls default deny between zones and allow only required flows. | Least connectivity. |
| NET-FR-003 | No DB internet exposure | MariaDB/PostgreSQL/object stores/internal message bus not publicly exposed. | Attack surface. |
| NET-FR-004 | Service-to-service auth | Internal network location alone does not authorize service access; workload identity/auth required. | Zero trust. |
| NET-FR-005 | Ingress | Only approved reverse proxy/API gateway/load balancer exposed externally; admin routes separately protected. | Controlled entry. |
| NET-FR-006 | Egress | Application/integration services use outbound allowlists/proxy/network policy; GxP DB has no arbitrary internet egress. | SSRF containment. |
| NET-FR-007 | OT boundary | Edge Gateway mediates IT/OT data flow; cloud/app services do not directly initiate arbitrary PLC connections. | Industrial isolation. |
| NET-FR-008 | Edge outbound preferred | Plant Edge to server connections outbound initiated where feasible. | Reduced inbound exposure. |
| NET-FR-009 | Admin plane | Administrative access through protected VPN/ZTNA/bastion/PAM path rather than public service ports. | Privileged isolation. |
| NET-FR-010 | Tenant isolation | Dedicated customer deployment is baseline; within deployment tenant/site scopes still enforced in application/data/jobs. | Defense in depth. |
| NET-FR-011 | Cross-site isolation | Site-scoped integrations, Edge identities, service config and background jobs cannot cross site without explicit enterprise scope. | Scope. |
| NET-FR-012 | Database roles | Separate DB users/roles by service/schema/write need; Frappe DB credential cannot write GxP DB. | Data ownership. |
| NET-FR-013 | Schema ownership | GxP service repositories own tables; integrations/read models use restricted views/API, not shared superuser. | Least privilege. |
| NET-FR-014 | Message bus ACL | NATS/event subjects ACL by service identity; no universal publish/subscribe credential. | Event integrity. |
| NET-FR-015 | Object store policy | Evidence buckets/prefixes restricted by service identity; immutable/WORM policies protected from app deletion. | Evidence integrity. |
| NET-FR-016 | Kubernetes namespace | Reference K8s deployment separates workloads/namespaces/service accounts/network policies by trust/function. | Container isolation. |
| NET-FR-017 | Container privilege | Run non-root, read-only filesystem/capability drops/seccomp/AppArmor where compatible. | Workload hardening. |
| NET-FR-018 | Host hardening | Reference OS baseline disables unnecessary services, applies patch/config baseline and time sync. | Secure host. |
| NET-FR-019 | TLS termination | TLS termination points explicit; re-encrypt/internal TLS where trust boundary requires. | Transport clarity. |
| NET-FR-020 | Private endpoints | Cloud DB/object/KMS prefer private networking/endpoints where supported. | Reduced public exposure. |
| NET-FR-021 | DNS | Internal service discovery controlled; DNS changes/security monitored; avoid trusting hostname without TLS identity. | Name integrity. |
| NET-FR-022 | Remote sites | Site-to-central connectivity uses secure VPN/private link/TLS with explicit routing; no flat corporate network assumption. | Enterprise. |
| NET-FR-023 | Environment isolation | Dev/test/validation/prod separated accounts/projects/namespaces/secrets/data; production credentials absent from non-prod. | SDLC safety. |
| NET-FR-024 | Synthetic data | Non-prod uses synthetic/deidentified data by default; production data copy requires controlled approval/sanitization. | Privacy. |
| NET-FR-025 | Backup isolation | Backup repository/access logically isolated from normal application compromise path. | Ransomware resilience. |
| NET-FR-026 | Monitoring access | Security monitoring has read/ingest permissions, not business-write privileges. | Separation. |
| NET-FR-027 | Port inventory | All inbound/outbound ports/protocols documented by deployment profile. | Reviewable. |
| NET-FR-028 | Network change | GxP-impacting firewall/routing/service-exposure changes controlled and tested. | Validated state. |
| NET-FR-029 | Segmentation test | Automated/periodic tests verify forbidden network paths remain blocked. | Verification. |
| NET-FR-030 | No security by IP only | IP allowlist may supplement but never replace identity/auth for regulated APIs. | Zero trust. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| generateNetworkPolicySet() | Infrastructure compiler | deployment_profile; service inventory; approved flow catalogue | NetworkPolicyBundle | NetworkPolicyGenerated |
| validateServiceFlow() | CI/security test | source identity/zone; destination; protocol/port | FlowDecision | NETWORK_FLOW_NOT_ALLOWED |
| issueSiteScopedEdgeNetworkProfile() | Deployment/Edge admin | site_id; gateway_id; required endpoints | EdgeNetworkProfile | EdgeNetworkProfileIssued |
| verifyTenantScopePropagation() | Security test/runtime assertion | AuthContext/job/event; expected tenant/site | ScopeVerification | TENANT_SCOPE_MISMATCH |
| testForbiddenNetworkPath() | Continuous/periodic security test | source workload; destination target | SegmentationTestResult | SegmentationControlFailed |
| validateDeploymentHardening() | CI/deploy admission | workload manifest/image/security context | HardeningResult | WORKLOAD_HARDENING_FAILED |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `network_flow_definition` | 8 | PostgreSQL (GxP Core, authoritative) |
| `deployment_security_profile` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (2):
| Operation | State-changing | Signature |
|---|---|---|
| `GET /security/v1/network-flows` | no | — |
| `GET /security/v1/deployment-security-profile` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (4):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ForbiddenNetworkPathDetected` | SPEC-SEC-006 | event_id |
| `TenantScopeMismatchDetected` | SPEC-SEC-006 | event_id |
| `WorkloadHardeningFailed` | SPEC-SEC-006 | event_id |
| `UnexpectedPublicExposureDetected` | SPEC-SEC-006 | event_id |

UI SURFACES:
- Trust Zone Diagram
- Network Flow Catalogue
- Segmentation Test Results
- Tenant/Site Isolation Test
- Deployment Hardening

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
- Frappe cannot connect to GxP DB directly
- integration service cannot access QA tables
- Edge cannot reach DB
- cross-site job blocked
- dev credential cannot reach prod
- container root policy
- public DB exposure detection
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-10/Document_66_SPEC-SEC-006_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-SEC-006/<test_case_id>/`.
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
