"""Document 95 (SPEC-VAL-017) Mutation Gateway command handlers -- Validation Summary Report,
Release-to-Production & Go-Live Authorization.

Signature policy (Document 106 / function catalogue FN-0917..FN-0928):
  * Row 169 -- `POST /validation/v1/summary-reports/{id}/approve` requires an `Approved` signature
    from an independent QA Releaser (the "Module approver role (QA Manager / Head of Quality)" signer
    class, resolved to `QA Releaser` -- the same mapping WP-12 uses), reason mandatory, signer
    independent of the validation recommendation author (VSR-FR-014 SoD).
  * Row 166 -- `POST /validation/v1/releases/{id}/authorize` requires a `Released` signature from a
    QA Releaser independent of every production performer on the record.
  * Row 167 -- `POST /validation/v1/releases/{id}/deployment-check` requires a `Released` signature
    from a QA Releaser independent of every production performer. The Document 95 §4 caller ("Deploy
    pipeline") triggers the check; a human QA Releaser authorizes it -- a service identity can never
    satisfy a signature requirement (SIG-FR-023).

  * `POST /validation/v1/summary-reports` (generation) is implemented **unsigned / RBAC-gated only**,
    following the function catalogue (FN-0923 marks it "evaluate via policy map", NOT "SIGNATURE
    POLICY LOOKUP REQUIRED", unlike FN-0925/0926/0927). Document 106 row 168 does list an `Approved`
    signature by a "Regulatory Affairs authorized submitter" for this path -- a signer class with no
    corresponding platform role, and inconsistent with every other validation module where authoring/
    generation is unsigned and only approve/authorize is signed. That conflict is raised as **SG-170**
    (non-blocking): the real Part 11 sign point for the VSR is `approve` (row 169, resolvable).

  * `GET /validation/v1/releases/{id}/go-live-readiness` and `record_post_go_live_verification()`
    carry no Document 106 row -- RBAC-gated only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.signature import service as signature_service
from app.modules.validation.models_wp14 import ValidatedReleaseAuthorization, ValidationSummaryReport
from app.modules.validation.shared import (
    finalize,
    receipt_from_existing,
    resolve_signature,
    verify_evidence_refs,
    verify_reauth_and_consume,
)
from app.mutation.errors import (
    DeploymentValidationMismatchError,
    GoLiveNotReadyError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    PostGoLiveVerificationFailedError,
    StaleVersionError,
    ValidationFailedError,
    ValidationSummaryBlockedError,
)
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_VSR = "validation_summary_report"
RECORD_TYPE_RELEASE_AUTH = "validated_release_authorization"


def create_challenge_hash(cmd) -> str:
    """The signed-CREATE challenge is bound to the command's *content* -- the volatile transport
    fields (`challenge_id`, `reauth_password`, `idempotency_key`) are excluded so the caller can
    compute the identical hash before the challenge_id exists."""
    return sha256_hex(
        cmd.model_dump(mode="json", exclude={"challenge_id", "reauth_password", "idempotency_key"})
    )


async def _apply_signature_for_create(session: AsyncSession, cmd, actor_user_id: uuid.UUID) -> uuid.UUID:
    """Signed-CREATE step-up: the new aggregate has no id when the challenge is made, so the challenge
    is bound to a hash of the command payload + version 1 (same shape as
    `app/modules/ai_governance/commands.py::_apply_signature`). Fresh step-up + single-use challenge
    consumption + signature creation, all in the caller's transaction.
    """
    from app.core.security import verify_password
    from app.modules.iam.models import User

    actor = await session.get(User, actor_user_id)
    if actor is None or not cmd.reauth_password or not verify_password(cmd.reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
        record_version=1, record_hash=create_challenge_hash(cmd),
    )
    signature = await signature_service.sign(
        session, challenge=challenge, auth_context={"method": "password_reauth"}
    )
    return signature.id

_RECOMMENDATIONS = ("RECOMMENDED", "RECOMMENDED_WITH_CONDITIONS", "NOT_RECOMMENDED")
_DECISIONS = ("APPROVED", "CONDITIONAL", "REJECTED")

# Go-live prerequisite gate names (VSR-FR-015). A gate value must be the string "PASS" to clear.
_GO_LIVE_GATES = (
    "training", "production_config", "backups", "interfaces", "support", "monitoring", "cutover_tasks",
)


# =====================================================================================================
# generateValidationSummaryReport() -- FN-0917  (unsigned; SG-170)
# =====================================================================================================

class GenerateValidationSummaryReportCommand(CommandEnvelope):
    report_number: str
    release_ref: str
    environment: str
    intended_use: str
    config_scope: str
    evidence_manifest_ref: str
    recommendation: str
    baselines: dict = {}
    execution_summary: dict = {}
    traceability_status: dict = {}         # {critical_gaps: [...], orphans: [...]}
    deviations: list[dict] = []            # [{ref, state: OPEN|CLOSED|ACCEPTED, critical: bool, release_impact}]
    security_summary: dict = {}            # {qualification, findings: [...], exceptions: [...], critical_open: bool}
    performance_summary: dict = {}
    dr_summary: dict = {}                  # {restore_qualification, achieved_rpo, achieved_rto, qualified: bool}
    migration_summary: dict | None = None
    part11_summary: dict = {}
    customer_responsibilities: list[dict] = []
    known_limitations: list[dict] = []
    customer: str | None = None
    site_id: uuid.UUID | None = None
    evidence_manifest: list[dict] = []
    retention_class: str | None = None


async def generate_validation_summary_report(
    session: AsyncSession, cmd: GenerateValidationSummaryReportCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.recommendation not in _RECOMMENDATIONS:
        raise ValidationFailedError("recommendation is not a recognised value", recommendation=cmd.recommendation)
    if not cmd.release_ref.strip():
        raise ValidationFailedError("release_ref is required (VSR-FR-002/017)")
    if not cmd.evidence_manifest_ref.strip():
        raise ValidationFailedError("evidence_manifest_ref is required -- the VSR references an immutable package (VSR-FR-020)")
    # VSR-FR-013 / Document 95 §13: known limitations are never omitted. An empty list is only valid
    # when explicitly declared so via a single sentinel entry.
    if not cmd.known_limitations:
        raise ValidationFailedError(
            "known_limitations must be stated explicitly (VSR-FR-013); pass [{\"limitation\": \"none\"}] if there are none"
        )
    await verify_evidence_refs(session, cmd.evidence_manifest)

    row = ValidationSummaryReport(
        site_id=cmd.site_id or site_id, report_number=cmd.report_number, release_ref=cmd.release_ref,
        customer=cmd.customer, environment=cmd.environment, intended_use=cmd.intended_use,
        config_scope=cmd.config_scope, baselines=cmd.baselines, execution_summary=cmd.execution_summary,
        traceability_status=cmd.traceability_status, deviations=cmd.deviations,
        security_summary=cmd.security_summary, performance_summary=cmd.performance_summary,
        dr_summary=cmd.dr_summary, migration_summary=cmd.migration_summary,
        part11_summary=cmd.part11_summary, customer_responsibilities=cmd.customer_responsibilities,
        known_limitations=cmd.known_limitations, recommendation=cmd.recommendation,
        recommendation_by_user_id=actor_user_id, recommendation_at=datetime.now(timezone.utc),
        evidence_manifest_ref=cmd.evidence_manifest_ref, retention_class=cmd.retention_class,
        state="DRAFT", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_VSR, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"report_number": row.report_number, "release_ref": row.release_ref,
                   "recommendation": row.recommendation},
        event_type="ValidationSummaryGenerated", expected_version=None,
        command_type="GenerateValidationSummaryReport", site_id=cmd.site_id or site_id,
    )


# =====================================================================================================
# evaluateGoLiveReadiness() -- FN-0918  (pure compute; GET surface, no write, no event)
# =====================================================================================================

def evaluate_go_live_readiness(vsr: ValidationSummaryReport, gates: dict) -> dict:
    """VSR-FR-015: return the go-live prerequisite checklist and blockers. Pure function -- no DB
    write, no event. `gates` is the caller-supplied evidence map {gate_name: "PASS" | <reason>}.
    """
    prerequisites = []
    blockers = []
    for name in _GO_LIVE_GATES:
        value = gates.get(name)
        status = "PASS" if value == "PASS" else "FAIL"
        prerequisites.append({"name": name, "status": status,
                              "detail": None if status == "PASS" else (value or "not evidenced")})
        if status != "PASS":
            blockers.append(name)

    # VSR-FR-006/007/009: an open critical deviation, an unresolved critical security finding, or a
    # missing DR qualification is itself a go-live blocker.
    if any(d.get("critical") and d.get("state") == "OPEN" for d in (vsr.deviations or [])):
        blockers.append("open_critical_deviation")
    if (vsr.security_summary or {}).get("critical_open"):
        blockers.append("open_critical_security_finding")
    if (vsr.dr_summary or {}).get("qualified") is False:
        blockers.append("dr_not_qualified")

    return {
        "vsr_id": str(vsr.id), "release_ref": vsr.release_ref, "recommendation": vsr.recommendation,
        "prerequisites": prerequisites, "blockers": blockers, "ready": not blockers,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


# =====================================================================================================
# approveValidationSummary() -- FN-0919  (signed; Document 106 row 169)
# =====================================================================================================

class ApproveValidationSummaryCommand(CommandEnvelope):
    report_id: uuid.UUID
    expected_version: int
    reason: str
    decision: str                          # APPROVED | CONDITIONAL | REJECTED
    decision_conditions: list[dict] = []   # [{condition, names_critical_control: bool}]
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_validation_summary(
    session: AsyncSession, cmd: ApproveValidationSummaryCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.decision not in _DECISIONS:
        raise ValidationFailedError("decision must be APPROVED, CONDITIONAL or REJECTED (VSR-FR-019)")
    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to approve a VSR (Document 106 row 169)")

    row = await session.get(ValidationSummaryReport, cmd.report_id)
    if row is None:
        raise NotFoundError("validation summary report not found")
    if row.state != "DRAFT":
        raise InvalidTransitionError("validation summary report is not DRAFT", current_state=row.state)
    if row.version != cmd.expected_version:
        raise StaleVersionError("VSR changed since this request was prepared", current_version=row.version)

    # VSR-FR-014 SoD: the QA/System-Owner authorizer is independent of the validation recommender.
    if actor_user_id == row.recommendation_by_user_id:
        raise ValidationFailedError(
            "the VSR approver must be independent of the validation recommendation author (VSR-FR-014, Document 106 row 169)"
        )

    if cmd.decision != "REJECTED":
        # VSR-FR-019: a condition cannot bypass a critical GxP control.
        if any(c.get("names_critical_control") for c in cmd.decision_conditions):
            raise ValidationSummaryBlockedError(
                "a CONDITIONAL/APPROVED VSR decision cannot carry a condition that names a critical GxP control (VSR-FR-019)"
            )
        # VSR-FR-006: an open critical exception blocks approval.
        if any(d.get("critical") and d.get("state") == "OPEN" for d in (row.deviations or [])):
            raise ValidationSummaryBlockedError("VSR has an open critical deviation/exception (VSR-FR-006)")
        if (row.security_summary or {}).get("critical_open"):
            raise ValidationSummaryBlockedError("VSR has an unresolved critical security finding (VSR-FR-007)")
    if cmd.decision == "APPROVED" and cmd.decision_conditions:
        raise ValidationFailedError("an APPROVED decision carries no conditions; use CONDITIONAL (VSR-FR-019)")
    if cmd.decision == "CONDITIONAL" and not cmd.decision_conditions:
        raise ValidationFailedError("a CONDITIONAL decision must record its conditions (VSR-FR-019)")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_VSR, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.decision = cmd.decision
    row.decision_conditions = cmd.decision_conditions
    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.signature_id = signature_id
    row.state = "APPROVED" if cmd.decision != "REJECTED" else "REJECTED"
    row.version += 1

    if row.state == "APPROVED":
        # Document 06 (VLT-FR-001): an approved VSR is a regulated final record referenced by the
        # release authorization (VSR-FR-020).
        from app.modules.vault import service as vault_service
        vault_obj = await vault_service.release_master(
            session, object_type=RECORD_TYPE_VSR, business_id=str(row.id), site_id=site_id,
            actor_user_id=actor_user_id,
            canonical_payload={
                "report_number": row.report_number, "release_ref": row.release_ref,
                "baselines": row.baselines, "execution_summary": row.execution_summary,
                "deviations": row.deviations, "known_limitations": row.known_limitations,
                "recommendation": row.recommendation, "decision": row.decision,
                "decision_conditions": row.decision_conditions,
                "evidence_manifest_ref": row.evidence_manifest_ref,
            },
        )
        row.vault_object_id = getattr(vault_obj, "id", None)

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_VSR, aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"state": "DRAFT"}, new_value={"state": row.state, "decision": row.decision},
        event_type="ValidationSummaryApproved", expected_version=cmd.expected_version,
        command_type="ApproveValidationSummary", site_id=site_id, signature_id=signature_id,
    )


# =====================================================================================================
# issueValidatedReleaseAuthorization() -- FN-0920  (signed; Document 106 row 166)
# =====================================================================================================

class IssueValidatedReleaseAuthorizationCommand(CommandEnvelope):
    vsr_id: uuid.UUID
    authorization_number: str
    environment: str
    config_fingerprint: str
    release_identity: dict                 # {image_digest, code_commit, sbom_ref, schema_version, migration_head, config_version}
    artifact_digests: dict
    decision: str                          # APPROVED | CONDITIONAL | REJECTED
    go_live_gates: dict                    # {gate_name: "PASS" | <reason>}
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str
    conditions: list[dict] = []            # [{condition, names_critical_control: bool}]
    production_performer_user_ids: list[str] = []
    site_id: uuid.UUID | None = None


async def issue_validated_release_authorization(
    session: AsyncSession, cmd: IssueValidatedReleaseAuthorizationCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.decision not in _DECISIONS:
        raise ValidationFailedError("decision must be APPROVED, CONDITIONAL or REJECTED (VSR-FR-019)")
    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to authorize a validated release (Document 106 row 166)")
    if not cmd.config_fingerprint.strip():
        raise ValidationFailedError("config_fingerprint is required (VSR-FR-016)")
    for key in ("image_digest", "schema_version", "migration_head", "config_version"):
        if not cmd.release_identity.get(key):
            raise ValidationFailedError(f"release_identity.{key} is required (VSR-FR-017)")

    vsr = await session.get(ValidationSummaryReport, cmd.vsr_id)
    if vsr is None:
        raise NotFoundError("validation summary report not found")
    if vsr.state != "APPROVED":
        raise InvalidTransitionError("the VSR is not APPROVED (VSR-FR-014)", current_state=vsr.state)

    # VSR-FR-014 SoD / Document 106 row 166: the authorizer is a QA Releaser independent of every
    # production performer on the record and of the validation recommender.
    performers = {str(u) for u in cmd.production_performer_user_ids}
    if str(actor_user_id) in performers:
        raise ValidationFailedError(
            "the release authorizer must be independent of every production performer (Document 106 row 166)"
        )
    if actor_user_id == vsr.recommendation_by_user_id:
        raise ValidationFailedError("the release authorizer must be independent of the validation recommender")

    readiness = evaluate_go_live_readiness(vsr, cmd.go_live_gates)

    if cmd.decision == "APPROVED" and readiness["blockers"]:
        raise GoLiveNotReadyError(
            "cannot issue an APPROVED validated release authorization over an unresolved go-live blocker (VSR-FR-015/019)",
            blockers=readiness["blockers"],
        )
    if cmd.decision != "REJECTED" and any(c.get("names_critical_control") for c in cmd.conditions):
        raise ValidationSummaryBlockedError(
            "a condition on a validated release authorization cannot name a critical GxP control (VSR-FR-019)"
        )
    if cmd.decision == "CONDITIONAL" and not cmd.conditions:
        raise ValidationFailedError("a CONDITIONAL authorization must record its conditions (VSR-FR-019)")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_RELEASE_AUTH, action="authorize")
    signature_id = None
    if policy.signature_required:
        signature_id = await _apply_signature_for_create(session, cmd, actor_user_id)

    row = ValidatedReleaseAuthorization(
        vsr_id=vsr.id, vsr_version=vsr.version, authorization_number=cmd.authorization_number,
        release_identity=cmd.release_identity, artifact_digests=cmd.artifact_digests,
        config_fingerprint=cmd.config_fingerprint, environment=cmd.environment,
        site_id=cmd.site_id or site_id, go_live_readiness=readiness, decision=cmd.decision,
        conditions=cmd.conditions, authorized_by_user_id=actor_user_id,
        authorized_at=datetime.now(timezone.utc), signature_id=signature_id,
        state="AUTHORIZED" if cmd.decision != "REJECTED" else "REJECTED", version=1,
        retention_class=vsr.retention_class,
    )
    session.add(row)
    await session.flush()

    # VSR-FR-015: the go-live readiness evaluation is itself a recorded event against the authorization
    # (evaluateGoLiveReadiness, FN-0918, has its own §7 GET surface but no dedicated write).
    await write_outbox_event(
        session, event_type="GoLiveReadinessEvaluated", aggregate_type=RECORD_TYPE_RELEASE_AUTH,
        aggregate_id=row.id, aggregate_version=1,
        payload={"ready": readiness["ready"], "blockers": readiness["blockers"]},
        correlation_id=uuid.uuid4(),
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_RELEASE_AUTH,
        aggregate_id=row.id, version=row.version, action="Released", actor_user_id=actor_user_id,
        reason=cmd.reason, old_value=None,
        new_value={"authorization_number": row.authorization_number, "decision": row.decision,
                   "config_fingerprint": row.config_fingerprint, "ready": readiness["ready"]},
        event_type="ValidatedReleaseAuthorized", expected_version=None,
        command_type="IssueValidatedReleaseAuthorization", site_id=cmd.site_id or site_id,
        signature_id=signature_id,
    )


# =====================================================================================================
# verifyDeploymentAgainstValidationRelease() -- FN-0921  (signed; Document 106 row 167)
# =====================================================================================================

class VerifyDeploymentAgainstValidationReleaseCommand(CommandEnvelope):
    authorization_id: uuid.UUID
    expected_version: int
    submitted_config_fingerprint: str
    submitted_artifact_digests: dict
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str
    production_performer_user_ids: list[str] = []


async def verify_deployment_against_validation_release(
    session: AsyncSession, cmd: VerifyDeploymentAgainstValidationReleaseCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required for a deployment check (Document 106 row 167)")

    row = await session.get(ValidatedReleaseAuthorization, cmd.authorization_id)
    if row is None:
        raise NotFoundError("validated release authorization not found")
    if row.state not in ("AUTHORIZED", "DEPLOYMENT_VERIFIED"):
        raise InvalidTransitionError(
            "the release authorization is not active (VSR-FR-022)", current_state=row.state
        )
    if row.decision == "REJECTED":
        raise InvalidTransitionError("the release authorization was REJECTED", current_state=row.state)
    if row.version != cmd.expected_version:
        raise StaleVersionError("release authorization changed since this request was prepared", current_version=row.version)
    if str(actor_user_id) in {str(u) for u in cmd.production_performer_user_ids}:
        raise ValidationFailedError(
            "the deployment check signer must be independent of every production performer (Document 106 row 167)"
        )

    # VSR-FR-016/017/022: compare the exact deployment against the validated release.
    fp_match = cmd.submitted_config_fingerprint == row.config_fingerprint
    digest_mismatches = [
        k for k, v in (row.artifact_digests or {}).items()
        if cmd.submitted_artifact_digests.get(k) != v
    ]
    extra_digests = [k for k in cmd.submitted_artifact_digests if k not in (row.artifact_digests or {})]
    matches = fp_match and not digest_mismatches and not extra_digests

    check = {
        "submitted_config_fingerprint": cmd.submitted_config_fingerprint,
        "config_fingerprint_match": fp_match, "digest_mismatches": digest_mismatches,
        "unexpected_digests": extra_digests, "matches": matches,
        "checked_by_user_id": str(actor_user_id), "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    if not matches:
        # Production promotion is tied to the exact validated release/configuration -- a mismatch fails
        # the technical gate; it is not promoted with an impact note (Document 95 §13).
        raise DeploymentValidationMismatchError(
            "deployment artifact digests / config fingerprint do not match the validated release (VSR-FR-016/017/022)",
            config_fingerprint_match=fp_match, digest_mismatches=digest_mismatches,
            unexpected_digests=extra_digests,
        )

    policy = await resolve_signature(session, record_type=RECORD_TYPE_RELEASE_AUTH, action="deployment_check")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )
    check["signature_id"] = str(signature_id) if signature_id else None

    row.deployment_check = check
    row.state = "DEPLOYMENT_VERIFIED"
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_RELEASE_AUTH,
        aggregate_id=row.id, version=row.version, action="Released", actor_user_id=actor_user_id,
        reason=cmd.reason, old_value={"state": "AUTHORIZED"},
        new_value={"state": "DEPLOYMENT_VERIFIED", "matches": True},
        event_type="DeploymentMatchesValidatedRelease", expected_version=cmd.expected_version,
        command_type="VerifyDeploymentAgainstValidationRelease", site_id=site_id, signature_id=signature_id,
    )


# =====================================================================================================
# recordPostGoLiveVerification() -- FN-0922  (unsigned; RBAC-gated only)
# =====================================================================================================

class RecordPostGoLiveVerificationCommand(CommandEnvelope):
    authorization_id: uuid.UUID
    expected_version: int
    outcome: str                           # PASS | FAIL
    smoke_results: list[dict] = []
    monitoring_results: list[dict] = []
    rollback_ref: str | None = None
    incident_ref: str | None = None
    change_ref: str | None = None
    notes: str | None = None


async def record_post_go_live_verification(
    session: AsyncSession, cmd: RecordPostGoLiveVerificationCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.outcome not in ("PASS", "FAIL"):
        raise ValidationFailedError("outcome must be PASS or FAIL")

    row = await session.get(ValidatedReleaseAuthorization, cmd.authorization_id)
    if row is None:
        raise NotFoundError("validated release authorization not found")
    if row.state not in ("DEPLOYMENT_VERIFIED", "GO_LIVE_VERIFIED"):
        raise InvalidTransitionError(
            "post-go-live verification requires a verified deployment (VSR-FR-023)", current_state=row.state
        )
    if row.version != cmd.expected_version:
        raise StaleVersionError("release authorization changed since this request was prepared", current_version=row.version)

    # VSR-FR-024: a failed post-go-live verification must route to the controlled rollback/incident/
    # change path -- it cannot be recorded as a bare failure.
    if cmd.outcome == "FAIL" and not (cmd.rollback_ref or cmd.incident_ref or cmd.change_ref):
        raise PostGoLiveVerificationFailedError(
            "a FAIL post-go-live verification must reference a controlled rollback / incident / change (VSR-FR-024)"
        )

    result = {
        "outcome": cmd.outcome, "smoke_results": cmd.smoke_results,
        "monitoring_results": cmd.monitoring_results, "rollback_ref": cmd.rollback_ref,
        "incident_ref": cmd.incident_ref, "change_ref": cmd.change_ref, "notes": cmd.notes,
        "recorded_by_user_id": str(actor_user_id), "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    row.post_go_live = result
    row.state = "GO_LIVE_VERIFIED" if cmd.outcome == "PASS" else "ROLLED_BACK"
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_RELEASE_AUTH,
        aggregate_id=row.id, version=row.version, action="StatusChanged", actor_user_id=actor_user_id,
        reason=cmd.notes, old_value={"state": "DEPLOYMENT_VERIFIED"},
        new_value={"state": row.state, "outcome": cmd.outcome},
        event_type="PostGoLiveVerificationCompleted", expected_version=cmd.expected_version,
        command_type="RecordPostGoLiveVerification", site_id=site_id,
    )
