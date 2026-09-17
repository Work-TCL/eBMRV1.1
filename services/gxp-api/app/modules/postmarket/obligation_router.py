"""Document 60 (SPEC-PM-003) REST surface, prefix `/postmarket/v1` (same surface as Document 58 -- both
are SPEC-PM-00x modules of WP-09's combined `postmarket` schema).

`addCorrectionRemovalScopeAmendment`, `placePostmarketLegalHold` and `getUnifiedRegulatoryCalendar` are
named functions/UI surfaces in Document 60's own contract catalogue but are missing from its terse 14-op
`# 12. APIs` list -- exposed here as extra operations (same precedent used for Document 58/59).
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.postmarket import obligation_commands as commands
from app.modules.postmarket.obligation_commands import _decision_content_hash, _field_action_reference_hash
from app.modules.postmarket.obligation_models import (
    ConstituentInformationShare,
    CorrectionRemovalRegulatoryRecord,
    PeriodicReportingCycle,
    RegulatoryObligation,
)
from app.modules.signature.service import chain_signatures_so_far, create_challenge, resolve_signature_requirement
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/postmarket/v1", tags=["postmarket-obligations"])


def _obligation_dict(o: RegulatoryObligation) -> dict:
    return {
        "id": str(o.id), "site_id": str(o.site_id), "obligation_type": o.obligation_type,
        "source_type": o.source_type, "source_id": str(o.source_id) if o.source_id else None,
        "source_version": o.source_version, "application_id": o.application_id,
        "rule_version_id": o.rule_version_id,
        "clock_start_at": o.clock_start_at.isoformat() if o.clock_start_at else None,
        "original_due_at": o.original_due_at.isoformat() if o.original_due_at else None,
        "current_due_at": o.current_due_at.isoformat() if o.current_due_at else None,
        "calendar_profile_id": o.calendar_profile_id, "details": o.details,
        "decision": o.decision, "decision_rationale": o.decision_rationale,
        "decision_by": str(o.decision_by) if o.decision_by else None,
        "decision_signature_id": str(o.decision_signature_id) if o.decision_signature_id else None,
        "deadline_override_evidence": o.deadline_override_evidence, "retention_basis": o.retention_basis,
        "legal_hold": o.legal_hold, "legal_hold_reason": o.legal_hold_reason,
        "legal_hold_authority": o.legal_hold_authority,
        "legal_hold_at": o.legal_hold_at.isoformat() if o.legal_hold_at else None,
        "state": o.state, "owner_subject_id": str(o.owner_subject_id) if o.owner_subject_id else None,
        "version": o.version, "created_at": o.created_at.isoformat(),
    }


def _share_dict(s: ConstituentInformationShare) -> dict:
    return {
        "id": str(s.id), "site_id": str(s.site_id), "safety_case_id": str(s.safety_case_id),
        "applicant_relationship_id": str(s.applicant_relationship_id),
        "applicant_relationship_version": s.applicant_relationship_version,
        "company_receipt_at": s.company_receipt_at.isoformat(), "due_at": s.due_at.isoformat(),
        "package_content": s.package_content, "package_digest": s.package_digest,
        "package_version": s.package_version,
        "shared_at": s.shared_at.isoformat() if s.shared_at else None,
        "shared_by": str(s.shared_by) if s.shared_by else None,
        "sharing_signature_id": str(s.sharing_signature_id) if s.sharing_signature_id else None,
        "delivery_evidence": s.delivery_evidence, "state": s.state, "version": s.version,
    }


def _correction_removal_dict(r: CorrectionRemovalRegulatoryRecord) -> dict:
    return {
        "id": str(r.id), "site_id": str(r.site_id), "field_action_reference": r.field_action_reference,
        "assessment_state": r.assessment_state, "regime": r.regime,
        "initiation_at": r.initiation_at.isoformat(), "due_at": r.due_at.isoformat() if r.due_at else None,
        "calendar_version": r.calendar_version, "required_facts": r.required_facts,
        "decision_by": str(r.decision_by) if r.decision_by else None,
        "decision_signature_id": str(r.decision_signature_id) if r.decision_signature_id else None,
        "scope_amendments": r.scope_amendments, "retention_class_code": r.retention_class_code,
        "assessment_approval_signatures": r.assessment_approval_signatures,
        "decision_approval_signatures": r.decision_approval_signatures,
        "state": r.state, "version": r.version,
    }


@router.get("/obligations/{obligation_id}")
async def get_obligation(
    obligation_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    obligation = await session.get(RegulatoryObligation, obligation_id)
    if obligation is None:
        raise NotFoundError("Regulatory obligation not found")
    await evaluate_policy(session, actor.user_id, action="regulatory_obligation.view", site_id=obligation.site_id)
    return _obligation_dict(obligation)


@router.get("/sharing/{share_id}")
async def get_sharing(
    share_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    share = await session.get(ConstituentInformationShare, share_id)
    if share is None:
        raise NotFoundError("Constituent information share not found")
    # No dedicated `.view` code exists for this entity -- reusing `.evaluate`, the same read-adjacent
    # reuse precedent as `evidence.download` for evidence metadata (see that module's GET for the pattern).
    await evaluate_policy(session, actor.user_id, action="constituent_information_share.evaluate", site_id=share.site_id)
    return _share_dict(share)


@router.get("/correction-removal/{record_id}")
async def get_correction_removal(
    record_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(CorrectionRemovalRegulatoryRecord, record_id)
    if record is None:
        raise NotFoundError("Correction/removal regulatory record not found")
    # No dedicated `.view` code exists for this entity -- reusing `.create`, same reuse precedent as above.
    await evaluate_policy(session, actor.user_id, action="correction_removal.create", site_id=record.site_id)
    return _correction_removal_dict(record)


@router.post("/applicant-relationships", response_model=MutationReceipt)
async def post_configure_applicant_relationship(
    cmd: commands.ConfigureApplicantRelationshipCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="applicant_relationship.configure", site_id=cmd.site_id)
        return await commands.configure_applicant_relationship(session, cmd, actor.user_id)


@router.post("/cases/{case_id}/part4-sharing:evaluate", response_model=MutationReceipt)
async def post_evaluate_part4_sharing(
    case_id: uuid.UUID, cmd: commands.EvaluatePart4SharingCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.safety_case_id != case_id:
        raise ValidationFailedError("case_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="constituent_information_share.evaluate", site_id=cmd.site_id)
        return await commands.evaluate_part4_information_sharing(session, cmd, actor.user_id)


@router.post("/sharing/{share_id}/package", response_model=MutationReceipt)
async def post_create_sharing_package(
    share_id: uuid.UUID, cmd: commands.CreateConstituentSharingPackageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.share_id != share_id:
        raise ValidationFailedError("share_id in path and body must match")
    async with session.begin():
        share = await session.get(ConstituentInformationShare, share_id)
        if share is None:
            raise NotFoundError("Constituent information share not found")
        await evaluate_policy(session, actor.user_id, action="constituent_information_share.package", site_id=share.site_id)
        return await commands.create_constituent_sharing_package(session, cmd, actor.user_id)


@router.post("/sharing/{share_id}/record-sent", response_model=MutationReceipt)
async def post_record_sharing_sent(
    share_id: uuid.UUID, cmd: commands.RecordConstituentInformationSharedCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.share_id != share_id:
        raise ValidationFailedError("share_id in path and body must match")
    async with session.begin():
        share = await session.get(ConstituentInformationShare, share_id)
        if share is None:
            raise NotFoundError("Constituent information share not found")
        await evaluate_policy(session, actor.user_id, action="constituent_information_share.record_sent", site_id=share.site_id)
        return await commands.record_constituent_information_shared(session, cmd, actor.user_id)


@router.post("/field-actions/{field_action_id}/correction-removal-assessment", response_model=MutationReceipt)
async def post_create_correction_removal_assessment(
    field_action_id: uuid.UUID, cmd: commands.CreateCorrectionRemovalAssessmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="correction_removal.create", site_id=cmd.site_id)
        return await commands.create_correction_removal_assessment(session, cmd, actor.user_id)


async def _create_chain_challenge(session: AsyncSession, *, record_type: str, record_id, content_hash: str, actor_user_id) -> dict:
    """SG-160 partial resolution (2026-09-14). Same shape as
    `vault/router.py::post_correction_signature_challenge()` -- chain position is derived from how many
    valid signatures this record already carries for `(record_type, record_id)`, never accepted from the
    caller (Document 106 section 13 test #5's "signature 2 issued before signature 1 exists" case)."""
    policy = await resolve_signature_requirement(session, record_type=record_type, action="sign")
    prior_signatures = await chain_signatures_so_far(session, record_type=record_type, record_id=record_id, record_version=1)
    position = len(prior_signatures) + 1
    if position > policy.signature_count:
        raise ValidationFailedError("This record has already collected every required signature", signature_count=policy.signature_count)
    if prior_signatures and content_hash != prior_signatures[0].record_hash:
        raise ValidationFailedError("Content must match what the earlier signer(s) in this chain approved")
    challenge = await create_challenge(
        session, user_id=actor_user_id, record_type=record_type, record_id=record_id,
        record_version=1, record_hash=content_hash, meaning=policy.meaning,
    )
    return {
        "challenge_id": str(challenge.id), "meaning": challenge.meaning,
        "chain_position": position, "signature_count": policy.signature_count,
        "expires_at": challenge.expires_at.isoformat(),
    }


class CorrectionRemovalAssessmentSignatureChallengeRequest(BaseModel):
    field_action_reference: dict


@router.post("/correction-removal/{record_id}/assessment-signature-challenges")
async def post_correction_removal_assessment_signature_challenge(
    record_id: uuid.UUID, body: CorrectionRemovalAssessmentSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        record = await session.get(CorrectionRemovalRegulatoryRecord, record_id)
        if record is None:
            raise NotFoundError("Correction/removal regulatory record not found")
        if record.state not in ("PENDING_ASSESSMENT_APPROVAL",):
            raise ValidationFailedError("Assessment is not awaiting a signature", current_state=record.state)
        return await _create_chain_challenge(
            session, record_type="correction_removal_assessment", record_id=record.id,
            content_hash=_field_action_reference_hash(body.field_action_reference), actor_user_id=actor.user_id,
        )


class CorrectionRemovalDecisionSignatureChallengeRequest(BaseModel):
    reportable: bool
    rationale: str
    calendar_version: str | None = None
    required_facts: dict = {}


@router.post("/correction-removal/{record_id}/decision-signature-challenges")
async def post_correction_removal_decision_signature_challenge(
    record_id: uuid.UUID, body: CorrectionRemovalDecisionSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        record = await session.get(CorrectionRemovalRegulatoryRecord, record_id)
        if record is None:
            raise NotFoundError("Correction/removal regulatory record not found")
        if record.state not in ("OPEN", "PENDING_DECISION_APPROVAL"):
            raise ValidationFailedError("Reportability decision is not awaiting a signature", current_state=record.state)
        return await _create_chain_challenge(
            session, record_type="correction_removal_regulatory_record", record_id=record.id,
            content_hash=_decision_content_hash(body), actor_user_id=actor.user_id,
        )


@router.post("/correction-removal/{record_id}/assessment-signatures", response_model=MutationReceipt)
async def post_approve_correction_removal_assessment(
    record_id: uuid.UUID, cmd: commands.ApproveCorrectionRemovalAssessmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """SG-160 partial resolution (2026-09-14): Document 106 row 130's independent-approver half. Not
    named in Document 60's own API list -- same "obvious continuation endpoint" precedent as
    `postApproveResultCorrection`/`postApproveStepResultCorrection` and `vault.complete_correction`."""
    if cmd.record_id != record_id:
        raise ValidationFailedError("record_id in path and body must match")
    async with session.begin():
        record = await session.get(CorrectionRemovalRegulatoryRecord, record_id)
        if record is None:
            raise NotFoundError("Correction/removal regulatory record not found")
        await evaluate_policy(session, actor.user_id, action="correction_removal.create", site_id=record.site_id)
        return await commands.approve_correction_removal_assessment(session, cmd, actor.user_id)


@router.post("/correction-removal/{record_id}/decision", response_model=MutationReceipt)
async def post_decide_correction_removal(
    record_id: uuid.UUID, cmd: commands.DecideCorrectionRemovalReportabilityCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.record_id != record_id:
        raise ValidationFailedError("record_id in path and body must match")
    async with session.begin():
        record = await session.get(CorrectionRemovalRegulatoryRecord, record_id)
        if record is None:
            raise NotFoundError("Correction/removal regulatory record not found")
        await evaluate_policy(session, actor.user_id, action="correction_removal.decide", site_id=record.site_id)
        return await commands.decide_correction_removal_reportability(session, cmd, actor.user_id)


@router.post("/correction-removal/{record_id}/decision-signatures", response_model=MutationReceipt)
async def post_approve_correction_removal_decision(
    record_id: uuid.UUID, cmd: commands.ApproveCorrectionRemovalDecisionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """SG-160 partial resolution (2026-09-14): Document 106 row 129's independent-approver half."""
    if cmd.record_id != record_id:
        raise ValidationFailedError("record_id in path and body must match")
    async with session.begin():
        record = await session.get(CorrectionRemovalRegulatoryRecord, record_id)
        if record is None:
            raise NotFoundError("Correction/removal regulatory record not found")
        await evaluate_policy(session, actor.user_id, action="correction_removal.decide", site_id=record.site_id)
        return await commands.approve_correction_removal_decision(session, cmd, actor.user_id)


@router.post("/correction-removal/{record_id}/scope-amendments", response_model=MutationReceipt)
async def post_amend_correction_removal_scope(
    record_id: uuid.UUID, cmd: commands.AddCorrectionRemovalScopeAmendmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.record_id != record_id:
        raise ValidationFailedError("record_id in path and body must match")
    async with session.begin():
        record = await session.get(CorrectionRemovalRegulatoryRecord, record_id)
        if record is None:
            raise NotFoundError("Correction/removal regulatory record not found")
        await evaluate_policy(session, actor.user_id, action="correction_removal.decide", site_id=record.site_id)
        return await commands.add_correction_removal_scope_amendment(session, cmd, actor.user_id)


@router.post("/field-alerts", response_model=MutationReceipt)
async def post_create_field_alert(
    cmd: commands.CreateFieldAlertAssessmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="regulatory_obligation.create", site_id=cmd.site_id)
        return await commands.create_field_alert_assessment(session, cmd, actor.user_id)


@router.post("/field-alerts/{obligation_id}/decision", response_model=MutationReceipt)
async def post_decide_field_alert(
    obligation_id: uuid.UUID, cmd: commands.DecideFieldAlertReportabilityCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.obligation_id != obligation_id:
        raise ValidationFailedError("obligation_id in path and body must match")
    async with session.begin():
        obligation = await session.get(RegulatoryObligation, obligation_id)
        if obligation is None:
            raise NotFoundError("Regulatory obligation not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_obligation.decide", site_id=obligation.site_id)
        return await commands.decide_field_alert_reportability(session, cmd, actor.user_id)


@router.post("/bpdr-tracks", response_model=MutationReceipt)
async def post_create_bpdr_track(
    cmd: commands.CreateBPDRTrackCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="regulatory_obligation.create", site_id=cmd.site_id)
        return await commands.create_bpdr_track(session, cmd, actor.user_id)


@router.post("/periodic-cycles:generate", response_model=MutationReceipt)
async def post_generate_periodic_cycle(
    cmd: commands.GeneratePeriodicReportingScheduleCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="periodic_reporting_cycle.generate", site_id=cmd.site_id)
        return await commands.generate_periodic_reporting_schedule(session, cmd, actor.user_id)


@router.post("/periodic-cycles/{cycle_id}/dataset:freeze")
async def post_freeze_periodic_dataset(
    cycle_id: uuid.UUID, cmd: commands.FreezePeriodicReportDatasetCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    if cmd.cycle_id != cycle_id:
        raise ValidationFailedError("cycle_id in path and body must match")
    async with session.begin():
        cycle = await session.get(PeriodicReportingCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Periodic reporting cycle not found")
        await evaluate_policy(session, actor.user_id, action="periodic_reporting_cycle.freeze", site_id=cycle.site_id)
        return await commands.freeze_periodic_report_dataset(session, cmd, actor.user_id)


@router.post("/fda-requests", response_model=MutationReceipt)
async def post_create_fda_request(
    cmd: commands.CreateFDAInformationRequestTaskCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="regulatory_obligation.create", site_id=cmd.site_id)
        return await commands.create_fda_information_request_task(session, cmd, actor.user_id)


@router.post("/obligations/{obligation_id}/deadline-overrides", response_model=MutationReceipt)
async def post_override_deadline(
    obligation_id: uuid.UUID, cmd: commands.ApplyRegulatoryDeadlineOverrideCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.obligation_id != obligation_id:
        raise ValidationFailedError("obligation_id in path and body must match")
    async with session.begin():
        obligation = await session.get(RegulatoryObligation, obligation_id)
        if obligation is None:
            raise NotFoundError("Regulatory obligation not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_obligation.override_deadline", site_id=obligation.site_id)
        return await commands.apply_regulatory_deadline_override(session, cmd, actor.user_id)


@router.post("/retention:calculate", response_model=MutationReceipt)
async def post_calculate_retention(
    cmd: commands.CalculatePostmarketRetentionPolicyCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        obligation = await session.get(RegulatoryObligation, cmd.obligation_id)
        if obligation is None:
            raise NotFoundError("Regulatory obligation not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_obligation.calculate_retention", site_id=obligation.site_id)
        return await commands.calculate_postmarket_retention_policy(session, cmd, actor.user_id)


@router.post("/obligations/{obligation_id}/legal-hold", response_model=MutationReceipt)
async def post_place_legal_hold(
    obligation_id: uuid.UUID, cmd: commands.PlacePostmarketLegalHoldCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.obligation_id != obligation_id:
        raise ValidationFailedError("obligation_id in path and body must match")
    async with session.begin():
        obligation = await session.get(RegulatoryObligation, obligation_id)
        if obligation is None:
            raise NotFoundError("Regulatory obligation not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_obligation.legal_hold", site_id=obligation.site_id)
        return await commands.place_postmarket_legal_hold(session, cmd, actor.user_id)


@router.get("/regulatory-calendar")
async def get_regulatory_calendar(
    site_id: uuid.UUID | None = None, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="regulatory_obligation.view", site_id=site_id)
        return await commands.get_unified_regulatory_calendar(session, site_id)
