"""Document 59 (SPEC-PM-002, REG-FR-001..032): reportability track creation, deadline calculation
(caller-supplied duration per REG-FR-003, weekend-only WORK_DAY per SG-158), reportability decisions,
report build/approve/payload/submission/acknowledgement lifecycle, follow-up tasks, Part 4 dedupe
evaluation and the audit-package freeze. See docs/generated/18_SPEC_GAPS.md SG-157/158/159.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.postmarket import commands as pm_commands
from app.modules.postmarket import reportability_commands as commands
from app.modules.postmarket.reportability_models import RegulatoryReport, RegulatorySubmissionAttempt, ReportabilityTrack
from app.modules.signature import service as signature_service
from app.modules.signature.models import SignaturePolicy
from app.mutation.errors import InvalidTransitionError, MissingSignatureError, StaleVersionError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, tag):
    user = User(
        username=f"reg.admin{tag}", email=f"reg.admin{tag}@example.com", full_name="Regulatory Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


def _seed_resolved_policies(db):
    """conftest.py's `seeded` fixture doesn't read scripts/seed.py's SIGNATURE_POLICY_FLOOR (same
    decoupling documented for the permission catalog) -- tests seed the actions that *do* have a real
    Document 106 resolution (rows 123/125/126/127/128) themselves, with signature_required=False for
    simplicity (the signature ceremony itself is exercised elsewhere, e.g. test_qms_deviation.py)."""
    for record_type, action in (
        ("reportability_track", "create"), ("regulatory_report", "create"), ("regulatory_report", "followup"),
        ("regulatory_report", "generate_payload"), ("regulatory_report", "submit"),
    ):
        db.add(SignaturePolicy(record_type=record_type, action=action, meaning="Approved", signature_required=False))


async def _sign(db, *, actor_id, record_type, record_version, record_hash):
    """SG-157 RESOLVED_APPROVED 2026-09-14: decideReportability()/approveRegulatoryReport() now really
    require a signature (conftest.py's global seed) -- no independence requirement, so the same actor
    signs throughout."""
    challenge = await signature_service.create_challenge(
        db, user_id=actor_id, record_type=record_type, record_id=uuid.uuid4(),
        record_version=record_version, record_hash=record_hash, meaning="Approved",
    )
    await db.flush()
    return challenge.id


async def _get(db, model, obj_id):
    async with db.begin():
        return await db.get(model, obj_id)


async def _create_case(db, seeded, owner_id):
    cmd = pm_commands.CreateSafetyCaseLinkCommand(
        idempotency_key=idem(), site_id=seeded["site_id"], safety_case_number=f"SC-{uuid.uuid4().hex[:8]}",
        source_record_type="complaint_record", source_record_id=uuid.uuid4(), source_record_version=1,
    )
    return await pm_commands.create_safety_case_link(db, cmd, owner_id)


@pytest.mark.asyncio
async def test_create_multiple_independent_tracks_for_one_case(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "1")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[
                    {"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K123456"}},
                    {"report_type_code": "DRUG_EXPEDITED_15", "report_type_version": "1.0", "application_context": {"nda": "NDA-000123"}},
                ],
            ), owner.id,
        )
    first_track = await _get(db, ReportabilityTrack, receipt.aggregate_id)
    assert first_track.report_type_code == "MDR_30"


@pytest.mark.asyncio
async def test_device_30_day_and_5_day_deadline_calculation(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "2")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        thirty_receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K123456"}}],
            ), owner.id,
        )
    clock_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    async with db.begin():
        await commands.calculate_regulatory_deadline(
            db, commands.CalculateRegulatoryDeadlineCommand(
                idempotency_key=idem(), track_id=thirty_receipt.aggregate_id, expected_version=1,
                clock_start_basis="COMPANY_AWARENESS", clock_start_at=clock_start,
                clock_start_rationale="date of company awareness of the death", calendar_type="CALENDAR_DAY",
                calendar_version="v1", rule_version="mdr-30-v1", duration_days=30,
            ), owner.id,
        )
    track = await _get(db, ReportabilityTrack, thirty_receipt.aggregate_id)
    assert track.due_at == clock_start + timedelta(days=30)
    assert track.original_due_at == track.due_at
    assert track.state == "CLOCK_SET"

    async with db.begin():
        case_receipt2 = await _create_case(db, seeded, owner.id)
        five_receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt2.aggregate_id,
                tracks=[{"report_type_code": "MDR_5", "report_type_version": "1.0", "application_context": {"device_application": "K123456"}}],
            ), owner.id,
        )
    # WORK_DAY: 5 work days from a Thursday (2026-01-01 was a Thursday) skips the intervening weekend.
    async with db.begin():
        await commands.calculate_regulatory_deadline(
            db, commands.CalculateRegulatoryDeadlineCommand(
                idempotency_key=idem(), track_id=five_receipt.aggregate_id, expected_version=1,
                clock_start_basis="AGENCY_REQUEST", clock_start_at=clock_start,
                clock_start_rationale="FDA remedial-action request received", calendar_type="WORK_DAY",
                calendar_version="v1", rule_version="mdr-5-v1", duration_days=5,
            ), owner.id,
        )
    track5 = await _get(db, ReportabilityTrack, five_receipt.aggregate_id)
    assert track5.due_at == datetime(2026, 1, 8, tzinfo=timezone.utc)  # Thu Jan 1 + 5 work days = Thu Jan 8


@pytest.mark.asyncio
async def test_original_due_at_immutable_after_first_calculation(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "3")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "DRUG_EXPEDITED_15", "report_type_version": "1.0", "application_context": {"nda": "NDA-1"}}],
            ), owner.id,
        )
    start = datetime(2026, 2, 1, tzinfo=timezone.utc)
    async with db.begin():
        await commands.calculate_regulatory_deadline(
            db, commands.CalculateRegulatoryDeadlineCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                clock_start_basis="SOURCE_RECEIPT", clock_start_at=start, clock_start_rationale="initial receipt",
                calendar_type="CALENDAR_DAY", calendar_version="v1", rule_version="drug-15-v1", duration_days=15,
            ), owner.id,
        )
    track = await _get(db, ReportabilityTrack, receipt.aggregate_id)
    original = track.original_due_at

    # A correction to clock_start_at recalculates due_at but never rewrites original_due_at.
    async with db.begin():
        await commands.calculate_regulatory_deadline(
            db, commands.CalculateRegulatoryDeadlineCommand(
                idempotency_key=idem(), track_id=track.id, expected_version=track.version,
                clock_start_basis="SOURCE_RECEIPT", clock_start_at=start + timedelta(days=2),
                clock_start_rationale="corrected receipt date", calendar_type="CALENDAR_DAY",
                calendar_version="v1", rule_version="drug-15-v1", duration_days=15,
            ), owner.id,
        )
    track = await _get(db, ReportabilityTrack, receipt.aggregate_id)
    assert track.original_due_at == original
    assert track.due_at == original + timedelta(days=2)


@pytest.mark.asyncio
async def test_part4_dedupe_false_because_deadline_differs(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "4")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[
                    {"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K1"}},
                    {"report_type_code": "PART4_30", "report_type_version": "1.0", "application_context": {"nda": "NDA-1"}},
                ],
            ), owner.id,
        )
    from sqlalchemy import select
    async with db.begin():
        rows = (await db.execute(select(ReportabilityTrack).where(ReportabilityTrack.safety_case_id == case_receipt.aggregate_id))).scalars().all()
        mdr_track = next(t for t in rows if t.report_type_code == "MDR_30")
        part4_track = next(t for t in rows if t.report_type_code == "PART4_30")

    async with db.begin():
        await commands.calculate_regulatory_deadline(
            db, commands.CalculateRegulatoryDeadlineCommand(
                idempotency_key=idem(), track_id=mdr_track.id, expected_version=1, clock_start_basis="COMPANY_AWARENESS",
                clock_start_at=datetime(2026, 1, 1, tzinfo=timezone.utc), clock_start_rationale="awareness",
                calendar_type="CALENDAR_DAY", calendar_version="v1", rule_version="mdr-30-v1", duration_days=30,
            ), owner.id,
        )
    async with db.begin():
        await commands.calculate_regulatory_deadline(
            db, commands.CalculateRegulatoryDeadlineCommand(
                idempotency_key=idem(), track_id=part4_track.id, expected_version=1, clock_start_basis="COMPANY_AWARENESS",
                clock_start_at=datetime(2026, 1, 1, tzinfo=timezone.utc), clock_start_rationale="awareness",
                calendar_type="CALENDAR_DAY", calendar_version="v1", rule_version="part4-30-v1", duration_days=45,
            ), owner.id,
        )
    result = await commands.evaluate_same_event_report_deduplication(
        db, commands.EvaluateSameEventDeduplicationCommand(
            idempotency_key=idem(), candidate_track_ids=[mdr_track.id, part4_track.id], rationale="checking Part 4 dedupe",
        ),
    )
    assert result["same_deadline"] is False
    assert result["eligible_for_single_report"] is False


@pytest.mark.asyncio
async def test_decide_reportability_requires_a_real_signature_then_signed_not_reportable(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "5")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "MALFUNCTION", "report_type_version": "1.0", "application_context": {"device_application": "K1"}}],
            ), owner.id,
        )

    # SG-157 RESOLVED_APPROVED 2026-09-14: decide_reportability really requires a signature now -- calling
    # without a challenge/reauth is rejected, not silently accepted.
    async with db.begin():
        with pytest.raises(MissingSignatureError):
            await commands.decide_reportability(
                db, commands.DecideReportabilityCommand(
                    idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                    decision="NOT_REPORTABLE", rationale="malfunction did not recur and would not cause harm",
                ), owner.id,
            )

    async with db.begin():
        track = await db.get(ReportabilityTrack, receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="reportability_track", record_version=track.version, record_hash=commands._track_hash(track))
        await commands.decide_reportability(
            db, commands.DecideReportabilityCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                decision="NOT_REPORTABLE", rationale="malfunction did not recur and would not cause harm",
                evidence_refs=[{"type": "engineering_evaluation", "id": str(uuid.uuid4())}],
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
    track = await _get(db, ReportabilityTrack, receipt.aggregate_id)
    assert track.decision == "NOT_REPORTABLE"
    assert track.state == "DECIDED"
    assert track.decision_by == owner.id


@pytest.mark.asyncio
async def test_report_build_requires_reportable_decision_and_stale_version_rejected(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "6")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K1"}}],
            ), owner.id,
        )

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.build_regulatory_report(
                db, commands.BuildRegulatoryReportCommand(
                    idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                    schema_code="MDR_V1", schema_version="1.0", content={"event": "death"}, field_provenance={},
                ), owner.id,
            )

    async with db.begin():
        track = await db.get(ReportabilityTrack, receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="reportability_track", record_version=track.version, record_hash=commands._track_hash(track))
        await commands.decide_reportability(
            db, commands.DecideReportabilityCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                decision="REPORTABLE", rationale="death causally linked to device malfunction",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
    async with db.begin():
        report_receipt = await commands.build_regulatory_report(
            db, commands.BuildRegulatoryReportCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=2,
                schema_code="MDR_V1", schema_version="1.0", content={"event": "death"}, field_provenance={"event": {"source_type": "safety_case", "source_id": str(case_receipt.aggregate_id)}},
                missing_information=[{"field": "patient_age", "reason": "not obtained"}],
            ), owner.id,
        )
    report = await _get(db, RegulatoryReport, report_receipt.aggregate_id)
    assert report.state == "DRAFT"
    assert report.report_version == 1

    # A stale track version (as if the track was redecided concurrently) is rejected.
    async with db.begin():
        with pytest.raises(StaleVersionError):
            await commands.build_regulatory_report(
                db, commands.BuildRegulatoryReportCommand(
                    idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                    schema_code="MDR_V1", schema_version="1.0", content={"event": "death"}, field_provenance={},
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_approve_generate_payload_and_duplicate_submission_blocked(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "7")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K1"}}],
            ), owner.id,
        )
        track = await db.get(ReportabilityTrack, receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="reportability_track", record_version=track.version, record_hash=commands._track_hash(track))
        await commands.decide_reportability(
            db, commands.DecideReportabilityCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                decision="REPORTABLE", rationale="serious injury",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
        report_receipt = await commands.build_regulatory_report(
            db, commands.BuildRegulatoryReportCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=2,
                schema_code="MDR_V1", schema_version="1.0", content={"event": "serious_injury"}, field_provenance={},
            ), owner.id,
        )

    async with db.begin():
        report = await db.get(RegulatoryReport, report_receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="regulatory_report", record_version=report.report_version, record_hash=sha256_hex(report.content))
        await commands.approve_regulatory_report(
            db, commands.ApproveRegulatoryReportCommand(
                idempotency_key=idem(), report_id=report_receipt.aggregate_id, expected_version=1,
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
    report = await _get(db, RegulatoryReport, report_receipt.aggregate_id)
    assert report.state == "APPROVED"

    async with db.begin():
        payload_result = await commands.generate_regulatory_payload(
            db, commands.GenerateRegulatoryPayloadCommand(
                idempotency_key=idem(), report_id=report.id, implementation_or_profile_version="emdr-3.1",
            ), owner.id,
        )
    assert payload_result["payload"]["family"] == "EMDR"

    async with db.begin():
        submit_receipt = await commands.submit_regulatory_report(
            db, commands.SubmitRegulatoryReportCommand(
                idempotency_key=idem(), report_id=report.id, channel="MANUAL", payload_version="v1",
                payload_digest=payload_result["payload_digest"], sender_identity="regulatory-affairs-team",
                manual_evidence_id=uuid.uuid4(),
            ), owner.id,
        )
    attempt = await _get(db, RegulatorySubmissionAttempt, submit_receipt.aggregate_id)
    assert attempt.transport_result == "SENT"
    report = await _get(db, RegulatoryReport, report.id)
    assert report.state == "SUBMITTED"

    # REG-FR-025: a second initial submission of the same approved report version is blocked.
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.submit_regulatory_report(
                db, commands.SubmitRegulatoryReportCommand(
                    idempotency_key=idem(), report_id=report.id, channel="MANUAL", payload_version="v1",
                    payload_digest=payload_result["payload_digest"], sender_identity="regulatory-affairs-team",
                    manual_evidence_id=uuid.uuid4(),
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_transport_timeout_then_fda_rejection_creates_resubmission_evidence(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "8")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "DRUG_EXPEDITED_15", "report_type_version": "1.0", "application_context": {"nda": "NDA-1"}}],
            ), owner.id,
        )
        track = await db.get(ReportabilityTrack, receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="reportability_track", record_version=track.version, record_hash=commands._track_hash(track))
        await commands.decide_reportability(
            db, commands.DecideReportabilityCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                decision="REPORTABLE", rationale="serious unexpected adverse experience",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
        report_receipt = await commands.build_regulatory_report(
            db, commands.BuildRegulatoryReportCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=2,
                schema_code="ICSR_E2B", schema_version="R3", content={"event": "sae"}, field_provenance={},
            ), owner.id,
        )
        report = await db.get(RegulatoryReport, report_receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="regulatory_report", record_version=report.report_version, record_hash=sha256_hex(report.content))
        await commands.approve_regulatory_report(
            db, commands.ApproveRegulatoryReportCommand(
                idempotency_key=idem(), report_id=report_receipt.aggregate_id, expected_version=1,
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )

    # No transport_result supplied for a non-MANUAL channel -- honestly TIMEOUT_UNCERTAIN, not SENT.
    async with db.begin():
        submit_receipt = await commands.submit_regulatory_report(
            db, commands.SubmitRegulatoryReportCommand(
                idempotency_key=idem(), report_id=report_receipt.aggregate_id, channel="ESG_NEXTGEN",
                payload_version="v1", payload_digest="deadbeef", sender_identity="esg-gateway-service",
            ), owner.id,
        )
    attempt = await _get(db, RegulatorySubmissionAttempt, submit_receipt.aggregate_id)
    assert attempt.transport_result == "TIMEOUT_UNCERTAIN"
    report = await _get(db, RegulatoryReport, report_receipt.aggregate_id)
    assert report.state == "APPROVED"  # not SUBMITTED -- transport never confirmed SENT

    # A later real transmission succeeds, then FDA rejects it -- REG-FR-019/026.
    async with db.begin():
        submit2 = await commands.submit_regulatory_report(
            db, commands.SubmitRegulatoryReportCommand(
                idempotency_key=idem(), report_id=report_receipt.aggregate_id, channel="ESG_NEXTGEN",
                payload_version="v1", payload_digest="deadbeef", sender_identity="esg-gateway-service",
                transport_result="SENT",
            ), owner.id,
        )
    async with db.begin():
        ack_receipt = await commands.ingest_submission_acknowledgement(
            db, commands.IngestSubmissionAcknowledgementCommand(
                idempotency_key=idem(), submission_attempt_id=submit2.aggregate_id, ack_level="AGENCY_ACCEPTANCE",
                ack_state="REJECTED", rejection_reason={"code": "SCHEMA_ERROR", "detail": "missing patient age"},
            ), owner.id,
        )
    assert ack_receipt.aggregate_id is not None


@pytest.mark.asyncio
async def test_followup_report_task_creates_new_track_linked_to_original(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "9")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K1"}}],
            ), owner.id,
        )
        track = await db.get(ReportabilityTrack, receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="reportability_track", record_version=track.version, record_hash=commands._track_hash(track))
        await commands.decide_reportability(
            db, commands.DecideReportabilityCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                decision="REPORTABLE", rationale="serious injury",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
        report_receipt = await commands.build_regulatory_report(
            db, commands.BuildRegulatoryReportCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=2,
                schema_code="MDR_V1", schema_version="1.0", content={"event": "serious_injury"}, field_provenance={},
            ), owner.id,
        )

    async with db.begin():
        followup_receipt = await commands.create_followup_report_task(
            db, commands.CreateFollowupReportTaskCommand(
                idempotency_key=idem(), original_report_id=report_receipt.aggregate_id,
                new_information_receipt={"detail": "patient outcome updated"}, rationale="new clinical information received",
            ), owner.id,
        )
    followup_track = await _get(db, ReportabilityTrack, followup_receipt.aggregate_id)
    assert followup_track.parent_track_id == receipt.aggregate_id
    assert followup_track.report_type_code == "FOLLOWUP"


@pytest.mark.asyncio
async def test_freeze_reportability_audit_package_is_reproducible(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "10")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K1"}}],
            ), owner.id,
        )

    async with db.begin():
        first = await commands.freeze_reportability_audit_package(
            db, commands.FreezeReportabilityAuditPackageCommand(
                idempotency_key=idem(), safety_case_id=case_receipt.aggregate_id, site_id=seeded["site_id"],
            ), owner.id,
        )
    assert any(t["track_id"] == str(receipt.aggregate_id) for t in first["tracks"])

    async with db.begin():
        second = await commands.freeze_reportability_audit_package(
            db, commands.FreezeReportabilityAuditPackageCommand(
                idempotency_key=idem(), safety_case_id=case_receipt.aggregate_id, site_id=seeded["site_id"],
            ), owner.id,
        )
    assert first["vault_object_id"] == second["vault_object_id"]


@pytest.mark.asyncio
async def test_create_tracks_via_http_and_unauthorized_rejected(client, db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "11")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)

    from tests.conftest import auth_headers, login
    resp = await client.post(
        f"/regulatory/v1/cases/{case_receipt.aggregate_id}/reportability-tracks",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "safety_case_id": str(case_receipt.aggregate_id),
            "tracks": [{"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K1"}}],
        },
    )
    assert resp.status_code == 401

    token = await login(client, "reg.admin11")
    resp = await client.post(
        f"/regulatory/v1/cases/{case_receipt.aggregate_id}/reportability-tracks",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "safety_case_id": str(case_receipt.aggregate_id),
            "tracks": [{"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K1"}}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_generate_payload_uses_aems_family_for_drug_biologic_tracks(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "12")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "BIOLOGIC_EXPEDITED_15", "report_type_version": "1.0", "application_context": {"bla": "BLA-000456"}}],
            ), owner.id,
        )
        track = await db.get(ReportabilityTrack, receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="reportability_track", record_version=track.version, record_hash=commands._track_hash(track))
        await commands.decide_reportability(
            db, commands.DecideReportabilityCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                decision="REPORTABLE", rationale="serious unexpected biologic adverse experience",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
        report_receipt = await commands.build_regulatory_report(
            db, commands.BuildRegulatoryReportCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=2,
                schema_code="ICSR_E2B", schema_version="R3", content={"event": "sae"}, field_provenance={},
            ), owner.id,
        )
        report = await db.get(RegulatoryReport, report_receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_type="regulatory_report", record_version=report.report_version, record_hash=sha256_hex(report.content))
        await commands.approve_regulatory_report(
            db, commands.ApproveRegulatoryReportCommand(
                idempotency_key=idem(), report_id=report_receipt.aggregate_id, expected_version=1,
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )

    async with db.begin():
        payload_result = await commands.generate_regulatory_payload(
            db, commands.GenerateRegulatoryPayloadCommand(
                idempotency_key=idem(), report_id=report_receipt.aggregate_id, implementation_or_profile_version="e2b-r3-v1",
            ), owner.id,
        )
    assert payload_result["payload"]["family"] == "AEMS"


@pytest.mark.asyncio
async def test_decide_and_approve_report_via_http_signature_challenges(client, db, seeded):
    """The `decide`/`approve` signature ceremony above is proven at the command layer by every other
    test in this file, using `signature_service.create_challenge()` directly. This is the one test that
    exercises the actual HTTP surface a real caller (the frontend) uses: `POST .../decision-signature-
    challenges` and `POST .../approval-signature-challenges` (added alongside SG-157's resolution --
    those two actions became real, resolved, signature-required policies, but had no HTTP endpoint a
    real client could call to obtain a challenge_id for them until now)."""
    async with db.begin():
        owner = await _make_admin(db, seeded, "13")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        receipt = await commands.create_reportability_tracks(
            db, commands.CreateReportabilityTracksCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], safety_case_id=case_receipt.aggregate_id,
                tracks=[{"report_type_code": "MDR_30", "report_type_version": "1.0", "application_context": {"device_application": "K999"}}],
            ), owner.id,
        )
        await commands.calculate_regulatory_deadline(
            db, commands.CalculateRegulatoryDeadlineCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=1,
                clock_start_basis="COMPANY_AWARENESS", clock_start_at=datetime.now(timezone.utc),
                clock_start_rationale="date of company awareness", calendar_type="CALENDAR_DAY",
                calendar_version="v1", rule_version="mdr-30-v1", duration_days=30,
            ), owner.id,
        )
    token = await login(client, "reg.admin13")

    # Unsigned decision attempt is blocked.
    unsigned = await client.post(
        f"/regulatory/v1/tracks/{receipt.aggregate_id}/decisions",
        json={
            "idempotency_key": idem(), "track_id": str(receipt.aggregate_id), "expected_version": 2,
            "decision": "REPORTABLE", "rationale": "serious unexpected adverse event",
        },
        headers=auth_headers(token),
    )
    assert unsigned.status_code == 428, unsigned.text
    assert unsigned.json()["code"] == "MISSING_SIGNATURE"

    decision_challenge = (
        await client.post(f"/regulatory/v1/tracks/{receipt.aggregate_id}/decision-signature-challenges", headers=auth_headers(token))
    ).json()
    assert decision_challenge["meaning"] == "Approved"
    decide_resp = await client.post(
        f"/regulatory/v1/tracks/{receipt.aggregate_id}/decisions",
        json={
            "idempotency_key": idem(), "track_id": str(receipt.aggregate_id), "expected_version": 2,
            "decision": "REPORTABLE", "rationale": "serious unexpected adverse event",
            "challenge_id": decision_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert decide_resp.status_code == 200, decide_resp.text
    track = await _get(db, ReportabilityTrack, receipt.aggregate_id)
    assert track.state == "DECIDED" and track.decision == "REPORTABLE"

    async with db.begin():
        report_receipt = await commands.build_regulatory_report(
            db, commands.BuildRegulatoryReportCommand(
                idempotency_key=idem(), track_id=receipt.aggregate_id, expected_version=track.version,
                schema_code="ICSR_E2B", schema_version="R3", content={"event": "sae"}, field_provenance={},
            ), owner.id,
        )

    approval_challenge = (
        await client.post(f"/regulatory/v1/reports/{report_receipt.aggregate_id}/approval-signature-challenges", headers=auth_headers(token))
    ).json()
    assert approval_challenge["meaning"] == "Approved"
    approve_resp = await client.post(
        f"/regulatory/v1/reports/{report_receipt.aggregate_id}/approve",
        json={
            "idempotency_key": idem(), "report_id": str(report_receipt.aggregate_id), "expected_version": 1,
            "challenge_id": approval_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert approve_resp.status_code == 200, approve_resp.text
    report = await _get(db, RegulatoryReport, report_receipt.aggregate_id)
    assert report.state == "APPROVED"
