"""Stable machine-readable error codes (MUT-FR-021 equivalent). Callers branch on `.code`, never on
message text.
"""


class GxPError(Exception):
    code: str = "SYSTEM_FAULT"
    status_code: int = 500

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class UnauthorizedError(GxPError):
    code = "UNAUTHORIZED"
    status_code = 401


class ForbiddenError(GxPError):
    code = "FORBIDDEN"
    status_code = 403


class ValidationFailedError(GxPError):
    code = "VALIDATION_FAILED"
    status_code = 422


class StaleVersionError(GxPError):
    code = "STALE_VERSION"
    status_code = 409


class InvalidTransitionError(GxPError):
    code = "INVALID_TRANSITION"
    status_code = 409


class MissingSignatureError(GxPError):
    code = "MISSING_SIGNATURE"
    status_code = 428


class SignatureChallengeInvalidError(GxPError):
    code = "SIGNATURE_CHALLENGE_INVALID"
    status_code = 409


class RoleMissingError(GxPError):
    """No effective role grants the requested action (IAM-FR-006 / Document 07 policy decision)."""

    code = "ROLE_MISSING"
    status_code = 403


class SodConflictError(GxPError):
    """Actor holds two roles a PROHIBITED standing-role-pair SoD rule forbids together (Document 107)."""

    code = "SOD_CONFLICT"
    status_code = 409


class StepRoleMismatchError(GxPError):
    """The recipe reserved this batch step for a role the actor does not hold (BAT-FR-007 / Document 10
    RecipeStep.required_role_code / SG-178). A holder of `batch_step.role_override` (Supervisor/Admin)
    may still proceed by supplying a documented `override_reason`, which is captured in the audit event."""

    code = "STEP_ROLE_MISMATCH"
    status_code = 403


class ProductionNotCompleteError(GxPError):
    """Document 11 §7's own named error code (BAT-FR-026): a batch cannot become 'production_complete'
    while any of its gxp_batch_step rows is not yet 'complete'."""

    code = "PRODUCTION_NOT_COMPLETE"
    status_code = 422


class ParameterRequiredError(GxPError):
    """Document 11 §7's own named error code (BAT-FR-015): a step cannot be completed while one of its
    recipe-declared required parameters (`gxp_recipe_parameter.required=True`) has no recorded
    `gxp_step_result` row."""

    code = "PARAMETER_REQUIRED"
    status_code = 422


class SignaturePolicyUnresolvedError(GxPError):
    """No signature policy resolved for a regulated action. Fail closed — never commit unsigned because
    policy data is missing (Doc 106 SIGP-FR-004)."""

    code = "SIGNATURE_POLICY_UNRESOLVED"
    status_code = 409


class IdempotencyConflictError(GxPError):
    code = "IDEMPOTENCY_CONFLICT"
    status_code = 409


class DependencyUnavailableError(GxPError):
    code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503


class NotFoundError(GxPError):
    code = "NOT_FOUND"
    status_code = 404


class QualificationExpiredError(GxPError):
    code = "QUALIFICATION_EXPIRED"
    status_code = 403


# Document 07 (SPEC-IAM-001, IAM-FR-010) declares QUALIFICATION_MISSING distinct from
# QUALIFICATION_EXPIRED -- no qualification record at all vs. one that has lapsed.
class QualificationMissingError(GxPError):
    code = "QUALIFICATION_MISSING"
    status_code = 403


class ConcurrentVaultReleaseError(GxPError):
    """Two releases for the same (object_type, business_id) raced and both computed the same next
    internal_version. The DB's UNIQUE(object_type, business_id, internal_version) constraint (migration
    616aed1058e9) is what actually prevents the silent duplicate/overwrite -- this only turns the raw
    IntegrityError into a clean, retryable domain error (VLT-FR-012/023)."""

    code = "CONCURRENT_VAULT_RELEASE"
    status_code = 409


class DuplicateSupplierError(GxPError):
    """SUP-FR-029: a likely-duplicate supplier legal identity was detected before creation. Merge is
    prohibited without a controlled data-management procedure -- this only blocks the create, it does not
    attempt to merge or link the candidate automatically."""

    code = "DUPLICATE_SUPPLIER_CANDIDATE"
    status_code = 409


class RuleGateFailedError(GxPError):
    """A released business rule gating this release/disposition did not resolve to PASS
    (MUT-FR-014/RUL-FR-016). Never raised when no released rule exists for the gate's rule_id -- the gate
    is a no-op until a deployment actually authors and releases one."""

    code = "RULE_GATE_FAILED"
    status_code = 409


# Document 110 (SPEC-GXP-008) §5's stable error registry, module-scoped to the rules/calculation domain
# (not added to spec-gxp-001's PlatformErrorCode -- Document 113 §4 reserves that registry for
# platform-wide classes). Only the four Document 110 codes a code path in this pass actually raises;
# UOM_UNKNOWN, RAW_VALUE_MISSING and INSTRUMENT_RESOLUTION_EXCEEDED have no class here because nothing
# raises them yet -- same "don't register a code nothing raises" discipline as SG-074/SG-088 (SG-143).


class PrecisionPolicyUnresolvedError(GxPError):
    """A rule's `precision_policy` does not resolve to a known Document 110 §2 calculation class, or is
    missing a field that class requires (e.g. CC-5's `reported_decimal_places`). Fail closed at draft
    time -- never guess a default numeric policy (AG-15)."""

    code = "PRECISION_POLICY_UNRESOLVED"
    status_code = 409


class DivisionUndefinedError(GxPError):
    """CALC-FR-010: division by zero or another undefined arithmetic result in a rule expression. Never
    a silent zero or NaN."""

    code = "DIVISION_UNDEFINED"
    status_code = 422


class NumericOverflowError(GxPError):
    """CALC-FR-002/N2: a value could not be rounded/represented at its calculation class's declared
    storage precision without loss the class does not permit."""

    code = "NUMERIC_OVERFLOW"
    status_code = 422


class UomUnknownError(GxPError):
    """CALC-FR-006/N6: a rule's `unit_policy` names a UOM code with no released `gxp_uom` row. Free-text
    units are prohibited -- this is the enforcement point."""

    code = "UOM_UNKNOWN"
    status_code = 422


class UomConversionUnavailableError(GxPError):
    """Document 110 §3: a rule's `unit_policy` requests a `convert_to` unit for which no released
    `gxp_uom_conversion` row resolves as of evaluation time. Conversion never happens implicitly --
    an unresolved conversion path fails closed rather than silently comparing mismatched units."""

    code = "UOM_CONVERSION_UNAVAILABLE"
    status_code = 404


# Document 26 (SPEC-QMS-001) §16's stable error registry.


class DeviationSourceInvalidError(GxPError):
    code = "DEVIATION_SOURCE_INVALID"
    status_code = 422


class ContainmentRequiredError(GxPError):
    code = "CONTAINMENT_REQUIRED"
    status_code = 409


class InvestigationIncompleteError(GxPError):
    code = "INVESTIGATION_INCOMPLETE"
    status_code = 409


class ImpactRequiredError(GxPError):
    code = "IMPACT_REQUIRED"
    status_code = 409


class DispositionRequiredError(GxPError):
    code = "DISPOSITION_REQUIRED"
    status_code = 409


class PlannedDeviationExpiredError(GxPError):
    code = "PLANNED_DEVIATION_EXPIRED"
    status_code = 409


class QaClosureRequiredError(GxPError):
    code = "QA_CLOSURE_REQUIRED"
    status_code = 409


# Document 27 (SPEC-QMS-002) §16's stable error registry.


class CapaSourceRequiredError(GxPError):
    code = "CAPA_SOURCE_REQUIRED"
    status_code = 422


class CapaRootCauseRequiredError(GxPError):
    code = "CAPA_ROOT_CAUSE_REQUIRED"
    status_code = 422


class ActionEvidenceRequiredError(GxPError):
    code = "ACTION_EVIDENCE_REQUIRED"
    status_code = 409


class ActionDependencyOpenError(GxPError):
    code = "ACTION_DEPENDENCY_OPEN"
    status_code = 409


class EffectivenessPlanRequiredError(GxPError):
    code = "EFFECTIVENESS_PLAN_REQUIRED"
    status_code = 409


class CapaClosureBlockedError(GxPError):
    code = "CAPA_CLOSURE_BLOCKED"
    status_code = 409


# Document 23 (SPEC-QC-001) §8's stable error registry.


class TestSpecNotEffectiveError(GxPError):
    """A test order was requested against a test definition whose specification is not released/
    effective (QC-FR-010)."""

    code = "TEST_SPEC_NOT_EFFECTIVE"
    status_code = 422


