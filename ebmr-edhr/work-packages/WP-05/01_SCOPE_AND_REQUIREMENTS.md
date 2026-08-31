# WP-05 — Scope & Requirements

**In scope:** Documents 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37

## Document 26 — Deviation & Investigation Management (SPEC-QMS-001)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DEV-FR-001..024 (24)

## Document 27 — CAPA Management (SPEC-QMS-002)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: CAPA-FR-001..022 (22)

## Document 28 — Nonconformance Management (SPEC-QMS-003)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: NCR-FR-001..018 (18)

## Document 29 — Change Control (SPEC-QMS-004)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: CHG-FR-001..024 (24)

## Document 30 — Document Control (SPEC-QMS-005)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DOC-FR-001..024 (24)

## Document 31 — Training & Personnel Qualification (SPEC-QMS-006)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: TRN-FR-001..024 (24)

## Document 32 — Supplier Quality / SCAR (SPEC-QMS-007)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: SCAR-FR-001..018 (18)

## Document 33 — Risk Management (SPEC-QMS-008)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: RSK-FR-001..018 (18)

## Document 34 — Internal Audit Management (SPEC-QMS-009)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: AUDIT-FR-001..017 (17)

## Document 35 — Complaint Management (SPEC-QMS-010)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: CMP-FR-001..024 (24)

## Document 36 — Recall / Field Action Management (SPEC-QMS-011)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **STANDARD-RISK**
- Requirements: FAR-FR-001..020 (20)

## Document 37 — Quality Metrics, Trending & Effectiveness Checks (SPEC-QMS-012)

