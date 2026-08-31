# Claude Code prompt — WP-10 / Document 68: Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security

TASK:
Implement the Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security module (SPEC-SEC-008) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_68_Secure_SDLC_Software_Supply_Chain_SBOM_Vulnerability_Release_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: SDLC-FR-001..034 (34)
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
contracts/openapi/spec-sec-008.yaml
contracts/events/spec-sec-008/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-sec-008/
```

REQUIREMENTS TO IMPLEMENT (34):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| SDLC-FR-001 | Secure SDLC policy | Security activities integrated into requirements, design, implementation, review, test, release and maintenance. | Lifecycle. |
| SDLC-FR-002 | SSDF mapping | Engineering process maps to NIST SSDF v1.1 practices; future v1.2 changes assessed separately when final. | Current baseline. |
| SDLC-FR-003 | Security requirements | Security requirement IDs traced from threats/ASVS/API controls to code/tests. | Traceability. |
| SDLC-FR-004 | Branch protection | Protected branches, reviewed PRs, status checks and restricted force-push for production code. | Integrity. |
| SDLC-FR-005 | Code review | At least one qualified reviewer; critical security/GxP modules may require CODEOWNERS/security/architecture review. | Independent review. |
| SDLC-FR-006 | Secret scanning | Pre-commit/CI scanning for credentials/private keys/tokens. | Leak prevention. |
| SDLC-FR-007 | SAST | Static analysis on supported languages with severity policy and suppression review. | Vulnerability detection. |
| SDLC-FR-008 | SCA | Dependency/software composition analysis with CVE/licensing metadata. | Supply chain. |
| SDLC-FR-009 | SBOM | Generate machine-readable SBOM per release/image, preferably SPDX or CycloneDX profile. | Inventory. |
| SDLC-FR-010 | Dependency pinning | Lockfiles/digests; production build does not consume unconstrained latest. | Reproducibility. |
| SDLC-FR-011 | Artifact signing | Release images/packages/manifests signed/attested; deployment verifies approved artifact. | Provenance. |
| SDLC-FR-012 | Build isolation | CI runners least privilege, ephemeral where possible, protected secrets, no untrusted PR access to production credentials. | Pipeline security. |
| SDLC-FR-013 | Reproducibility/provenance | Record source commit, build workflow, builder, dependency lock, SBOM, artifact digest and tests. | Trace. |
| SDLC-FR-014 | Container scanning | Base image/package vulnerabilities scanned; image pinned by digest. | Runtime hygiene. |
| SDLC-FR-015 | IaC scanning | Terraform/K8s/Helm/config scanned for security misconfiguration. | Infrastructure security. |
| SDLC-FR-016 | DAST/API test | Automated dynamic/API security tests on deployable environments. | Runtime validation. |
| SDLC-FR-017 | Dependency allowlist | High-risk/native/cryptography/security libraries receive review/approval; abandoned packages avoided. | Risk control. |
| SDLC-FR-018 | Vulnerability intake | Internal scans, customer reports, researchers and vendor advisories enter vulnerability register. | Complete intake. |
| SDLC-FR-019 | Severity | Use controlled severity model considering exploitability, exposure, GxP/data impact and known exploitation. | Prioritization. |
| SDLC-FR-020 | KEV awareness | Known exploited vulnerability status is included in prioritization/patch decision. | Real-world risk. |
| SDLC-FR-021 | Remediation SLA | Target remediation by severity/profile; exceptions time-bounded/risk-approved. | Governance. |
| SDLC-FR-022 | Coordinated disclosure | Security contact/process for customer/researcher reports and advisories. | Transparency. |
| SDLC-FR-023 | CVE process | Product vulnerabilities receive CVE/advisory handling where organization becomes CNA/uses CNA process as applicable. | Industry practice. |
| SDLC-FR-024 | Patch release | Security patch uses controlled build/sign/test/deploy path and Change/validation impact as required. | Safe updates. |
| SDLC-FR-025 | Backport policy | Supported release branches and security backport policy defined. | Customer support. |
| SDLC-FR-026 | Penetration testing | Independent/manual pen test before regulated pilot and periodically/material-change based. | Assurance. |
| SDLC-FR-027 | Threat-driven tests | Threat model abuse cases become security test cases. | Risk based. |
| SDLC-FR-028 | Fuzzing | Parsers/custom protocols/file import/high-risk APIs fuzzed where practical. | Robustness. |
| SDLC-FR-029 | Security regression | Previously fixed vulnerability gets regression test where feasible. | Prevent recurrence. |
| SDLC-FR-030 | Release security gate | Critical/high unresolved vulnerabilities/control failures can block release according to policy. | No insecure release. |
| SDLC-FR-031 | Validation linkage | Security-impacting change feeds CSA/CSV validation impact and controlled deployment evidence. | GxP. |
| SDLC-FR-032 | Third-party components | Commercial/open-source components have owner, version, license, support/EOL and vulnerability-monitoring status. | Supply chain. |
| SDLC-FR-033 | Base image lifecycle | Approved minimal base images, refresh cadence and EOL tracking. | Container security. |
| SDLC-FR-034 | Customer update evidence | Release notes include security/validation-impact information without exposing exploit details irresponsibly. | Enterprise operations. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| generateReleaseSBOM() | CI release pipeline | artifact/image; dependency graph; build metadata | SBOMRef | ReleaseSBOMGenerated |
| scanReleaseArtifact() | CI security gate | artifact digest; scanners/profiles | SecurityScanReport | ReleaseArtifactScanned |
| evaluateSecurityReleaseGate() | CI/release approver | scan report; open vulnerabilities; exceptions; security-control tests | SecurityGateDecision | SecurityReleaseBlocked/Passed |
| registerVulnerability() | Scanner/researcher/customer/security | component/version; finding; evidence; affected releases | VulnerabilityRecord | VulnerabilityRegistered |
| assessVulnerabilitySeverity() | Security team | vuln_id; CVSS/exploit/KEV/exposure/GxP impact inputs | VulnerabilityAssessment | VulnerabilityAssessed |
| approveVulnerabilityException() | Security/Risk/Quality if GxP | vuln_id; rationale; compensating controls; expiry | VulnerabilityException | VulnerabilityExceptionApproved |
| signReleaseArtifact() | Release pipeline | artifact digest; provenance; signing identity | SignedArtifactRef | ReleaseArtifactSigned |
| verifyDeploymentArtifact() | Deployment admission | artifact/image; expected release | ArtifactVerification | UNTRUSTED_ARTIFACT |
| publishSecurityAdvisory() | Security response | vulnerability; affected/fixed versions; mitigation; disclosure timing | SecurityAdvisory | SecurityAdvisoryPublished |
| createSecurityRegressionTest() | Engineering | vuln/threat ID; reproducer; expected fixed behavior | SecurityTestRef | SecurityRegressionTestAdded |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `software_component_inventory` | 5 | PostgreSQL (GxP Core, authoritative) |
| `vulnerability_record` | 11 | PostgreSQL (GxP Core, authoritative) |
| `release_security_evidence` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /security/v1/vulnerabilities` | yes | — |
| `POST /security/v1/vulnerabilities/{id}/assess` | yes | — |
| `POST /security/v1/vulnerabilities/{id}/exceptions` | yes | — |
| `GET /security/v1/releases/{id}/security-evidence` | no | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ReleaseSBOMGenerated` | SPEC-SEC-008 | event_id |
| `VulnerabilityRegistered` | SPEC-SEC-008 | event_id |
| `VulnerabilityAssessed` | SPEC-SEC-008 | event_id |
| `SecurityReleaseBlocked` | SPEC-SEC-008 | event_id |
| `ReleaseArtifactSigned` | SPEC-SEC-008 | event_id |
| `SecurityAdvisoryPublished` | SPEC-SEC-008 | event_id |

UI SURFACES:
- Vulnerability Register
- Component/SBOM Inventory
- Security Release Gate
- Exceptions
- Pen Test Findings
- Security Advisories
- Supported Releases

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
- secret in repo
- critical dependency CVE
- KEV critical library
- unsigned image blocked
- SBOM mismatch
- vulnerable base image
- untrusted PR secret access
- pen-test BOLA finding
- security exception expiry
- regression test
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-10/Document_68_SPEC-SEC-008_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-SEC-008/<test_case_id>/`.
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