class RawDataRequiredError(GxPError):
    """Analyst completion was attempted while a required test definition still has no recorded result
    (QC-FR-031)."""

    code = "RAW_DATA_REQUIRED"
    status_code = 422


# Document 28 (SPEC-QMS-003) §16's stable error registry.


class NcrScopeRequiredError(GxPError):
    code = "NCR_SCOPE_REQUIRED"
    status_code = 422


class SegregationRequiredError(GxPError):
    code = "SEGREGATION_REQUIRED"
    status_code = 409


class DispositionNotAllowedError(GxPError):
    code = "DISPOSITION_NOT_ALLOWED"
    status_code = 422


class UseAsIsNotAuthorizedError(GxPError):
    code = "USE_AS_IS_NOT_AUTHORIZED"
    status_code = 409


class ReworkRouteRequiredError(GxPError):
    code = "REWORK_ROUTE_REQUIRED"
    status_code = 409


class ReinspectionRequiredError(GxPError):
    code = "REINSPECTION_REQUIRED"
    status_code = 409


class NcrClosureBlockedError(GxPError):
    code = "NCR_CLOSURE_BLOCKED"
    status_code = 409


# Document 24 (SPEC-QC-002) §9's stable error registry.


class LimsMappingNotFoundError(GxPError):
    code = "LIMS_MAPPING_NOT_FOUND"
    status_code = 404


class LimsMethodMismatchError(GxPError):
    code = "LIMS_METHOD_MISMATCH"
    status_code = 422


class LimsUomInvalidError(GxPError):
    code = "LIMS_UOM_INVALID"
    status_code = 422


class LimsDuplicateEventError(GxPError):
    code = "LIMS_DUPLICATE_EVENT"
    status_code = 409


class LimsResultVersionStaleError(GxPError):
    code = "LIMS_RESULT_VERSION_STALE"
    status_code = 409


class LimsSampleUnknownError(GxPError):
    code = "LIMS_SAMPLE_UNKNOWN"
    status_code = 404


# Document 29 (SPEC-QMS-004) §16's stable error registry.


class ChangeImpactIncompleteError(GxPError):
    code = "CHANGE_IMPACT_INCOMPLETE"
    status_code = 409


class RegulatoryReviewRequiredError(GxPError):
    code = "REGULATORY_REVIEW_REQUIRED"
    status_code = 409


class ValidationIncompleteError(GxPError):
    code = "VALIDATION_INCOMPLETE"
    status_code = 409


class TrainingIncompleteError(GxPError):
    code = "TRAINING_INCOMPLETE"
    status_code = 409


class ChangeNotApprovedError(GxPError):
    code = "CHANGE_NOT_APPROVED"
    status_code = 409


class EffectiveDateBlockedError(GxPError):
    code = "EFFECTIVE_DATE_BLOCKED"
    status_code = 409


# Document 25 (SPEC-QC-003) §11's stable error registry. Document 25 also declares RETEST_LIMIT_REACHED
# and OOS_RELEASE_BLOCK_ACTIVE; no class exists for either here since no code path this pass throws them
# (SG-074 -- no numeric retest-count policy value exists anywhere in the baseline; release-engine blocker
# wiring is cross-module, out of scope this pass) -- same "don't register a code nothing raises" discipline
# as every prior module.


class OosAlreadyExistsError(GxPError):
    code = "OOS_ALREADY_EXISTS"
    status_code = 409


class OriginalResultRequiredError(GxPError):
    code = "ORIGINAL_RESULT_REQUIRED"
    status_code = 422


class LabCauseEvidenceRequiredError(GxPError):
    code = "LAB_CAUSE_EVIDENCE_REQUIRED"
    status_code = 422


class RetestNotAuthorizedError(GxPError):
    code = "RETEST_NOT_AUTHORIZED"
    status_code = 409


class ResampleNotAuthorizedError(GxPError):
    code = "RESAMPLE_NOT_AUTHORIZED"
    status_code = 409


# InvestigationIncompleteError (code INVESTIGATION_INCOMPLETE) is reused from Document 26's registry
# above -- OOS-FR-005's "no investigation activity recorded yet" is the same class of precondition.


class ImpactAssessmentRequiredError(GxPError):
    code = "IMPACT_ASSESSMENT_REQUIRED"
    status_code = 409


class QaApprovalRequiredError(GxPError):
    code = "QA_APPROVAL_REQUIRED"
    status_code = 409


class OotRuleNotReleasedError(GxPError):
    code = "OOT_RULE_NOT_RELEASED"
    status_code = 422


# Document 30 (SPEC-QMS-005) §16's stable error registry.


class DocumentReviewIncompleteError(GxPError):
    code = "DOCUMENT_REVIEW_INCOMPLETE"
    status_code = 409


class DocumentSignatureRequiredError(GxPError):
    code = "DOCUMENT_SIGNATURE_REQUIRED"
    status_code = 428


class EffectivePrerequisitesIncompleteError(GxPError):
    code = "EFFECTIVE_PREREQUISITES_INCOMPLETE"
    status_code = 409


class DocumentVersionObsoleteError(GxPError):
    code = "DOCUMENT_VERSION_OBSOLETE"
    status_code = 409


class ControlledCopyConflictError(GxPError):
    code = "CONTROLLED_COPY_CONFLICT"
    status_code = 409


# Document 31 (SPEC-QMS-006) §16's stable error registry. TRAINING_REQUIRED, TRAINING_EXPIRED,
# ASSESSMENT_FAILED, QUALIFICATION_REQUIRED and QUALIFICATION_EXPIRED have no class here since no code
# path this pass throws them (SG-088 -- the platform-wide execution gate is cross-module and out of
# scope), the same "don't register a code nothing raises" discipline as SG-074's OOS codes.


class TrainerNotQualifiedError(GxPError):
    code = "TRAINER_NOT_QUALIFIED"
    status_code = 409


class WaiverNotAuthorizedError(GxPError):
    code = "WAIVER_NOT_AUTHORIZED"
    status_code = 409


# Document 21 (SPEC-MAT-002C) §6's declared error registry. Status codes chosen by matching precedent:
# state/eligibility rejections use 409 (like INVALID_TRANSITION), input validation uses 422 (like
# VALIDATION_FAILED), a missing-required-auth-type uses 428 (like MISSING_SIGNATURE).
class WrongMaterialError(GxPError):
    code = "WRONG_MATERIAL"
    status_code = 422


class LotIneligibleError(GxPError):
    code = "LOT_INELIGIBLE"
    status_code = 409


class ContainerIneligibleError(GxPError):
    code = "CONTAINER_INELIGIBLE"
    status_code = 409


class BalanceIneligibleError(GxPError):
    code = "BALANCE_INELIGIBLE"
    status_code = 409


class ReadingUnstableError(GxPError):
    code = "READING_UNSTABLE"
    status_code = 409


class WeightOutOfToleranceError(GxPError):
    code = "WEIGHT_OUT_OF_TOLERANCE"
    status_code = 422


class ManualFallbackNotAllowedError(GxPError):
    code = "MANUAL_FALLBACK_NOT_ALLOWED"
    status_code = 409


class VerifierRequiredError(GxPError):
    code = "VERIFIER_REQUIRED"
    status_code = 428


class SourceQuantityInsufficientError(GxPError):
    code = "SOURCE_QUANTITY_INSUFFICIENT"
    status_code = 422


class ScarSourceRequiredError(GxPError):
    code = "SCAR_SOURCE_REQUIRED"
    status_code = 422


class SupplierResponseIncompleteError(GxPError):
    code = "SUPPLIER_RESPONSE_INCOMPLETE"
    status_code = 422


class ScarReviewRejectedError(GxPError):
    code = "SCAR_REVIEW_REJECTED"
    status_code = 409


class EffectivenessRequiredError(GxPError):
    code = "EFFECTIVENESS_REQUIRED"
    status_code = 409


class SupplierSourceSuspendedError(GxPError):
    code = "SUPPLIER_SOURCE_SUSPENDED"
    status_code = 409


# Document 22 (SPEC-MAT-002D) §6's declared error registry.
class BatchMismatchError(GxPError):
    code = "BATCH_MISMATCH"
    status_code = 409


class QuantityExceedsAvailableError(GxPError):
    code = "QUANTITY_EXCEEDS_AVAILABLE"
    status_code = 422


class ReturnConditionReviewRequiredError(GxPError):
    code = "RETURN_CONDITION_REVIEW_REQUIRED"
    status_code = 409


class AdjustmentApprovalRequiredError(GxPError):
    code = "ADJUSTMENT_APPROVAL_REQUIRED"
    status_code = 409


