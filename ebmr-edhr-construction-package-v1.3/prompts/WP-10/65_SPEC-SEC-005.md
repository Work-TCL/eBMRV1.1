# Claude Code prompt — WP-10 / Document 65: Secrets Management, PKI, Cryptography & Key Lifecycle

TASK:
Implement the Secrets Management, PKI, Cryptography & Key Lifecycle module (SPEC-SEC-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_65_Secrets_PKI_Cryptography_Key_Lifecycle_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: KEY-FR-001..028 (28)
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
contracts/openapi/spec-sec-005.yaml
contracts/events/spec-sec-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-sec-005/
```

REQUIREMENTS TO IMPLEMENT (28):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| KEY-FR-001 | Secret inventory | Inventory database passwords, OAuth secrets, API keys, signing keys, mTLS keys, Edge certs and encryption keys with owner/rotation policy. | Known secrets. |
| KEY-FR-002 | Secret manager abstraction | Production secrets retrieved from Kubernetes/cloud/on-prem secret manager abstraction; source-controlled plaintext prohibited. | Central management. |
| KEY-FR-003 | Secret references | Application config stores secret references/identifiers, not secret values. | Safe config. |
| KEY-FR-004 | Least access | Each service identity can retrieve only required secrets. | Least privilege. |
| KEY-FR-005 | Rotation | Rotation supported without code change; overlap/grace for credentials/certs where protocol requires. | Lifecycle. |
| KEY-FR-006 | Emergency rotation | Compromised secret can be revoked/rotated rapidly with incident linkage. | Response. |
| KEY-FR-007 | PKI hierarchy | Document root/intermediate/issuing authorities or enterprise CA integration for service/Edge certificates. | Trust. |
| KEY-FR-008 | Certificate issuance | Certificate subject/SAN/purpose/tenant/site/service binding validated before issuance. | Identity. |
| KEY-FR-009 | Certificate rotation | Automated/controlled renewal before expiry; failed renewal alerts. | Availability. |
| KEY-FR-010 | Certificate revocation | Revoked identity rejected promptly according to deployment's CRL/OCSP/trust-store approach. | Compromise containment. |
| KEY-FR-011 | TLS | TLS configured using current approved deployment baseline; obsolete protocol/cipher disabled. | Transport security. |
| KEY-FR-012 | mTLS | Use mTLS for selected service/Edge/admin integration boundaries where architecture requires. | Strong workload identity. |
| KEY-FR-013 | At-rest encryption | Volumes/object stores/backups use platform-approved at-rest encryption; sensitive application fields can use envelope/field encryption when risk requires. | Data confidentiality. |
| KEY-FR-014 | Field encryption | Patient/reporter/sensitive secret-like data fields can be encrypted with tenant/data-class keys where required. | Privacy. |
| KEY-FR-015 | Key hierarchy | Data-encryption keys separated from key-encryption/master keys; external KMS/HSM supported. | Separation. |
| KEY-FR-016 | Crypto agility | Algorithms/key sizes identified by versioned crypto profile so platform can migrate without schema redesign. | Future-proof. |
| KEY-FR-017 | Hashing | Use approved cryptographic hashing for evidence/audit/manifests; algorithm recorded with hash. | Integrity. |
| KEY-FR-018 | Passwords | Human password hashing delegated to IdP using modern adaptive hashing; app does not implement own password DB. | Correct scope. |
| KEY-FR-019 | Signature cryptography | Part 11 signature evidence integrity uses Document 04/Vault design; do not confuse cryptographic document signing with user authentication. | Semantics. |
| KEY-FR-020 | Audit checkpoints | Audit integrity checkpoint signing key separate from TLS/application credentials. | Blast radius. |
| KEY-FR-021 | Backup keys | Backup encryption keys and restore procedures documented/tested; avoid unrecoverable encrypted backups. | Recoverability. |
| KEY-FR-022 | Key access logging | KMS/HSM/secret accesses/administrative changes logged. | Detection. |
| KEY-FR-023 | No secret logging | Application/Edge/CI redacts Authorization headers, cookies, private keys, passwords/tokens and configured sensitive fields. | Leak prevention. |
| KEY-FR-024 | No secret in artifact | Container images/build outputs/packages do not contain environment secrets. | Supply-chain hygiene. |
| KEY-FR-025 | Certificate pinning/trust | OPC UA/custom partner trust stores managed explicitly; 'trust all' prohibited in production. | External security. |
| KEY-FR-026 | Tenant key strategy | Dedicated deployment/customer keys supported; shared SaaS-style keying not assumed. | Enterprise isolation. |
| KEY-FR-027 | Key destruction | Retired keys destroyed only after retention/restore/legal requirements permit; destruction evidence recorded. | Lifecycle. |
| KEY-FR-028 | Crypto self-test | Startup/health checks detect missing/expired/inaccessible critical keys/certs and fail safely. | Operational assurance. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| resolveSecret() | Service runtime | secret_ref; service identity; purpose | SecretHandle/value | SecretAccessed; SECRET_ACCESS_DENIED |
| rotateSecret() | Security Admin/automation | secret_id; new credential material/generator; overlap policy | SecretRotationResult | SecretRotated; SECRET_ROTATION_FAILED |
| issueServiceCertificate() | PKI service | CSR; service identity; SANs; validity; profile | CertificateRef | CertificateIssued |
| rotateCertificate() | Automation/Admin | certificate_id; CSR | CertificateRotation | CertificateRotated |
| revokeCertificate() | Security/Incident | certificate serial; reason | RevocationReceipt | CertificateRevoked |
| encryptSensitiveField() | Application crypto service | tenant/key context; plaintext bytes; AAD | EncryptedField | FIELD_ENCRYPTION_FAILED |
| decryptSensitiveField() | Authorized service | ciphertext envelope; access context | Plaintext | FIELD_DECRYPTION_DENIED |
| hashEvidence() | Evidence/Audit/Edge | stream/bytes; crypto profile | DigestRef | EvidenceHashed |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `secret_metadata` | 8 | PostgreSQL (GxP Core, authoritative) |
| `certificate_metadata` | 8 | PostgreSQL (GxP Core, authoritative) |
| `crypto_profile` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (5):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /security/v1/secrets/{id}/rotate` | yes | — |
| `POST /security/v1/certificates:issue` | yes | — |
| `POST /security/v1/certificates/{id}/rotate` | yes | — |
| `POST /security/v1/certificates/{id}/revoke` | yes | — |
| `GET /security/v1/crypto-health` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `SecretAccessDenied` | SPEC-SEC-005 | event_id |
| `SecretRotated` | SPEC-SEC-005 | event_id |
| `CertificateIssued` | SPEC-SEC-005 | event_id |
| `CertificateRotated` | SPEC-SEC-005 | event_id |
| `CertificateRevoked` | SPEC-SEC-005 | event_id |
| `CryptoHealthFailed` | SPEC-SEC-005 | event_id |
| `KeyAccessAnomaly` | SPEC-SEC-005 | event_id |

UI SURFACES:
- Secret Inventory (metadata only)
- Certificate Inventory
- Rotation Dashboard
- Crypto Profiles
- Trust Stores
- Key Access Audit

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
- expired service cert
- rotation with no outage
- revoked Edge cert
- secret leaked scanner test
- field encryption wrong tenant key
- backup restore with retired key
- trust-all cert config blocked
- hash algorithm migration
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-10/Document_65_SPEC-SEC-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-SEC-005/<test_case_id>/`.
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
