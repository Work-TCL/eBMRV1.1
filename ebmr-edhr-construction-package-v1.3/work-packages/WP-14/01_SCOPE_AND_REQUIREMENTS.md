# WP-14 — Scope & Requirements

**In scope:** Documents 85, 87, 95

## Document 85 — Performance Qualification (PQ), UAT & Business Process Verification (SPEC-VAL-007)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PQ-FR-001..020 (20)

## Document 87 — Data Migration, Conversion, Cutover & Reconciliation Validation (SPEC-VAL-009)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: MIGV-FR-001..022 (22)

## Document 95 — Validation Summary Report, Release-to-Production & Go-Live Authorization (SPEC-VAL-017)

- Code location: `validation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: VSR-FR-001..024 (24)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| PQ-FR-001 | 85 | Business-process suitability | PQ verifies real intended workflows with trained representative users/procedures. | Fit for use. |
| PQ-FR-002 | 85 | Customer/site scope | PQ deployment/site/process-specific where configuration differs. | Configured product. |
| PQ-FR-003 | 85 | Representative scenarios | Use end-to-end product/process scenarios. | Operational relevance. |
| PQ-FR-004 | 85 | Representative roles | Production/QA/QC/warehouse/engineering roles participate as applicable. | User suitability. |
| PQ-FR-005 | 85 | Training prerequisite | PQ participants trained/qualified. | Credible execution. |
| PQ-FR-006 | 85 | Product profile | Include PFS/injector/inhalation/coated profile only when applicable. | Risk based. |
| PQ-FR-007 | 85 | Material flow | Receipt→quarantine→release→dispense→consume/return/reconcile. | End-to-end. |
| PQ-FR-008 | 85 | QC flow | Sample→test→review→OOS exception/disposition. | Lab. |
| PQ-FR-009 | 85 | Deviation flow | Batch exception→deviation→impact→resolution/release. | QMS. |
| PQ-FR-010 | 85 | Signature flow | Configured IdP/signature/approval/QA release executed by real role. | Actual use. |
| PQ-FR-011 | 85 | Edge/device flow | Representative scanner/balance/machine input if site uses it. | Factory. |
| PQ-FR-012 | 85 | ERP/LIMS flow | Customer interfaces included when go-live depends on them. | Integration. |
| PQ-FR-013 | 85 | Shift/handoff | Long-running handoff/resume represented when applicable. | Operations. |
| PQ-FR-014 | 85 | Procedure compatibility | SOP/work instruction must match actual UI/process. | Human system. |
| PQ-FR-015 | 85 | Usability observation | Capture confusion/error-prone workflow as validation observation. | Practical fit. |
| PQ-FR-016 | 85 | Business exceptions | Include realistic exception/recovery paths. | Operational confidence. |
| PQ-FR-017 | 85 | UAT equivalence | Controlled customer UAT may satisfy PQ evidence if VMP criteria met. | Efficiency. |
| PQ-FR-018 | 85 | Go-live blockers | Critical process/procedure/training failure blocks PQ. | Safe deployment. |
| PQ-FR-019 | 85 | Customer acceptance | Process Owner/System Owner/QA approvals according to matrix. | Ownership. |
| PQ-FR-020 | 85 | Template reuse | Vendor scenarios reusable as template, not customer acceptance substitute. | Scalable service. |
| MIGV-FR-001 | 87 | Migration plan | Define source, scope, cutoff, transformations, owners and acceptance. | Controlled conversion. |
| MIGV-FR-002 | 87 | Source snapshot | Identify/freeze exact source export/cutoff/hash. | Reproducibility. |
| MIGV-FR-003 | 87 | Profiling | Assess completeness, duplicates, orphans, invalid values. | Risk awareness. |
| MIGV-FR-004 | 87 | Mapping | Source→target entity/field/UOM/status mapping versioned/approved. | Clarity. |
| MIGV-FR-005 | 87 | Transformation code | Scripts/version reviewed and testable. | Controlled logic. |
| MIGV-FR-006 | 87 | Regulated history | Preserve needed history/provenance or controlled legacy archive. | Continuity. |
| MIGV-FR-007 | 87 | Identity mapping | Legacy ID→new ID mapping retained. | Trace. |
| MIGV-FR-008 | 87 | Reference integrity | Relationships reconciled after import. | Integrity. |
| MIGV-FR-009 | 87 | Counts/totals | Counts, hashes, quantities/control totals by data class. | Completeness. |
| MIGV-FR-010 | 87 | Sampling/full compare | Use full automated compare for critical fields where feasible, otherwise risk-based sampling. | Evidence. |
| MIGV-FR-011 | 87 | Attachments | Evidence object counts/hashes/links reconciled. | Evidence. |
| MIGV-FR-012 | 87 | Legacy signatures | Preserve/migrate signature evidence without recreating historic signature as new signing. | Integrity. |
| MIGV-FR-013 | 87 | Legacy audit | Import provenance-marked audit/history or retain accessible legacy archive. | History. |
| MIGV-FR-014 | 87 | Timezones | Source timezone/precision semantics explicitly handled. | Chronology. |
| MIGV-FR-015 | 87 | Decimal/UOM | Conversion precision and UOM rules tested. | Accuracy. |
| MIGV-FR-016 | 87 | Dry runs | Material migration uses rehearsal(s) based on risk/scale. | Cutover confidence. |
| MIGV-FR-017 | 87 | Cutover delta | Final delta/change-freeze strategy reconciles late changes. | Completeness. |
| MIGV-FR-018 | 87 | Errors | Rejected records retained with reason/disposition. | No silent loss. |
| MIGV-FR-019 | 87 | Rollback | Fallback strategy avoids losing post-cutover transactions. | Operational safety. |
| MIGV-FR-020 | 87 | Approval | Final migration accepted only after reconciliation/deviation disposition. | Gate. |
| MIGV-FR-021 | 87 | Legacy access | Post-cutover legacy read-only retrieval strategy documented. | Inspection. |
| MIGV-FR-022 | 87 | Evidence retention | Scripts/config/logs/source hashes/reconciliations retained. | Audit. |
| VSR-FR-001 | 95 | VSR generation | Generate VSR from authoritative validation artifacts. | Final evidence. |
| VSR-FR-002 | 95 | Scope | State system/release/customer/environment/config/intended use. | Boundary. |
| VSR-FR-003 | 95 | Baselines | List requirement/risk/design/test/config/IQ/OQ/PQ/security/performance/DR baselines. | Reproducible. |
| VSR-FR-004 | 95 | Execution summary | Summarize evidence by method/risk/module/status. | Coverage. |
| VSR-FR-005 | 95 | Traceability | Include critical gap/orphan status. | Completeness. |
| VSR-FR-006 | 95 | Deviations | Include open/closed/accepted exceptions and release impact. | Transparency. |
| VSR-FR-007 | 95 | Security | Include qualification/findings/exceptions. | Risk. |
| VSR-FR-008 | 95 | Performance | Include operating envelope/limitations. | Operations. |
| VSR-FR-009 | 95 | DR | Include restore/DR qualification and achieved objectives. | Recovery. |
| VSR-FR-010 | 95 | Migration | Include migration validation if applicable. | Cutover. |
| VSR-FR-011 | 95 | Part 11 | Include Part 11 package/customer responsibilities. | Compliance. |
| VSR-FR-012 | 95 | Customer responsibilities | Outstanding SOP/training/certification/config duties explicit. | Shared validation. |
| VSR-FR-013 | 95 | Known limitations | Approved limitations/workarounds/monitoring listed. | Transparency. |
| VSR-FR-014 | 95 | Recommendation/approval | Validation recommendation separate from QA/System Owner authorization. | SoD. |
| VSR-FR-015 | 95 | Go-live prerequisites | Training, prod config, backups, interfaces, support, monitoring/cutover tasks checked. | Readiness. |
| VSR-FR-016 | 95 | Configuration fingerprint | Record approved production configuration hash. | Validated state. |
| VSR-FR-017 | 95 | Release identity | Exact image/code/SBOM/schema/migration/config versions. | Software identity. |
| VSR-FR-018 | 95 | Approval | VSR electronically approved/signed by required roles. | Controlled. |
| VSR-FR-019 | 95 | Decision | APPROVED/CONDITIONAL/REJECTED; condition cannot bypass critical GxP control. | Explicit. |
| VSR-FR-020 | 95 | Evidence manifest | VSR references immutable validation package. | Inspection. |
| VSR-FR-021 | 95 | Customer package | Generate vendor/customer subset based on responsibility/access. | Commercial. |
| VSR-FR-022 | 95 | Pipeline gate | Production promotion checks validated release authorization. | Technical gate. |
| VSR-FR-023 | 95 | Post-go-live | Defined smoke/monitoring verification. | Safe deployment. |
| VSR-FR-024 | 95 | Rollback | Failed post-go-live verification follows controlled rollback/incident/change. | Recovery. |