class DestructionNotAuthorizedError(GxPError):
    code = "DESTRUCTION_NOT_AUTHORIZED"
    status_code = 409


class ReconciliationFailedError(GxPError):
    code = "RECONCILIATION_FAILED"
    status_code = 422


class ErpPostingPendingError(GxPError):
    code = "ERP_POSTING_PENDING"
    status_code = 409


# Document 33 (SPEC-QMS-008) §16's stable error registry. RISK_REVIEW_OVERDUE has no class here since no
# code path this pass throws it (no background due/expiry scheduler exists anywhere in this codebase yet)
# -- same "don't register a code nothing raises" discipline as SG-074/SG-088.


class RiskMethodNotReleasedError(GxPError):
    code = "RISK_METHOD_NOT_RELEASED"
    status_code = 422


class RiskInputIncompleteError(GxPError):
    code = "RISK_INPUT_INCOMPLETE"
    status_code = 422


class ResidualRiskReviewRequiredError(GxPError):
    code = "RESIDUAL_RISK_REVIEW_REQUIRED"
    status_code = 409


class RiskAcceptanceNotAuthorizedError(GxPError):
    code = "RISK_ACCEPTANCE_NOT_AUTHORIZED"
    status_code = 409


# Document 34 (SPEC-QMS-009) §16's stable error registry.


class AuditorSodConflictError(GxPError):
    code = "AUDITOR_SOD_CONFLICT"
    status_code = 409


class AuditScopeIncompleteError(GxPError):
    code = "AUDIT_SCOPE_INCOMPLETE"
    status_code = 422


class FindingResponseRequiredError(GxPError):
    code = "FINDING_RESPONSE_REQUIRED"
    status_code = 409


class FindingVerificationRequiredError(GxPError):
    code = "FINDING_VERIFICATION_REQUIRED"
    status_code = 409


class AuditClosureBlockedError(GxPError):
    code = "AUDIT_CLOSURE_BLOCKED"
    status_code = 409


# Document 35 (SPEC-QMS-010) §17's stable error registry.


class ComplaintProductUnresolvedError(GxPError):
    code = "COMPLAINT_PRODUCT_UNRESOLVED"
    status_code = 422


class InvestigationDecisionRequiredError(GxPError):
    code = "INVESTIGATION_DECISION_REQUIRED"
    status_code = 409


class NoInvestigationRationaleRequiredError(GxPError):
    code = "NO_INVESTIGATION_RATIONALE_REQUIRED"
    status_code = 422


class ReportabilityAssessmentRequiredError(GxPError):
    code = "REPORTABILITY_ASSESSMENT_REQUIRED"
    status_code = 409


class ComplaintClosureBlockedError(GxPError):
    code = "COMPLAINT_CLOSURE_BLOCKED"
    status_code = 409


# Document 36 (SPEC-QMS-011) §17's stable error registry.


class FieldActionScopeRequiredError(GxPError):
    code = "FIELD_ACTION_SCOPE_REQUIRED"
    status_code = 422


# ReportabilityAssessmentRequiredError (code REPORTABILITY_ASSESSMENT_REQUIRED) is reused from Document
# 35's registry above -- FAR-FR-006's "reportability must be assessed before approval" is the same class
# of precondition.


class CommunicationNotApprovedError(GxPError):
    code = "COMMUNICATION_NOT_APPROVED"
    status_code = 409


class ReconciliationIncompleteError(GxPError):
    code = "RECONCILIATION_INCOMPLETE"
    status_code = 409


# EffectivenessRequiredError (code EFFECTIVENESS_REQUIRED) is reused from Document 32's registry above --
# FAR-FR-013's "effectiveness check missing before closure" is the same class of precondition.


class FieldActionClosureBlockedError(GxPError):
    code = "FIELD_ACTION_CLOSURE_BLOCKED"
    status_code = 409


# Document 37 (SPEC-QMS-012) §16's stable error registry.


class MetricDefinitionNotReleasedError(GxPError):
    code = "METRIC_DEFINITION_NOT_RELEASED"
    status_code = 422


class MetricSourceIncompleteError(GxPError):
    code = "METRIC_SOURCE_INCOMPLETE"
    status_code = 422


class SnapshotStaleError(GxPError):
    code = "SNAPSHOT_STALE"
    status_code = 409


class EffectivenessCriterionRequiredError(GxPError):
    code = "EFFECTIVENESS_CRITERION_REQUIRED"
    status_code = 422


class EffectivenessInconclusiveError(GxPError):
    code = "EFFECTIVENESS_INCONCLUSIVE"
    status_code = 422


class ManagementPackageFrozenError(GxPError):
    code = "MANAGEMENT_PACKAGE_FROZEN"
    status_code = 409


# Document 38 (SPEC-EQP-001) §16 stable error codes.
class EquipmentNotQualifiedError(GxPError):
    code = "EQUIPMENT_NOT_QUALIFIED"
    status_code = 403


class CalibrationExpiredError(GxPError):
    code = "CALIBRATION_EXPIRED"
    status_code = 409


class MaintenanceDueError(GxPError):
    code = "MAINTENANCE_DUE"
    status_code = 409


class EquipmentOutOfServiceError(GxPError):
    code = "EQUIPMENT_OUT_OF_SERVICE"
    status_code = 409


class PostMaintenanceVerificationRequiredError(GxPError):
    code = "POST_MAINTENANCE_VERIFICATION_REQUIRED"
    status_code = 409


class CalibrationOotImpactRequiredError(GxPError):
    code = "CALIBRATION_OOT_IMPACT_REQUIRED"
    status_code = 409


class EquipmentClassMismatchError(GxPError):
    code = "EQUIPMENT_CLASS_MISMATCH"
    status_code = 422


# Document 39 (SPEC-EQP-002) §16 stable error codes.
class CleaningRequiredError(GxPError):
    code = "CLEANING_REQUIRED"
    status_code = 409


class DirtyHoldExceededError(GxPError):
    code = "DIRTY_HOLD_EXCEEDED"
    status_code = 409


class CleanHoldExpiredError(GxPError):
    code = "CLEAN_HOLD_EXPIRED"
    status_code = 409


class CleaningVerificationFailedError(GxPError):
    code = "CLEANING_VERIFICATION_FAILED"
    status_code = 409


class LineClearanceRequiredError(GxPError):
    code = "LINE_CLEARANCE_REQUIRED"
    status_code = 409


class PreviousBatchIdentityPresentError(GxPError):
    code = "PREVIOUS_BATCH_IDENTITY_PRESENT"
    status_code = 409


class WrongEquipmentInstalledError(GxPError):
    code = "WRONG_EQUIPMENT_INSTALLED"
    status_code = 422


# Document 41 (SPEC-EQP-004) §16 stable error codes.
class EmProgramNotEffectiveError(GxPError):
    code = "EM_PROGRAM_NOT_EFFECTIVE"
    status_code = 409


class EmLocationInvalidError(GxPError):
    code = "EM_LOCATION_INVALID"
    status_code = 422


class EmInstrumentIneligibleError(GxPError):
    code = "EM_INSTRUMENT_INELIGIBLE"
    status_code = 422


class EmDataGapError(GxPError):
    code = "EM_DATA_GAP"
    status_code = 409


class EmActionLimitExceededError(GxPError):
    code = "EM_ACTION_LIMIT_EXCEEDED"
    status_code = 409


class EmAreaNotReadyError(GxPError):
    code = "EM_AREA_NOT_READY"
    status_code = 409


class EmReviewRequiredError(GxPError):
    code = "EM_REVIEW_REQUIRED"
    status_code = 409


# Document 42 (SPEC-EQP-005) §16 stable error codes.
class CycleProfileNotEffectiveError(GxPError):
    code = "CYCLE_PROFILE_NOT_EFFECTIVE"
    status_code = 409


class SterilizerIneligibleError(GxPError):
    code = "STERILIZER_INELIGIBLE"
    status_code = 422


class LoadPatternInvalidError(GxPError):
    code = "LOAD_PATTERN_INVALID"
    status_code = 422


class CycleParameterFailedError(GxPError):
    code = "CYCLE_PARAMETER_FAILED"
    status_code = 409


class CycleReviewRequiredError(GxPError):
    code = "CYCLE_REVIEW_REQUIRED"
    status_code = 409


class FilterIntegrityFailedError(GxPError):
    code = "FILTER_INTEGRITY_FAILED"
    status_code = 409


class SterileStatusExpiredError(GxPError):
    code = "STERILE_STATUS_EXPIRED"
    status_code = 409


