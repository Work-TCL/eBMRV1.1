"""Document 60 (SPEC-PM-003, PMO-FR-001..032): applicant relationships, Part 4 constituent information
sharing (5-calendar-day clock), Part 806 correction/removal assessment (10-working-day clock, scope
amendments), Field Alert (3-working-day clock) and BPDR obligations, periodic reporting cycles (reusing
Document 58's dataset freeze), FDA information requests, deadline overrides, longest-applicable retention
and legal hold. See docs/generated/18_SPEC_GAPS.md SG-160.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.postmarket import commands as pm_commands
from app.modules.postmarket import obligation_commands as commands
from app.modules.postmarket.obligation_models import (
    ApplicantRelationship,
    ConstituentInformationShare,
    CorrectionRemovalRegulatoryRecord,
    PeriodicReportingCycle,
    RegulatoryObligation,
)
from app.modules.signature.models import SignaturePolicy
from app.mutation.errors import SignaturePolicyUnresolvedError, StaleVersionError, ValidationFailedError
from tests.conftest import DEMO_PASSWORD, idem


async def _make_admin(db, seeded, tag):
    user = User(
        username=f"pmo.admin{tag}", email=f"pmo.admin{tag}@example.com", full_name="PMO Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


def _seed_resolved_policies(db):
    """conftest.py's `seeded` fixture doesn't read scripts/seed.py's SIGNATURE_POLICY_FLOOR -- tests seed
    the one action that *does* have a real Document 106 resolution (row 132) themselves."""
    db.add(SignaturePolicy(record_type="constituent_information_share", action="record_sent", meaning="Performed", signature_required=False))


def _allow_unresolved_decision_actions(db):
    """SG-160: correction_removal.decide and regulatory_obligation.override_deadline have no Document
    106 resolution -- tests seed a permissive local policy to exercise the business logic beyond the
    fail-closed check."""
    db.add(SignaturePolicy(record_type="correction_removal_regulatory_record", action="decide", meaning="Approved", signature_required=False))
    db.add(SignaturePolicy(record_type="regulatory_obligation", action="override_deadline", meaning="Approved", signature_required=False))
    db.add(SignaturePolicy(record_type="regulatory_obligation", action="decide_field_alert", meaning="Approved", signature_required=False))


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
async def test_two_constituent_applicants_create_correct_sharing_recipients(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "1")
        case_receipt = await _create_case(db, seeded, owner.id)
        device_rel = await commands.configure_applicant_relationship(
            db, commands.ConfigureApplicantRelationshipCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], product_version_reference={"product_version_id": str(uuid.uuid4())},
                applicant_role="CONSTITUENT_PART_APPLICANT", applicant_name="Device Constituent Co",
                address={"line1": "1 Device Way"}, contact={"email": "regulatory@device.example"},
            ), owner.id,
        )
        drug_rel = await commands.configure_applicant_relationship(
            db, commands.ConfigureApplicantRelationshipCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], product_version_reference={"product_version_id": str(uuid.uuid4())},
                applicant_role="CONSTITUENT_PART_APPLICANT", applicant_name="Drug Constituent Co",
                address={"line1": "1 Drug Ave"}, contact={"email": "regulatory@drug.example"},
            ), owner.id,
        )

    receipt_at = datetime(2026, 3, 2, tzinfo=timezone.utc)  # Monday
    async with db.begin():
        share1 = await commands.evaluate_part4_information_sharing(
            db, commands.EvaluatePart4SharingCommand(
                idempotency_key=idem(), safety_case_id=case_receipt.aggregate_id, site_id=seeded["site_id"],
                applicant_relationship_id=device_rel.aggregate_id, company_receipt_at=receipt_at,
            ), owner.id,
        )
    async with db.begin():
        share2 = await commands.evaluate_part4_information_sharing(
            db, commands.EvaluatePart4SharingCommand(
                idempotency_key=idem(), safety_case_id=case_receipt.aggregate_id, site_id=seeded["site_id"],
                applicant_relationship_id=drug_rel.aggregate_id, company_receipt_at=receipt_at,
            ), owner.id,
        )
    s1 = await _get(db, ConstituentInformationShare, share1.aggregate_id)
    s2 = await _get(db, ConstituentInformationShare, share2.aggregate_id)
    assert s1.applicant_relationship_id == device_rel.aggregate_id
    assert s2.applicant_relationship_id == drug_rel.aggregate_id
    # PMO-FR-004: 5 calendar days, stated directly in Document 60's own text.
    assert s1.due_at == receipt_at + timedelta(days=5)


@pytest.mark.asyncio
async def test_missing_package_blocks_record_sent_completion(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "2")
        _seed_resolved_policies(db)
        case_receipt = await _create_case(db, seeded, owner.id)
        rel = await commands.configure_applicant_relationship(
            db, commands.ConfigureApplicantRelationshipCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], product_version_reference={"product_version_id": str(uuid.uuid4())},
                applicant_role="CONSTITUENT_PART_APPLICANT", applicant_name="Device Constituent Co",
                address={"line1": "1 Device Way"}, contact={"email": "regulatory@device.example"},
            ), owner.id,
        )
        share = await commands.evaluate_part4_information_sharing(
            db, commands.EvaluatePart4SharingCommand(
                idempotency_key=idem(), safety_case_id=case_receipt.aggregate_id, site_id=seeded["site_id"],
                applicant_relationship_id=rel.aggregate_id, company_receipt_at=datetime.now(timezone.utc),
            ), owner.id,
        )

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.record_constituent_information_shared(
                db, commands.RecordConstituentInformationSharedCommand(
                    idempotency_key=idem(), share_id=share.aggregate_id, expected_version=1,
                    sent_at=datetime.now(timezone.utc), channel="secure_portal",
                ), owner.id,
            )

    async with db.begin():
        await commands.create_constituent_sharing_package(
            db, commands.CreateConstituentSharingPackageCommand(
                idempotency_key=idem(), share_id=share.aggregate_id, expected_version=1,
                package_content={"summary": "adverse event summary"},
            ), owner.id,
        )
    async with db.begin():
        await commands.record_constituent_information_shared(
            db, commands.RecordConstituentInformationSharedCommand(
                idempotency_key=idem(), share_id=share.aggregate_id, expected_version=2,
                sent_at=datetime.now(timezone.utc), channel="secure_portal", delivery_evidence={"ack": "delivered"},
            ), owner.id,
        )
    result = await _get(db, ConstituentInformationShare, share.aggregate_id)
    assert result.state == "SHARED"
    assert result.package_version == 1


@pytest.mark.asyncio
async def test_reportable_and_nonreportable_correction_removal_paths(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "3")
        initiation = datetime(2026, 4, 6, tzinfo=timezone.utc)  # Monday
        record = await commands.create_correction_removal_assessment(
            db, commands.CreateCorrectionRemovalAssessmentCommand(
                idempotency_key=idem(), site_id=seeded["site_id"],
                field_action_reference={"field_action_id": str(uuid.uuid4()), "scope_snapshot_version": 1},
                initiation_at=initiation,
            ), owner.id,
        )

    # SG-160: no signature resolution yet for this specific fresh policy row check.
    async with db.begin():
        with pytest.raises(SignaturePolicyUnresolvedError):
            await commands.decide_correction_removal_reportability(
                db, commands.DecideCorrectionRemovalReportabilityCommand(
                    idempotency_key=idem(), record_id=record.aggregate_id, expected_version=1,
                    reportable=True, rationale="meets Part 806 reportability criteria",
                ), owner.id,
            )

    async with db.begin():
        _allow_unresolved_decision_actions(db)
        await commands.decide_correction_removal_reportability(
            db, commands.DecideCorrectionRemovalReportabilityCommand(
                idempotency_key=idem(), record_id=record.aggregate_id, expected_version=1,
                reportable=True, rationale="meets Part 806 reportability criteria", calendar_version="v1",
            ), owner.id,
        )
    reportable_record = await _get(db, CorrectionRemovalRegulatoryRecord, record.aggregate_id)
    assert reportable_record.regime == "PART_806_REPORT"
    # PMO-FR-010: 10 working days from initiation (Monday + 10 work days).
    assert reportable_record.due_at == initiation + timedelta(days=14)  # 2 weekends skipped

    async with db.begin():
        record2 = await commands.create_correction_removal_assessment(
            db, commands.CreateCorrectionRemovalAssessmentCommand(
                idempotency_key=idem(), site_id=seeded["site_id"],
                field_action_reference={"field_action_id": str(uuid.uuid4()), "scope_snapshot_version": 1},
                initiation_at=initiation,
            ), owner.id,
        )
        await commands.decide_correction_removal_reportability(
            db, commands.DecideCorrectionRemovalReportabilityCommand(
                idempotency_key=idem(), record_id=record2.aggregate_id, expected_version=1,
                reportable=False, rationale="does not meet Part 806 reportability criteria",
            ), owner.id,
        )
    nonreportable_record = await _get(db, CorrectionRemovalRegulatoryRecord, record2.aggregate_id)
    assert nonreportable_record.regime == "PART_806_20_RECORD"
    assert nonreportable_record.due_at is None
    assert nonreportable_record.retention_class_code == "RC-806"

    # PMO-FR-012: scope expansion amendment appended, original decision preserved.
    async with db.begin():
        await commands.add_correction_removal_scope_amendment(
            db, commands.AddCorrectionRemovalScopeAmendmentCommand(
                idempotency_key=idem(), record_id=record.aggregate_id, expected_version=2,
                amendment={"additional_lots": ["LOT-002", "LOT-003"]}, rationale="scope expanded to additional lots",
            ), owner.id,
        )
    amended = await _get(db, CorrectionRemovalRegulatoryRecord, record.aggregate_id)
    assert len(amended.scope_amendments) == 1
    assert amended.regime == "PART_806_REPORT"  # original decision untouched


@pytest.mark.asyncio
async def test_field_alert_3_working_day_clock_and_bpdr_track(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "4")
        _allow_unresolved_decision_actions(db)
        receipt_at = datetime(2026, 5, 4, tzinfo=timezone.utc)  # Monday
        alert = await commands.create_field_alert_assessment(
            db, commands.CreateFieldAlertAssessmentCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], source_type="complaint_record", source_id=uuid.uuid4(),
                application_id="NDA-000123", distributed_batches=["LOT-100", "LOT-101"], issue_type="contamination",
                facility="Site A", applicant_receipt_at=receipt_at,
            ), owner.id,
        )
    obligation = await _get(db, RegulatoryObligation, alert.aggregate_id)
    assert obligation.obligation_type == "FIELD_ALERT"
    # PMO-FR-014: 3 working days from a Monday receipt.
    assert obligation.current_due_at == datetime(2026, 5, 7, tzinfo=timezone.utc)  # Thursday

    async with db.begin():
        await commands.decide_field_alert_reportability(
            db, commands.DecideFieldAlertReportabilityCommand(
                idempotency_key=idem(), obligation_id=alert.aggregate_id, expected_version=1,
                decision="REPORTABLE", rationale="distributed lot contamination confirmed",
            ), owner.id,
        )
    obligation = await _get(db, RegulatoryObligation, alert.aggregate_id)
    assert obligation.decision == "REPORTABLE"
    assert obligation.state == "DECIDED"

    async with db.begin():
        bpdr = await commands.create_bpdr_track(
            db, commands.CreateBPDRTrackCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], source_type="deviation_record", source_id=uuid.uuid4(),
                application_id="BLA-000456", deviation_facts={"description": "biologic manufacturing deviation"},
                discovery_at=datetime.now(timezone.utc),
            ), owner.id,
        )
    bpdr_obligation = await _get(db, RegulatoryObligation, bpdr.aggregate_id)
    assert bpdr_obligation.obligation_type == "BPDR"


@pytest.mark.asyncio
async def test_periodic_cycle_generation_no_duplicates_and_part4_augmentation(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "5")
        cycle_receipt = await commands.generate_periodic_reporting_schedule(
            db, commands.GeneratePeriodicReportingScheduleCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], application_reference="NDA-000123",
                cycle_type="QUARTERLY", period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                period_end=datetime(2026, 3, 31, tzinfo=timezone.utc), inclusion_rules_version="v1",
                part4_augmentation_required=True,
            ), owner.id,
        )
    cycle = await _get(db, PeriodicReportingCycle, cycle_receipt.aggregate_id)
    assert cycle.part4_augmentation_required is True

    # PMO-FR-017: "without duplicates" for the same application/type/period.
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.generate_periodic_reporting_schedule(
                db, commands.GeneratePeriodicReportingScheduleCommand(
                    idempotency_key=idem(), site_id=seeded["site_id"], application_reference="NDA-000123",
                    cycle_type="QUARTERLY", period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    period_end=datetime(2026, 3, 31, tzinfo=timezone.utc), inclusion_rules_version="v1",
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_freeze_periodic_dataset_reuses_document_58(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "6")
        await _create_case(db, seeded, owner.id)
        cycle_receipt = await commands.generate_periodic_reporting_schedule(
            db, commands.GeneratePeriodicReportingScheduleCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], application_reference="NDA-000789",
                cycle_type="ANNUAL", period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
                period_end=datetime(2025, 12, 31, tzinfo=timezone.utc), inclusion_rules_version="v1",
            ), owner.id,
        )
    async with db.begin():
        result = await commands.freeze_periodic_report_dataset(
            db, commands.FreezePeriodicReportDatasetCommand(
                idempotency_key=idem(), cycle_id=cycle_receipt.aggregate_id, expected_version=1,
                source_cutoff=datetime.now(timezone.utc),
            ), owner.id,
        )
    assert result["state"] == "FROZEN"
    assert "vault_object_id" in result["dataset"]
    cycle = await _get(db, PeriodicReportingCycle, cycle_receipt.aggregate_id)
    assert cycle.dataset_snapshot_id is not None


@pytest.mark.asyncio
async def test_fda_request_requires_due_date_and_deadline_override_preserves_original(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "7")
        received = datetime.now(timezone.utc)
        request = await commands.create_fda_information_request_task(
            db, commands.CreateFDAInformationRequestTaskCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], application_id="NDA-000123",
                agency_reference="CDER-2026-0456", requested_events_or_information="all complaint records for lot LOT-100",
                due_at=received + timedelta(days=30), received_at=received,
            ), owner.id,
        )
    obligation = await _get(db, RegulatoryObligation, request.aggregate_id)
    original_due = obligation.original_due_at

    async with db.begin():
        with pytest.raises(SignaturePolicyUnresolvedError):
            await commands.apply_regulatory_deadline_override(
                db, commands.ApplyRegulatoryDeadlineOverrideCommand(
                    idempotency_key=idem(), obligation_id=request.aggregate_id, expected_version=1,
                    new_due_at=original_due + timedelta(days=15), agency_evidence={"letter_ref": "CDER-2026-0456-EXT"},
                    reason="FDA granted a 15-day extension",
                ), owner.id,
            )

    async with db.begin():
        _allow_unresolved_decision_actions(db)
        await commands.apply_regulatory_deadline_override(
            db, commands.ApplyRegulatoryDeadlineOverrideCommand(
                idempotency_key=idem(), obligation_id=request.aggregate_id, expected_version=1,
                new_due_at=original_due + timedelta(days=15), agency_evidence={"letter_ref": "CDER-2026-0456-EXT"},
                reason="FDA granted a 15-day extension",
            ), owner.id,
        )
    obligation = await _get(db, RegulatoryObligation, request.aggregate_id)
    assert obligation.original_due_at == original_due  # PMO-FR-024: original never changes
    assert obligation.current_due_at == original_due + timedelta(days=15)


@pytest.mark.asyncio
async def test_retention_selects_longest_and_never_shortens(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "8")
        request = await commands.create_fda_information_request_task(
            db, commands.CreateFDAInformationRequestTaskCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], application_id="NDA-000123",
                agency_reference="CDER-2026-0999", requested_events_or_information="complaint history",
                due_at=datetime.now(timezone.utc) + timedelta(days=30), received_at=datetime.now(timezone.utc),
            ), owner.id,
        )

    async with db.begin():
        await commands.calculate_postmarket_retention_policy(
            db, commands.CalculatePostmarketRetentionPolicyCommand(
                idempotency_key=idem(), obligation_id=request.aggregate_id, expected_version=1,
                applicable_regimes=[
                    {"regime": "21_CFR_803", "rule_version": "v1", "calculated_duration_days": 3650},
                    {"regime": "21_CFR_4", "rule_version": "v1", "calculated_duration_days": 5475},
                ],
            ), owner.id,
        )
    obligation = await _get(db, RegulatoryObligation, request.aggregate_id)
    assert obligation.retention_basis["selected_longest_days"] == 5475

    # PMO-FR-027: a later, shorter calculation never silently reduces the already-selected longest.
    async with db.begin():
        await commands.calculate_postmarket_retention_policy(
            db, commands.CalculatePostmarketRetentionPolicyCommand(
                idempotency_key=idem(), obligation_id=request.aggregate_id, expected_version=2,
                applicable_regimes=[{"regime": "21_CFR_803", "rule_version": "v2", "calculated_duration_days": 1825}],
            ), owner.id,
        )
    obligation = await _get(db, RegulatoryObligation, request.aggregate_id)
    assert obligation.retention_basis["selected_longest_days"] == 5475


@pytest.mark.asyncio
async def test_legal_hold_is_recorded_and_visible_on_the_obligation(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "9")
        request = await commands.create_fda_information_request_task(
            db, commands.CreateFDAInformationRequestTaskCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], application_id="NDA-000123",
                agency_reference="CDER-2026-1111", requested_events_or_information="pending litigation records",
                due_at=datetime.now(timezone.utc) + timedelta(days=30), received_at=datetime.now(timezone.utc),
            ), owner.id,
        )

    async with db.begin():
        await commands.place_postmarket_legal_hold(
            db, commands.PlacePostmarketLegalHoldCommand(
                idempotency_key=idem(), obligation_id=request.aggregate_id, expected_version=1,
                reason="pending litigation", authority="General Counsel",
            ), owner.id,
        )
    obligation = await _get(db, RegulatoryObligation, request.aggregate_id)
    assert obligation.legal_hold is True
    assert obligation.legal_hold_authority == "General Counsel"


@pytest.mark.asyncio
async def test_unified_regulatory_calendar_reports_overdue_items(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "10")
        await commands.create_fda_information_request_task(
            db, commands.CreateFDAInformationRequestTaskCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], application_id="NDA-000123",
                agency_reference="CDER-2026-2222", requested_events_or_information="overdue example",
                due_at=datetime.now(timezone.utc) - timedelta(days=1), received_at=datetime.now(timezone.utc) - timedelta(days=10),
            ), owner.id,
        )
    calendar = await commands.get_unified_regulatory_calendar(db, seeded["site_id"])
    assert calendar["overdue_count"] >= 1


@pytest.mark.asyncio
async def test_create_applicant_relationship_via_http_requires_auth(client, db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "11")

    from tests.conftest import auth_headers, login
    body = {
        "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "product_version_reference": {"product_version_id": str(uuid.uuid4())},
        "applicant_role": "COMBINATION_PRODUCT_APPLICANT", "applicant_name": "Combo Product Co",
        "address": {"line1": "1 Combo Blvd"}, "contact": {"email": "regulatory@combo.example"},
    }
    resp = await client.post("/postmarket/v1/applicant-relationships", json=body)
    assert resp.status_code == 401

    token = await login(client, "pmo.admin11")
    resp = await client.post("/postmarket/v1/applicant-relationships", json=body, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
