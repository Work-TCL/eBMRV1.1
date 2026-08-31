"""Document 58 (SPEC-PM-001, PMS-FR-001..034): postmarket source registration, safety case intake/
product-resolution/classification/follow-up/duplicate-linking, surveillance metrics (Vault-backed
reproducibility), signal-rule recurrence detection, and the safety signal lifecycle including escalation
to real QMS modules (CAPA/Field Action). See docs/generated/18_SPEC_GAPS.md SG-154/155/156.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.postmarket import commands as pm_commands
from app.modules.postmarket.models import SafetyCase, SafetySignal
from app.modules.qms.capa_models import CapaRecord
from app.modules.qms.field_action_models import FieldAction
from app.modules.signature.models import SignaturePolicy
from app.mutation.errors import (
    ExpectednessReferenceRequiredError,
    InvalidTransitionError,
    NotFoundError,
    PmsCaseDuplicateSourceError,
    ProductUnresolvedError,
    SafetyClassificationIncompleteError,
    SignalScopeInvalidError,
    StaleSafetyCaseVersionError,
    ValidationFailedError,
)
from app.mutation.errors import SignaturePolicyUnresolvedError
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, tag):
    user = User(
        username=f"pm.admin{tag}", email=f"pm.admin{tag}@example.com", full_name="PM Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


def _allow_signal_actions(db):
    """SG-156: no Document 106 resolution exists for safety_signal open/assess/escalate -- tests that
    exercise the business logic beyond fail-closed seed a permissive local policy, same precedent
    test_qms_deviation.py uses for its own disposition/close SG-138 gap."""
    for action in ("open", "assess", "escalate"):
        db.add(SignaturePolicy(record_type="safety_signal", action=action, meaning="Performed", signature_required=False))


async def _get(db, model, obj_id):
    """A bare `db.get()`/`session.execute()` outside `async with db.begin()` triggers SQLAlchemy 2.0
    autobegin, which then collides with the *next* explicit `async with db.begin()` in the same test
    ("A transaction is already begun on this Session") -- every read in this file goes through its own
    short-lived transaction instead."""
    async with db.begin():
        return await db.get(model, obj_id)


async def _create_case(db, seeded, owner_id, **overrides):
    cmd = pm_commands.CreateSafetyCaseLinkCommand(
        idempotency_key=idem(), site_id=seeded["site_id"], safety_case_number=f"SC-{uuid.uuid4().hex[:8]}",
        source_record_type="complaint_record", source_record_id=uuid.uuid4(), source_record_version=1,
        **overrides,
    )
    return await pm_commands.create_safety_case_link(db, cmd, owner_id)


@pytest.mark.asyncio
async def test_create_safety_case_link_and_duplicate_source_rejected(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "1")
    source_id = uuid.uuid4()
    async with db.begin():
        cmd = pm_commands.CreateSafetyCaseLinkCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], safety_case_number="SC-0001",
            source_record_type="complaint_record", source_record_id=source_id, source_record_version=1,
        )
        receipt = await pm_commands.create_safety_case_link(db, cmd, owner.id)
    case = await _get(db, SafetyCase, receipt.aggregate_id)
    assert case.state == "RECEIVED"
    assert case.identity_resolution_state == "UNKNOWN_QUEUE"

    async with db.begin():
        dup_cmd = pm_commands.CreateSafetyCaseLinkCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], safety_case_number="SC-0002",
            source_record_type="complaint_record", source_record_id=source_id, source_record_version=1,
        )
        with pytest.raises(PmsCaseDuplicateSourceError):
            await pm_commands.create_safety_case_link(db, dup_cmd, owner.id)


@pytest.mark.asyncio
async def test_resolve_marketed_product_unknown_then_resolved(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "2")
        receipt = await _create_case(db, seeded, owner.id)

    async with db.begin():
        with pytest.raises(ProductUnresolvedError):
            await pm_commands.resolve_marketed_product(
                db, pm_commands.ResolveMarketedProductCommand(
                    idempotency_key=idem(), case_id=receipt.aggregate_id, expected_version=1, mark_resolved=True,
                ), owner.id,
            )

    async with db.begin():
        product_id = uuid.uuid4()
        await pm_commands.resolve_marketed_product(
            db, pm_commands.ResolveMarketedProductCommand(
                idempotency_key=idem(), case_id=receipt.aggregate_id, expected_version=1,
                marketed_product_id=product_id, mark_resolved=True,
            ), owner.id,
        )
    case = await db.get(SafetyCase, receipt.aggregate_id)
    assert case.identity_resolution_state == "RESOLVED"
    assert case.marketed_product_id == product_id
    assert case.state == "IDENTITY_RESOLUTION"
    assert case.version == 2


@pytest.mark.asyncio
async def test_classify_case_requires_expectedness_reference_then_versions_history(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "3")
        receipt = await _create_case(db, seeded, owner.id)

    async with db.begin():
        with pytest.raises(SafetyClassificationIncompleteError):
            await pm_commands.classify_safety_case(
                db, pm_commands.ClassifySafetyCaseCommand(
                    idempotency_key=idem(), case_id=receipt.aggregate_id, expected_version=1,
                    classification={}, rationale="empty",
                ), owner.id,
            )

    async with db.begin():
        with pytest.raises(ExpectednessReferenceRequiredError):
            await pm_commands.classify_safety_case(
                db, pm_commands.ClassifySafetyCaseCommand(
                    idempotency_key=idem(), case_id=receipt.aggregate_id, expected_version=1,
                    classification={"expectedness": "unexpected"}, rationale="missing ref",
                ), owner.id,
            )

    async with db.begin():
        await pm_commands.classify_safety_case(
            db, pm_commands.ClassifySafetyCaseCommand(
                idempotency_key=idem(), case_id=receipt.aggregate_id, expected_version=1,
                classification={"severity": "serious"}, constituent_attribution="DEVICE", rationale="first pass",
            ), owner.id,
        )
    case = await _get(db, SafetyCase, receipt.aggregate_id)
    assert case.state == "INITIAL_CLASSIFICATION"
    assert case.current_classification_version == 1
    assert case.classification_history == []

    # Reclassification (PMS-FR-016: no judgment is ever destroyed) appends the prior version.
    async with db.begin():
        await pm_commands.classify_safety_case(
            db, pm_commands.ClassifySafetyCaseCommand(
                idempotency_key=idem(), case_id=receipt.aggregate_id, expected_version=2,
                classification={"severity": "non-serious"}, rationale="reassessed after review",
            ), owner.id,
        )
    case = await db.get(SafetyCase, receipt.aggregate_id)
    assert case.current_classification_version == 2
    assert len(case.classification_history) == 1
    assert case.classification_history[0]["classification"] == {"severity": "serious"}


@pytest.mark.asyncio
async def test_followup_sets_reassessment_flag_and_stale_version_forces_refresh(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "4")
        receipt = await _create_case(db, seeded, owner.id)

    async with db.begin():
        await pm_commands.add_safety_case_followup(
            db, pm_commands.AddSafetyCaseFollowupCommand(
                idempotency_key=idem(), case_id=receipt.aggregate_id, expected_version=1,
                followup_receipt_at=datetime.now(timezone.utc), source_reference={"channel": "phone"},
                new_information={"detail": "new adverse event reported"},
            ), owner.id,
        )
    case = await _get(db, SafetyCase, receipt.aggregate_id)
    assert case.reassessment_required is True
    assert case.version == 2

    # PMS-FR-016/# 12: a stale expected_version (as if a reviewer's screen is out of date) is rejected.
    async with db.begin():
        with pytest.raises(StaleSafetyCaseVersionError):
            await pm_commands.add_safety_case_followup(
                db, pm_commands.AddSafetyCaseFollowupCommand(
                    idempotency_key=idem(), case_id=receipt.aggregate_id, expected_version=1,
                    followup_receipt_at=datetime.now(timezone.utc), source_reference={"channel": "phone"},
                    new_information={"detail": "concurrent update"},
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_duplicate_candidates_found_and_linked_without_deletion(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "5")
        r1 = await _create_case(db, seeded, owner.id)
        r2 = await _create_case(db, seeded, owner.id)

    async with db.begin():
        candidates = await pm_commands.find_probable_duplicates(
            db, pm_commands.FindProbableDuplicatesCommand(idempotency_key=idem(), case_id=r1.aggregate_id),
        )
    assert any(c["case_id"] == str(r2.aggregate_id) for c in candidates)

    async with db.begin():
        await pm_commands.link_duplicate_cases(
            db, pm_commands.LinkDuplicateCasesCommand(
                idempotency_key=idem(), canonical_case_id=r1.aggregate_id,
                duplicate_case_ids=[r2.aggregate_id], rationale="same report, two intake channels",
            ), owner.id,
        )
    # PMS-FR-015: linked, never deleted -- both rows still exist.
    dup = await db.get(SafetyCase, r2.aggregate_id)
    canonical = await db.get(SafetyCase, r1.aggregate_id)
    assert dup.canonical_case_id == canonical.id
    assert canonical is not None and dup is not None


@pytest.mark.asyncio
async def test_calculate_surveillance_metric_is_reproducible_via_vault(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "6")
        await _create_case(db, seeded, owner.id)

    cmd = pm_commands.CalculateSurveillanceMetricCommand(
        idempotency_key=idem(), metric_definition_version="v1", scope={"site_id": str(seeded["site_id"])},
        period={}, source_cutoff=datetime.now(timezone.utc),
    )
    async with db.begin():
        first = await pm_commands.calculate_surveillance_metric(db, cmd, owner.id)
    # Same (metric_definition_version, scope, period) key -- PMS-FR-019: denominator explicitly uncertain
    # when not supplied, and the historical formula version reproduces the same stored Vault snapshot.
    async with db.begin():
        second = await pm_commands.calculate_surveillance_metric(db, cmd, owner.id)
    assert first["vault_object_id"] == second["vault_object_id"]
    assert first["denominator_uncertain"] is True


@pytest.mark.asyncio
async def test_evaluate_signal_rules_detects_recurrence(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "7")
        await _create_case(db, seeded, owner.id)
        await _create_case(db, seeded, owner.id)

    triggers = await pm_commands.evaluate_signal_rules(
        db, pm_commands.EvaluateSignalRulesCommand(
            idempotency_key=idem(), signal_rule_versions=["v1"], case_scope={"site_id": str(seeded["site_id"])},
        ),
    )
    assert any(t["trigger_type"] == "RECURRENCE" and t["source_record_type"] == "complaint_record" for t in triggers)


@pytest.mark.asyncio
async def test_open_signal_fails_closed_without_signature_policy(db, seeded):
    """SG-156: no Document 106 resolution exists yet -- proves the Mutation Gateway actually fails
    closed rather than silently defaulting."""
    async with db.begin():
        owner = await _make_admin(db, seeded, "8")
        receipt = await _create_case(db, seeded, owner.id)

    async with db.begin():
        with pytest.raises(SignaturePolicyUnresolvedError):
            await pm_commands.open_safety_signal(
                db, pm_commands.OpenSafetySignalCommand(
                    idempotency_key=idem(), site_id=seeded["site_id"], signal_code=f"SIG-{uuid.uuid4().hex[:8]}",
                    detection_source="REVIEWER", trigger_refs=[], population_definition={"product": "x"},
                    case_ids_for_snapshot=[receipt.aggregate_id], rationale="manual review flagged a cluster",
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_signal_lifecycle_assess_invalid_transition_and_escalate_to_capa(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "9")
        _allow_signal_actions(db)
        receipt = await _create_case(db, seeded, owner.id)

    async with db.begin():
        with pytest.raises(SignalScopeInvalidError):
            await pm_commands.open_safety_signal(
                db, pm_commands.OpenSafetySignalCommand(
                    idempotency_key=idem(), site_id=seeded["site_id"], signal_code="SIG-BAD",
                    detection_source="NOT_A_SOURCE", trigger_refs=[], population_definition={"product": "x"},
                    case_ids_for_snapshot=[receipt.aggregate_id], rationale="bad detection_source",
                ), owner.id,
            )

    async with db.begin():
        signal_receipt = await pm_commands.open_safety_signal(
            db, pm_commands.OpenSafetySignalCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], signal_code=f"SIG-{uuid.uuid4().hex[:8]}",
                detection_source="REVIEWER", trigger_refs=[{"kind": "manual"}], population_definition={"product": "x"},
                case_ids_for_snapshot=[receipt.aggregate_id], rationale="manual review flagged a cluster",
            ), owner.id,
        )
    signal = await _get(db, SafetySignal, signal_receipt.aggregate_id)
    assert signal.state == "DETECTED"
    assert signal.case_snapshot["cases"][0]["case_id"] == str(receipt.aggregate_id)

    # DETECTED cannot jump straight to CONFIRMED.
    async with db.begin():
        with pytest.raises(InvalidTransitionError):
            await pm_commands.assess_safety_signal(
                db, pm_commands.AssessSafetySignalCommand(
                    idempotency_key=idem(), signal_id=signal.id, expected_version=1,
                    assessment={"note": "skip ahead"}, next_state="CONFIRMED",
                ), owner.id,
            )

    async with db.begin():
        await pm_commands.assess_safety_signal(
            db, pm_commands.AssessSafetySignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=1,
                assessment={"note": "triaged"}, next_state="TRIAGE",
            ), owner.id,
        )
    async with db.begin():
        await pm_commands.assess_safety_signal(
            db, pm_commands.AssessSafetySignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=2,
                assessment={"note": "assessed"}, next_state="ASSESSMENT",
            ), owner.id,
        )
    async with db.begin():
        await pm_commands.assess_safety_signal(
            db, pm_commands.AssessSafetySignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=3,
                assessment={"clinical": "confirmed pattern"}, next_state="CONFIRMED",
            ), owner.id,
        )
    signal = await _get(db, SafetySignal, signal_receipt.aggregate_id)
    assert signal.state == "CONFIRMED"
    assert len(signal.assessment_history) == 2  # the TRIAGE and ASSESSMENT assessments, not the current one

    # PMS-FR-024: escalation calls the real CAPA creation command and stores the cross-link.
    async with db.begin():
        escalate_receipt = await pm_commands.escalate_signal_to_qms_or_regulatory(
            db, pm_commands.EscalateSignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=4, target_module="CAPA",
                target_command={
                    "site_id": str(seeded["site_id"]), "capa_number": f"CAPA-{uuid.uuid4().hex[:8]}",
                    "source_type": "trend", "source_id": str(signal.id), "source_version": signal.version,
                    "problem_statement": "recurring device malfunction pattern", "risk_class": "high",
                    "owner_subject_id": str(owner.id), "target_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "root_cause_ref": {"proactive_rationale": "signal-driven, no investigation on file yet"},
                },
                rationale="confirmed signal requires corrective action",
            ), owner.id,
        )
    # escalate_receipt.aggregate_id is the *signal's* receipt (the postmarket aggregate this command
    # mutates) -- the target CAPA's id is on escalation_links, not on this function's own return value.
    signal = await _get(db, SafetySignal, signal_receipt.aggregate_id)
    assert len(signal.escalation_links) == 1
    assert signal.escalation_links[0]["target_module"] == "CAPA"
    assert escalate_receipt.aggregate_id == signal.id
    capa = await _get(db, CapaRecord, uuid.UUID(signal.escalation_links[0]["target_aggregate_id"]))
    assert capa is not None
    assert str(capa.source_id) == str(signal.id)


@pytest.mark.asyncio
async def test_escalate_signal_to_field_action_and_reportability_track_not_yet_implemented(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "10")
        _allow_signal_actions(db)
        receipt = await _create_case(db, seeded, owner.id)
        signal_receipt = await pm_commands.open_safety_signal(
            db, pm_commands.OpenSafetySignalCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], signal_code=f"SIG-{uuid.uuid4().hex[:8]}",
                detection_source="RULE", rule_version="v1", trigger_refs=[{"kind": "recurrence"}],
                population_definition={"product": "x"}, case_ids_for_snapshot=[receipt.aggregate_id],
                rationale="recurrence trigger",
            ), owner.id,
        )
    async with db.begin():
        signal = await db.get(SafetySignal, signal_receipt.aggregate_id)
        signal.state = "CONFIRMED"  # test-only shortcut past the lifecycle already covered above

    async with db.begin():
        fa_receipt = await pm_commands.escalate_signal_to_qms_or_regulatory(
            db, pm_commands.EscalateSignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=signal.version, target_module="FIELD_ACTION",
                target_command={
                    "site_id": str(seeded["site_id"]), "action_number": f"FA-{uuid.uuid4().hex[:8]}",
                    "action_type": "correction", "trigger_ref": {"source_type": "trend", "signal_id": str(signal.id)},
                },
                rationale="confirmed device signal requires a field correction",
            ), owner.id,
        )
    signal = await _get(db, SafetySignal, signal_receipt.aggregate_id)
    assert fa_receipt.aggregate_id == signal.id  # this function's own receipt is for the signal, not the target
    fa = await _get(db, FieldAction, uuid.UUID(signal.escalation_links[0]["target_aggregate_id"]))
    assert fa is not None

    async with db.begin():
        signal = await db.get(SafetySignal, signal_receipt.aggregate_id)
        with pytest.raises(ValidationFailedError):
            await pm_commands.escalate_signal_to_qms_or_regulatory(
                db, pm_commands.EscalateSignalCommand(
                    idempotency_key=idem(), signal_id=signal.id, expected_version=signal.version,
                    target_module="REPORTABILITY_TRACK", target_command={}, rationale="needs Document 59",
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_same_receipt(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "11")
    key = idem()
    cmd = pm_commands.RegisterPostmarketSourceCommand(
        idempotency_key=key, site_id=seeded["site_id"], source_type="LITERATURE",
        organization_or_system="PubMed monitoring", channel="monthly literature review", owner_subject_id=owner.id,
    )
    async with db.begin():
        first = await pm_commands.register_postmarket_source(db, cmd, owner.id)
    async with db.begin():
        second = await pm_commands.register_postmarket_source(db, cmd, owner.id)
    assert first.aggregate_id == second.aggregate_id


@pytest.mark.asyncio
async def test_register_source_rejects_unknown_source_type(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "12")
        from app.mutation.errors import PmsSourceInvalidError
        with pytest.raises(PmsSourceInvalidError):
            await pm_commands.register_postmarket_source(
                db, pm_commands.RegisterPostmarketSourceCommand(
                    idempotency_key=idem(), site_id=seeded["site_id"], source_type="NOT_A_TYPE",
                    organization_or_system="x", channel="x", owner_subject_id=owner.id,
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_dashboard_reflects_open_cases_and_backlog(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "13")
        r1 = await _create_case(db, seeded, owner.id)
    async with db.begin():
        await pm_commands.add_safety_case_followup(
            db, pm_commands.AddSafetyCaseFollowupCommand(
                idempotency_key=idem(), case_id=r1.aggregate_id, expected_version=1,
                followup_receipt_at=datetime.now(timezone.utc), source_reference={"channel": "email"},
                new_information={"detail": "additional report"},
            ), owner.id,
        )
    summary = await pm_commands.get_postmarket_dashboard(db, seeded["site_id"])
    assert summary["open_cases"] >= 1
    assert summary["followup_backlog"] >= 1


@pytest.mark.asyncio
async def test_register_source_via_http_requires_auth(client, db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "14")
    resp = await client.post(
        "/postmarket/v1/sources",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "source_type": "REGULATOR",
            "organization_or_system": "FDA MedWatch", "channel": "portal feed", "owner_subject_id": str(owner.id),
        },
    )
    assert resp.status_code == 401

    token = await login(client, "pm.admin14")
    resp = await client.post(
        "/postmarket/v1/sources",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "source_type": "REGULATOR",
            "organization_or_system": "FDA MedWatch", "channel": "portal feed", "owner_subject_id": str(owner.id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_build_periodic_safety_dataset_is_reproducible_and_scoped_to_interval(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "15")
        in_scope = await _create_case(db, seeded, owner.id)

    cmd = pm_commands.BuildPeriodicSafetyDatasetCommand(
        idempotency_key=idem(), application_id="NDA-000123", interval_start=datetime.now(timezone.utc) - timedelta(days=90),
        interval_end=datetime.now(timezone.utc) + timedelta(days=1), report_type="PSUR", cutoff=datetime.now(timezone.utc),
        site_id=seeded["site_id"],
    )
    async with db.begin():
        first = await pm_commands.build_periodic_safety_dataset(db, cmd, owner.id)
    assert any(ref["case_id"] == str(in_scope.aggregate_id) for ref in first["case_refs"])

    # PMS-FR-032: same (application_id, report_type, interval) key with unchanged underlying data
    # reproduces the same frozen Vault snapshot rather than creating a new one each call.
    async with db.begin():
        second = await pm_commands.build_periodic_safety_dataset(db, cmd, owner.id)
    assert first["vault_object_id"] == second["vault_object_id"]