class ReprocessingAuthorizationRequiredError(GxPError):
    code = "REPROCESSING_AUTHORIZATION_REQUIRED"
    status_code = 409


# Document 40 (SPEC-EQP-003) §16 stable error codes. ASEPTIC_OPERATOR_NOT_QUALIFIED is declared in the
# spec but not raised anywhere this pass -- no personnel-qualification entity exists in this codebase to
# check against (same restraint as Document 38's unenforced MUT-FR-007 qualification gate), see SPEC_GAP.
class AsepticAreaNotReadyError(GxPError):
    code = "ASEPTIC_AREA_NOT_READY"
    status_code = 409


class SterileComponentIneligibleError(GxPError):
    code = "STERILE_COMPONENT_INELIGIBLE"
    status_code = 422


class SterilizationStatusInvalidError(GxPError):
    code = "STERILIZATION_STATUS_INVALID"
    status_code = 422


class AsepticHoldTimeExceededError(GxPError):
    code = "ASEPTIC_HOLD_TIME_EXCEEDED"
    status_code = 409


class UnplannedInterventionReviewRequiredError(GxPError):
    code = "UNPLANNED_INTERVENTION_REVIEW_REQUIRED"
    status_code = 409


class AsepticEnvironmentExcursionError(GxPError):
    code = "ASEPTIC_ENVIRONMENT_EXCURSION"
    status_code = 409


# Document 43 (SPEC-EDGE-001) §4 declared error codes -- only the ones a server-side-only build actually
# raises (CONFIG_SIGNATURE_INVALID/PLUGIN_UNSUPPORTED/SOURCE_MAPPING_NOT_FOUND/NORMALIZATION_FAILED/
# UOM_INCOMPATIBLE/BUFFER_STORAGE_FAILURE/UPSTREAM_UNAVAILABLE/HEALTH_POST_FAILED/COMMAND_PROFILE_DISABLED/
# INTERLOCK_DENIED all belong to the on-prem gateway runtime this pass does not build -- no class here,
# same "don't register a code nothing raises" discipline as SG-074/SG-088).
class EnrollmentTokenInvalidError(GxPError):
    code = "ENROLLMENT_TOKEN_INVALID"
    status_code = 422


class DuplicateGatewayError(GxPError):
    code = "DUPLICATE_GATEWAY"
    status_code = 409


class CertRotationFailedError(GxPError):
    code = "CERT_ROTATION_FAILED"
    status_code = 409


# Document 48 (SPEC-ERP-001) declared error registry (docs/generated/00_PROJECT_OUTLINE.md / traceability).
# ERP_RECONCILIATION_MISMATCH has no class here -- it is surfaced as an outbox event
# (ReconciliationMismatchDetected) on a created IntegrationReconciliationDifference row, never as a
# rejection thrown back at a caller, same "don't register a code nothing raises" discipline as SG-074/088.
class ErpInstanceInvalidError(GxPError):
    code = "ERP_INSTANCE_INVALID"
    status_code = 422


class ErpCapabilityUnsupportedError(GxPError):
    """ERP-ARC-003: the resolved adapter does not declare support for the requested operation."""

    code = "ERP_CAPABILITY_UNSUPPORTED"
    status_code = 422


class ErpMappingNotFoundError(GxPError):
    code = "ERP_MAPPING_NOT_FOUND"
    status_code = 404


class ErpMappingAmbiguousError(GxPError):
    """MDS-FR-008: fuzzy/name-based matching found more than one plausible internal candidate -- proposes
    nothing automatically, always requires human disambiguation."""

    code = "ERP_MAPPING_AMBIGUOUS"
    status_code = 409


class ErpMappingConflictError(GxPError):
    code = "ERP_MAPPING_CONFLICT"
    status_code = 409


class ErpExternalConflictError(GxPError):
    """INT-FR-007/010: same idempotency key or inbound external_event_id resubmitted with a different
    payload hash -- reused for both the outbound command ledger and the inbound event ledger (same class
    of integrity conflict, ERP_EXTERNAL_CONFLICT covers both per Document 48's declared registry)."""

    code = "ERP_EXTERNAL_CONFLICT"
    status_code = 409


class ErpThrottledError(GxPError):
    """INT-FR-022: the per-instance/operation circuit breaker is OPEN -- the caller must wait for the
    breaker's half-open probe window rather than dispatching now."""

    code = "ERP_THROTTLED"
    status_code = 429


class ErpAuthFailedError(GxPError):
    """ERP-ARC-028: the resolved ErpInstance has no usable credential for its declared auth_method."""

    code = "ERP_AUTH_FAILED"
    status_code = 401


# Document 47 (SPEC-EDGE-005) §3 declared error registry -- only the ones this server-side-only build
# actually raises (COMMAND_INTERLOCK_DENIED belongs to the on-prem `executeMachineCommandAtEdge()` this
# pass does not build -- no class here, same "don't register a code nothing raises" discipline as
# SG-074/SG-088).
class MappingValidationIncompleteError(GxPError):
    code = "MAPPING_VALIDATION_INCOMPLETE"
    status_code = 422


class BatchContextAmbiguousError(GxPError):
    code = "BATCH_CONTEXT_AMBIGUOUS"
    status_code = 409


class MappingNotEffectiveError(GxPError):
    code = "MAPPING_NOT_EFFECTIVE"
    status_code = 422


class SourceNotAllowedError(GxPError):
    code = "SOURCE_NOT_ALLOWED"
    status_code = 422


class FreshnessFailedError(GxPError):
    code = "FRESHNESS_FAILED"
    status_code = 422


class CommandNotAllowedError(GxPError):
    code = "COMMAND_NOT_ALLOWED"
    status_code = 422


# --- Document 54 (SPEC-DDCP-001) stable errors, §10 -----------------------------------------------


class ProfileSchemaInvalidError(GxPError):
    code = "PROFILE_SCHEMA_INVALID"
    status_code = 422


class ProfileReleaseBlockedError(GxPError):
    code = "PROFILE_RELEASE_BLOCKED"
    status_code = 422


class PfsProfileNotEffectiveError(GxPError):
    code = "PFS_PROFILE_NOT_EFFECTIVE"
    status_code = 422


class BulkNotReleasedError(GxPError):
    code = "BULK_NOT_RELEASED"
    status_code = 422


class PrimaryComponentNotReleasedError(GxPError):
    code = "PRIMARY_COMPONENT_NOT_RELEASED"
    status_code = 422


class LineNotReadyError(GxPError):
    code = "LINE_NOT_READY"
    status_code = 409


class SterileFiltrationRequiredError(GxPError):
    code = "STERILE_FILTRATION_REQUIRED"
    status_code = 422


class FillProgramMismatchError(GxPError):
    code = "FILL_PROGRAM_MISMATCH"
    status_code = 422


class FillIpcOosError(GxPError):
    code = "FILL_IPC_OOS"
    status_code = 422


# NOTE: `FilterIntegrityFailedError` (code FILTER_INTEGRITY_FAILED) is defined once, above with the
# sterile/filter errors at status 409. An accidental duplicate here (status 422) was removed 2026-09-10 —
# it shadowed the 409 definition and was raised by nothing. If a future Document 42 filtration-integrity
# check needs it, it already exists at 409.


class CciTestFailedError(GxPError):
    code = "CCI_TEST_FAILED"
    status_code = 422


class DeviceTestFailedError(GxPError):
    code = "DEVICE_TEST_FAILED"
    status_code = 422


class PfsReconciliationFailedError(GxPError):
    code = "PFS_RECONCILIATION_FAILED"
    status_code = 422


class DuplicateSourceEventError(GxPError):
    """PFS-FR-010/INT-style replay guard: the same machine/edge source_event_id resubmitted for
    production_count_ledger."""

    code = "DUPLICATE_SOURCE_EVENT"
    status_code = 409


class FillStageIncompleteError(GxPError):
    code = "FILL_STAGE_INCOMPLETE"
    status_code = 422


class BulkHoldTimeExceededError(GxPError):
    """PFS-FR-007. Distinct from the equipment module's AsepticHoldTimeExceededError/DirtyHoldExceededError
    -- this codebase's own precedent is a per-module hold-time error, not a shared one."""

    code = "BULK_HOLD_TIME_EXCEEDED"
    status_code = 409


class ConstituentAttributeMissingError(GxPError):
    """PFS-FR-016."""

    code = "CONSTITUENT_ATTRIBUTE_MISSING"
    status_code = 422


class ConstituentTypeMismatchError(GxPError):
    """PFS-FR-028: no implicit DRUG/BIOLOGIC equivalency against a profile's declared requirement."""

    code = "CONSTITUENT_TYPE_MISMATCH"
    status_code = 422


