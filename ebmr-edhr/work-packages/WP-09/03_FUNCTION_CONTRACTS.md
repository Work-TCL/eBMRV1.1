# WP-09 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| registerPostmarketSource() | 58 | Regulatory Admin | source_type:string; organization:string; channel:string; owner_id:uuid; ingestion_profile_id:uuid | Authorized; source type/config valid | PostmarketSource |
| createSafetyCaseLink() | 58 | Complaint/Service/Literature ingestion | source_record_type:string; source_record_id:uuid; source_record_version:int; receipt timestamps; pro | Source exists; source/version not already linked | SafetyCase |
| resolveMarketedProduct() | 58 | Safety intake processor | case_id:uuid; product identifiers; lot/serial/NDC/UDI | Catalogue/mappings available | ProductResolution |
| classifySafetyCase() | 58 | Safety/Regulatory reviewer | case_id; classification DTO; expectedness_ref?; rationale; signature? | Reviewer authorized/qualified; latest follow-up reviewed | SafetyClassification |
| addSafetyCaseFollowup() | 58 | Intake/Safety | case_id; new_information; receipt_at; evidence_refs[] | Case active; source attributable | SafetyFollowup |
| findProbableDuplicates() | 58 | Processor/AI advisory | case_id; matching_policy_version | Policy released | DuplicateCandidate[] |
| linkDuplicateCases() | 58 | Safety reviewer | canonical_case_id; duplicate_case_ids[]; rationale | Authorized; cases exist and versions current | DuplicateLinkResult |
| calculateSurveillanceMetric() | 58 | Scheduled analytics | metric_definition_version; scope; period; source_cutoff | Metric definition released; source availability recorded | SurveillanceMetricSnapshot |
| evaluateSignalRules() | 58 | Scheduled/manual | metric snapshots; case set; signal_rule_versions | Rules effective | SignalRuleResult[] |
| openSafetySignal() | 58 | Safety reviewer/rule | trigger_refs[]; product/constituent scope; rationale | No duplicate open signal unless separately justified | SafetySignal |
| assessSafetySignal() | 58 | Safety/Medical/Quality team | signal_id; assessment; scope; recommended actions; signatures | Role/SoD policy met | SafetySignalAssessment |
| escalateSignalToQMSOrRegulatory() | 58 | Safety/Regulatory | signal_id; action_type; target_module; rationale | Signal assessed; action authorized | EscalationReceipt |
| buildPeriodicSafetyDataset() | 58 | Periodic report service | application_id; interval_start; interval_end; report_type; cutoff | Reporting profile configured | PeriodicSafetyDataset |
| createReportabilityTracks() | 59 | Safety classification / field action / quality event | safety_case_id:uuid; application_profile_id:uuid; constituent_set[]; source_snapshot_id | Product/application resolved; rule catalogue effective | ReportabilityTrack[] |
| calculateRegulatoryDeadline() | 59 | Reportability service | track_id; clock_start; rule_version; calendar_profile | Rule applicable; clock start available/reviewed | DeadlineCalculation |
| decideReportability() | 59 | Authorized Regulatory/Safety reviewer | track_id; decision enum; rationale; evidence_refs[]; signature | Reviewer authorized/qualified; case/version current | ReportabilityDecision |
| buildRegulatoryReport() | 59 | Report author/service | report_task_id; report_schema_version; case_snapshot; reviewer entries | Track REPORTABLE; schema/profile effective | RegulatoryReportDraft |
| approveRegulatoryReport() | 59 | Regulatory approver | report_id; expected_version; signature | Validation checks pass; current source snapshot reviewed | ApprovedRegulatoryReport |
| generateEMDRPayload() | 59 | eMDR adapter | approved MDR report; implementation_package_version | Report routes to eMDR; mapper/schema validated | SubmissionPayload |
| generateAEMSPayload() | 59 | AEMS adapter | approved ICSR; e2b_profile_version | Report routes to AEMS; effective E2B profile | SubmissionPayload |
| submitRegulatoryReport() | 59 | Submission worker / authorized manual user | report_id; channel; payload_version; idempotency_key | Approved; channel active; report version not already accepted | SubmissionAttempt |
| ingestSubmissionAcknowledgement() | 59 | ESG/eMDR/AEMS callback/poller/manual evidence | attempt_id; ack_type; external_id; status; raw_ack_ref | Ack source authenticated/authorized; attempt exists | SubmissionStatus |
| handleSubmissionRejection() | 59 | Submission service | attempt_id; rejection_code/details | Ack says rejected | ResubmissionTask |
| createFollowupReportTask() | 59 | Safety follow-up / FDA request | original_report_id; new_information_receipt; rule/context | Original submitted; follow-up condition met | FollowupReportTask |
| evaluateSameEventReportDeduplication() | 59 | Regulatory reviewer | candidate_track_ids[]; rule versions; report content comparison | Part 4 context active | DeduplicationAssessment |
| freezeReportabilityAuditPackage() | 59 | Inspection/export | case_id and/or report IDs | Records current/readable | RegulatoryEvidencePackage |
| configureApplicantRelationship() | 60 | Regulatory Admin | product/application IDs; applicant roles; counterpart name/address/contact; effective dates | Authorized; product/application valid; overlap rules satisfied | ApplicantRelationship |
| evaluatePart4InformationSharing() | 60 | Safety case/follow-up | safety_case_id; company_receipt_at; application/profile; applicant relationships | Marketed combination product; current relationship/rule exists | InformationSharingAssessment |
| createConstituentSharingPackage() | 60 | Regulatory reviewer | sharing_task_id; safety information snapshot; recipient relationship version | Task open; recipient resolved; package complete | SharingPackage |
| recordConstituentInformationShared() | 60 | Regulatory user/integration | sharing_task_id; sent_at; channel; recipient; delivery_evidence | Approved package; deadline active | SharingReceipt |
| createCorrectionRemovalAssessment() | 60 | Document 36 event | field_action_id; initiation_at; device/application profile | Field-action scope snapshot exists | CorrectionRemovalAssessment |
| decideCorrectionRemovalReportability() | 60 | Regulatory reviewer | assessment_id; reportable:boolean; rationale; signature | Reviewer authorized; field-action facts current | CorrectionRemovalDecision |
| createFieldAlertAssessment() | 60 | Complaint/Deviation/OOS/Field Action | application/product; distributed batches; issue facts; applicant_receipt_at | NDA context configured; distributed-product candidate | FieldAlertAssessment |
| decideFieldAlertReportability() | 60 | Regulatory/Quality reviewer | assessment_id; decision; rationale; signature | Reviewer authorized; source evidence reviewed | FieldAlertDecision |
| createBPDRTrack() | 60 | Biologic quality/deviation event | product/application; deviation facts; discovery/receipt dates | Biologic/BLA profile configured | BPDRTrack |
| generatePeriodicReportingSchedule() | 60 | Regulatory calendar job | application_id; approval/license date; reporting profile; FDA overrides | Profile effective | PeriodicSchedule |
| freezePeriodicReportDataset() | 60 | Periodic report owner | cycle_id; source_cutoff | Cycle in data collection; source surveillance complete enough per procedure | PeriodicDatasetRef |
| createFDAInformationRequestTask() | 60 | Regulatory user/inbound correspondence | agency letter/ref; requested info/events; due_at; received_at | Request verified/authenticated operationally | FDARequestTask |
| applyRegulatoryDeadlineOverride() | 60 | Regulatory manager | obligation_id; new_due_at; agency evidence; reason; signature | Authorized; source evidence valid | DeadlineOverride |
| calculatePostmarketRetentionPolicy() | 60 | Records Management | product/application profile; applicable regimes; record type | Applicability matrix approved | RetentionPolicyDecision |
| placePostmarketLegalHold() | 60 | Legal/Regulatory | record scope; reason; authority; effective_at | Authorized | LegalHold |
