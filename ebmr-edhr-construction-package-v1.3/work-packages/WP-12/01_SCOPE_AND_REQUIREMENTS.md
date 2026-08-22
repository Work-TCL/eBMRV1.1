# WP-12 — Scope & Requirements

**In scope:** Documents 79, 80, 81, 82, 83, 84, 86, 88, 89, 90, 91, 92, 93, 94, 96

## Document 79 — Validation Master Plan & Computer Software Assurance Strategy (SPEC-VAL-001)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: VAL-FR-001..028 (28)

## Document 80 — Intended Use, GxP Criticality & Software Function Risk Classification (SPEC-VAL-002)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: RISK-FR-001..022 (22)

## Document 81 — Requirements, Design Inputs & Validation Traceability Management (SPEC-VAL-003)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: REQ-FR-001..023 (23)

## Document 82 — Validation Test Strategy, Test Methods & Objective Evidence Governance (SPEC-VAL-004)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: TST-FR-001..024 (24)

## Document 83 — Installation Qualification (IQ) & Installed Baseline Verification (SPEC-VAL-005)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: IQ-FR-001..021 (21)

## Document 84 — Operational Qualification (OQ) & Functional Control Verification (SPEC-VAL-006)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: OQ-FR-001..018 (18)

## Document 86 — Infrastructure, Cloud, Platform & Environment Qualification (SPEC-VAL-008)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: INFQ-FR-001..020 (20)

## Document 88 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation (SPEC-VAL-010)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: P11-FR-001..026 (26)

## Document 89 — Audit Trail, Record Version Vault & Data Integrity Validation (SPEC-VAL-011)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DIV-FR-001..024 (24)

## Document 90 — Integration, Edge, Device, Peripheral & Interface Validation (SPEC-VAL-012)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: IFV-FR-001..024 (24)

## Document 91 — Backup, Restore, PITR & Disaster Recovery Qualification (SPEC-VAL-013)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DRV-FR-001..022 (22)

## Document 92 — Security Qualification, Vulnerability Verification & Penetration Testing (SPEC-VAL-014)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: SECQ-FR-001..024 (24)

## Document 93 — Performance, Load, Capacity & Reliability Qualification (SPEC-VAL-015)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PERFQ-FR-001..024 (24)

## Document 94 — Validation Defect, Deviation, Test Exception & Remediation Management (SPEC-VAL-016)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: VEX-FR-001..022 (22)