# Document 55 (SPEC-DDCP-002) §9 stable errors. SG-150.
class InjectorProfileNotEffectiveError(GxPError):
    code = "INJECTOR_PROFILE_NOT_EFFECTIVE"
    status_code = 422


class ContainerAlreadyUsedError(GxPError):
    code = "CONTAINER_ALREADY_USED"
    status_code = 409


class WrongContainerDevicePairingError(GxPError):
    code = "WRONG_CONTAINER_DEVICE_PAIRING"
    status_code = 422


class AssemblyProgramMismatchError(GxPError):
    code = "ASSEMBLY_PROGRAM_MISMATCH"
    status_code = 422


class UnitReconciliationFailedError(GxPError):
    code = "INJECTOR_RECONCILIATION_FAILED"
    status_code = 422


# Document 56 (SPEC-DDCP-003) §9 stable errors. SG-150.
class InhalationProfileNotEffectiveError(GxPError):
    code = "INHALATION_PROFILE_NOT_EFFECTIVE"
    status_code = 422


class EnvironmentNotReadyError(GxPError):
    code = "ENVIRONMENT_NOT_READY"
    status_code = 409


class FillRouteMismatchError(GxPError):
    code = "FILL_ROUTE_MISMATCH"
    status_code = 422


class ClosureTestFailedError(GxPError):
    code = "CLOSURE_TEST_FAILED"
    status_code = 422


class BlendHoldTimeExceededError(GxPError):
    """INH-FR-019. Distinct from BulkHoldTimeExceededError (Document 54) -- this codebase's own precedent
    is a per-module hold-time error, not a shared one."""

    code = "BLEND_HOLD_TIME_EXPIRED"
    status_code = 409


class InhalerReconciliationFailedError(GxPError):
    code = "INHALER_RECONCILIATION_FAILED"
    status_code = 422


class DoseUnitBindingAlreadyUsedError(GxPError):
    """INH-FR-011: same 'prevent duplicate/cross-use' discipline as Document 55/57's own unit-binding
    errors (ContainerAlreadyUsedError/DeviceToCoatingBindingAlreadyUsedError)."""

    code = "DOSE_UNIT_BINDING_ALREADY_USED"
    status_code = 409


# Document 57 (SPEC-DDCP-004) §10 stable errors. SG-150.
class CoatedDeviceProfileNotEffectiveError(GxPError):
    code = "COATED_DEVICE_PROFILE_NOT_EFFECTIVE"
    status_code = 422


class SubstrateNotReleasedError(GxPError):
    code = "SUBSTRATE_NOT_RELEASED"
    status_code = 422


class CoatingDrugNotReleasedError(GxPError):
    code = "COATING_DRUG_NOT_RELEASED"
    status_code = 422


class CoatingHoldTimeExpiredError(GxPError):
    """COAT-FR-003 (coating solution hold time). Distinct from BulkHoldTimeExceededError/
    BlendHoldTimeExceededError -- this codebase's own per-module hold-time error precedent."""

    code = "COATING_HOLD_TIME_EXPIRED"
    status_code = 409


class CoatingEnvironmentNotReadyError(GxPError):
    code = "COATING_ENVIRONMENT_NOT_READY"
    status_code = 409


class CoatingProgramMismatchError(GxPError):
    code = "COATING_PROGRAM_MISMATCH"
    status_code = 422


class CoatingParameterExcursionError(GxPError):
    code = "COATING_PARAMETER_EXCURSION"
    status_code = 409


class DrugLoadingOosError(GxPError):
    code = "DRUG_LOADING_OOS"
    status_code = 422


class SterilizationInteractionReviewRequiredError(GxPError):
    code = "STERILIZATION_INTERACTION_REVIEW_REQUIRED"
    status_code = 422


class CoatingReconciliationFailedError(GxPError):
    code = "COATING_RECONCILIATION_FAILED"
    status_code = 422


class DeviceToCoatingBindingAlreadyUsedError(GxPError):
    """COAT-FR-010: same "prevent duplicate/cross-use" discipline as Document 55's ContainerAlreadyUsedError."""

    code = "DEVICE_COATING_BINDING_ALREADY_USED"
    status_code = 409


class ReleaseBlockersPresentError(GxPError):
    code = "RELEASE_BLOCKERS_PRESENT"
    status_code = 422
    status_code = 422


# ---------------------------------------------------------------------------------------------------
# Document 58 (SPEC-PM-001) -- Postmarket Surveillance, Safety Case & Signal Management. Stable error
# codes taken verbatim from Document 58 # 14.
# ---------------------------------------------------------------------------------------------------


class PmsSourceInvalidError(GxPError):
    code = "PMS_SOURCE_INVALID"
    status_code = 422


class PmsCaseDuplicateSourceError(GxPError):
    """PMS-FR-002: a (source_record_type, source_record_id, source_record_version) already has a
    linked safety_case -- createSafetyCaseLink() is not itself the duplicate-detection engine
    (findProbableDuplicates() is); this specifically guards against re-linking the exact same source
    record/version twice."""

    code = "PMS_CASE_DUPLICATE_SOURCE"
    status_code = 409


class ProductUnresolvedError(GxPError):
    """PMS-FR-005: raised only where a caller asserts resolution without supplying enough identity to
    resolve it -- an honestly unresolved case is data (identity_resolution_state=UNKNOWN_QUEUE), not
    an error; this fires when resolveMarketedProduct() is asked to mark RESOLVED without identifiers."""

    code = "PRODUCT_UNRESOLVED"
    status_code = 422


class SafetyClassificationIncompleteError(GxPError):
    code = "SAFETY_CLASSIFICATION_INCOMPLETE"
    status_code = 422


class ExpectednessReferenceRequiredError(GxPError):
    code = "EXPECTEDNESS_REFERENCE_REQUIRED"
    status_code = 422


class MedicalReviewRequiredError(GxPError):
    code = "MEDICAL_REVIEW_REQUIRED"
    status_code = 422


class SignalScopeInvalidError(GxPError):
    code = "SIGNAL_SCOPE_INVALID"
    status_code = 422


class PeriodicDatasetNotReproducibleError(GxPError):
    code = "PERIODIC_DATASET_NOT_REPRODUCIBLE"
    status_code = 422


class StaleSafetyCaseVersionError(GxPError):
    """PMS-FR-016/# 12: a follow-up received during review must force the reviewer to refresh -- this
    is the same optimistic-concurrency contract as StaleVersionError, given its own Document-58-specific
    stable code per # 14."""

    code = "STALE_SAFETY_CASE_VERSION"
    status_code = 409


class ThreatScopeInvalidError(GxPError):
    """Document 61 (SPEC-SEC-001) `createThreatModelVersion()`'s own named error code (# 4)."""

    code = "THREAT_SCOPE_INVALID"
    status_code = 422


class SecurityRiskInputIncompleteError(GxPError):
    """SEC-THR-014: `calculateSecurityRisk()`/`acceptResidualSecurityRisk()` require complete
    impact/likelihood/rating inputs, and residual risk must exist before it can be accepted."""

    code = "SECURITY_RISK_INPUT_INCOMPLETE"
    status_code = 422


class TokenInvalidError(GxPError):
    """Document 62 (SPEC-SEC-002) `validateIdentityToken()`'s own named error code (# 4): wrong issuer,
    wrong audience, expired, bad signature, clock-skew-out-of-bounds or malformed."""

    code = "TOKEN_INVALID"
    status_code = 401


class FreshAuthenticationRequiredError(GxPError):
    """Document 62 (SPEC-SEC-002) `requireFreshAuthentication()`'s own named error code (# 4):
    IAMSEC-FR-008 step-up for a sensitive security/admin operation, independent of Part 11 signing."""

    code = "FRESH_AUTH_REQUIRED"
    status_code = 428


class AdminCommandNotAllowedError(GxPError):
    """Document 63 (SPEC-SEC-003) `executeControlledAdminCommand()`'s own named error code (# 4):
    PAM-FR-018 -- the command_code is not on the allowlist."""

    code = "ADMIN_COMMAND_NOT_ALLOWED"
    status_code = 422


class PrivilegedAccessDeniedError(GxPError):
    """Document 63 (SPEC-SEC-003) `evaluatePrivilegedGrant()`'s own named error code (# 4): no active
    grant authorizes this subject/operation/resource/time."""

    code = "PRIVILEGED_ACCESS_DENIED"
    status_code = 403