- Code location: `services/gxp-api/src/modules/qms`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: MET-FR-001..024 (24)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| DEV-FR-001 | 26 | Deviation initiation | Create planned/unplanned deviation from batch, QC, material, equipment, environment, supplier, document or system source. | Every deviation attributable. |
| DEV-FR-002 | 26 | Automatic source | Rules/Batch/QC/Edge can create deviation candidate with exact source event/version. | No retyping required. |
| DEV-FR-003 | 26 | Triage | Classify planned/unplanned, severity, product impact and investigation priority using released methodology. | Consistent routing. |
| DEV-FR-004 | 26 | Immediate correction | Record immediate correction separately from root-cause/CAPA. | Containment not confused with systemic action. |
| DEV-FR-005 | 26 | Containment | Place batch/material/equipment/area on hold where required. | Risk bounded. |
| DEV-FR-006 | 26 | Investigator | Assign qualified investigator, owner and due date; reassignment audited. | Ownership clear. |
| DEV-FR-007 | 26 | Investigation plan | Define records, interviews, batches/products and technical evidence to review. | Structured investigation. |
| DEV-FR-008 | 26 | Cross-batch investigation | Extend investigation to associated batches/products when relevant. | Supports §211.192. |
| DEV-FR-009 | 26 | Evidence graph | Link batch, audit, QC, equipment, materials, environment, supplier and files. | Complete evidence. |
| DEV-FR-010 | 26 | Root cause | Support configurable root-cause methods and 'no assignable cause' when justified. | No forced fake cause. |
| DEV-FR-011 | 26 | Impact assessment | Assess quality, patient/user, released/distributed product, validation, data integrity and regulatory impact. | Complete impact. |
| DEV-FR-012 | 26 | Disposition | Continue/hold/reject/rework/reprocess/additional test/destroy/field-action assessment according to policy. | Controlled outcome. |
| DEV-FR-013 | 26 | CAPA need | Record CAPA required/not required with rationale. | Systemic action decision. |
| DEV-FR-014 | 26 | Change need | Link Change Control for permanent process/spec/system/document changes. | Controlled change. |
| DEV-FR-015 | 26 | Training need | Create retraining/qualification actions where appropriate. | Training integrated. |
| DEV-FR-016 | 26 | Planned deviation | Pre-approved, bounded by scope/date/batches; cannot become permanent alternative process. | Temporary exception. |
| DEV-FR-017 | 26 | Extension | Due-date extension requires reason, risk review and approval; old due date retained. | No silent aging. |
| DEV-FR-018 | 26 | Closure | Require investigation, impact, disposition and mandatory linked actions before QA closure. | No premature closure. |
| DEV-FR-019 | 26 | QA signature | Final conclusion/disposition/closure signed according to policy. | Independent Quality authority. |
| DEV-FR-020 | 26 | Reopen | New evidence reopens through controlled action preserving prior closure. | History. |
| DEV-FR-021 | 26 | Recurrence | Find similar prior deviations by code/product/process/equipment/root cause. | Trend. |
| DEV-FR-022 | 26 | Release integration | Open/critical deviations create review/release blockers based on rule. | No release bypass. |
| DEV-FR-023 | 26 | Escalation | Critical/overdue deviation notifications/escalation. | Timely handling. |
| DEV-FR-024 | 26 | Export | Written investigation with conclusions/follow-up and evidence exportable. | Inspection-ready. |
| CAPA-FR-001 | 27 | CAPA initiation | Create from deviation/OOS/OOT/NCR/complaint/audit/supplier/risk/trend/security/validation source. | Source explicit. |
| CAPA-FR-002 | 27 | Problem statement | Define verified problem and scope separately from solution. | Correct framing. |
| CAPA-FR-003 | 27 | Priority | Assign risk/priority and target date. | Risk based. |
| CAPA-FR-004 | 27 | Root-cause link | Reference investigation/root cause or proactive prevention rationale. | Evidence based. |
| CAPA-FR-005 | 27 | Corrective action | Define action addressing cause of detected issue. | Corrective. |
| CAPA-FR-006 | 27 | Preventive/systemic action | Support broader preventive/systemic action without forcing artificial categories. | Systemic improvement. |
| CAPA-FR-007 | 27 | Action owner/evidence | Every action has owner, due date, deliverable/evidence and state. | Accountability. |
| CAPA-FR-008 | 27 | Dependencies | Actions link Change, Training, Validation, Supplier, Software Release, Equipment etc. | Cross-module. |
| CAPA-FR-009 | 27 | Implementation verification | Reviewer verifies evidence and actual implementation. | Not checkbox-only. |
| CAPA-FR-010 | 27 | Effectiveness criteria | Define measurable criterion, data source, observation period and due date before check. | Objective. |
| CAPA-FR-011 | 27 | Effectiveness result | Pass/fail/inconclusive with evidence and reviewer. | True effectiveness. |
| CAPA-FR-012 | 27 | Failed effectiveness | Reopen CAPA/new investigation/action based on policy. | No cosmetic close. |
| CAPA-FR-013 | 27 | Extension | Reason/risk/approval; original due date retained. | Aging controlled. |
| CAPA-FR-014 | 27 | Escalation | Overdue/high-risk/repeat CAPA escalates. | Management visibility. |
| CAPA-FR-015 | 27 | Closure | All mandatory actions and effectiveness complete before QA closure. | Complete. |
| CAPA-FR-016 | 27 | Cancellation | Duplicate/not-required cancellation with Quality rationale. | History. |
| CAPA-FR-017 | 27 | Reopen | Recurrence/new evidence can reopen. | History. |
| CAPA-FR-018 | 27 | Recurrence analysis | Link new quality events to prior CAPA to assess recurrence. | Effectiveness signal. |
| CAPA-FR-019 | 27 | Multi-site scope | CAPA scope can be site/product/process/enterprise. | Scalable. |
| CAPA-FR-020 | 27 | Metrics | Aging, overdue, effectiveness failures, recurrence. | QMS dashboard. |
| CAPA-FR-021 | 27 | Signatures | Plan approval, extension, effectiveness and closure signed per policy. | Attributable. |
| CAPA-FR-022 | 27 | Export | Complete action/evidence/effectiveness history exportable. | Inspection-ready. |
| NCR-FR-001 | 28 | NCR initiation | Create nonconformance for material/component/subassembly/device/packaging/finished output. | Scope exact. |
| NCR-FR-002 | 28 | Automatic source | Failed QC/test/inspection can create NCR candidate. | Immediate. |
| NCR-FR-003 | 28 | Segregation | Hold/segregate exact lots/serials/quantities electronically and physically. | Prevent use. |
| NCR-FR-004 | 28 | Requirement violated | Reference exact specification/test/requirement and objective evidence. | Clear. |
| NCR-FR-005 | 28 | Evaluation | Assess severity, usability, quality/safety/performance and investigation need. | Risk. |
| NCR-FR-006 | 28 | Disposition | Rework, repair where allowed, return, scrap/destroy, concession/use-as-is only if policy permits. | Controlled. |
| NCR-FR-007 | 28 | Use-as-is restriction | Default restricted; technical/Quality justification and authority required. | Bounded. |
| NCR-FR-008 | 28 | Rework route | Use approved route/work instruction; original failure preserved. | Trace. |
| NCR-FR-009 | 28 | Reinspection/retest | Required after rework according to approved criteria; prior failure remains. | Evidence. |
| NCR-FR-010 | 28 | Supplier link | Link source supplier/material and SCAR if needed. | Supplier quality. |
| NCR-FR-011 | 28 | Batch/release impact | Affected scope creates release blocker/hold. | No bypass. |
| NCR-FR-012 | 28 | CAPA trigger | Significant/repeat NCR can require CAPA. | Systemic. |
| NCR-FR-013 | 28 | Partial scope | Disposition exact units/serials/quantity without changing unaffected product. | Device scale. |
| NCR-FR-014 | 28 | Scrap/destruction | Integrate inventory/destruction transaction. | Quantity closure. |
| NCR-FR-015 | 28 | Approval | Quality/engineering approval by disposition/profile. | Independent. |
| NCR-FR-016 | 28 | Reopen | New evidence can reopen. | History. |
| NCR-FR-017 | 28 | Trend | Defect codes trend by process/product/supplier. | Metrics. |
| NCR-FR-018 | 28 | Export | Complete evidence/disposition/rework/retest export. | Inspection-ready. |
| CHG-FR-001 | 29 | Change request | Create change for product/process/recipe/spec/material/source/equipment/facility/software/document/method/label/supplier. | Broad control. |
| CHG-FR-002 | 29 | Classification | Temporary/permanent and risk class using approved methodology. | Routing. |
| CHG-FR-003 | 29 | Current/proposed state | Document current state, proposed state and reason/business need. | Clear intent. |
| CHG-FR-004 | 29 | Affected objects | Link exact object versions potentially affected. | Impact graph. |
| CHG-FR-005 | 29 | Regulatory impact | Qualified Regulatory/Quality assesses filing/notification/approval/reportability implications. | Human authority. |
| CHG-FR-006 | 29 | Quality impact | Assess product quality/safety/performance. | Quality. |
| CHG-FR-007 | 29 | Validation impact | Assess process/equipment/software validation/requalification. | Validated state. |
| CHG-FR-008 | 29 | Risk assessment | Create/link risk assessment when required. | Risk based. |
| CHG-FR-009 | 29 | Training impact | Identify documents/roles/users needing training before effective date. | Readiness. |
| CHG-FR-010 | 29 | Open-batch/inventory impact | Assess open batches, released stock, materials, labels and transition plan. | Cutover safe. |
| CHG-FR-011 | 29 | Data/migration impact | Assess schema/master-data/migration/backfill/data-integrity requirements. | System safe. |
| CHG-FR-012 | 29 | Implementation plan | Tasks, owners, dependencies, evidence, target/effective date, rollback. | Executable. |
| CHG-FR-013 | 29 | Pre-approval | Quality/technical/regulatory approvals before implementation except controlled emergency path. | Controlled. |
| CHG-FR-014 | 29 | Emergency change | Time-bounded emergency path with reason/risk and mandatory retrospective review. | No loophole. |
| CHG-FR-015 | 29 | Execution evidence | Tasks link PR/build/release/equipment/document evidence. | Trace. |
| CHG-FR-016 | 29 | Verification/validation | Verify implemented state and required test/qualification before use. | Qualified. |
| CHG-FR-017 | 29 | Effective date | New state usable only after prerequisites/training/approval complete. | Controlled activation. |
| CHG-FR-018 | 29 | Post-implementation review | Verify intended result/no adverse effect when required. | Effectiveness. |
| CHG-FR-019 | 29 | Rollback | Controlled action preserving both versions/evidence. | History. |
| CHG-FR-020 | 29 | Closure | Close after implementation, verification, training/validation and follow-up. | Complete. |
| CHG-FR-021 | 29 | Cancellation | Retain reason/approval/history. | Integrity. |
| CHG-FR-022 | 29 | Software traceability | Software changes link requirement, code PR, tests, SBOM, validation impact, deployment. | CSA/CSV. |
| CHG-FR-023 | 29 | Master linkage | New product/recipe/spec/doc version can reference governing Change Control. | Trace. |
| CHG-FR-024 | 29 | Export | Before/after, impacts, approvals and evidence exportable. | Inspection-ready. |
| DOC-FR-001 | 30 | Document master | Controlled document has immutable business identity, type, owner, department/site/profile and lifecycle. | Canonical identity. |
| DOC-FR-002 | 30 | Versioning | Each revision is separate version; released content immutable. | History. |
| DOC-FR-003 | 30 | Content storage | Store authoritative content/file in Vault/Evidence with hash and version. | Integrity. |
| DOC-FR-004 | 30 | Source/rendition | Differentiate editable source from released rendition/PDF where applicable. | Meaning preserved. |
| DOC-FR-005 | 30 | Review workflow | Technical/Quality/Regulatory reviewers based on document type. | Appropriate review. |
| DOC-FR-006 | 30 | Approval/e-signature | Controlled release requires policy-defined signatures. | Attributable. |
| DOC-FR-007 | 30 | Effective date | Version becomes usable only at approved effective date after prerequisites. | Controlled use. |
| DOC-FR-008 | 30 | Supersession | New effective version supersedes future use; historical records retain exact old version. | No drift. |
| DOC-FR-009 | 30 | Obsolete | Obsolete versions removed from normal current-use view but historically retrievable. | Prevent unintended use. |
| DOC-FR-010 | 30 | Controlled copy | Optional numbered controlled-copy issue/recipient/location/status. | Distribution control. |
| DOC-FR-011 | 30 | Uncontrolled copy marking | Print/download may be watermarked/marked uncontrolled per policy. | User awareness. |
| DOC-FR-012 | 30 | Periodic review | Review interval/due date with reminders/escalation. | Lifecycle. |
| DOC-FR-013 | 30 | Training impact | Release determines training assignment to roles/sites/users. | Training integrated. |
| DOC-FR-014 | 30 | Acknowledgment | Read-and-understand training is separate from approval signature. | Semantics. |
| DOC-FR-015 | 30 | Change link | Major revision may require Change Control. | Trace. |
| DOC-FR-016 | 30 | Relationships | Parent/child/reference links by exact version or explicit current-reference semantics. | Dependency clarity. |
| DOC-FR-017 | 30 | Forms/templates | Controlled forms and executable templates are versioned/released. | No uncontrolled forms. |
| DOC-FR-018 | 30 | External documents | Track external standards/guidance/customer specs with source/revision/applicability without unauthorized copying. | External control. |
| DOC-FR-019 | 30 | Access | Document-class/site/role access server-side. | Confidentiality. |
| DOC-FR-020 | 30 | Distribution audit | Audit controlled-copy generation/distribution where policy requires. | Evidence. |
| DOC-FR-021 | 30 | Retirement | Retire with reason/effective date/impact. | History. |
| DOC-FR-022 | 30 | Migration | Imported historical docs retain source/provenance; no fabricated approvals. | Integrity. |
| DOC-FR-023 | 30 | Search | Current/obsolete search by code/title/type/owner/site/effective date. | Usability. |
| DOC-FR-024 | 30 | Export | Revision/approval/effective/distribution history exportable. | Inspection-ready. |
| TRN-FR-001 | 31 | Curriculum | Define curriculum by role/site/department/product/process/equipment/area. | Targeted. |
| TRN-FR-002 | 31 | Requirement source | Training can originate from document, role, qualification, change, CAPA or manager assignment. | Trace. |
| TRN-FR-003 | 31 | Assignment | Assign user/group with due/effective date and completion type. | Actionable. |
| TRN-FR-004 | 31 | Training types | Read/understand, instructor-led, practical/OJT, exam, demonstration, qualification, recurring. | Flexible. |
| TRN-FR-005 | 31 | Exact content version | Document training references exact released version. | Correct content. |
| TRN-FR-006 | 31 | Completion evidence | Trainee/trainer/date/score/result/evidence/signature. | Evidence. |
| TRN-FR-007 | 31 | Assessment | Quiz/exam/pass score/attempt rules; question bank versioned if used. | Competency. |
| TRN-FR-008 | 31 | Practical qualification | Observed checklist/process/equipment scope and evaluator. | Skill. |
| TRN-FR-009 | 31 | Qualification issuance | Completion may issue qualification with effective/expiry dates. | IAM integration. |
| TRN-FR-010 | 31 | Expiry/renewal | Recurring training/qualification renewal and execution blocking at expiry. | Current competence. |
| TRN-FR-011 | 31 | Grace period | Explicit controlled policy only. | No hidden grace. |
| TRN-FR-012 | 31 | Retraining triggers | Document revision, change, CAPA, deviation, performance, periodic cycle. | Current knowledge. |
| TRN-FR-013 | 31 | Revision impact | Document release decides whether retraining required and for whom. | Risk based. |
| TRN-FR-014 | 31 | Equivalency | Prior training/experience credit requires evidence/approval. | Controlled. |
| TRN-FR-015 | 31 | Waiver | Reason/scope/approver/expiry if permitted. | Bounded. |
| TRN-FR-016 | 31 | Execution gate | Policy Service blocks operation when training/qualification inactive. | Real enforcement. |
| TRN-FR-017 | 31 | Trainer qualification | Trainer/evaluator qualification where required. | Qualified assessor. |
| TRN-FR-018 | 31 | Temporary auth | Uses Document 07 process; training module cannot bypass authority. | No loophole. |
| TRN-FR-019 | 31 | Overdue escalation | Critical overdue training escalates. | Timely. |
| TRN-FR-020 | 31 | Training matrix | Role-vs-required training/qualification/gaps/expiry. | Management. |
| TRN-FR-021 | 31 | External training | Record external course/certificate with evidence/approval. | Broader competence. |
| TRN-FR-022 | 31 | History | Role/department changes do not rewrite old training. | Integrity. |
| TRN-FR-023 | 31 | Transcript | Complete training/qualification export. | Inspection-ready. |
| TRN-FR-024 | 31 | Failed attempts | Failed/expired attempts retained. | Data integrity. |
| SCAR-FR-001 | 32 | Supplier quality case | Create from incoming reject, deviation, complaint, audit, trend or manufacturing defect. | Source linked. |
| SCAR-FR-002 | 32 | Affected source | Identify supplier/manufacturer site, material/spec and affected lots/products. | Scope exact. |
| SCAR-FR-003 | 32 | Containment | Hold lot/source/new receipts/use if risk requires; link ASL status. | Immediate control. |
| SCAR-FR-004 | 32 | SCAR issue | Formal request with problem/evidence, required response and due dates. | Supplier action. |
| SCAR-FR-005 | 32 | Acknowledgment | Track supplier acknowledgment/contact. | Communication. |
| SCAR-FR-006 | 32 | Supplier root cause | Capture supplier-provided root cause/evidence as supplier statement, not automatically accepted fact. | Review. |
| SCAR-FR-007 | 32 | Supplier actions | Track supplier corrections/corrective actions and implementation evidence. | Action. |
| SCAR-FR-008 | 32 | Internal review | Supplier Quality/QA accepts/rejects response with rationale/signature. | Authority. |
| SCAR-FR-009 | 32 | Effectiveness | Verify incoming/performance data after implementation. | True closure. |
| SCAR-FR-010 | 32 | Requalification | Significant issue may trigger audit/requalification. | ASL. |
| SCAR-FR-011 | 32 | Source suspension | Supplier-material approval can be suspended pending resolution. | Procurement gate. |
| SCAR-FR-012 | 32 | Alternate source | Emergency alternative source links deviation/change. | Controlled. |
| SCAR-FR-013 | 32 | Internal CAPA | Internal CAPA may also be required. | Ownership. |
| SCAR-FR-014 | 32 | Repeat issue | Detect recurrence by supplier/material/defect. | Trend. |
| SCAR-FR-015 | 32 | Escalation | Overdue response escalates. | Timeliness. |
| SCAR-FR-016 | 32 | Closure | Close only after accepted response/effectiveness/source decision. | Complete. |
| SCAR-FR-017 | 32 | Performance impact | SCAR contributes to supplier scorecard/risk. | Data driven. |
| SCAR-FR-018 | 32 | Export | Correspondence/evidence/history exportable. | Inspection-ready. |
| RSK-FR-001 | 33 | Risk register | Create controlled product/process/system/supplier/equipment/software risk. | Common register. |
| RSK-FR-002 | 33 | Methodology | Select approved risk methodology; formula/version controlled. | Consistent. |
| RSK-FR-003 | 33 | Hazard/problem | Define hazard/failure/problem, context and potential effect/harm. | Clear. |
| RSK-FR-004 | 33 | Initial assessment | Capture pre-control risk inputs/score/class. | Baseline. |
| RSK-FR-005 | 33 | Controls | Link preventive/detective controls and evidence. | Trace. |
| RSK-FR-006 | 33 | Residual assessment | Reassess after controls. | Decision. |
| RSK-FR-007 | 33 | Acceptance | Role/authority/rationale based on risk level. | Governance. |
| RSK-FR-008 | 33 | Mitigation actions | Link CAPA/change/tasks. | Action. |
| RSK-FR-009 | 33 | Quality-event link | Deviation/OOS/Complaint/Audit can trigger risk review. | Living risk. |
| RSK-FR-010 | 33 | Change link | Change Control can require reassessment before approval. | Integrated. |
| RSK-FR-011 | 33 | Object mapping | Link product/version, recipe/step, equipment, supplier, software component. | Specific. |
| RSK-FR-012 | 33 | Versioning | Historical assessments/scores preserved. | History. |
| RSK-FR-013 | 33 | Periodic review | Review cycle and escalation. | Current. |
| RSK-FR-014 | 33 | Signal review | Trend/complaint/incident can trigger unscheduled review. | Responsive. |
| RSK-FR-015 | 33 | Matrix configuration | Risk matrix/method controlled; no universal hardcoded FMEA. | Flexible. |
| RSK-FR-016 | 33 | Human acceptance | AI may suggest evidence but cannot accept risk. | Authority. |
| RSK-FR-017 | 33 | Dashboard | Heatmap/trends/overdue mitigations. | Visibility. |
| RSK-FR-018 | 33 | Export | Assessment/control/acceptance history exportable. | Inspection-ready. |
| AUDIT-FR-001 | 34 | Audit program | Define annual/multi-period audit program by site/process/system/supplier where applicable. | Planned oversight. |
| AUDIT-FR-002 | 34 | Audit plan | Scope, objectives, criteria, references, auditors, schedule, auditees. | Clear plan. |
| AUDIT-FR-003 | 34 | Auditor independence | Policy prevents auditor from auditing own direct work/function where required. | Objectivity. |
| AUDIT-FR-004 | 34 | Checklist | Versioned checklist/template supports sampling prompts but never limits auditor findings. | Consistent. |
| AUDIT-FR-005 | 34 | Evidence | Capture interview/record/sample/evidence references with access controls. | Evidence. |
| AUDIT-FR-006 | 34 | Finding | Requirement/observation/evidence/severity/classification. | Objective finding. |
| AUDIT-FR-007 | 34 | Finding response | Assign owner, correction, root-cause/action and due dates. | Accountability. |
| AUDIT-FR-008 | 34 | CAPA link | Significant/systemic finding can create CAPA. | Integration. |
| AUDIT-FR-009 | 34 | Verification | Auditor/QA verifies action/effectiveness. | Closure quality. |
| AUDIT-FR-010 | 34 | Audit report | Generate controlled report from approved record. | Formal output. |
| AUDIT-FR-011 | 34 | Closure | Close only after findings dispositioned per policy. | Complete. |
| AUDIT-FR-012 | 34 | Schedule change | Reschedule/cancel with reason/approval; old schedule retained. | Transparency. |
| AUDIT-FR-013 | 34 | Confidentiality | Role/site access restrictions. | Security. |
| AUDIT-FR-014 | 34 | Repeat findings | Detect recurrence by process/requirement/root cause. | Trend. |
| AUDIT-FR-015 | 34 | Metrics | Completion, overdue findings, recurrence, CAPA links. | Management. |
| AUDIT-FR-016 | 34 | External audit tracking | Track external audits/inspection commitments separately where configured. | Broader QMS. |
| AUDIT-FR-017 | 34 | Export | Plan/evidence/findings/responses/closure exportable. | Inspection-ready. |
| CMP-FR-001 | 35 | Complaint intake | Capture oral/written/electronic complaint from customer, patient/user, distributor, service, sales or regulator. | All channels. |
| CMP-FR-002 | 35 | Known information | Product name/strength/configuration, lot/batch/serial/UDI, complainant, date, nature, country/event details and reply where known. | Complaint file. |
| CMP-FR-003 | 35 | Acknowledgment | Track complaint acknowledgment/communication. | Customer handling. |
| CMP-FR-004 | 35 | Product identification | Resolve product/lot/serial; unknown IDs go to reconciliation queue. | Trace. |
| CMP-FR-005 | 35 | Constituent classification | Drug/device/interface/combination/packaging/label/usability/unknown. | DDCP aware. |
| CMP-FR-006 | 35 | Triage | Quality/Regulatory seriousness/criticality assessment under approved procedure. | Safety. |
| CMP-FR-007 | 35 | Investigation decision | Quality determines investigation required/not required. | 211.198 support. |
| CMP-FR-008 | 35 | No-investigation rationale | If not investigated, reason and responsible approver recorded. | 211.198 support. |
| CMP-FR-009 | 35 | Investigation | Link batch/device history, QC, deviations, materials, equipment, complaints, service and returned product. | Complete. |
| CMP-FR-010 | 35 | Returned product | Track chain of custody, testing, preservation and disposition. | Evidence. |
| CMP-FR-011 | 35 | Genealogy | Serial/lot lookup identifies constituents/materials/related product. | DDCP. |
| CMP-FR-012 | 35 | Reportability assessment | Separate authorized assessment with rationale, regime, trigger/date and due date; software does not decide legal outcome alone. | Controlled. |
| CMP-FR-013 | 35 | Part 4 PMSR profile | Support multiple constituent/application reporting regimes and information-sharing hooks. | Combination support. |
| CMP-FR-014 | 35 | Device reporting hook | MDR/eMDR reference/workflow where applicable. | Postmarket. |
| CMP-FR-015 | 35 | Drug safety hook | FAERS/safety-system reference/escalation where applicable. | Postmarket. |
| CMP-FR-016 | 35 | Trend | Complaint codes/failure mode/product/lot/constituent trend. | Signal. |
| CMP-FR-017 | 35 | CAPA | Significant/repeat complaint can create CAPA. | Systemic. |
| CMP-FR-018 | 35 | Field action | Complaint can trigger recall/field-action assessment. | Containment. |
| CMP-FR-019 | 35 | Response | Track approved response to complainant. | Communication. |
| CMP-FR-020 | 35 | Closure | Investigation decision, reportability, CAPA/field action and response complete per policy. | Complete. |
| CMP-FR-021 | 35 | Retention | Apply product/profile/predicate retention policy. | Durable. |
| CMP-FR-022 | 35 | Privacy | Restrict/minimize personal/health data. | Confidentiality. |
| CMP-FR-023 | 35 | Duplicate detection | Link duplicate reports without deleting original intake. | Integrity. |
| CMP-FR-024 | 35 | Export | Known data, investigation/follow-up or no-investigation rationale, reportability and response exportable. | Inspection-ready. |
| FAR-FR-001 | 36 | Assessment initiation | Create from complaint, deviation, CAPA, trend, regulatory request or management decision. | Trigger linked. |
| FAR-FR-002 | 36 | Action classification | Recall/correction/removal/field action/customer advisory/stock recovery or configured terminology. | Explicit. |
| FAR-FR-003 | 36 | Affected scope | Use Genealogy to identify products/lots/serials/packages/distribution references. | Accurate. |
| FAR-FR-004 | 36 | Constituent scope | DDCP action can target whole product or constituent/interface with final-product impact. | Combination aware. |
| FAR-FR-005 | 36 | Risk assessment | Link health/product risk assessment and rationale. | Evidence. |
| FAR-FR-006 | 36 | Reportability assessment | Authorized Regulatory determines applicable Part 806/drug/biologic/Part4 obligations/deadlines. | Human authority. |
| FAR-FR-007 | 36 | Distribution hold | Block undistributed inventory when required. | Containment. |
| FAR-FR-008 | 36 | Consignee snapshot | Resolve and freeze distribution/consignee scope from ERP/WMS/CRM. | Communication scope. |
| FAR-FR-009 | 36 | Communication package | Version/approve notification text/instructions/attachments. | Controlled. |
| FAR-FR-010 | 36 | Notification tracking | Recipient/date/channel/delivery/acknowledgment/follow-up. | Execution. |
| FAR-FR-011 | 36 | Return/correction plan | Return/inspect/correct/update/replace/destroy plan. | Disposition. |
| FAR-FR-012 | 36 | Unit reconciliation | Affected/contacted/returned/corrected/destroyed/unavailable/outstanding. | Effectiveness. |
| FAR-FR-013 | 36 | Effectiveness checks | Verify communication/action effectiveness under approved plan. | Control. |
| FAR-FR-014 | 36 | Submission evidence | Store regulatory report/submission IDs/dates/acknowledgments. | Evidence. |
| FAR-FR-015 | 36 | Corrections/removals record | Maintain applicable device correction/removal records even if reporting decision is no. | Part 806 support. |
| FAR-FR-016 | 36 | CAPA link | Underlying systemic action links CAPA. | Systemic. |
| FAR-FR-017 | 36 | Status updates | Track management/regulatory updates and milestones. | Governance. |
| FAR-FR-018 | 36 | Closure | Scope reconciliation, action, submissions, effectiveness and dependencies complete. | Complete. |
| FAR-FR-019 | 36 | Scope expansion | New affected product reopens/expands controlled version. | Dynamic. |
| FAR-FR-020 | 36 | Export | Decision/scope/communication/reconciliation/submission/closure package exportable. | Inspection-ready. |
| MET-FR-001 | 37 | Metric catalogue | Controlled metric code, owner, numerator/denominator/data source, frequency/scope. | Stable semantics. |
| MET-FR-002 | 37 | Metric versioning | Formula/data mapping change creates version/effective date. | No trend distortion. |
| MET-FR-003 | 37 | Deviation metrics | Counts/rates/severity/recurrence/product/process/site/root cause/aging. | Quality. |
| MET-FR-004 | 37 | CAPA metrics | Open/overdue/cycle time/effectiveness failures/repeat issues. | CAPA health. |
| MET-FR-005 | 37 | OOS/OOT metrics | Rate by test/product/method/instrument/site and recurrence. | Lab signal. |
| MET-FR-006 | 37 | NCR metrics | Defect/nonconformance by product/supplier/process/device test. | Manufacturing. |
| MET-FR-007 | 37 | Complaint metrics | Rate/failure mode/product/lot/constituent/reportability/field-action signals. | Postmarket. |
| MET-FR-008 | 37 | Supplier metrics | Reject rate/SCAR aging/audit/performance. | Supplier. |
| MET-FR-009 | 37 | Audit metrics | Completion/overdue findings/repeat findings. | QMS. |
| MET-FR-010 | 37 | Training metrics | Overdue/expiry/failure/execution-block incidents. | Competency. |
| MET-FR-011 | 37 | Batch quality | Review/release cycle, exception count, right-first-time, yield/reconciliation failures. | Operations. |
| MET-FR-012 | 37 | Trend rules | Versioned thresholds/control rules/alerts separate from raw metric. | Signal. |
| MET-FR-013 | 37 | Normalization | Denominator/volume/time normalization explicit. | No misleading rates. |
| MET-FR-014 | 37 | Snapshot | Store source cutoff and formula version for period result. | Reproducible. |
| MET-FR-015 | 37 | Drilldown | Authorized drilldown to source records. | Evidence. |
| MET-FR-016 | 37 | Management review package | Freeze periodic quality summary/dashboard/export. | Review support. |
| MET-FR-017 | 37 | Alert/escalation | Threshold creates alert/assessment; CAPA only if configured/decided. | Controlled. |
| MET-FR-018 | 37 | Effectiveness framework | Shared criterion/period/data/result for CAPA/SCAR/field action. | Reuse. |
| MET-FR-019 | 37 | Failed effectiveness | Escalate/reopen/new action according to source policy. | No hidden fail. |
| MET-FR-020 | 37 | AI analytics | AI may summarize signals but cannot modify official metrics/actions. | Advisory. |
| MET-FR-021 | 37 | Access | Tenant/site/role restrictions. | Security. |
| MET-FR-022 | 37 | Export/API | Structured analytics export without direct write access. | BI integration. |
| MET-FR-023 | 37 | Late/corrected data | Recalculation creates new snapshot/version; prior approved package immutable. | History. |
| MET-FR-024 | 37 | Performance/freshness | Async/materialized calculations show source cutoff/freshness. | No stale ambiguity. |