## Document 96 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance (SPEC-VAL-018)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: VSM-FR-001..028 (28)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| VAL-FR-001 | 79 | Validation policy | Define product validation policy for DDCP/device/pharma deployment profiles. | Single strategy. |
| VAL-FR-002 | 79 | CSA applicability | Medical-device production/QMS functions use FDA 2026 CSA risk-based assurance principles. | Current FDA approach. |
| VAL-FR-003 | 79 | Drug validation basis | Drug constituent functions map Part 11/predicate rules/211.68 independently of device CSA guidance. | Correct scope. |
| VAL-FR-004 | 79 | Intended-use hierarchy | System → module → function → deployment intended use documented before assurance decision. | Risk context. |
| VAL-FR-005 | 79 | Validation plan version | Validation Master Plan versioned/released and linked to release family. | Controlled plan. |
| VAL-FR-006 | 79 | Deliverables | Define required artifacts by risk, deployment and customer responsibility. | Predictable evidence. |
| VAL-FR-007 | 79 | Responsibility matrix | Define vendor vs customer validation duties for platform, config, interfaces, SOPs, training and PQ/UAT. | Shared responsibility. |
| VAL-FR-008 | 79 | Risk-based rigor | Test method, independence and evidence depth increase with GxP/process risk. | Proportionate assurance. |
| VAL-FR-009 | 79 | Automated evidence | Controlled CI/unit/integration/system automation may provide objective validation evidence. | CSA efficiency. |
| VAL-FR-010 | 79 | Exploratory evidence | Exploratory testing permitted when risk allows and charter, actions, findings and conclusion are retained. | Flexible assurance. |
| VAL-FR-011 | 79 | Scripted evidence | Higher-risk or complex functions use detailed expected-results testing where needed. | Higher assurance. |
| VAL-FR-012 | 79 | Supplier evidence reuse | Code review, automated tests, SBOM, scans and design reviews can contribute when traceable. | Avoid duplication. |
| VAL-FR-013 | 79 | Representative environment | Qualification environment represents production configuration; differences documented/assessed. | Representative testing. |
| VAL-FR-014 | 79 | Configuration validation | Customer GxP configuration/rules/workflows/interfaces require validation beyond platform baseline. | Configured product. |
| VAL-FR-015 | 79 | Interface validation | ERP/LIMS/Edge/device interfaces separately scoped by intended use/risk. | Boundary assurance. |
| VAL-FR-016 | 79 | Migration validation | Data migration/conversion has dedicated plan/reconciliation/evidence. | Data integrity. |
| VAL-FR-017 | 79 | Part 11 validation | Electronic records/signatures/audit/copies/retention/access controls explicitly verified. | Part 11. |
| VAL-FR-018 | 79 | Infrastructure qualification | Cloud/on-prem infrastructure, backup, security and time prerequisites qualified. | Environment confidence. |
| VAL-FR-019 | 79 | Performance/security | Risk-relevant performance/security evidence required before regulated pilot. | Operational suitability. |
| VAL-FR-020 | 79 | Deviation handling | Validation deviations/defects/failures controlled; unresolved critical blockers prevent release. | No paper pass. |
| VAL-FR-021 | 79 | Traceability | Requirements ↔ risk ↔ functions ↔ tests ↔ evidence ↔ defects ↔ release. | Inspection-ready. |
| VAL-FR-022 | 79 | Approval roles | Validation author/reviewer/approver/QA release roles separated by policy. | SoD. |
| VAL-FR-023 | 79 | Customer package | Generate vendor baseline plus customer/site qualification package. | Commercial usability. |
| VAL-FR-024 | 79 | Release gate | Go-live requires approved VSR and exact validated artifact/configuration. | Controlled go-live. |
| VAL-FR-025 | 79 | Ongoing state | Periodic review/change impact/revalidation maintain validated state. | Lifecycle. |
| VAL-FR-026 | 79 | Evidence retention | Validation evidence retained according to applicable system/customer/regulatory policy. | Evidence. |
| VAL-FR-027 | 79 | Electronic validation records | Validation approvals/evidence use controlled electronic records/signatures when relied upon electronically. | Self-consistency. |
| VAL-FR-028 | 79 | No document-count metric | Assurance judged by risk coverage and evidence, not number of scripts/pages. | CSA intent. |
| RISK-FR-001 | 80 | Intended use | Document intended use at system/module/function level and affected regulated process. | Risk basis. |
| RISK-FR-002 | 80 | GxP impact | Classify direct/indirect/no GxP impact with rationale. | Scoping. |
| RISK-FR-003 | 80 | Quality impact | Assess patient/product quality, safety, data integrity and release consequences. | CSA risk. |
| RISK-FR-004 | 80 | Failure mode | Identify process/business failure if function fails or produces wrong result. | Real risk. |
| RISK-FR-005 | 80 | Detectability | Assess likelihood failure is detected before harm/wrong decision. | Risk dimension. |
| RISK-FR-006 | 80 | Automation role | Classify informational/advisory/calculation/enforcement/control/automated decision. | Criticality. |
| RISK-FR-007 | 80 | Record role | Identify whether function creates/modifies/signs/audits/archives predicate-rule record. | Part 11 scope. |
| RISK-FR-008 | 80 | Signature role | Identify whether function performs/relies on legally binding e-signature. | Part 11. |
| RISK-FR-009 | 80 | Constituent scope | For DDCP identify drug/device/biologic/final-combination impact. | Part 4 context. |
| RISK-FR-010 | 80 | Risk category | Use controlled higher-process-risk/standard-risk plus internal criticality as configured. | CSA alignment. |
| RISK-FR-011 | 80 | Assurance method | Risk drives testing style, depth, independence and evidence. | Proportionate. |
| RISK-FR-012 | 80 | Configuration risk | Assess customer workflow/rule/form/interface configuration separately from platform code. | Configured state. |
| RISK-FR-013 | 80 | Supplier component risk | Assess third-party/OSS/service based on intended use and controls. | Supply-chain. |
| RISK-FR-014 | 80 | Infrastructure risk | Assess critical infrastructure failure/recovery effects. | Environment. |
| RISK-FR-015 | 80 | Interface risk | Assess external data/mapping/source/output failure and detection. | Integration. |
| RISK-FR-016 | 80 | AI risk | AI advisory functions separately classified; autonomous regulated decisions prohibited. | AI governance. |
| RISK-FR-017 | 80 | Risk version | Assessment tied to exact requirement/function/design/config version. | Traceability. |
| RISK-FR-018 | 80 | Change reassessment | Material change triggers risk impact reassessment. | Lifecycle. |
| RISK-FR-019 | 80 | Residual risk | Post-control risk documented and approved. | Governance. |
| RISK-FR-020 | 80 | Scoring method | Methodology versioned; numeric score never replaces rationale. | Quality. |
| RISK-FR-021 | 80 | Out-of-scope rationale | Validation exclusion documented/reviewed and change-sensitive. | Inspection. |
| RISK-FR-022 | 80 | Coverage | Every higher-risk function maps controls and objective evidence. | Completeness. |
| REQ-FR-001 | 81 | Requirement registry | Ingest all stable requirements with source document/ID/version. | Single registry. |
| REQ-FR-002 | 81 | Requirement types | Classify business/GxP/security/data/interface/performance/validation/config requirements. | Coverage. |
| REQ-FR-003 | 81 | Testability | Requirement must be verifiable or explicitly rationale-based design constraint. | Quality. |
| REQ-FR-004 | 81 | Acceptance criteria | Critical requirements include objective acceptance criteria. | No vague pass. |
| REQ-FR-005 | 81 | Regulatory source | Derived requirement stores source and binding/guidance status. | Explainability. |
| REQ-FR-006 | 81 | Risk link | Requirement links risk/intended-use function assessment. | Risk trace. |
| REQ-FR-007 | 81 | Design link | Requirement maps function/service/API/schema/UI/config artifact. | Design trace. |
| REQ-FR-008 | 81 | Test link | Requirement maps tests/evidence or justified alternative verification. | Evidence. |
| REQ-FR-009 | 81 | Defect link | Failed evidence links defect/deviation. | Closure. |
| REQ-FR-010 | 81 | Release baseline | Release identifies exact requirement versions in scope. | Configuration control. |
| REQ-FR-011 | 81 | Supersession | Superseded requirements remain retained/versioned. | History. |
| REQ-FR-012 | 81 | Change impact | Requirement change identifies affected design/tests/risk/docs. | Efficient revalidation. |
| REQ-FR-013 | 81 | Bidirectional trace | Navigate requirement→test and test→requirements. | Inspection. |
| REQ-FR-014 | 81 | Orphan detection | Detect unimplemented/untested critical requirements and orphan tests. | Completeness. |
| REQ-FR-015 | 81 | Coverage metrics | Coverage by risk/module/profile visible but percentage not sole release criterion. | Visibility. |
| REQ-FR-016 | 81 | Function catalogue link | Claude-generated function contracts become design trace targets. | Construction. |
| REQ-FR-017 | 81 | API/event/schema trace | OpenAPI/AsyncAPI/DB migration entries map requirement IDs. | Technical trace. |
| REQ-FR-018 | 81 | Automated metadata | Test code/results carry stable test/requirement IDs. | Repeatability. |
| REQ-FR-019 | 81 | Customer URS | Customer-specific URS layers on product requirements without overwriting vendor baseline. | Commercial. |
| REQ-FR-020 | 81 | SPEC_GAP | SPEC_GAP tracked as unresolved requirement/design issue and release blocker by severity. | No guessing. |
| REQ-FR-021 | 81 | Baseline freeze | Freeze requirement set/version/hash for validation/release. | Controlled. |
| REQ-FR-022 | 81 | Export | Traceability export CSV/PDF/JSON generated from authoritative graph. | Inspection. |
| REQ-FR-023 | 81 | No spreadsheet authority | Spreadsheet is export, not authoritative traceability source. | Integrity. |
| TST-FR-001 | 82 | Test methods | Support automated, scripted manual, exploratory, review/inspection, analysis and supplier-evidence verification. | CSA flexibility. |
| TST-FR-002 | 82 | Method selection | Risk, complexity, determinism and control drive test method. | Risk based. |
| TST-FR-003 | 82 | Versioning | Approved/executed test definition immutable/versioned. | Evidence. |
| TST-FR-004 | 82 | Preconditions | Define environment/config/data/roles/dependencies. | Repeatability. |
| TST-FR-005 | 82 | Expected results | Scripted/automated tests have objective expected result/tolerance. | Clear pass. |
| TST-FR-006 | 82 | Exploratory charter | Retain charter, tester, actions, observations, conclusion and evidence. | Objective evidence. |
| TST-FR-007 | 82 | Test data | Synthetic/controlled data identified/versioned; production data avoided unless controlled. | Governance. |
| TST-FR-008 | 82 | Environment fingerprint | Capture app/build/config/DB/schema/browser/device/interface versions. | Reproducibility. |
| TST-FR-009 | 82 | Automated evidence | Capture test code commit, runner/image, logs/results/artifacts. | Trustworthy automation. |
| TST-FR-010 | 82 | Manual execution | Capture performer, timestamps, actual result, evidence, deviations. | Attribution. |
| TST-FR-011 | 82 | Review | Higher-risk evidence independently reviewed according to VMP. | Assurance. |
| TST-FR-012 | 82 | Approval signature | Validation approval uses controlled signature when relied upon electronically. | Controlled evidence. |
| TST-FR-013 | 82 | Failure retention | Failure remains; later pass is separate execution. | History. |
| TST-FR-014 | 82 | Blocked/skipped | Require reason and release impact. | No false coverage. |
| TST-FR-015 | 82 | Evidence hash | Logs/screenshots/files stored via Evidence Store with hash. | Integrity. |
| TST-FR-016 | 82 | Evidence efficiency | Screenshots supplement stronger machine evidence rather than replace it. | Efficient validation. |
| TST-FR-017 | 82 | Independence | Tester/reviewer independence risk-based; developer evidence may count when justified. | Balanced. |
| TST-FR-018 | 82 | Flaky tests | Flaky automated tests tracked and cannot be sole critical evidence. | Evidence quality. |
| TST-FR-019 | 82 | Regression | Risk-based regression suite derived from change impact. | Lifecycle. |
| TST-FR-020 | 82 | Negative tests | Higher-risk functions include invalid/unauthorized/failure-state tests. | Robustness. |
| TST-FR-021 | 82 | Concurrency | Critical idempotency/version/locking functions include race/retry tests. | Distributed correctness. |
| TST-FR-022 | 82 | Recovery | Critical flows include restart/dependency outage/recovery evidence. | Reliability. |
| TST-FR-023 | 82 | Protocol export | Human-readable protocol/result generated from authoritative records. | Inspection. |
| TST-FR-024 | 82 | No result editing | Executed result corrected by amendment/new execution, not in-place edit. | Integrity. |
| IQ-FR-001 | 83 | Installation scope | Identify installed components, versions, environment topology and responsibilities. | Known installation. |
| IQ-FR-002 | 83 | Prerequisites | Verify OS/K8s/runtime/network/DNS/NTP/storage/DB/object/PKI/backups. | Ready environment. |
| IQ-FR-003 | 83 | Artifact identity | Verify deployed image/package digest/signature matches approved release. | Correct software. |
| IQ-FR-004 | 83 | SBOM/provenance | Reference approved SBOM/build provenance. | Supply-chain. |
| IQ-FR-005 | 83 | Configuration baseline | Capture environment/config/feature flags without secret values. | Reproducibility. |
| IQ-FR-006 | 83 | Secret/certs | Verify required secret references/cert validity/scope. | Security. |
| IQ-FR-007 | 83 | DB/schema | Verify PostgreSQL/MariaDB versions/migrations/schemas. | Persistence. |
| IQ-FR-008 | 83 | Object store | Verify encryption/immutability/access/evidence operations. | Evidence. |
| IQ-FR-009 | 83 | NATS/Temporal | Verify version/config/auth/storage/namespace. | Platform. |
| IQ-FR-010 | 83 | Frappe site | Verify Frappe app/site/migrations. | UI. |
| IQ-FR-011 | 83 | Network controls | Verify required and forbidden network paths. | Security. |
| IQ-FR-012 | 83 | Time sync | Verify UTC/NTP within approved threshold. | Chronology. |
| IQ-FR-013 | 83 | Backup config | Verify backup/PITR/key/monitoring configuration exists. | Recovery. |
| IQ-FR-014 | 83 | Observability | Verify critical metrics/logs/alerts registered. | Operations. |
| IQ-FR-015 | 83 | Host inventory | Capture nodes/specs/ownership. | Trace. |
| IQ-FR-016 | 83 | External endpoints | Verify IdP/ERP/LIMS/Edge endpoint/trust configs in scope. | Integration. |
| IQ-FR-017 | 83 | Environment segregation | Verify validation/prod data/secrets/endpoints not mixed. | SDLC. |
| IQ-FR-018 | 83 | Exceptions | Mismatches become validation deviations before IQ completion. | No silent variance. |
| IQ-FR-019 | 83 | Delta IQ | Upgrade/rebuild supports risk-based delta/full IQ. | Lifecycle. |
| IQ-FR-020 | 83 | Automated IQ | Controlled install/preflight automation may generate primary evidence. | Efficiency. |
| IQ-FR-021 | 83 | Approval | IQ requires reviewer approval and deviation disposition. | Gate. |
| OQ-FR-001 | 84 | Functional scope | Verify system functions/controls against approved requirements/risk in IQ environment. | Functional assurance. |
| OQ-FR-002 | 84 | Core GxP controls | Mutation, authorization, signature, audit, Vault, rules and release explicitly tested. | Core GxP. |
| OQ-FR-003 | 84 | Boundary conditions | Test invalid states, limits, stale versions, missing inputs and unauthorized actions. | Robustness. |
| OQ-FR-004 | 84 | State machines | Verify allowed/forbidden transitions. | Operational checks. |
| OQ-FR-005 | 84 | Calculations | Verify decimal/UOM/rounding/rule vectors. | Accuracy. |
| OQ-FR-006 | 84 | Batch/QMS/material/QC | Representative regulated module flows covered by risk. | Business controls. |
| OQ-FR-007 | 84 | Equipment/sterile | Representative equipment/cleaning/EM/sterile controls for DDCP profile. | Production. |
| OQ-FR-008 | 84 | Error handling | Verify stable errors/fail-closed behavior. | Safety. |
| OQ-FR-009 | 84 | Concurrency | Verify optimistic lock/idempotency/duplicate requests. | Distributed correctness. |
| OQ-FR-010 | 84 | Restart/recovery | Test worker/app restart during critical flows. | Reliability. |
| OQ-FR-011 | 84 | Roles/SoD | Representative positive/negative authority matrix. | Authorization. |
| OQ-FR-012 | 84 | Configuration | Test exact released configuration/rules/templates. | Configured state. |
| OQ-FR-013 | 84 | Automated reuse | CI integration/API tests may satisfy OQ when environment/config equivalence established. | CSA. |
| OQ-FR-014 | 84 | End-user fit | Operational user fit belongs PQ/UAT rather than forcing all into OQ. | Separation. |
| OQ-FR-015 | 84 | Defect closure | Failures map defect/deviation/retest. | No hidden failure. |
| OQ-FR-016 | 84 | Coverage | Higher-risk requirements receive objective OQ or justified equivalent evidence. | Risk coverage. |
| OQ-FR-017 | 84 | Independent review | Critical evidence reviewed per VMP. | Assurance. |
| OQ-FR-018 | 84 | Approval | OQ approval prerequisite to PQ/go-live as configured. | Gate. |
| INFQ-FR-001 | 86 | Qualified baseline | Define qualified cloud/on-prem services, versions and config ranges. | Infrastructure control. |
| INFQ-FR-002 | 86 | Shared responsibility | Document provider/product/customer controls/evidence. | Cloud assurance. |
| INFQ-FR-003 | 86 | Supplier evidence | Vendor certifications/docs supplement actual configuration verification. | Balanced assurance. |
| INFQ-FR-004 | 86 | Kubernetes | Verify cluster/version/network/storage/security/time/admission config. | Runtime. |
| INFQ-FR-005 | 86 | Databases | Verify Postgres/MariaDB version/config/HA/backup/access/monitoring. | Persistence. |
| INFQ-FR-006 | 86 | Object store | Verify encryption/immutability/versioning/access/lifecycle/hash retrieval. | Evidence. |
| INFQ-FR-007 | 86 | NATS | Verify streams/replicas/storage/auth/TLS/monitoring. | Messaging. |
| INFQ-FR-008 | 86 | Temporal | Verify namespace/auth/persistence/worker connectivity/backup. | Orchestration. |
| INFQ-FR-009 | 86 | Secrets/KMS | Verify retrieval/rotation/cert renewal/key recovery. | Security. |
| INFQ-FR-010 | 86 | Network | Verify required/forbidden flows and Edge boundary. | Isolation. |
| INFQ-FR-011 | 86 | Clock | Verify NTP/UTC and alarms. | Chronology. |
| INFQ-FR-012 | 86 | Monitoring | Verify critical metrics/log/alerts. | Operations. |
| INFQ-FR-013 | 86 | Backup | Link actual restore evidence from Doc91. | Recovery. |
| INFQ-FR-014 | 86 | Capacity | Resources meet intended sizing. | Performance. |
| INFQ-FR-015 | 86 | HA | Failover behavior tested/justified by deployment tier. | Availability. |
| INFQ-FR-016 | 86 | On-prem | Customer hardware/storage/network prerequisites verified. | Deployment. |
| INFQ-FR-017 | 86 | Patching | Patch/change qualification model defined. | Lifecycle. |
| INFQ-FR-018 | 86 | Drift | Production drift monitored against qualified baseline. | Validated state. |
| INFQ-FR-019 | 86 | Environment equivalence | Validation→production intentional differences documented. | Confidence. |
| INFQ-FR-020 | 86 | Requalification | Material infrastructure change triggers scoped requalification. | Lifecycle. |
| P11-FR-001 | 88 | Part 11 scope | Identify records/signatures relied upon electronically under predicate rules. | Scope. |
| P11-FR-002 | 88 | Accuracy/reliability | Verify intended functions create accurate/reliable records. | 11.10(a). |
| P11-FR-003 | 88 | Altered record discernment | Verify invalid/altered record detection. | 11.10(a). |
| P11-FR-004 | 88 | Human-readable copies | Verify accurate complete human-readable export. | 11.10(b). |
| P11-FR-005 | 88 | Electronic copies | Verify electronic export with required metadata. | 11.10(b). |
| P11-FR-006 | 88 | Retention/retrieval | Verify ready retrieval through retention/archive. | 11.10(c). |
| P11-FR-007 | 88 | Access | Verify authorized-only record/system access. | 11.10(d). |
| P11-FR-008 | 88 | Audit trail | Verify secure timestamped audit, prior values, retention/review. | 11.10(e). |
| P11-FR-009 | 88 | Operational checks | Verify sequencing prevents invalid workflow order. | 11.10(f). |
| P11-FR-010 | 88 | Authority checks | Verify role/qualification/SoD/signature authority. | 11.10(g). |
| P11-FR-011 | 88 | Device/source checks | Verify scanner/balance/Edge/device validity as applicable. | 11.10(h). |
| P11-FR-012 | 88 | Training | Verify relevant training/qualification controls. | 11.10(i). |
| P11-FR-013 | 88 | Signature accountability policy | Customer responsibility/evidence documented. | 11.10(j). |
| P11-FR-014 | 88 | Documentation controls | Verify controlled system documentation/access/change history. | 11.10(k). |
| P11-FR-015 | 88 | Signature manifestation | Verify signer printed name, time and meaning in display/export. | 11.50. |
| P11-FR-016 | 88 | Signature linking | Verify signature cannot be transferred to falsify another record by ordinary means. | 11.70. |
| P11-FR-017 | 88 | Unique identity | Verify unique signer mapping and identity verification responsibility. | 11.100. |
| P11-FR-018 | 88 | Signature components | Verify configured signing ceremony satisfies applicable controls. | 11.200. |
| P11-FR-019 | 88 | Version binding | Signature binds exact record/version/hash/action/meaning. | Platform control. |
| P11-FR-020 | 88 | Fresh step-up | V1 validates fresh step-up for every regulated signature per Document 04. | Stronger baseline. |
| P11-FR-021 | 88 | Failed signing | Expired challenge/stale version/replay/wrong signer fails. | Security. |
| P11-FR-022 | 88 | Correction | Signed/released correction creates new version, not edit. | Integrity. |
| P11-FR-023 | 88 | Clock | Signature/audit UTC consistency verified. | Chronology. |
| P11-FR-024 | 88 | Open systems | Additional controls assessed where deployment/use is open-system context. | Scope. |
| P11-FR-025 | 88 | Customer certification | §11.100 certification/support remains customer responsibility. | Responsibility. |
| P11-FR-026 | 88 | Control matrix | Every applicable control maps test/evidence/config/procedure. | Inspection. |
| DIV-FR-001 | 89 | Audit append-only | Normal roles cannot update/delete audit events. | Tamper resistance. |
| DIV-FR-002 | 89 | Old/new values | Changed regulated fields preserve prior/new values and reason/signature links. | History. |
| DIV-FR-003 | 89 | Hash chain | Verify per-record hash-chain continuity/tamper detection. | Integrity. |
| DIV-FR-004 | 89 | Checkpoints | Verify signed integrity checkpoints and verification. | Tamper evidence. |
| DIV-FR-005 | 89 | Tamper simulation | Controlled isolated DBA tamper/removal/reorder test is detected. | Independent detection. |
| DIV-FR-006 | 89 | Vault immutability | Released versions immutable/retrievable. | History. |
| DIV-FR-007 | 89 | Canonicalization | Same payload produces stable digest under approved vectors. | Reproducibility. |
| DIV-FR-008 | 89 | Manifest | Record version manifest hashes exact evidence refs. | Completeness. |
| DIV-FR-009 | 89 | Correction/supersession | New version/relationship preserves original. | Data integrity. |
| DIV-FR-010 | 89 | Void | Void never erases content/history. | History. |
| DIV-FR-011 | 89 | Restore integrity | Restore preserves audit/hash/version/evidence relationships. | DR. |
| DIV-FR-012 | 89 | Migration provenance | Migrated data distinguished with source/transformation metadata. | Trace. |
| DIV-FR-013 | 89 | Failed result retention | Failed/OOS/rejected/test history retained after success/retest. | Completeness. |
| DIV-FR-014 | 89 | Timestamp provenance | Source vs receive/server time preserved. | Chronology. |
| DIV-FR-015 | 89 | Attribution | Human/service/device/source attribution verified. | Attributable. |
| DIV-FR-016 | 89 | Offline chronology | Edge/offline buffering preserves contemporaneous source chronology. | Contemporaneous. |
| DIV-FR-017 | 89 | Original evidence | Raw instrument/machine evidence linkage/hash retained as required. | Original. |
| DIV-FR-018 | 89 | Accuracy | Calculation/UOM/transformation versions and vectors verified. | Accurate. |
| DIV-FR-019 | 89 | Complete genealogy | Representative batch genealogy complete. | Complete. |
| DIV-FR-020 | 89 | Ordering | Late/duplicate/out-of-order data cannot corrupt official history. | Consistent. |
| DIV-FR-021 | 89 | Enduring | Archive/cold retrieval and hash verification. | Enduring. |
| DIV-FR-022 | 89 | Available | Retained records retrievable for inspection within accepted time. | Available. |
| DIV-FR-023 | 89 | Audit review | Review annotations do not mutate original events. | Review integrity. |
| DIV-FR-024 | 89 | Retention/hold | Legal hold/retention blocks premature destruction. | Governance. |
| IFV-FR-001 | 90 | Interface inventory | Every GxP ERP/LIMS/Edge/device/API/file interface identified by owner/version/use. | Complete scope. |
| IFV-FR-002 | 90 | Contract version | Validate exact schema/API/event/mapping/profile version. | Contract assurance. |
| IFV-FR-003 | 90 | Authentication | Validate mTLS/OAuth/token/cert and unauthorized rejection. | Security. |
| IFV-FR-004 | 90 | Data mapping | Source→canonical→GxP field/UOM/status test vectors. | Accuracy. |
| IFV-FR-005 | 90 | Source identity | Verify system/device/site/tenant attribution. | Trace. |
| IFV-FR-006 | 90 | Timestamp | Verify source/receive time and clock-quality handling. | Chronology. |
| IFV-FR-007 | 90 | Quality status | Bad/uncertain/stale/comm-error propagation. | No false good. |
| IFV-FR-008 | 90 | Idempotency | Duplicate/replay does not duplicate effect. | Reliability. |
| IFV-FR-009 | 90 | Ordering | Out-of-order/stale version handling. | Consistency. |
| IFV-FR-010 | 90 | Store-forward | Outage/recovery preserves events with no loss/duplicate GxP effect. | Edge resilience. |
| IFV-FR-011 | 90 | Buffer capacity | Expected offline horizon/disk threshold behavior. | Operational. |
| IFV-FR-012 | 90 | ERP uncertain commit | Timeout after external commit reconciles before retry. | No duplicate posting. |
| IFV-FR-013 | 90 | LIMS result | Wrong sample/method/spec/version rejected. | Lab integrity. |
| IFV-FR-014 | 90 | Barcode/balance | Wrong identity/unstable/calibration/manual fallback behavior. | Peripheral. |
| IFV-FR-015 | 90 | PLC/SCADA | Wrong mapping/program/context/quality blocked. | Machine evidence. |
| IFV-FR-016 | 90 | Machine command | If enabled test allowlist/signature/interlock/readback; otherwise verify disabled. | Safety. |
| IFV-FR-017 | 90 | File transfer | Checksum/schema/duplicate/ack/rejection tested. | Batch integration. |
| IFV-FR-018 | 90 | Schema evolution | Compatible/breaking contract changes tested. | Lifecycle. |
| IFV-FR-019 | 90 | Security abuse | Replay/spoof invalid cert/webhook tests. | Security. |
| IFV-FR-020 | 90 | Recovery | Adapter/gateway restart resumes correctly. | Reliability. |
| IFV-FR-021 | 90 | Reconciliation | External/internal transaction/master-data reconciliation. | Completeness. |
| IFV-FR-022 | 90 | Failure visibility | Failure appears in operations/QA review as intended. | No silent failure. |
| IFV-FR-023 | 90 | Simulator | Controlled simulators reproduce failures and edge cases. | Repeatability. |
| IFV-FR-024 | 90 | Customer delta | Customer interface configuration receives delta qualification. | Deployment. |
| DRV-FR-001 | 91 | Scope | Map all persistent/critical components to RPO/RTO profile. | Complete. |
| DRV-FR-002 | 91 | Backup evidence | Verify backup/manifest/WAL/object/config evidence. | Protection. |
| DRV-FR-003 | 91 | Actual restore | Restore real data into isolated environment. | Objective recovery. |
| DRV-FR-004 | 91 | PITR | Recover PostgreSQL to selected timestamp/LSN. | PITR. |
| DRV-FR-005 | 91 | RPO | Measure latest recovered data vs expected source marker. | Objective. |
| DRV-FR-006 | 91 | RTO | Measure recovery declaration/start to validated service-ready. | Objective. |
| DRV-FR-007 | 91 | Audit continuity | Verify audit/version/outbox relationships. | GxP. |
| DRV-FR-008 | 91 | Evidence | Verify metadata→object hash/availability. | Evidence. |
| DRV-FR-009 | 91 | MariaDB | Restore/rebuild/reconcile Frappe projections. | UI recovery. |
| DRV-FR-010 | 91 | NATS | Recover/config and verify outbox catch-up. | Messaging. |
| DRV-FR-011 | 91 | Temporal | Resume orchestration without false domain state. | Orchestration. |
| DRV-FR-012 | 91 | Secrets/keys | Recovered data remains decryptable; missing/rotated key behavior tested. | Crypto. |
| DRV-FR-013 | 91 | Failover | Standby promotion/split-brain prevention where HA. | Availability. |
| DRV-FR-014 | 91 | Failback | Controlled rejoin/failback where applicable. | Operations. |
| DRV-FR-015 | 91 | Regional/site DR | Secondary region/site activation where required. | Enterprise. |
| DRV-FR-016 | 91 | Network/DNS/cert | Recovery endpoints/routing/trust validated. | Accessibility. |
| DRV-FR-017 | 91 | Security | Recovery preserves auth/network/least privilege. | Secure recovery. |
| DRV-FR-018 | 91 | GxP smoke | Representative create/read/sign/audit/evidence operation after recovery. | Business verification. |
| DRV-FR-019 | 91 | Data-loss detection | Missing interval detection/assessment works if RPO exceeded. | Transparency. |
| DRV-FR-020 | 91 | Runbook | Current operators can execute runbook; deviations update procedure. | Human readiness. |
| DRV-FR-021 | 91 | Cadence | Restore/DR qualification repeated per risk/profile. | Ongoing. |
| DRV-FR-022 | 91 | Approval | Qualification approved with achieved RPO/RTO. | Gate. |
| SECQ-FR-001 | 92 | Scope | Threat/control matrix from Docs61–68 forms baseline. | Risk driven. |
| SECQ-FR-002 | 92 | Authentication | SSO/MFA/session/token negative tests. | Identity. |
| SECQ-FR-003 | 92 | Authorization | BOLA/BFLA/property/cross-tenant/site tests. | Access. |
| SECQ-FR-004 | 92 | Signature separation | Verify auth/MFA cannot bypass regulated signature. | GxP. |
| SECQ-FR-005 | 92 | Privileged access | JIT/support/break-glass/no QA authority tests. | PAM. |
| SECQ-FR-006 | 92 | Secrets | No secret in repo/image/log; rotation/revocation. | Credential security. |
| SECQ-FR-007 | 92 | PKI | Invalid/expired/revoked cert behavior. | Trust. |
| SECQ-FR-008 | 92 | API security | Injection/XSS/CSRF/SSRF/file/rate/unsafe third-party input. | OWASP. |
| SECQ-FR-009 | 92 | Network | Forbidden paths/admin/OT boundaries. | Zero trust. |
| SECQ-FR-010 | 92 | Encryption | TLS/at-rest/field encryption config tests. | Confidentiality. |
| SECQ-FR-011 | 92 | Logging | Critical security events reach central detection; redaction verified. | Detection. |
| SECQ-FR-012 | 92 | Detection rules | Synthetic events trigger alert/source-silence detection. | Monitoring. |
| SECQ-FR-013 | 92 | Containment | Session/cert/secret/connector isolation tested. | Response. |
| SECQ-FR-014 | 92 | Supply chain | SBOM/signature/provenance/untrusted artifact controls. | SDLC. |
| SECQ-FR-015 | 92 | Scans | SAST/SCA/IaC/container evidence and exceptions reviewed. | Secure release. |
| SECQ-FR-016 | 92 | Pen test | Independent/manual pen test before regulated pilot and per policy/change. | Assurance. |
| SECQ-FR-017 | 92 | Pen scope | Frappe/UI/GxP APIs/admin/integrations/tenant boundaries included; OT testing controlled. | Complete. |
| SECQ-FR-018 | 92 | Safe testing | Destructive tests in validation env unless approved production rules. | Safety. |
| SECQ-FR-019 | 92 | Finding lifecycle | Finding links vulnerability/deviation/change/retest. | Closure. |
| SECQ-FR-020 | 92 | Release block | Unresolved critical/high blocks release unless formal allowed exception. | Gate. |
| SECQ-FR-021 | 92 | Regression | Fixed vulnerability gets regression test where feasible. | Recurrence. |
| SECQ-FR-022 | 92 | Customer package | Security qualification summary without exposing sensitive exploit detail. | Commercial. |
| SECQ-FR-023 | 92 | Separate evidence | Security qualification does not replace functional/Part11 validation. | Balanced. |
| SECQ-FR-024 | 92 | Approval | Security + QA/Validation review GxP-impact findings. | Governance. |
| PERFQ-FR-001 | 93 | Load model | Use target users/plants/batches/steps/audit/device event assumptions. | Representative scale. |
| PERFQ-FR-002 | 93 | Critical latency | Measure mutation/read/sign/review/release p50/p95/p99. | Responsiveness. |
| PERFQ-FR-003 | 93 | Throughput | Measure sustainable mutation/audit/outbox/event rates. | Capacity. |
| PERFQ-FR-004 | 93 | Concurrent users | Test target role mix and concurrency. | Enterprise. |
| PERFQ-FR-005 | 93 | Batch scale | Test thousands of steps/batch and simultaneous batches. | eBMR. |
| PERFQ-FR-006 | 93 | Audit scale | Test millions audit/day equivalent/bursts. | Data scale. |
| PERFQ-FR-007 | 93 | Event lag | Outbox/NATS consumer lag under burst/recovery. | Async. |
| PERFQ-FR-008 | 93 | Edge catch-up | Configured long offline backlog catch-up without core overload. | Plant. |
| PERFQ-FR-009 | 93 | Object evidence | Large upload/download/manifest performance. | Storage. |
| PERFQ-FR-010 | 93 | Search/report isolation | Heavy reads do not starve critical execution. | Read layer. |
| PERFQ-FR-011 | 93 | Signature latency | Fresh step-up/signature transaction measured. | Critical UX. |
| PERFQ-FR-012 | 93 | DB saturation | Monitor connection/WAL/locks/IO/bloat under load. | Bottleneck. |
| PERFQ-FR-013 | 93 | Autoscaling | Stateless scaling and DB-pool limits verified. | Elasticity. |
| PERFQ-FR-014 | 93 | Backpressure | Overload is bounded, not data loss/crash. | Resilience. |
| PERFQ-FR-015 | 93 | Soak | Long duration catches leaks/growth/partition issues. | Stability. |
| PERFQ-FR-016 | 93 | Failover under load | Selected DB/broker/worker failure tests. | Resilience. |
| PERFQ-FR-017 | 93 | Graceful degradation | Dependency outages follow capability matrix. | Availability. |
| PERFQ-FR-018 | 93 | Headroom | Identify validated capacity/headroom/scaling trigger. | Sizing. |
| PERFQ-FR-019 | 93 | On-prem sizing | Translate results to hardware profile. | Commercial deployment. |
| PERFQ-FR-020 | 93 | Regression | Baseline performance versioned by release. | Quality. |
| PERFQ-FR-021 | 93 | NFR trace | Thresholds link NFR/SLO requirement IDs. | Trace. |
| PERFQ-FR-022 | 93 | Production-equivalent durability | Use real fsync/WAL/audit/security settings. | Validity. |
| PERFQ-FR-023 | 93 | Data volume realism | Use representative table/index cardinality. | Realism. |
| PERFQ-FR-024 | 93 | Approval | Approved envelope/limitations retained. | Transparency. |
| VEX-FR-001 | 94 | Event types | Distinguish defect, test failure, protocol/environment deviation, evidence issue, requirement gap. | Clear workflow. |
| VEX-FR-002 | 94 | Automatic creation | Critical failed test can create validation exception automatically. | No loss. |
| VEX-FR-003 | 94 | Original evidence | Original failure/evidence immutable. | History. |
| VEX-FR-004 | 94 | Triage | Severity and GxP/release impact assessed. | Risk. |
| VEX-FR-005 | 94 | Engineering link | Issue/PR/commit linked to validation failure. | Trace. |
| VEX-FR-006 | 94 | QMS link | Validated-state impact can link/create Quality deviation. | QMS. |
| VEX-FR-007 | 94 | Protocol deviation | Departure from approved procedure records reason/impact/approval. | Controlled. |
| VEX-FR-008 | 94 | Environment deviation | Wrong environment/config may invalidate result. | Evidence validity. |
| VEX-FR-009 | 94 | Evidence issue | Missing/corrupt evidence cannot remain unexplained PASS. | Integrity. |
| VEX-FR-010 | 94 | Root cause | Critical/recurrent failure gets appropriate cause analysis. | Quality. |
| VEX-FR-011 | 94 | Fix link | Correction/change/version linked. | Remediation. |
| VEX-FR-012 | 94 | Retest scope | Direct/regression retest based on cause/change/risk. | Adequate verification. |
| VEX-FR-013 | 94 | Retest identity | New execution ID; prior failure remains. | History. |
| VEX-FR-014 | 94 | Disposition | OPEN/FIX/RETEST/ACCEPTED_WITH_RATIONALE/DEFERRED_BLOCKING/CLOSED. | Explicit. |
| VEX-FR-015 | 94 | Risk acceptance | Acceptance without fix needs residual-risk approval and cannot violate binding requirement. | Governance. |
| VEX-FR-016 | 94 | Release blocker | Critical/high unresolved/invalid evidence blocks release by policy. | Gate. |
| VEX-FR-017 | 94 | Known limitation | Approved limitation appears in VSR/release/customer package where material. | Transparency. |
| VEX-FR-018 | 94 | Trend | Track recurring failures/flaky tests/root causes. | Improvement. |
| VEX-FR-019 | 94 | Closure | Fix/retest/impact/approval needed. | Complete. |
| VEX-FR-020 | 94 | Reopen | New evidence can reopen with history. | Lifecycle. |
| VEX-FR-021 | 94 | Audit | Triage/disposition/closure/reopen audited/signed as policy. | Accountability. |
| VEX-FR-022 | 94 | VSR link | Open/accepted deviations automatically included in VSR. | Inspection. |
| VSM-FR-001 | 96 | Validated baseline | Inventory software/services/config/rules/interfaces/infrastructure/procedures in validated state. | Known state. |
| VSM-FR-002 | 96 | Change trigger | Every controlled change evaluates validation impact before production. | Lifecycle. |
| VSM-FR-003 | 96 | Impact scope | Identify affected requirements/risk/functions/tests/interfaces/data/security/performance/SOP/training. | Complete impact. |
| VSM-FR-004 | 96 | Revalidation level | NONE_WITH_RATIONALE/DOC_REVIEW/TARGETED_TEST/PARTIAL/FULL_REQUALIFICATION. | Proportionate. |
| VSM-FR-005 | 96 | Emergency change | Expedited route allowed with risk/evidence and retrospective completion. | Continuity. |
| VSM-FR-006 | 96 | Patches | OS/runtime/library/security patches use risk-based impact, not blanket full regression. | CSA. |
| VSM-FR-007 | 96 | GxP config | Rule/workflow/form/signature/role/interface config change assessed. | Configured state. |
| VSM-FR-008 | 96 | Infrastructure change | DB/cloud/K8s/storage/network changes map requalification scope. | Environment. |
| VSM-FR-009 | 96 | Interface change | ERP/LIMS/device schema/version change maps requalification. | Integration. |
| VSM-FR-010 | 96 | Data change | Migration/bulk repair/master conversion receives validation scope. | Integrity. |
| VSM-FR-011 | 96 | Periodic schedule | Validated deployments reviewed at risk/contract interval. | Ongoing assurance. |
| VSM-FR-012 | 96 | Review inputs | Changes, incidents, CAPA, defects, vulnerabilities, DR, performance, access, vendor/EOL and audit trends. | Holistic. |
| VSM-FR-013 | 96 | Version support | Unsupported/EOL dependencies flagged/remediated. | Lifecycle. |
| VSM-FR-014 | 96 | Drift review | Production config/infrastructure compared to validated baseline. | State control. |
| VSM-FR-015 | 96 | Training/SOP | Procedure/training currentness/effectiveness reviewed after process change. | Human system. |
| VSM-FR-016 | 96 | Part 11 review | Identity/signature/audit/archive control changes/incidents assessed. | Compliance. |
| VSM-FR-017 | 96 | DR review | Latest restore/DR evidence and RPO/RTO issues reviewed. | Recovery. |
| VSM-FR-018 | 96 | Security review | Pen/scans/open findings/incidents/exceptions reviewed. | Cybersecurity. |
| VSM-FR-019 | 96 | Capacity review | Growth/headroom/SLO issues reviewed. | Reliability. |
| VSM-FR-020 | 96 | Customer review | Enabled modules/config/interfaces/site deviations included. | Deployment. |
| VSM-FR-021 | 96 | Decision | VALIDATED_CONFIRMED/ACTION_REQUIRED/REVALIDATION_REQUIRED/SUSPENDED. | Explicit. |
| VSM-FR-022 | 96 | Actions | Findings create Change/CAPA/validation action with owner/due date. | Improvement. |
| VSM-FR-023 | 96 | Suspension | Critical integrity/security/validation issue can suspend affected use. | Risk control. |
| VSM-FR-024 | 96 | Release continuity | Each release references prior baseline/change impact/delta or VSR. | Continuity. |
| VSM-FR-025 | 96 | Evidence | Periodic review/revalidation retained with system history. | Inspection. |
| VSM-FR-026 | 96 | Decommission | Retirement includes record archive/retrieval/access/integration shutdown. | Lifecycle end. |
| VSM-FR-027 | 96 | Supplier change | Major cloud/identity/vendor dependency change triggers impact. | External dependency. |
| VSM-FR-028 | 96 | No perpetual validation | Initial validation never means permanent assurance without controlled lifecycle. | Principle. |