# ---------------------------------------------------------------------------------------------------
# Document 64 (SPEC-SEC-004) -- Application, API, UI & Secure Runtime Engineering. Stable error codes
# taken verbatim from Document 64 # 4's function-contract catalogue (the "Events / Errors / Tests"
# column). REPLAY_DETECTED already exists in docs/generated/14_ERROR_CODE_REGISTRY.md (SPEC-GXP-001)
# without a class here -- given one now because verifyWebhook() actually raises it.
# ---------------------------------------------------------------------------------------------------


class AccessDeniedError(GxPError):
    """`authorizeObjectAccess()` -- APPSEC-FR-001/002/003/013/028/029. Server-side object/function/
    property authorization failed (BOLA/BFLA/IDOR/mass-assignment/graph-traversal). Deliberately does
    not echo the requested resource identity back in the message (APPSEC-FR-005 least disclosure)."""

    code = "ACCESS_DENIED"
    status_code = 403


class RequestSchemaInvalidError(GxPError):
    """`validateRequestSchema()` -- APPSEC-FR-004/023. Typed-schema validation rejected the request:
    unknown property, wrong type, length/range/enum/format violation, or unsafe deserialization shape."""

    code = "REQUEST_SCHEMA_INVALID"
    status_code = 422


class UnsafeContentRejectedError(GxPError):
    """`sanitizeRichText()` -- APPSEC-FR-008/022. Rich-text/expression input contained a construct the
    allowlist sanitizer will not neutralise safely (script element, event handler, javascript: URI,
    template/code-evaluation token)."""

    code = "UNSAFE_CONTENT_REJECTED"
    status_code = 422


class SsrfDestinationBlockedError(GxPError):
    """`validateOutboundDestination()` -- APPSEC-FR-011. The requested outbound URL/host is not on the
    `outbound_destination` allowlist, or resolves to a private / loopback / link-local / cloud-metadata
    address. Fail closed (Document 64 # 10)."""

    code = "SSRF_DESTINATION_BLOCKED"
    status_code = 403


class FileTypeBlockedError(GxPError):
    """`validateFileUpload()` -- APPSEC-FR-012. Declared/sniffed content type, extension or size is
    outside the upload policy."""

    code = "FILE_TYPE_BLOCKED"
    status_code = 422


class MalwareDetectedError(GxPError):
    """`validateFileUpload()` -- APPSEC-FR-012. The upload matched a malware signature (EICAR test
    vector in this build) and was quarantined, not stored in the evidence path."""

    code = "MALWARE_DETECTED"
    status_code = 422


class RateLimitedError(GxPError):
    """`enforceRateLimit()` -- APPSEC-FR-014/015. The subject/client/IP/operation bucket is exhausted.
    Reuses the RATE_LIMITED code already in the registry (SPEC-EDGE-002)."""

    code = "RATE_LIMITED"
    status_code = 429


class WebhookAuthFailedError(GxPError):
    """`verifyWebhook()` -- APPSEC-FR-020. Signature/mTLS/timestamp verification of an inbound webhook
    failed against the provider's `webhook_profile`."""

    code = "WEBHOOK_AUTH_FAILED"
    status_code = 401


class ReplayDetectedError(GxPError):
    """`verifyWebhook()` / inbound message replay guard -- APPSEC-FR-007/011/014/019/020. The same
    external message id / delivery id was already accepted, or its timestamp is outside the profile's
    replay window. Code REPLAY_DETECTED is already in docs/generated/14_ERROR_CODE_REGISTRY.md."""

    code = "REPLAY_DETECTED"
    status_code = 409


class DeprecatedApiBlockedError(GxPError):
    """API versioning -- APPSEC-FR-016/027. A deprecated endpoint version past its sunset date was
    called. Emits `DeprecatedAPIUsed` telemetry regardless; blocks only past sunset."""

    code = "DEPRECATED_API_BLOCKED"
    status_code = 410


# ---------------------------------------------------------------------------------------------------
# Document 65 (SPEC-SEC-005) -- Secrets Management, PKI, Cryptography & Key Lifecycle. Codes from the
# function-contract catalogue (# 4) and # 9 events.
# ---------------------------------------------------------------------------------------------------


class SecretAccessDeniedError(GxPError):
    """`resolveSecret()` -- KEY-FR-004. The requesting service identity is not on the secret's
    `consumer_identities` allowlist, or the secret ref is not ACTIVE."""

    code = "SECRET_ACCESS_DENIED"
    status_code = 403


class SecretRotationFailedError(GxPError):
    """`rotateSecret()` -- KEY-FR-005/006. New credential material invalid, consumer validation failed,
    or the secret is not in a rotatable state."""

    code = "SECRET_ROTATION_FAILED"
    status_code = 409


class FieldEncryptionFailedError(GxPError):
    """`encryptSensitiveField()` -- KEY-FR-014. No key available for the tenant/data-class context, or
    the crypto profile does not resolve."""

    code = "FIELD_ENCRYPTION_FAILED"
    status_code = 500


class FieldDecryptionDeniedError(GxPError):
    """`decryptSensitiveField()` -- KEY-FR-014. Access context not authorized for this field/data class,
    wrong key version/tenant key, or AEAD authentication failed (tamper)."""

    code = "FIELD_DECRYPTION_DENIED"
    status_code = 403


class TrustAllProhibitedError(GxPError):
    """KEY-FR-025 / Document 65 # 14: an attempt to configure an 'accept-all' / 'trust-all' certificate
    mode for a production trust store. Never permitted."""

    code = "TRUST_ALL_PROHIBITED"
    status_code = 422


class CryptoHealthFailedError(GxPError):
    """`crypto-health` / KEY-FR-028: a critical key or certificate is missing, expired or inaccessible.
    Fail safe (Document 65 # 10)."""

    code = "CRYPTO_HEALTH_FAILED"
    status_code = 503


class SecretAlreadyExistsError(GxPError):
    """`createSecret()` -- a `secret_metadata` row already uses this `secret_ref` (unique per KEY-FR-002)."""

    code = "SECRET_ALREADY_EXISTS"
    status_code = 409


class SecretProviderNotIntegratedError(GxPError):
    """`fetchSecretValue()` -- SG-126: the secret is registered against a provider (K8S_SECRET, AWS_SM,
    VAULT) this build has no live client for. Fails closed rather than fabricating a fetch; ON_PREM is
    the only provider with a real value-fetch path in this build."""

    code = "SECRET_PROVIDER_NOT_INTEGRATED"
    status_code = 501


class SecretValueNotSetError(GxPError):
    """`fetchSecretValue()` -- the secret is a registered ON_PREM secret but no value has been stored
    for it yet (`setSecretValue()` was never called)."""

    code = "SECRET_VALUE_NOT_SET"
    status_code = 404


# ---------------------------------------------------------------------------------------------------
# Document 66 (SPEC-SEC-006) -- Network, Tenant, Deployment Isolation & Zero-Trust. Codes from # 4.
# ---------------------------------------------------------------------------------------------------


class NetworkFlowNotAllowedError(GxPError):
    """`validateServiceFlow()` -- NET-FR-002/004. The intended source->destination/protocol/port
    connection is not in the approved `network_flow_definition` catalogue for the deployment profile."""

    code = "NETWORK_FLOW_NOT_ALLOWED"
    status_code = 403


class TenantScopeMismatchError(GxPError):
    """`verifyTenantScopePropagation()` -- NET-FR-010/011. A downstream job/event/context does not carry
    a tenant/site scope compatible with the originating AuthContext."""

    code = "TENANT_SCOPE_MISMATCH"
    status_code = 409


class WorkloadHardeningFailedError(GxPError):
    """`validateDeploymentHardening()` -- NET-FR-017. A workload manifest/security context violates the
    hardening baseline (root user, privilege escalation, host mounts, added capabilities, host network)."""

    code = "WORKLOAD_HARDENING_FAILED"
    status_code = 422


class SegmentationControlFailedError(GxPError):
    """`testForbiddenNetworkPath()` -- NET-FR-029. A network path that must remain blocked was reachable
    (or the simulation shows it would be)."""

    code = "SEGMENTATION_CONTROL_FAILED"
    status_code = 409


# ---------------------------------------------------------------------------------------------------
# Document 67 (SPEC-SEC-007) -- Security Logging, Monitoring, Incident Response & Forensics. Codes
# from # 4 and the mandatory-negative catalogue.
# ---------------------------------------------------------------------------------------------------


class IncidentContainmentNotAllowedError(GxPError):
    """`executeIncidentContainment()` -- MON-FR-015. The requested containment command is not on the
    allowlist, or the incident is not in a state that accepts containment."""

    code = "INCIDENT_CONTAINMENT_NOT_ALLOWED"
    status_code = 422


