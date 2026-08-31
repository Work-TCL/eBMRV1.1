# Claude Code prompt — WP-11 / Document 77: Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture

TASK:
Implement the Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture module (SPEC-DATA-009) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_77_Cloud_Neutral_Kubernetes_OnPrem_Deployment_Upgrade_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DEP-FR-001..035 (35)
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
contracts/openapi/spec-data-009.yaml
contracts/events/spec-data-009/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-009/
```

REQUIREMENTS TO IMPLEMENT (35):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DEP-FR-001 | Deployment profiles | Support AWS, Azure, private cloud/on-prem Kubernetes and controlled VM/container profile without vendor-specific domain code. | Cloud-neutral. |
| DEP-FR-002 | Dedicated customer deployment | Baseline production uses dedicated customer deployment/isolation; multi-tenant shared deployment requires separate architecture approval. | Enterprise. |
| DEP-FR-003 | Environment separation | dev/test/validation/staging/prod logically separated with distinct secrets/data/endpoints. | SDLC. |
| DEP-FR-004 | IaC | Infrastructure defined in version-controlled Terraform/OpenTofu/Helm/Kustomize or approved equivalents. | Reproducible. |
| DEP-FR-005 | Immutable images | Services deployed from signed immutable image digest/release. | Supply-chain. |
| DEP-FR-006 | Configuration | Environment config separated from code; GxP/security config version controlled and approved as required. | Change control. |
| DEP-FR-007 | Kubernetes namespaces | Separate platform/GxP/integration/observability or equivalent boundaries with service accounts/network policy. | Isolation. |
| DEP-FR-008 | Stateless services | Frappe/GxP APIs/workers run as stateless horizontally scalable deployments where architecture permits. | Scale. |
| DEP-FR-009 | Stateful services | Managed services preferred where suitable; self-hosted stateful components use operators/StatefulSets/VMs with tested persistence/backup. | Reliability. |
| DEP-FR-010 | Persistent volumes | PVC/storage class performance/durability/retention explicitly configured; PVC retention not backup. | Storage. |
| DEP-FR-011 | Ingress | TLS ingress/API gateway with WAF/rate limits as deployment requires; admin endpoints segregated. | Security. |
| DEP-FR-012 | Service discovery | Internal DNS/service names stable and environment-scoped. | Runtime. |
| DEP-FR-013 | Secrets | External secret manager/CSI/operator or controlled equivalent; no plaintext Kubernetes Secret manifests in repo. | Security. |
| DEP-FR-014 | PKI | Service/Edge certificates provisioned through documented CA/KMS workflow. | Identity. |
| DEP-FR-015 | Database endpoints | Managed/private endpoints or internal-only services; no public DB. | Security. |
| DEP-FR-016 | Object store | Provider abstraction maps S3/Azure/on-prem endpoints and WORM/immutability capabilities. | Portability. |
| DEP-FR-017 | NATS | NATS cluster/service profile pins version, storage, replicas, TLS/auth, monitoring and backup/config. | Messaging. |
| DEP-FR-018 | Temporal | Temporal Cloud/self-hosted profile with namespace/auth/persistence/worker config. | Orchestration. |
| DEP-FR-019 | Redis/search | Optional deployment with HA/persistence according to cache/search role; service can degrade if unavailable. | Read layer. |
| DEP-FR-020 | Resource requests/limits | Kubernetes workloads define requests/limits based on load tests; avoid arbitrary tiny defaults. | Scheduling. |
| DEP-FR-021 | Probes | Startup/readiness/liveness probes are service-semantic; readiness fails when dependency needed to serve safely is unavailable. | Correct routing. |
| DEP-FR-022 | Graceful shutdown | APIs/workers drain requests/jobs/outbox leases before termination within configured grace. | Safe rollout. |
| DEP-FR-023 | Pod disruption | PDB/topology spread/anti-affinity used where availability warrants. | Resilience. |
| DEP-FR-024 | Autoscaling | Stateless workers/API HPA/KEDA or equivalent uses safe metrics and max bounds; DB connections considered. | Scale. |
| DEP-FR-025 | Rolling deploy | Rolling/canary/blue-green strategy per service risk; DB migrations backward compatible across rollout window. | Availability. |
| DEP-FR-026 | Rollback | Application rollback does not blindly reverse incompatible DB migration; migration compatibility plan explicit. | Safe release. |
| DEP-FR-027 | On-prem install | Air-gapped/private registry/offline package mode supported for enterprise plants where required. | Deployment. |
| DEP-FR-028 | On-prem prerequisites | CPU/RAM/storage/network/NTP/DNS/PKI/backup prerequisites machine-checkable before install. | Successful setup. |
| DEP-FR-029 | Installation validation | Post-install automated health/security/data/queue/storage/auth checks produce evidence report. | Qualification aid. |
| DEP-FR-030 | Upgrade | Upgrade preflight, backup, migration, deployment, smoke tests, rollback decision and validation evidence. | Controlled change. |
| DEP-FR-031 | Infrastructure drift | Detect IaC/config drift in production and alert/require reconciliation. | Validated state. |
| DEP-FR-032 | Feature flags | Runtime flags versioned/scoped; GxP-affecting flag cannot silently change regulated behavior outside change/release controls. | Safe config. |
| DEP-FR-033 | Time sync | All hosts/nodes use approved UTC/NTP/PTP strategy and monitor offset. | Chronology. |
| DEP-FR-034 | Certificate/DNS expiry | Monitor certificates/domains/dependencies before expiry. | Availability. |
| DEP-FR-035 | No single-node assumption | Production reference can scale beyond one host; on-prem compact profile explicitly documents reduced HA. | Commercial scalability. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| validateDeploymentPrerequisites() | Installer/CI | deployment profile; discovered infrastructure | PrerequisiteReport | DEPLOYMENT_PREREQUISITE_FAILED |
| renderInfrastructurePlan() | IaC pipeline | customer/environment profile; versions; sizing | InfrastructurePlan | InfrastructurePlanGenerated |
| applyInfrastructurePlan() | Authorized deploy pipeline | signed plan/artifacts; environment | DeploymentResult | InfrastructureApplied |
| runPostInstallQualificationChecks() | Installer/Validation | environment; check profile | InstallationCheckReport | InstallationChecksCompleted |
| performRollingUpgrade() | Release pipeline | current/new release; migration plan; rollout strategy | UpgradeResult | PlatformUpgraded |
| detectInfrastructureDrift() | Scheduled/CI | declared IaC state; observed resources | DriftReport | InfrastructureDriftDetected |
| scaleService() | Autoscaler/operator | service; target replicas/capacity trigger | ScaleResult | ServiceScaled |
| drainWorkerSafely() | Deployment lifecycle | worker instance; grace deadline | DrainResult | WorkerDrained |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (1 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `deployment_profile` | 8 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `DeploymentPrerequisiteFailed` | SPEC-DATA-009 | event_id |
| `InfrastructureApplied` | SPEC-DATA-009 | event_id |
| `InstallationChecksCompleted` | SPEC-DATA-009 | event_id |
| `InfrastructureDriftDetected` | SPEC-DATA-009 | event_id |
| `PlatformUpgraded` | SPEC-DATA-009 | event_id |
| `RollbackInitiated` | SPEC-DATA-009 | event_id |
| `CertificateExpiryWarning` | SPEC-DATA-009 | event_id |

UI SURFACES:
- Deployment Inventory
- Version Matrix
- Install Preflight
- Upgrade Dashboard
- Drift
- Capacity/Autoscaling
- Post-Install Qualification

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
- fresh cloud install
- air-gapped on-prem install
- NTP missing preflight
- PVC lost pod reschedule
- rolling API upgrade
- worker drains outbox
- DB migration backward compatibility
- failed smoke rollback
- IaC drift
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_77_SPEC-DATA-009_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-009/<test_case_id>/`.
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
