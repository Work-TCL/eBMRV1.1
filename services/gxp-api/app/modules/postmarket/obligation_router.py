"""Document 60 (SPEC-PM-003) REST surface, prefix `/postmarket/v1` (same surface as Document 58 -- both
are SPEC-PM-00x modules of WP-09's combined `postmarket` schema).

`addCorrectionRemovalScopeAmendment`, `placePostmarketLegalHold` and `getUnifiedRegulatoryCalendar` are
named functions/UI surfaces in Document 60's own contract catalogue but are missing from its terse 14-op
`# 12. APIs` list -- exposed here as extra operations (same precedent used for Document 58/59).
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.postmarket import obligation_commands as commands
from app.modules.postmarket.obligation_models import (
    ConstituentInformationShare,
    CorrectionRemovalRegulatoryRecord,
    PeriodicReportingCycle,
    RegulatoryObligation,
)
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/postmarket/v1", tags=["postmarket-obligations"])


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