class GxpImpactAssessmentRequiredError(GxPError):
    """`closeSecurityIncident()` -- MON-FR-016 / Document 67 # 14: an incident touching regulated data
    cannot be closed before its GxP-impact assessment is recorded."""

    code = "GXP_IMPACT_ASSESSMENT_REQUIRED"
    status_code = 409


class IncidentEvidenceRequiredError(GxPError):
    """`closeSecurityIncident()` -- MON-FR-014: closure requires at least the containment/recovery
    evidence the policy names for the incident's severity."""

    code = "INCIDENT_EVIDENCE_REQUIRED"
    status_code = 409


class SodIndependenceRequiredError(GxPError):
    """A dynamic (action-level) independence rule was violated at completion time: the actor performing
    an independent verify / approve / close is the same person who performed / authored / owns the
    record (Document 107 second control type, SIG-FR-018). Distinct from `SOD_CONFLICT`, which is the
    standing-role-pair check evaluated up front."""

    code = "SOD_INDEPENDENCE_REQUIRED"
    status_code = 409


# ---------------------------------------------------------------------------------------------------
# Document 68 (SPEC-SEC-008) -- Secure SDLC, Supply Chain, SBOM, Vulnerability & Release Security.
# Codes from # 4 and the mandatory-negative catalogue.
# ---------------------------------------------------------------------------------------------------


class UntrustedArtifactError(GxPError):
    """`verifyDeploymentArtifact()` -- SDLC-FR-011. Signature, digest, SBOM linkage, provenance or
    approved-release check failed for a deployment artifact."""

    code = "UNTRUSTED_ARTIFACT"
    status_code = 409


class SecurityReleaseBlockedError(GxPError):
    """`evaluateSecurityReleaseGate()` -- SDLC-FR-030. Unresolved critical/high findings or failed
    security-control tests block the release per policy."""

    code = "SECURITY_RELEASE_BLOCKED"
    status_code = 409


class VulnerabilityExceptionConflictError(GxPError):
    """`approveVulnerabilityException()` -- SDLC-FR-021. An active, non-expired exception decision
    already exists for this vulnerability, or the vulnerability is already remediated/closed."""

    code = "VULNERABILITY_EXCEPTION_CONFLICT"
    status_code = 409


# =================================================================================================
# Document 69 (SPEC-DATA-001) -- Enterprise Data Ownership, Persistence Topology & Data Lineage.
# =================================================================================================


class DataOwnerUnknownError(GxPError):
    """`resolveDataOwner()` -- DATA-FR-001. No `data_ownership_registry` row declares an authoritative
    owner/store for the requested entity type. The registry is fail-closed: an unknown entity type is
    an error, never a guessed owner (AG-15)."""

    code = "DATA_OWNER_UNKNOWN"
    status_code = 404


class ForbiddenDataOwnerWriteError(GxPError):
    """`assertAuthoritativeWriteAllowed()` -- DATA-FR-025 / DATA-FR-030. A service tried to write an
    authoritative entity it does not own per the `data_ownership_registry`. Only the owning service's
    migration/command package may alter its authoritative tables."""

    code = "FORBIDDEN_DATA_OWNER_WRITE"
    status_code = 403


class ProjectionStaleError(GxPError):
    """`getProjectionFreshness()` -- DATA-FR-008. The projection's last projected source version lags
    the authoritative source beyond the freshness policy; a regulated action must re-read the
    authoritative record rather than trust this projection."""

    code = "PROJECTION_STALE"
    status_code = 409


class CrossStoreMismatchError(GxPError):
    """`verifyCrossStoreConsistency()` -- DATA-FR-028. A projection/integration target diverged from
    the authoritative source (count/version/hash); the projection must be rebuilt from the
    authoritative source."""

    code = "CROSS_STORE_MISMATCH"
    status_code = 409


# =================================================================================================
# Document 70 (SPEC-DATA-002) -- PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency.
# =================================================================================================


class OutboxDuplicateError(GxPError):
    """`appendOutboxEvent()` -- PG-FR-011/014. An outbox row with the same idempotency/event identity
    already exists in this transaction's scope."""

    code = "OUTBOX_DUPLICATE"
    status_code = 409


class PartitionCreateFailedError(GxPError):
    """`createTimePartition()` -- PG-FR-016/030. Creating/attaching a time partition failed (overlap,
    bad bounds, or the parent is not a partitioned table)."""

    code = "PARTITION_CREATE_FAILED"
    status_code = 500


class PartitionGapDetectedError(GxPError):
    """`verifyPartitionCoverage()` -- PG-FR-030. A partitioned table has no partition covering the
    current or an imminent future time window; writes would fail visibly."""

    code = "PARTITION_GAP_DETECTED"
    status_code = 409


class DatabaseIntegrityFailureError(GxPError):
    """`runDatabaseIntegrityCheck()` -- PG-FR-023/032. A checksum / amcheck / managed integrity check
    reported corruption."""

    code = "DB_INTEGRITY_FAILURE"
    status_code = 500


class PrimaryUnavailableError(GxPError):
    """`getPrimaryConsistencyRead()` -- PG-FR-031. The authoritative primary is unreachable; a
    regulated command/signature read must fail closed rather than fall back to a replica."""

    code = "PRIMARY_UNAVAILABLE"
    status_code = 503


class ReplicaTooStaleError(GxPError):
    """`runReadReplicaQuery()` -- PG-FR-031. Replica lag exceeds the caller's declared max_staleness;
    the query is refused rather than served stale data."""

    code = "REPLICA_TOO_STALE"
    status_code = 503


class DeadlockDetectedError(GxPError):
    """PG-FR-012. A PostgreSQL deadlock (SQLSTATE 40P01) was detected; the caller should retry the
    whole transaction with backoff a bounded number of times."""

    code = "DEADLOCK_DETECTED"
    status_code = 409


# =================================================================================================
# Document 72 (SPEC-DATA-004) -- Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle.
# =================================================================================================


class EvidenceUploadDeniedError(GxPError):
    """`stageEvidenceUpload()` -- OBJ-FR-003/015. The upload request failed authorization or the
    declared type/size policy before any object was staged."""

    code = "EVIDENCE_UPLOAD_DENIED"
    status_code = 403


class EvidenceHashMismatchError(GxPError):
    """`finalizeEvidenceUpload()` / `verifyEvidenceIntegrity()` -- OBJ-FR-002/016. The stored object's
    digest does not match the expected/declared hash; the object is not promoted / is flagged."""

    code = "EVIDENCE_HASH_MISMATCH"
    status_code = 409


class EvidenceObjectImmutableError(GxPError):
    """OBJ-FR-004/017. An attempt was made to overwrite or edit a finalized evidence object in place;
    a correction must create a new object/version."""

    code = "EVIDENCE_OBJECT_IMMUTABLE"
    status_code = 409


class EvidenceNotFinalizedError(GxPError):
    """OBJ-FR-004. The evidence object is still STAGED/QUARANTINE and cannot be referenced by a
    manifest, downloaded through the ordinary path, or held."""

    code = "EVIDENCE_NOT_FINALIZED"
    status_code = 409


class EvidenceAccessDeniedError(GxPError):
    """`authorizeEvidenceDownload()` -- OBJ-FR-011/012/030. The subject is not authorized for this
    evidence object / purpose; no download token is issued and no bucket listing is exposed."""

    code = "EVIDENCE_ACCESS_DENIED"
    status_code = 403


class EvidenceMissingError(GxPError):
    """`verifyEvidenceIntegrity()` -- OBJ-FR-023. Evidence metadata exists but the backing object is
    not present in the store; a critical integrity signal and a release/inspection blocker."""

    code = "EVIDENCE_MISSING"
    status_code = 409


class EvidencePurgeBlockedError(GxPError):
    """`purgeExpiredEvidence()` -- OBJ-FR-018/019. Purge was blocked by an active legal hold, an
    unexpired retention window, or a still-referencing manifest."""

    code = "EVIDENCE_PURGE_BLOCKED"
    status_code = 409


# =================================================================================================
# Document 73 (SPEC-DATA-005) -- NATS/JetStream Event Bus, Transactional Outbox & Async Contracts.
# =================================================================================================


class OutboxPublishStateConflictError(GxPError):
    """`markOutboxPublished()` -- EVT-FR-004. The outbox row was already marked published (or its
    state changed) since the publisher claimed it; the publish result is not applied twice."""

    code = "OUTBOX_PUBLISH_STATE_CONFLICT"
    status_code = 409


