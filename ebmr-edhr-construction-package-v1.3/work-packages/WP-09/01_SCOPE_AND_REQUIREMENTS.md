# WP-09 — Scope & Requirements

**In scope:** Documents 58, 59, 60

## Document 58 — Postmarket Surveillance, Safety Case & Signal Management (SPEC-PM-001)

- Code location: `services/gxp-api/src/modules/postmarket`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PMS-FR-001..034 (34)

## Document 59 — Regulatory Reportability Assessment & Electronic Safety Submission Management (SPEC-PM-002)

- Code location: `services/gxp-api/src/modules/postmarket`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: REG-FR-001..032 (32)

## Document 60 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar (SPEC-PM-003)

- Code location: `services/gxp-api/src/modules/postmarket`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PMO-FR-001..032 (32)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| PMS-FR-001 | 58 | Source registry | Register complaint, service, repair, literature, regulator, distributor, field action, manufacturing, QC, study and external-safety sources with source owner and ingestion profile. | All safety information attributable. |
| PMS-FR-002 | 58 | Linked safety case | Create safety_case as a regulatory/surveillance layer referencing the source QMS/service record and version; do not copy source record into a second editable truth. | No duplicated QMS master. |
| PMS-FR-003 | 58 | Receipt/awareness chronology | Store source receipt, company initial receipt, regulatory-clock candidate, follow-up receipt and system ingestion timestamps separately. | Deadline reconstruction. |
| PMS-FR-004 | 58 | Product resolution | Resolve exact marketed product/application, lot/batch/serial, UDI/NDC and DDCP constituent architecture when known. | Correct regime and genealogy. |
| PMS-FR-005 | 58 | Unknown identity queue | Unknown product/lot/serial remains open data-quality task and is never discarded. | Completeness. |
| PMS-FR-006 | 58 | Controlled coding | Use versioned event, failure, complaint, device-problem and clinical coding dictionaries; retain code-system/version. | Consistent trending. |
| PMS-FR-007 | 58 | Seriousness attributes | Capture death, life-threatening, hospitalization, disability, congenital anomaly and medically-important inputs without automatically deciding reportability. | Safety assessment. |
| PMS-FR-008 | 58 | Device-event attributes | Capture death/serious-injury/malfunction candidates, caused/contributed evidence and remedial-action context. | MDR inputs. |
| PMS-FR-009 | 58 | Drug/biologic attributes | Capture adverse experience, seriousness, expectedness-reference, causality/reasonable-possibility inputs and reporter/source. | Drug/biologic inputs. |
| PMS-FR-010 | 58 | Manufacturing-event surveillance | Allow quality/manufacturing events to enter surveillance even without an injury when profile/rules make them relevant. | Combination-product breadth. |
| PMS-FR-011 | 58 | Field-action link | Document 36 field action creates a linked surveillance/regulatory source without duplicating execution data. | Postmarket/QMS connection. |
| PMS-FR-012 | 58 | Constituent attribution | Classify possible Drug, Biologic, Device, Interface, Packaging/Label, User Interaction or Unknown involvement. | DDCP analysis. |
| PMS-FR-013 | 58 | Multiple assessment tracks | One safety case can feed several independent reportability tracks while remaining one source case. | Combination-product support. |
| PMS-FR-014 | 58 | Duplicate detection | Detect probable duplicate reports using source/event/product/patient/device identifiers; original source records are retained. | No lost intake. |
| PMS-FR-015 | 58 | Duplicate linking | Link duplicates/related cases to a canonical case without destructive merge. | Integrity. |
| PMS-FR-016 | 58 | Follow-up versioning | Every material follow-up creates immutable follow-up version, receipt date, source/evidence and reassessment flags. | Dynamic case. |
| PMS-FR-017 | 58 | Expectedness reference | Expectedness assessment references exact labeling/reference-safety-information version used. | Reproducible decision. |
| PMS-FR-018 | 58 | Trend population | Define product/family/site/lot/device/constituent/event population and time window. | Meaningful metrics. |
| PMS-FR-019 | 58 | Exposure denominator | Use distribution/exposure data with source cutoff/version where available; explicitly mark denominator uncertainty. | Normalized rates. |
| PMS-FR-020 | 58 | Signal rules | Versioned statistical/business rules may flag severity/frequency shifts, clusters, recurrence or lot concentration. | Early detection. |
| PMS-FR-021 | 58 | Formal safety signal | Open signal from rule or authorized reviewer with frozen case/evidence snapshot. | Controlled signal. |
| PMS-FR-022 | 58 | Signal assessment | Assess clinical, device, drug, manufacturing, quality and genealogy evidence, plausibility, scope and action need. | Multidisciplinary review. |
| PMS-FR-023 | 58 | Signal state machine | DETECTED→TRIAGE→ASSESSMENT→REFUTED/MONITORING/CONFIRMED→ACTION→CLOSED. | Explicit lifecycle. |
| PMS-FR-024 | 58 | Escalation | Confirmed/critical signal may create CAPA, Change, Risk Review, Field Action or Document 59 reportability task. | Actionable. |
| PMS-FR-025 | 58 | Genealogy clustering | Use genealogy to identify affected component/material/device lots, equipment routes and process families. | Manufacturing intelligence. |
| PMS-FR-026 | 58 | Literature source | Literature event stores citation, source file/reference, reviewer and case/signal relationship. | Broad surveillance. |
| PMS-FR-027 | 58 | External authority source | FDA/other authority safety information can be referenced as external evidence without overwriting internal assessment. | Context. |
| PMS-FR-028 | 58 | AI advisory boundary | AI may summarize, suggest duplicates/codes/clusters; it cannot decide seriousness, causality, expectedness, reportability or closure. | Human authority. |
| PMS-FR-029 | 58 | Privacy | Patient/reporter identifiers use minimum-necessary access, encryption/pseudonymization and explicit retention. | Confidentiality. |
| PMS-FR-030 | 58 | Medical review | Where required, qualified medical reviewer records assessment, rationale, evidence and signature/time. | Qualified decision. |
| PMS-FR-031 | 58 | Regulatory handoff | Cases requiring formal legal/reporting assessment create one or more Document 59 tracks from a frozen case snapshot. | Deterministic handoff. |
| PMS-FR-032 | 58 | Periodic dataset | Qualifying cases/signals/actions are selected into immutable periodic safety dataset by application/reporting profile. | Periodic-report support. |
| PMS-FR-033 | 58 | Dashboard | Show serious cases, reportability pending, signal aging, rates, clusters, field actions and follow-up backlog. | Operational visibility. |
| PMS-FR-034 | 58 | Audit/export | Complete source→case→follow-up→signal→action history exportable with versions/signatures. | Inspection-ready. |
| REG-FR-001 | 59 | Independent reportability tracks | One safety case can have multiple independent tracks by report type/regime. | DDCP support. |
| REG-FR-002 | 59 | Application context | Track NDA/ANDA/BLA/device application plus combination-product applicant vs constituent-part applicant role. | Correct applicability. |
| REG-FR-003 | 59 | Versioned report catalogue | Report types/rules are effective-dated configuration: MDR 30-day, MDR 5-day, malfunction, drug/biologic expedited, follow-up/supplemental and future report types. | No hardcoded legal logic. |
| REG-FR-004 | 59 | Human decision authority | Rules calculate candidate applicability and deadlines; authorized reviewer makes final REPORTABLE/NOT_REPORTABLE/PENDING decision. | No autonomous legal decision. |
| REG-FR-005 | 59 | Clock-start basis | Each track stores source receipt/awareness basis, selected clock start, rationale, reviewer and rule version. | Explainable deadline. |
| REG-FR-006 | 59 | Calendar engine | Support CALENDAR_DAY, WORK_DAY, WORKING_DAY and explicit agency due dates with versioned calendars. | Correct time computation. |
| REG-FR-007 | 59 | MDR 30-day track | Support applicable manufacturer 30-calendar-day death/serious-injury/malfunction reporting. | Part 803. |
| REG-FR-008 | 59 | MDR 5-day track | Support qualifying 5-work-day remedial-action/FDA-request reporting. | Part 803. |
| REG-FR-009 | 59 | Malfunction assessment | Capture malfunction, recurrence-consequence rationale, device evaluation and evidence. | MDR basis. |
| REG-FR-010 | 59 | Drug expedited track | Support serious+unexpected drug adverse-experience 15-calendar-day candidate. | 314.80. |
| REG-FR-011 | 59 | Biologic expedited track | Support serious+unexpected biologic adverse-experience 15-calendar-day candidate. | 600.80. |
| REG-FR-012 | 59 | Part 4 modified timing | Support applicable 30-calendar-day constituent drug/biologic expedited timing for device-authorized combination products. | Combination timing. |
| REG-FR-013 | 59 | Follow-up/supplemental | New information can create follow-up report task with original report link and own rule/deadline. | Ongoing reporting. |
| REG-FR-014 | 59 | Report schema | Every report type uses versioned canonical data-element schema and versioned transport mapper. | Submission quality. |
| REG-FR-015 | 59 | Missing information | Required unavailable data is represented as unknown/not obtained with follow-up task where applicable; never fabricated. | Integrity. |
| REG-FR-016 | 59 | Field provenance | Each report field traces to safety case, complaint, product, genealogy, investigation or attributable reviewer entry. | Auditability. |
| REG-FR-017 | 59 | Narrative control | Medical/regulatory narrative is versioned, reviewed and approved/signed per policy. | Controlled content. |
| REG-FR-018 | 59 | eMDR payload | Generate validated eMDR payload through versioned implementation-package/profile mapper. | Electronic device reporting. |
| REG-FR-019 | 59 | eMDR acknowledgements | Track submission/processing acknowledgements and accepted/rejected state; send success alone is not FDA acceptance. | Submission proof. |
| REG-FR-020 | 59 | AEMS ICSR payload | Generate drug/biologic ICSR through configured E2B(R2/R3) profile and ESG NextGen, or controlled SRP/manual workflow if applicable. | Electronic safety reporting. |
| REG-FR-021 | 59 | E2B effective date | E2B standard is effective-dated config with R3 transition support; do not code one permanent format. | Future proof. |
| REG-FR-022 | 59 | Manual submission fallback | If automated connector unavailable, create approved submission package and require manual transmission evidence. | Business continuity. |
| REG-FR-023 | 59 | Attempt ledger | Every transmission attempt stores report/payload version/hash, sender/service identity, channel, endpoint/profile, timestamp, response and external correlation. | Evidence. |
| REG-FR-024 | 59 | Submitted payload immutability | Submitted payload cannot be edited; correction/follow-up creates new report/payload version. | History. |
| REG-FR-025 | 59 | Duplicate submission prevention | Prevent accidental second initial submission of same approved report version. | Idempotency. |
| REG-FR-026 | 59 | Rejected submission | Rejected payload creates correction/resubmission workflow preserving original payload/ack. | Recoverability. |
| REG-FR-027 | 59 | Deadline escalation | Due-soon/overdue tracks escalate to configured Regulatory management roles. | Timeliness. |
| REG-FR-028 | 59 | Exemption/alternate arrangement | Approved reporting exemption/alternate arrangement is versioned evidence/rule, not a code bypass. | Flexibility. |
| REG-FR-029 | 59 | Periodic linkage | Expedited/device reports feed applicable periodic-report datasets/summary rules. | Cross-report integration. |
| REG-FR-030 | 59 | Part 4 same-event dedupe | Evaluate whether one report can satisfy multiple requirements only when required content, manner and deadline conditions are met and reviewer approves. | Avoid duplicate reporting correctly. |
| REG-FR-031 | 59 | FDA information request | Agency request creates task with exact request reference, events/information requested and explicit agency due date. | Regulatory response. |
| REG-FR-032 | 59 | Audit/export | Export rule version, decisions, deadlines, report versions, payloads, acknowledgements, follow-ups and signatures. | Inspection-ready. |
| PMO-FR-001 | 60 | Applicant-role master | Model combination-product applicant, constituent-part applicants, application numbers/types, addresses, contacts and effective relationship dates. | Part 4 context. |
| PMO-FR-002 | 60 | Product/applicant mapping | Each marketed DDCP product version maps relevant applicant relationships and constituent/application roles. | Correct recipient/rules. |
| PMO-FR-003 | 60 | Part 4 sharing trigger | Qualifying safety information can create information-sharing assessment/task when rule applies. | §4.103 support. |
| PMO-FR-004 | 60 | 5-calendar-day sharing clock | Calculate no-later-than 5 calendar days from applicable applicant receipt date for §4.103 sharing. | Timeliness. |
| PMO-FR-005 | 60 | Immutable sharing package | Freeze exact information shared and provenance; later corrections/follow-up create new package/version. | Recordkeeping. |
| PMO-FR-006 | 60 | Recipient evidence | Record recipient applicant name/address/contact/channel and relationship version. | §4.103 record. |
| PMO-FR-007 | 60 | Sharing evidence | Record company receipt date, sharing date/time, package hash, sender and delivery/ack evidence when available. | Proof. |
| PMO-FR-008 | 60 | Sharing escalation | Due-soon/failed constituent sharing escalates to Regulatory management. | Compliance operations. |
| PMO-FR-009 | 60 | Correction/removal assessment | Document 36 Field Action creates linked Part 806 correction/removal assessment; do not duplicate action scope/communications. | Device postmarket. |
| PMO-FR-010 | 60 | 806 10-working-day clock | If reportable under configured §806.10 rule, calculate 10 working days from initiation. | Timely reporting. |
| PMO-FR-011 | 60 | 806 nonreportable record | If not reportable, create controlled §806.20 record with required source/action facts and retention. | Recordkeeping. |
| PMO-FR-012 | 60 | Scope extension amendment | Field-action expansion to additional lots/batches creates amendment assessment/task where required. | Dynamic action. |
| PMO-FR-013 | 60 | Field Alert candidate | Distributed drug-product quality issue from Complaint/Deviation/OOS/Field Action can create NDA Field Alert assessment. | 314.81 linkage. |
| PMO-FR-014 | 60 | Field Alert 3-working-day clock | When applicable, calculate 3 working days from applicant receipt of qualifying information. | Timeliness. |
| PMO-FR-015 | 60 | Field Alert evidence | Link distributed batches, issue type, facility, specifications/contamination/mix-up facts and submission/rapid-communication evidence. | Traceability. |
| PMO-FR-016 | 60 | BPDR candidate | Biologic/product deviation can create BPDR assessment/report task where applicable. | Biologic postmarket. |
| PMO-FR-017 | 60 | Periodic schedule | Maintain quarterly/annual or FDA-configured periodic safety reporting cycles by application/profile. | Calendar. |
| PMO-FR-018 | 60 | Periodic dataset freeze | Use Document 58 immutable interval/cutoff dataset; preserve source versions and inclusion rules. | Reproducible report. |
| PMO-FR-019 | 60 | Part 4 periodic augmentation | For applicable NDA/ANDA/BLA combination products containing a device constituent, include required summary/analysis of applicable device reports for interval. | Part 4. |
| PMO-FR-020 | 60 | FDA information request | Written FDA request creates task with request reference, reason/purpose, requested events/information and agency due date. | Agency response. |
| PMO-FR-021 | 60 | Regulatory correspondence | Store incoming/outgoing correspondence, agency/center, submission/reference numbers, due dates and owner. | Trace. |
| PMO-FR-022 | 60 | Unified regulatory calendar | Show expedited reports, sharing, 806, Field Alerts, BPDR, periodic reports, agency requests and commitments. | Operations. |
| PMO-FR-023 | 60 | Deadline source/basis | Every obligation stores rule/citation/agency-letter source, clock start, original/current due date and calendar profile. | Explainable. |
| PMO-FR-024 | 60 | Deadline override | Agency-granted alternate schedule/extension can change current due date only with evidence, authority and preserved original deadline. | Controlled override. |
| PMO-FR-025 | 60 | Longest-applicable retention | Combination-product postmarket records use configured longest applicable reporting recordkeeping period. | §4.105 support. |
| PMO-FR-026 | 60 | Retention basis | Store all applicable regimes, rule versions, calculated durations/triggers and selected longest rule. | Transparent retention. |
| PMO-FR-027 | 60 | No retrospective shortening | Later profile/rule change cannot silently shorten retention of existing records. | Durability. |
| PMO-FR-028 | 60 | Legal/regulatory hold | Authorized hold suspends normal purge/destruction and preserves reason/scope. | Governance. |
| PMO-FR-029 | 60 | Submission linkage | Obligations reference Document 59 regulatory report/submission or controlled manual evidence; no duplicate submitted-payload store. | Single submission truth. |
| PMO-FR-030 | 60 | Field-action linkage | Part 806 record references exact Document 36 field-action/scope snapshot. | No duplication. |
| PMO-FR-031 | 60 | Periodic report state | SCHEDULED→DATA_COLLECTION→FROZEN→ANALYSIS→APPROVED→SUBMITTED→ACK/ARCHIVE. | Controlled lifecycle. |
| PMO-FR-032 | 60 | Inspection dashboard/export | Show due/overdue obligations and export applicant-sharing, 806, Field Alert/BPDR, periodic, agency-request and retention evidence. | Inspection-ready. |
