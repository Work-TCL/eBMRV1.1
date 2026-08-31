# 14 — Error Code Registry

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Stable machine-readable error codes extracted from the controlled specifications (MUT-FR-021).

---

Clients must branch on the code, never on free text. Codes are contract surface: adding or changing one is an API contract change (Doc 101).

| Error code | Owning module | Class | Source document |
|---|---|---|---|
| `ACTION_DEPENDENCY_OPEN` | SPEC-QMS-002 | dependency/system | 27 |
| `ACTION_EVIDENCE_REQUIRED` | SPEC-QMS-002 | domain validation | 27 |
| `ACTION_MISMATCH` | SPEC-GXP-002 | domain validation | 04 |
| `ACTION_NOT_AUTHORIZED` | SPEC-GXP-001 | authentication/authorization | 03 |
| `APPLICANT_RELATIONSHIP_MISSING` | SPEC-PM-003 | domain validation | 60 |
| `AREA_SCOPE_DENIED` | SPEC-IAM-001 | authentication/authorization | 07 |
| `ASEPTIC_AREA_NOT_READY` | SPEC-EQP-003 | domain validation | 40 |
| `ASEPTIC_ENVIRONMENT_EXCURSION` | SPEC-EQP-003 | domain validation | 40 |
| `ASEPTIC_HOLD_TIME_EXCEEDED` | SPEC-EQP-003 | domain validation | 40 |
| `ASEPTIC_OPERATOR_NOT_QUALIFIED` | SPEC-EQP-003 | domain validation | 40 |
| `ASSEMBLY_PROGRAM_MISMATCH` | SPEC-DDCP-002 | domain validation | 55 |
| `ASSESSMENT_FAILED` | SPEC-QMS-006 | dependency/system | 31 |
| `AUDITOR_SOD_CONFLICT` | SPEC-QMS-009 | concurrency/idempotency | 34 |
| `AUDIT_CLOSURE_BLOCKED` | SPEC-QMS-009 | domain validation | 34 |
| `AUDIT_SCOPE_INCOMPLETE` | SPEC-QMS-009 | authentication/authorization | 34 |
| `AUTHENTICATION_REQUIRED` | SPEC-GXP-001 | authentication/authorization | 03 |
| `AUTH_ASSURANCE_TOO_LOW` | SPEC-GXP-002 | authentication/authorization | 04 |
| `AUTH_CONTEXT_INVALID` | SPEC-GXP-002 | authentication/authorization | 04 |
| `AUTH_FAILED` | SPEC-EDGE-002 | authentication/authorization | 44 |
| `AUTH_NOT_FRESH` | SPEC-GXP-002 | authentication/authorization | 04 |
| `BAD_NATIVE_QUALITY` | SPEC-EDGE-002 | domain validation | 44 |
| `BREAK_GLASS_REQUIRED` | SPEC-IAM-001 | domain validation | 07 |
| `BULK_NOT_RELEASED` | SPEC-DDCP-001 | domain validation | 54 |
| `BUSINESS_REJECT` | SPEC-ERP-006 | domain validation | 53 |
| `CALIBRATION_EXPIRED` | SPEC-EQP-001 | domain validation | 38 |
| `CALIBRATION_OOT_IMPACT_REQUIRED` | SPEC-EQP-001 | domain validation | 38 |
| `CAPA_CLOSURE_BLOCKED` | SPEC-QMS-002 | domain validation | 27 |
| `CAPA_ROOT_CAUSE_REQUIRED` | SPEC-QMS-002 | domain validation | 27 |
| `CAPA_SOURCE_REQUIRED` | SPEC-QMS-002 | domain validation | 27 |
| `CCI_TEST_FAILED` | SPEC-DDCP-001 | dependency/system | 54 |
| `CERT_UNTRUSTED` | SPEC-EDGE-002 | domain validation | 44 |
| `CHALLENGE_ALREADY_USED` | SPEC-GXP-002 | domain validation | 04 |
| `CHALLENGE_CANCELLED` | SPEC-GXP-002 | domain validation | 04 |
| `CHALLENGE_EXPIRED` | SPEC-GXP-002 | domain validation | 04 |
| `CHANGE_IMPACT_INCOMPLETE` | SPEC-QMS-004 | domain validation | 29 |
| `CHANGE_NOT_APPROVED` | SPEC-QMS-004 | domain validation | 29 |
| `CLEANING_REQUIRED` | SPEC-EQP-002 | domain validation | 39 |
| `CLEANING_VERIFICATION_FAILED` | SPEC-EQP-002 | dependency/system | 39 |
| `CLEAN_HOLD_EXPIRED` | SPEC-EQP-002 | domain validation | 39 |
| `CLOCK_START_REQUIRED` | SPEC-PM-002 | domain validation | 59 |
| `CLOSURE_TEST_FAILED` | SPEC-DDCP-003 | dependency/system | 56 |
| `COATED_DEVICE_PROFILE_NOT_EFFECTIVE` | SPEC-DDCP-004 | domain validation | 57 |
| `COATING_DRUG_NOT_RELEASED` | SPEC-DDCP-004 | domain validation | 57 |
| `COATING_ENVIRONMENT_NOT_READY` | SPEC-DDCP-004 | domain validation | 57 |
| `COATING_HOLD_TIME_EXPIRED` | SPEC-DDCP-004 | domain validation | 57 |
| `COATING_PARAMETER_EXCURSION` | SPEC-DDCP-004 | domain validation | 57 |
| `COATING_PROGRAM_MISMATCH` | SPEC-DDCP-004 | domain validation | 57 |
| `COATING_RECONCILIATION_FAILED` | SPEC-DDCP-004 | dependency/system | 57 |
| `COMMAND_UNKNOWN` | SPEC-GXP-001 | domain validation | 03 |
| `COMMUNICATION_NOT_APPROVED` | SPEC-QMS-011 | domain validation | 36 |
| `COMPLAINT_CLOSURE_BLOCKED` | SPEC-QMS-010 | domain validation | 35 |
| `COMPLAINT_PRODUCT_UNRESOLVED` | SPEC-QMS-010 | domain validation | 35 |
| `CONTAINER_ALREADY_USED` | SPEC-DDCP-002 | domain validation | 55 |
| `CONTAINMENT_REQUIRED` | SPEC-QMS-001 | domain validation | 26 |
| `CONTROLLED_COPY_CONFLICT` | SPEC-QMS-005 | concurrency/idempotency | 30 |
| `CORRECTION_REMOVAL_SCOPE_MISSING` | SPEC-PM-003 | authentication/authorization | 60 |
| `CRC_ERROR` | SPEC-EDGE-002 | dependency/system | 44 |
| `CYCLE_PARAMETER_FAILED` | SPEC-EQP-005 | dependency/system | 42 |
| `CYCLE_PROFILE_NOT_EFFECTIVE` | SPEC-EQP-005 | domain validation | 42 |
| `CYCLE_REVIEW_REQUIRED` | SPEC-EQP-005 | domain validation | 42 |
| `DEPENDENCY_UNAVAILABLE` | SPEC-GXP-001 | dependency/system | 03 |
| `DEVIATION_SOURCE_INVALID` | SPEC-QMS-001 | domain validation | 26 |
| `DEVICE_COMPONENT_NOT_RELEASED` | SPEC-DDCP-002 | domain validation | 55 |
| `DEVICE_TEST_FAILED` | SPEC-DDCP-001 | dependency/system | 54 |
| `DIRTY_HOLD_EXCEEDED` | SPEC-EQP-002 | domain validation | 39 |
| `DISPOSITION_NOT_ALLOWED` | SPEC-QMS-003 | domain validation | 28 |
| `DISPOSITION_REQUIRED` | SPEC-QMS-001 | domain validation | 26 |
| `DOCUMENT_REVIEW_INCOMPLETE` | SPEC-QMS-005 | domain validation | 30 |
| `DOCUMENT_SIGNATURE_REQUIRED` | SPEC-QMS-005 | signature | 30 |
| `DOCUMENT_VERSION_OBSOLETE` | SPEC-QMS-005 | concurrency/idempotency | 30 |
| `DOSE_COUNTER_TEST_FAILED` | SPEC-DDCP-003 | dependency/system | 56 |
| `DOSE_DELIVERY_FAILED` | SPEC-DDCP-002 | dependency/system | 55 |
| `DRUG_CONTAINER_NOT_RELEASED` | SPEC-DDCP-002 | domain validation | 55 |
| `DRUG_LOADING_OOS` | SPEC-DDCP-004 | domain validation | 57 |
| `DUPLICATE_SUPPLIER_CANDIDATE` | SPEC-MAT-001 | domain validation | 18 |
| `E2B_MAPPING_ERROR` | SPEC-PM-002 | dependency/system | 59 |
| `EFFECTIVENESS_CRITERION_REQUIRED` | SPEC-QMS-012 | domain validation | 37 |
| `EFFECTIVENESS_INCONCLUSIVE` | SPEC-QMS-012 | domain validation | 37 |
| `EFFECTIVENESS_PLAN_REQUIRED` | SPEC-QMS-002 | domain validation | 27 |
| `EFFECTIVENESS_REQUIRED` | SPEC-QMS-007 | domain validation | 32, 36 |
| `EFFECTIVE_DATE_BLOCKED` | SPEC-QMS-004 | domain validation | 29 |
| `EFFECTIVE_PREREQUISITES_INCOMPLETE` | SPEC-QMS-005 | domain validation | 30 |
| `EMDR_SCHEMA_ERROR` | SPEC-PM-002 | dependency/system | 59 |
| `EM_ACTION_LIMIT_EXCEEDED` | SPEC-EQP-004 | domain validation | 41 |
| `EM_AREA_NOT_READY` | SPEC-EQP-004 | domain validation | 41 |
| `EM_DATA_GAP` | SPEC-EQP-004 | domain validation | 41 |
| `EM_INSTRUMENT_INELIGIBLE` | SPEC-EQP-004 | domain validation | 41 |
| `EM_LOCATION_INVALID` | SPEC-EQP-004 | domain validation | 41 |
| `EM_PROGRAM_NOT_EFFECTIVE` | SPEC-EQP-004 | domain validation | 41 |
| `EM_REVIEW_REQUIRED` | SPEC-EQP-004 | domain validation | 41 |
| `ENDPOINT_UNREACHABLE` | SPEC-EDGE-002 | domain validation | 44 |
| `ENVIRONMENT_NOT_READY` | SPEC-DDCP-003 | domain validation | 56 |
| `EQUIPMENT_CLASS_MISMATCH` | SPEC-EQP-001 | domain validation | 38 |
| `EQUIPMENT_NOT_QUALIFIED` | SPEC-EQP-001 | domain validation | 38 |
| `EQUIPMENT_OUT_OF_SERVICE` | SPEC-EQP-001 | domain validation | 38 |
| `ERP_AUTH_FAILED` | SPEC-ERP-001 | authentication/authorization | 48 |
| `ERP_CAPABILITY_UNSUPPORTED` | SPEC-ERP-001 | domain validation | 48 |
| `ERP_EXTERNAL_CONFLICT` | SPEC-ERP-001 | concurrency/idempotency | 48 |
| `ERP_INSTANCE_INVALID` | SPEC-ERP-001 | domain validation | 48 |
| `ERP_MAPPING_CONFLICT` | SPEC-ERP-001 | concurrency/idempotency | 48 |
| `ERP_MAPPING_NOT_FOUND` | SPEC-ERP-001 | domain validation | 48 |
| `ERP_RECONCILIATION_MISMATCH` | SPEC-ERP-001 | domain validation | 48 |
| `ERP_THROTTLED` | SPEC-ERP-001 | domain validation | 48 |
| `ERP_TIMEOUT` | SPEC-ERP-001 | dependency/system | 48 |
| `ERP_VALIDATION_REJECTED` | SPEC-ERP-001 | domain validation | 48 |
| `EXPECTEDNESS_REFERENCE_REQUIRED` | SPEC-PM-001 | domain validation | 58 |
| `EXPECTED_VERSION_REQUIRED` | SPEC-GXP-001 | concurrency/idempotency | 03 |
| `FDA_REQUEST_DUE_DATE_REQUIRED` | SPEC-PM-003 | domain validation | 60 |
| `FIELD_ACTION_CLOSURE_BLOCKED` | SPEC-QMS-011 | domain validation | 36 |
| `FIELD_ACTION_SCOPE_REQUIRED` | SPEC-QMS-011 | authentication/authorization | 36 |
| `FIELD_ALERT_APPLICATION_MISMATCH` | SPEC-PM-003 | domain validation | 60 |
| `FILL_IPC_OOS` | SPEC-DDCP-001 | domain validation | 54 |
| `FILL_PROGRAM_MISMATCH` | SPEC-DDCP-001 | domain validation | 54 |
| `FILL_ROUTE_MISMATCH` | SPEC-DDCP-003 | domain validation | 56 |
| `FILTER_INTEGRITY_FAILED` | SPEC-EQP-005 | dependency/system | 42, 54 |
| `FINDING_RESPONSE_REQUIRED` | SPEC-QMS-009 | domain validation | 34 |
| `FINDING_VERIFICATION_REQUIRED` | SPEC-QMS-009 | domain validation | 34 |
| `FOLLOWUP_DEADLINE_MISSING` | SPEC-PM-002 | domain validation | 59 |
| `FORMULATION_NOT_RELEASED` | SPEC-DDCP-003 | domain validation | 56 |
| `IDEMPOTENCY_CONFLICT` | SPEC-GXP-001 | concurrency/idempotency | 03 |
| `IMPACT_ASSESSMENT_REQUIRED` | SPEC-QC-003 | domain validation | 25 |
| `IMPACT_REQUIRED` | SPEC-QMS-001 | domain validation | 26 |
| `INHALATION_PROFILE_NOT_EFFECTIVE` | SPEC-DDCP-003 | domain validation | 56 |
| `INHALER_COMPONENT_NOT_RELEASED` | SPEC-DDCP-003 | domain validation | 56 |
| `INHALER_QC_OOS` | SPEC-DDCP-003 | domain validation | 56 |
| `INHALER_RECONCILIATION_FAILED` | SPEC-DDCP-003 | dependency/system | 56 |
| `INJECTOR_PROFILE_NOT_EFFECTIVE` | SPEC-DDCP-002 | domain validation | 55 |
| `INJECTOR_RECONCILIATION_FAILED` | SPEC-DDCP-002 | dependency/system | 55 |
| `INJECTOR_TEST_FAILED` | SPEC-DDCP-002 | dependency/system | 55 |
| `INVESTIGATION_DECISION_REQUIRED` | SPEC-QMS-010 | domain validation | 35 |
| `INVESTIGATION_INCOMPLETE` | SPEC-QC-003 | domain validation | 25, 26 |
| `LABEL_QUANTITY_EXCEEDED` | SPEC-EBMR-007 | domain validation | 16 |
| `LABEL_RECONCILIATION_FAILED` | SPEC-EBMR-007 | dependency/system | 16 |
| `LABEL_VERSION_INCORRECT` | SPEC-EBMR-007 | concurrency/idempotency | 16 |
| `LAB_CAUSE_EVIDENCE_REQUIRED` | SPEC-QC-003 | domain validation | 25 |
| `LEGAL_HOLD_ACTIVE` | SPEC-PM-003 | domain validation | 60 |
| `LIMS_DUPLICATE_EVENT` | SPEC-QC-002 | domain validation | 24 |
| `LIMS_EVIDENCE_INVALID` | SPEC-QC-002 | domain validation | 24 |
| `LIMS_MAPPING_NOT_FOUND` | SPEC-QC-002 | domain validation | 24 |
| `LIMS_METHOD_MISMATCH` | SPEC-QC-002 | domain validation | 24 |
| `LIMS_RECONCILIATION_MISMATCH` | SPEC-QC-002 | domain validation | 24 |
| `LIMS_RESULT_SCHEMA_INVALID` | SPEC-QC-002 | domain validation | 24 |
| `LIMS_RESULT_VERSION_STALE` | SPEC-QC-002 | concurrency/idempotency | 24 |
| `LIMS_SAMPLE_UNKNOWN` | SPEC-QC-002 | domain validation | 24 |
| `LIMS_SOURCE_NOT_AUTHORIZED` | SPEC-QC-002 | authentication/authorization | 24 |
| `LIMS_UOM_INVALID` | SPEC-QC-002 | domain validation | 24 |
| `LINE_CLEARANCE_REQUIRED` | SPEC-EBMR-007 | domain validation | 16, 39 |
| `LINE_NOT_READY` | SPEC-DDCP-001 | domain validation | 54 |
| `LOAD_PATTERN_INVALID` | SPEC-EQP-005 | domain validation | 42 |
| `MAINTENANCE_DUE` | SPEC-EQP-001 | domain validation | 38 |
| `MANAGEMENT_PACKAGE_FROZEN` | SPEC-QMS-012 | domain validation | 37 |
| `MANUAL_REVIEW` | SPEC-ERP-006 | domain validation | 53 |
| `MEANING_MISMATCH` | SPEC-GXP-002 | domain validation | 04 |
| `MEDICAL_REVIEW_REQUIRED` | SPEC-PM-001 | domain validation | 58 |
| `METRIC_DEFINITION_NOT_RELEASED` | SPEC-QMS-012 | domain validation | 37 |
| `METRIC_SOURCE_INCOMPLETE` | SPEC-QMS-012 | domain validation | 37 |
| `NCR_CLOSURE_BLOCKED` | SPEC-QMS-003 | domain validation | 28 |
| `NCR_SCOPE_REQUIRED` | SPEC-QMS-003 | authentication/authorization | 28 |
| `NO_INVESTIGATION_RATIONALE_REQUIRED` | SPEC-QMS-010 | domain validation | 35 |
| `OOS_ALREADY_EXISTS` | SPEC-QC-003 | domain validation | 25 |
| `OOS_RELEASE_BLOCK_ACTIVE` | SPEC-QC-003 | domain validation | 25 |
| `OOT_RULE_NOT_RELEASED` | SPEC-QC-003 | domain validation | 25 |
| `ORIGINAL_RESULT_REQUIRED` | SPEC-QC-003 | domain validation | 25 |
| `PACKAGE_AGGREGATION_CONFLICT` | SPEC-EBMR-007 | concurrency/idempotency | 16 |
| `PACKAGING_MATERIAL_INELIGIBLE` | SPEC-EBMR-007 | domain validation | 16 |
| `PART4_SHARING_DEADLINE_MISSING` | SPEC-PM-003 | domain validation | 60 |
| `PART4_SHARING_RECIPIENT_MISSING` | SPEC-PM-003 | domain validation | 60 |
| `PAYLOAD_SCHEMA_INVALID` | SPEC-EDGE-002 | domain validation | 44 |
| `PERIODIC_DATASET_NOT_REPRODUCIBLE` | SPEC-PM-001 | domain validation | 58 |
| `PERIODIC_REPORT_PROFILE_MISSING` | SPEC-PM-003 | domain validation | 60 |
| `PFS_PROFILE_NOT_EFFECTIVE` | SPEC-DDCP-001 | domain validation | 54 |
| `PFS_RECONCILIATION_FAILED` | SPEC-DDCP-001 | dependency/system | 54 |
| `PLANNED_DEVIATION_EXPIRED` | SPEC-QMS-001 | domain validation | 26 |
| `PMS_CASE_DUPLICATE_SOURCE` | SPEC-PM-001 | domain validation | 58 |
| `PMS_SOURCE_INVALID` | SPEC-PM-001 | domain validation | 58 |
| `POST_MAINTENANCE_VERIFICATION_REQUIRED` | SPEC-EQP-001 | domain validation | 38 |
| `PREVIOUS_BATCH_IDENTITY_PRESENT` | SPEC-EQP-002 | domain validation | 39 |
| `PRIMARY_COMPONENT_NOT_RELEASED` | SPEC-DDCP-001 | domain validation | 54 |
| `PRIVILEGED_ROLE_RESTRICTED` | SPEC-IAM-001 | authentication/authorization | 07 |
| `PRODUCT_SCOPE_DENIED` | SPEC-IAM-001 | authentication/authorization | 07 |
| `PRODUCT_UNRESOLVED` | SPEC-PM-001 | domain validation | 58 |
| `PROTOCOL_EXCEPTION` | SPEC-EDGE-002 | domain validation | 44 |
| `QA_APPROVAL_REQUIRED` | SPEC-QC-003 | domain validation | 25 |
| `QA_CLOSURE_REQUIRED` | SPEC-QMS-001 | domain validation | 26 |
| `QUALIFICATION_EXPIRED` | SPEC-IAM-001 | domain validation | 07, 31 |
| `QUALIFICATION_MISSING` | SPEC-IAM-001 | domain validation | 07 |
| `QUALIFICATION_REQUIRED` | SPEC-GXP-001 | domain validation | 03, 31 |
| `RATE_LIMIT` | SPEC-ERP-006 | domain validation | 53 |
| `RATE_LIMITED` | SPEC-EDGE-002 | domain validation | 44 |
| `RAW_DATA_REQUIRED` | SPEC-QC-001 | domain validation | 23 |
| `READ_TIMEOUT` | SPEC-EDGE-002 | dependency/system | 44 |
| `REASON_REQUIRED` | SPEC-GXP-001 | domain validation | 03 |
| `RECONCILIATION_INCOMPLETE` | SPEC-QMS-011 | domain validation | 36 |
| `RECONNECT_FAILED` | SPEC-EDGE-002 | dependency/system | 44 |
| `RECORD_HASH_CHANGED` | SPEC-GXP-002 | domain validation | 04 |
| `RECORD_VERSION_CHANGED` | SPEC-GXP-002 | concurrency/idempotency | 04 |
| `REGULATORY_REVIEW_REQUIRED` | SPEC-QMS-004 | domain validation | 29, 59 |
| `REINSPECTION_REQUIRED` | SPEC-QMS-003 | domain validation | 28 |
| `REPLAY_DETECTED` | SPEC-GXP-001 | domain validation | 03 |
| `REPORTABILITY_ASSESSMENT_REQUIRED` | SPEC-QMS-010 | domain validation | 35, 36 |
| `REPORTING_PROFILE_MISSING` | SPEC-PM-002 | domain validation | 59 |
| `REPORT_REQUIRED_DATA_MISSING` | SPEC-PM-002 | domain validation | 59 |
| `REPORT_SCHEMA_NOT_EFFECTIVE` | SPEC-PM-002 | domain validation | 59 |
| `REPRINT_REASON_REQUIRED` | SPEC-EBMR-007 | domain validation | 16 |
| `REPROCESSING_AUTHORIZATION_REQUIRED` | SPEC-EQP-005 | authentication/authorization | 42 |
| `RESAMPLE_NOT_AUTHORIZED` | SPEC-QC-003 | authentication/authorization | 25 |
| `RESIDUAL_RISK_REVIEW_REQUIRED` | SPEC-QMS-008 | domain validation | 33 |
| `RESOURCE_INELIGIBLE` | SPEC-GXP-001 | domain validation | 03 |
| `RETENTION_RULE_MISSING` | SPEC-PM-003 | domain validation | 60 |
| `RETEST_LIMIT_REACHED` | SPEC-QC-003 | domain validation | 25 |
| `RETEST_NOT_AUTHORIZED` | SPEC-QC-003 | authentication/authorization | 25 |
| `REWORK_ROUTE_REQUIRED` | SPEC-QMS-003 | domain validation | 28 |
| `RISK_ACCEPTANCE_NOT_AUTHORIZED` | SPEC-QMS-008 | authentication/authorization | 33 |
| `RISK_INPUT_INCOMPLETE` | SPEC-QMS-008 | domain validation | 33 |
| `RISK_METHOD_NOT_RELEASED` | SPEC-QMS-008 | domain validation | 33 |
| `RISK_REVIEW_OVERDUE` | SPEC-QMS-008 | domain validation | 33 |
| `ROLE_MISSING` | SPEC-IAM-001 | domain validation | 07 |
| `RULE_FAILED` | SPEC-GXP-001 | dependency/system | 03 |
| `SAFETY_CLASSIFICATION_INCOMPLETE` | SPEC-PM-001 | domain validation | 58 |
| `SCAR_REVIEW_REJECTED` | SPEC-QMS-007 | domain validation | 32 |
| `SCAR_SOURCE_REQUIRED` | SPEC-QMS-007 | domain validation | 32 |
| `SCHEMA_INVALID` | SPEC-GXP-001 | domain validation | 03 |
| `SEGREGATION_REQUIRED` | SPEC-QMS-003 | domain validation | 28 |
| `SERIAL_DUPLICATE` | SPEC-EBMR-007 | domain validation | 16 |
| `SERVER_ERROR` | SPEC-ERP-006 | dependency/system | 53 |
| `SERVICE_ACCOUNT_NOT_ALLOWED` | SPEC-GXP-002 | domain validation | 04 |
| `SESSION_EXPIRED` | SPEC-EDGE-002 | domain validation | 44 |
| `SIGNAL_SCOPE_INVALID` | SPEC-PM-001 | authentication/authorization | 58 |
| `SIGNATURE_ALREADY_CONSUMED` | SPEC-GXP-002 | signature | 04 |
| `SIGNATURE_INVALID` | SPEC-GXP-001 | signature | 03 |
| `SIGNATURE_POLICY_NOT_FOUND` | SPEC-GXP-002 | signature | 04 |
| `SIGNATURE_REQUIRED` | SPEC-GXP-001 | signature | 03 |
| `SIGNATURE_STALE` | SPEC-GXP-001 | signature | 03 |
| `SIGNER_NOT_ELIGIBLE` | SPEC-GXP-002 | signature | 04 |
| `SIGNING_ENTITLEMENT_MISSING` | SPEC-IAM-001 | signature | 07 |
| `SITE_SCOPE_DENIED` | SPEC-GXP-001 | authentication/authorization | 03, 07 |
| `SNAPSHOT_STALE` | SPEC-QMS-012 | concurrency/idempotency | 37 |
| `SOD_CONFLICT` | SPEC-GXP-001 | concurrency/idempotency | 03, 04, 07 |
| `SOURCE_MAPPING_NOT_FOUND` | SPEC-EDGE-002 | domain validation | 44 |
| `SOURCE_NOT_REGISTERED` | SPEC-GXP-001 | domain validation | 03 |
| `STALE_REGULATORY_OBLIGATION_VERSION` | SPEC-PM-003 | concurrency/idempotency | 60 |
| `STALE_REPORT_VERSION` | SPEC-PM-002 | concurrency/idempotency | 59 |
| `STALE_SAFETY_CASE_VERSION` | SPEC-PM-001 | concurrency/idempotency | 58 |
| `STALE_VERSION` | SPEC-GXP-001 | concurrency/idempotency | 03, 101 |
| `STATE_TRANSITION_INVALID` | SPEC-GXP-001 | domain validation | 03 |
| `STERILE_COMPONENT_INELIGIBLE` | SPEC-EQP-003 | domain validation | 40 |
| `STERILE_FILTRATION_REQUIRED` | SPEC-DDCP-001 | domain validation | 54 |
| `STERILE_STATUS_EXPIRED` | SPEC-EQP-005 | domain validation | 42 |
| `STERILIZATION_INTERACTION_REVIEW_REQUIRED` | SPEC-DDCP-004 | domain validation | 57 |
| `STERILIZATION_STATUS_INVALID` | SPEC-EQP-003 | domain validation | 40 |
| `STERILIZER_INELIGIBLE` | SPEC-EQP-005 | domain validation | 42 |
| `SUBJECT_INACTIVE` | SPEC-IAM-001 | domain validation | 07 |
| `SUBMISSION_CHANNEL_UNAVAILABLE` | SPEC-PM-002 | dependency/system | 59 |
| `SUBMISSION_DUPLICATE_BLOCKED` | SPEC-PM-002 | domain validation | 59 |
| `SUBMISSION_REJECTED` | SPEC-PM-002 | domain validation | 59 |
| `SUBSTRATE_NOT_RELEASED` | SPEC-DDCP-004 | domain validation | 57 |
| `SUPPLIER_RESPONSE_INCOMPLETE` | SPEC-QMS-007 | domain validation | 32 |
| `SUPPLIER_SOURCE_SUSPENDED` | SPEC-QMS-007 | domain validation | 32 |
| `SYSTEM_ERROR` | SPEC-GXP-001 | dependency/system | 03 |
| `TEMP_AUTH_EXPIRED` | SPEC-IAM-001 | authentication/authorization | 07 |
| `TEST_SPEC_NOT_EFFECTIVE` | SPEC-QC-001 | domain validation | 23 |
| `TENANT_SCOPE_DENIED` | SPEC-GXP-001 | authentication/authorization | 03 |
| `TIMEOUT_UNCERTAIN` | SPEC-ERP-006 | dependency/system | 53 |
| `TOKEN_INVALID` | SPEC-GXP-001 | authentication/authorization | 03 |
| `TRAINER_NOT_QUALIFIED` | SPEC-QMS-006 | domain validation | 31 |
| `TRAINING_EXPIRED` | SPEC-QMS-006 | domain validation | 31 |
| `TRAINING_INCOMPLETE` | SPEC-IAM-001 | domain validation | 07, 29 |
| `TRAINING_REQUIRED` | SPEC-QMS-006 | domain validation | 31 |
| `TRANSIENT_NETWORK` | SPEC-ERP-006 | domain validation | 53 |
| `UDI_INVALID` | SPEC-EBMR-007 | domain validation | 16 |
| `UNIT_GENEALOGY_INCOMPLETE` | SPEC-DDCP-002 | domain validation | 55 |
| `UNPLANNED_INTERVENTION_REVIEW_REQUIRED` | SPEC-EQP-003 | domain validation | 40 |
| `USE_AS_IS_NOT_AUTHORIZED` | SPEC-QMS-003 | authentication/authorization | 28 |
| `VALIDATION_INCOMPLETE` | SPEC-QMS-004 | domain validation | 29 |
| `WAIVER_NOT_AUTHORIZED` | SPEC-QMS-006 | authentication/authorization | 31 |
| `WRITE_DISABLED` | SPEC-EDGE-002 | domain validation | 44 |
| `WRONG_CONTAINER_DEVICE_PAIRING` | SPEC-DDCP-002 | domain validation | 55 |
| `WRONG_EQUIPMENT_INSTALLED` | SPEC-EQP-002 | domain validation | 39 |
| `WRONG_PRODUCT_LABEL` | SPEC-EBMR-007 | domain validation | 16 |
| `WRONG_SIGNER` | SPEC-GXP-002 | signature | 04 |

**Total distinct error codes: 277**

## Rules
- Every rejected regulated command returns a registry code.
- HTTP status mapping lives in OpenAPI and is stable.
- New codes require a contract PR and consumer impact review.
- Free-text messages may be localized; codes may not.