class EventAlreadyProcessedError(GxPError):
    """`consumeEventIdempotently()` -- EVT-FR-005/006. This (consumer, event_id) pair already has a
    recorded result in `consumer_inbox`; the caller should treat this as a successful no-op, not an
    error to surface to an end user (raised here so call sites can choose)."""

    code = "EVENT_ALREADY_PROCESSED"
    status_code = 409


class HandlerFailedError(GxPError):
    """`consumeEventIdempotently()` -- EVT-FR-026. The consumer handler raised a business-validation
    failure (as opposed to a transient dependency failure, which is not wrapped here and should be
    retried by the caller)."""

    code = "HANDLER_FAILED"
    status_code = 422


class EventSchemaBreakingChangeError(GxPError):
    """`verifyEventSchemaCompatibility()` -- EVT-FR-011/012. The proposed schema removes/narrows a
    field a consumer may depend on; CI blocks the change unless a new event/schema version is used."""

    code = "EVENT_SCHEMA_BREAKING_CHANGE"
    status_code = 409


# =================================================================================================
# Document 75 (SPEC-DATA-007) -- Caching, Search, Read Models, Reporting Projections & Analytics.
# =================================================================================================


class SearchFilterNotAllowedError(GxPError):
    """`authorizeSearchQuery()` -- READ-FR-022. A requested filter/sort field is not on the
    per-index-type allowlist; prevents abusive arbitrary queries and accidental PII exposure."""

    code = "SEARCH_FILTER_NOT_ALLOWED"
    status_code = 422


class SearchResultStaleError(GxPError):
    """`fetchSearchResultDetail()` -- READ-FR-011/013. The indexed document's source version lags the
    authoritative record beyond policy; the caller must re-fetch the authoritative detail rather than
    treat the search hit as current (raised only when the caller opts into strict freshness)."""

    code = "SEARCH_RESULT_STALE"
    status_code = 409


# =================================================================================================
# Document 76 (SPEC-DATA-008) -- Backup, Restore, Point-in-Time Recovery & Disaster Recovery.
# =================================================================================================


class RecoveryValidationFailedError(GxPError):
    """`validateRecoveredPlatform()` -- DR-FR-025. The recovered environment failed a mandatory
    smoke/integrity/security/GxP check; the platform is not declared healthy for regulated work."""

    code = "RECOVERY_VALIDATION_FAILED"
    status_code = 409


class RestoreTestFailedError(GxPError):
    """`executePostgresRestoreTest()` -- DR-FR-016/017. The restore into the isolated target failed an
    application-level integrity check (row counts, checksums, PITR target not reached)."""

    code = "RESTORE_TEST_FAILED"
    status_code = 409


class EvidenceRestoreMismatchError(GxPError):
    """`reconcileEvidenceAfterRestore()` -- DR-FR-019. A restored evidence metadata row's object
    reference/hash could not be verified against the object store after restore."""

    code = "EVIDENCE_RESTORE_MISMATCH"
    status_code = 409


# =================================================================================================
# Document 77 (SPEC-DATA-009) -- Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade.
# =================================================================================================


class DeploymentPrerequisiteFailedError(GxPError):
    """`validateDeploymentPrerequisites()` -- DEP-FR-028/029. A required pre-install/pre-upgrade check
    (DB reachable, migrations at head, no default secret, clock sane) failed; install/upgrade must not
    proceed."""

    code = "DEPLOYMENT_PREREQUISITE_FAILED"
    status_code = 409


# =================================================================================================
# Document 87 (SPEC-VAL-009) / Document 95 (SPEC-VAL-017) -- Data Migration & Validation Summary
# Report / Go-Live Authorization. `app/modules/validation/commands_migration.py` and
# `commands_vsr.py` reference these but the classes were never added when the module was built
# (WP-11/12/14 bookkeeping desync, see docs/generated/18_SPEC_GAPS.md history).
# =================================================================================================


class LegacyTraceMissingError(GxPError):
    """`verifyLegacyRecordTrace()` -- MIGV-FR-007/021, Document 87 §4's declared `LEGACY_TRACE_MISSING`
    error name. Neither the identity map, the rejected-record ledger, nor the controlled legacy-archive
    reference has a trace for the requested legacy id."""

    code = "LEGACY_TRACE_MISSING"
    status_code = 404


class GoLiveNotReadyError(GxPError):
    """`authorizeValidatedRelease()` -- VSR-FR-015/019. An APPROVED validated-release-authorization
    decision was requested while at least one go-live gate/blocker is still open."""

    code = "GO_LIVE_NOT_READY"
    status_code = 409


class ValidationSummaryBlockedError(GxPError):
    """VSR-FR-006/019. A CONDITIONAL/APPROVED validation summary report decision names a condition
    that would bypass a critical GxP control, or the record still carries an open critical
    deviation/exception -- either blocks the decision regardless of who signs it."""

    code = "VALIDATION_SUMMARY_BLOCKED"
    status_code = 409


class DeploymentValidationMismatchError(GxPError):
    """`checkDeploymentValidationMatch()` -- VSR-FR-016/017/022, Document 95 §13. The artifact digests
    or configuration fingerprint submitted for production promotion do not match the exact release the
    VSR validated; the technical gate fails closed rather than promoting with an impact note."""

    code = "DEPLOYMENT_VALIDATION_MISMATCH"
    status_code = 409


class PostGoLiveVerificationFailedError(GxPError):
    """VSR-FR-024. A FAIL post-go-live verification outcome was recorded without a rollback, incident
    or change reference -- a bare failure is not permitted; it must route to a controlled path."""

    code = "POST_GO_LIVE_VERIFICATION_FAILED"
    status_code = 422


# =================================================================================================
# Document 105 (SPEC-AI-001) -- AI Governance for Regulated Manufacturing. `app/modules/ai_governance/
# commands.py` references these but the classes were never added when the module was built (see
# SG-168's history in docs/generated/18_SPEC_GAPS.md -- the entry itself was lost to the same
# status-file lost-update race as the module's tracked build stage).
# =================================================================================================


class AIUseCaseNotActiveError(GxPError):
    """AI-FR-001/002. An advisory request targeted an AI use case that is not in the ACTIVE state;
    only an active, registered use case may serve advisory requests."""

    code = "AI_USE_CASE_NOT_ACTIVE"
    status_code = 409


class AIModelNotApprovedError(GxPError):
    """AI-FR-007/021. The requested model deployment is not an approved production deployment for
    this use case; an unapproved model/version cannot serve regulated-adjacent advisory traffic."""

    code = "AI_MODEL_NOT_APPROVED"
    status_code = 403


class AIToolNotAllowlistedError(GxPError):
    """AI-FR-009/010. The requested tool call is not on the use case's explicit read/write allowlist,
    or exceeds its declared risk class; production AI tools are read-only unless individually
    approved."""

    code = "AI_TOOL_NOT_ALLOWLISTED"
    status_code = 403


class AIDataClassificationDeniedError(GxPError):
    """AI-FR-011/031/032. The retrieved record's data classification is not approved for this use
    case, is outside the caller's own tenant/site scope, or is a security secret -- secrets are never
    included in AI context regardless of use-case configuration."""

    code = "AI_DATA_CLASSIFICATION_DENIED"
    status_code = 403


class AIPromptInjectionBlockedError(GxPError):
    """AI-FR-014/025. Retrieved or user-supplied content matched a known instruction-override
    pattern; the content is untrusted and cannot redefine system/tool policy, so the escalation this
    content would have triggered is blocked."""

    code = "AI_PROMPT_INJECTION_BLOCKED"
    status_code = 403


class AIOutputInvalidError(GxPError):
    """AI-FR-018/019. No usable result was produced -- the provider was unavailable or timed out, it
    returned no structured output, or the output failed schema validation. The system reports
    insufficient evidence rather than fabricating or guessing an output."""

    code = "AI_OUTPUT_INVALID"
    status_code = 422


class AIEvaluationCriticalFailureError(GxPError):
    """AI-FR-022/024. A release-gate evaluation against the use case's versioned evaluation set
    produced a BLOCK decision -- a critical failure class (e.g. prompt-injection or unsafe-tool-call
    rate) is not permitted to hide behind an acceptable overall average."""

    code = "AI_EVALUATION_CRITICAL_FAILURE"
    status_code = 409


class AIRegulatedDecisionBoundaryError(GxPError):
    """AI-FR-003/004. A proposed AI action falls inside the regulated-decision boundary the AI is
    never permitted to cross autonomously (sign, release, disposition, approve, alter audit, submit a
    report); the action must instead go through the normal authorization/signature/Mutation Gateway
    path with a qualified human as the actor."""

    code = "AI_REGULATED_DECISION_BOUNDARY"
    status_code = 403
