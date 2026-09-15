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
from app.modules.postmarket import obligation_commands
from app.modules.postmarket.models import SafetyCase, SafetySignal
from app.modules.postmarket.obligation_models import CorrectionRemovalRegulatoryRecord
from app.modules.qms.capa_models import CapaRecord
from app.modules.qms.field_action_models import FieldAction
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    ExpectednessReferenceRequiredError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    PmsCaseDuplicateSourceError,
    ProductUnresolvedError,
    SafetyClassificationIncompleteError,
    SignalScopeInvalidError,
    StaleSafetyCaseVersionError,
    ValidationFailedError,
)
from app.mutation.hashing import sha256_hex
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


async def _sign(db, *, actor_id, record_version, record_hash):
    """SG-156 RESOLVED_APPROVED 2026-09-14: safety_signal.open/assess/escalate now really require a
    signature (conftest.py's global seed), so tests exercising the successful path create a real
    challenge and consume it -- no independence requirement, so the same actor signs throughout."""
    challenge = await signature_service.create_challenge(
        db, user_id=actor_id, record_type="safety_signal", record_id=uuid.uuid4(),
        record_version=record_version, record_hash=record_hash, meaning="Approved",
    )
    await db.flush()
    return challenge.id


async def _get(db, model, obj_id):
    """A bare `db.get()`/`session.execute()` outside `async with db.begin()` triggers SQLAlchemy 2.0
    autobegin, which then collides with the *next* explicit `async with db.begin()` in the same test
    ("A transaction is already begun on this Session") -- every read in this file goes through its own
    short-lived transaction instead. See `_get_fresh()` below for a test that also mutates through the
    HTTP `client` fixture's own separate session and needs a guaranteed-fresh read back through `db`."""
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
async def test_open_signal_requires_a_real_signature(db, seeded):
    """SG-156 RESOLVED_APPROVED 2026-09-14: opening a safety signal now really requires a signature
    (Document 106 resolved to "per RBAC grant, no independence") -- calling without a challenge/reauth
    is rejected, not silently accepted; the fail-closed guarantee moved from "policy unresolved" to
    "signature actually required", which is the real regulated behaviour this gap always meant."""
    async with db.begin():
        owner = await _make_admin(db, seeded, "8")
        receipt = await _create_case(db, seeded, owner.id)

    async with db.begin():
        with pytest.raises(MissingSignatureError):
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

    signal_code = f"SIG-{uuid.uuid4().hex[:8]}"
    async with db.begin():
        challenge_id = await _sign(db, actor_id=owner.id, record_version=1, record_hash=sha256_hex({"signal_code": signal_code}))
        signal_receipt = await pm_commands.open_safety_signal(
            db, pm_commands.OpenSafetySignalCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], signal_code=signal_code,
                detection_source="REVIEWER", trigger_refs=[{"kind": "manual"}], population_definition={"product": "x"},
                case_ids_for_snapshot=[receipt.aggregate_id], rationale="manual review flagged a cluster",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
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
        signal = await db.get(SafetySignal, signal.id)
        challenge_id = await _sign(db, actor_id=owner.id, record_version=signal.version, record_hash=pm_commands._signal_hash(signal))
        await pm_commands.assess_safety_signal(
            db, pm_commands.AssessSafetySignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=1,
                assessment={"note": "triaged"}, next_state="TRIAGE",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
    async with db.begin():
        signal = await db.get(SafetySignal, signal.id)
        challenge_id = await _sign(db, actor_id=owner.id, record_version=signal.version, record_hash=pm_commands._signal_hash(signal))
        await pm_commands.assess_safety_signal(
            db, pm_commands.AssessSafetySignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=2,
                assessment={"note": "assessed"}, next_state="ASSESSMENT",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
    async with db.begin():
        signal = await db.get(SafetySignal, signal.id)
        challenge_id = await _sign(db, actor_id=owner.id, record_version=signal.version, record_hash=pm_commands._signal_hash(signal))
        await pm_commands.assess_safety_signal(
            db, pm_commands.AssessSafetySignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=3,
                assessment={"clinical": "confirmed pattern"}, next_state="CONFIRMED",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
    signal = await _get(db, SafetySignal, signal_receipt.aggregate_id)
    assert signal.state == "CONFIRMED"
    assert len(signal.assessment_history) == 2  # the TRIAGE and ASSESSMENT assessments, not the current one

    # PMS-FR-024: escalation calls the real CAPA creation command and stores the cross-link.
    async with db.begin():
        signal = await db.get(SafetySignal, signal.id)
        challenge_id = await _sign(db, actor_id=owner.id, record_version=signal.version, record_hash=pm_commands._signal_hash(signal))
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
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
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
        receipt = await _create_case(db, seeded, owner.id)
        signal_code = f"SIG-{uuid.uuid4().hex[:8]}"
        challenge_id = await _sign(db, actor_id=owner.id, record_version=1, record_hash=sha256_hex({"signal_code": signal_code}))
        signal_receipt = await pm_commands.open_safety_signal(
            db, pm_commands.OpenSafetySignalCommand(
                idempotency_key=idem(), site_id=seeded["site_id"], signal_code=signal_code,
                detection_source="RULE", rule_version="v1", trigger_refs=[{"kind": "recurrence"}],
                population_definition={"product": "x"}, case_ids_for_snapshot=[receipt.aggregate_id],
                rationale="recurrence trigger", challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), owner.id,
        )
    async with db.begin():
        signal = await db.get(SafetySignal, signal_receipt.aggregate_id)
        signal.state = "CONFIRMED"  # test-only shortcut past the lifecycle already covered above

    async with db.begin():
        signal = await db.get(SafetySignal, signal_receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=owner.id, record_version=signal.version, record_hash=pm_commands._signal_hash(signal))
        fa_receipt = await pm_commands.escalate_signal_to_qms_or_regulatory(
            db, pm_commands.EscalateSignalCommand(
                idempotency_key=idem(), signal_id=signal.id, expected_version=signal.version, target_module="FIELD_ACTION",
                target_command={
                    "site_id": str(seeded["site_id"]), "action_number": f"FA-{uuid.uuid4().hex[:8]}",
                    "action_type": "correction", "trigger_ref": {"source_type": "trend", "signal_id": str(signal.id)},
                },
                rationale="confirmed device signal requires a field correction",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
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


async def _get_fresh(db, model, obj_id):
    """Like `_get()`, but forces a real re-read even if `db`'s identity map already holds a
    (possibly stale) copy of this row -- needed only for a test that mutates through the HTTP `client`
    fixture's own separate, request-scoped session while reading back through `db`. `app/core/db.py::
    SessionLocal` sets `expire_on_commit=False`, so `db` never learns about another session's commit on
    its own. A session-wide `db.expire_all()` here (instead of `populate_existing`) was tried first and
    broke unrelated tests elsewhere in this file with a `MissingGreenlet` error -- `populate_existing`
    is scoped to just this one query and does not have that effect."""
    async with db.begin():
        return await db.get(model, obj_id, populate_existing=True)


# ---------------------------------------------------------------------------------------------------
# CorrectionRemovalRegulatoryRecord -- SG-160 partial resolution (2026-09-14, project-owner-directed).
# Document 106 rows 129/130: "Authorized corrector + independent approver", count 2, corrector and
# approver MUST differ, reason mandatory. Reuses vault/commands.py's own chain-signature mechanism
# (enforce_chain_signer_policy/chain_signatures_so_far, SG-035 pair 4) -- same test shape as
# test_vault.py::test_correction_two_signature_chain_succeeds.
# ---------------------------------------------------------------------------------------------------


async def test_correction_removal_assessment_and_decision_two_signature_chains(client, db, seeded):
    async with db.begin():
        corrector = await _make_admin(db, seeded, "cr1")
        approver = await _make_admin(db, seeded, "cr2")
    corrector_token = await login(client, "pm.admincr1")
    approver_token = await login(client, "pm.admincr2")

    field_action_reference = {"field_action_id": str(uuid.uuid4()), "scope": "lot-recall"}
    initiation_at = datetime.now(timezone.utc).isoformat()

    # --- Assessment creation (row 130): unsigned request, then a 2-signature chain to open it ---
    resp = await client.post(
        f"/postmarket/v1/field-actions/{field_action_reference['field_action_id']}/correction-removal-assessment",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]),
            "field_action_reference": field_action_reference, "initiation_at": initiation_at,
        },
        headers=auth_headers(corrector_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is None
    record_id = resp.json()["aggregate_id"]
    record = await _get_fresh(db, CorrectionRemovalRegulatoryRecord, record_id)
    assert record.state == "PENDING_ASSESSMENT_APPROVAL"

    # Unsigned attempt to approve is blocked.
    unsigned = await client.post(
        f"/postmarket/v1/correction-removal/{record_id}/assessment-signatures",
        json={"idempotency_key": idem(), "record_id": record_id, "field_action_reference": field_action_reference},
        headers=auth_headers(corrector_token),
    )
    assert unsigned.status_code == 428, unsigned.text
    assert unsigned.json()["code"] == "MISSING_SIGNATURE"

    # Position 1 (corrector).
    challenge_1 = (
        await client.post(
            f"/postmarket/v1/correction-removal/{record_id}/assessment-signature-challenges",
            json={"field_action_reference": field_action_reference}, headers=auth_headers(corrector_token),
        )
    ).json()
    assert challenge_1["chain_position"] == 1 and challenge_1["signature_count"] == 2
    resp1 = await client.post(
        f"/postmarket/v1/correction-removal/{record_id}/assessment-signatures",
        json={
            "idempotency_key": idem(), "record_id": record_id, "field_action_reference": field_action_reference,
            "challenge_id": challenge_1["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(corrector_token),
    )
    assert resp1.status_code == 200, resp1.text
    record = await _get_fresh(db, CorrectionRemovalRegulatoryRecord, record_id)
    assert record.state == "PENDING_ASSESSMENT_APPROVAL"  # still not open -- only one of two signatures

    # SoD: the same corrector cannot also sign position 2.
    same_actor_challenge = (
        await client.post(
            f"/postmarket/v1/correction-removal/{record_id}/assessment-signature-challenges",
            json={"field_action_reference": field_action_reference}, headers=auth_headers(corrector_token),
        )
    ).json()
    same_actor_resp = await client.post(
        f"/postmarket/v1/correction-removal/{record_id}/assessment-signatures",
        json={
            "idempotency_key": idem(), "record_id": record_id, "field_action_reference": field_action_reference,
            "challenge_id": same_actor_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(corrector_token),
    )
    assert same_actor_resp.status_code == 409, same_actor_resp.text
    assert same_actor_resp.json()["code"] == "SOD_INDEPENDENCE_REQUIRED"

    # Position 2 (independent approver) -- now the assessment opens.
    challenge_2 = (
        await client.post(
            f"/postmarket/v1/correction-removal/{record_id}/assessment-signature-challenges",
            json={"field_action_reference": field_action_reference}, headers=auth_headers(approver_token),
        )
    ).json()
    assert challenge_2["chain_position"] == 2
    resp2 = await client.post(
        f"/postmarket/v1/correction-removal/{record_id}/assessment-signatures",
        json={
            "idempotency_key": idem(), "record_id": record_id, "field_action_reference": field_action_reference,
            "challenge_id": challenge_2["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(approver_token),
    )
    assert resp2.status_code == 200, resp2.text
    record = await _get_fresh(db, CorrectionRemovalRegulatoryRecord, record_id)
    assert record.state == "OPEN"
    assert len(record.assessment_approval_signatures) == 2

    # --- Reportability decision (row 129): decide() itself consumes position 1 (record_id already
    # exists), approve_correction_removal_decision() consumes position 2 and applies the decision. ---
    decision_challenge_1 = (
        await client.post(
            f"/postmarket/v1/correction-removal/{record_id}/decision-signature-challenges",
            json={"reportable": True, "rationale": "Confirmed defect affects distributed lots"},
            headers=auth_headers(corrector_token),
        )
    ).json()
    assert decision_challenge_1["chain_position"] == 1
    decide_resp = await client.post(
        f"/postmarket/v1/correction-removal/{record_id}/decision",
        json={
            "idempotency_key": idem(), "record_id": record_id, "expected_version": record.version,
            "reportable": True, "rationale": "Confirmed defect affects distributed lots",
            "challenge_id": decision_challenge_1["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(corrector_token),
    )
    assert decide_resp.status_code == 200, decide_resp.text
    record = await _get_fresh(db, CorrectionRemovalRegulatoryRecord, record_id)
    assert record.state == "PENDING_DECISION_APPROVAL"
    assert record.assessment_state is None  # not applied yet -- only staged once fully signed

    decision_challenge_2 = (
        await client.post(
            f"/postmarket/v1/correction-removal/{record_id}/decision-signature-challenges",
            json={"reportable": True, "rationale": "Confirmed defect affects distributed lots"},
            headers=auth_headers(approver_token),
        )
    ).json()
    assert decision_challenge_2["chain_position"] == 2
    approve_decision_resp = await client.post(
        f"/postmarket/v1/correction-removal/{record_id}/decision-signatures",
        json={
            "idempotency_key": idem(), "record_id": record_id, "expected_version": record.version,
            "reportable": True, "rationale": "Confirmed defect affects distributed lots",
            "challenge_id": decision_challenge_2["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(approver_token),
    )
    assert approve_decision_resp.status_code == 200, approve_decision_resp.text
    record = await _get_fresh(db, CorrectionRemovalRegulatoryRecord, record_id)
    assert record.state == "DECIDED"
    assert record.assessment_state == "REPORTABLE"
    assert record.regime == "PART_806_REPORT"
    assert record.due_at is not None
    assert len(record.decision_approval_signatures) == 2


@pytest.mark.asyncio
async def test_open_assess_escalate_signal_via_http_signature_challenges(client, db, seeded):
    """Every other signal test in this file exercises SG-156's signature requirement at the command
    layer via `_sign()` (direct `signature_service.create_challenge()`). This is the one test that
    proves the actual HTTP endpoints a real caller (the frontend) uses:
    `POST /signals/signature-challenges` (open -- signs a not-yet-created record), `POST /signals/
    {id}/assessment-signature-challenges` and `POST /signals/{id}/escalation-signature-challenges`.
    These endpoints didn't exist until now -- SG-156 made open/assess/escalate really require a
    signature, but nothing exposed a way to obtain a challenge_id for them over HTTP."""
    async with db.begin():
        owner = await _make_admin(db, seeded, "http1")
        case_receipt = await _create_case(db, seeded, owner.id)
    token = await login(client, "pm.adminhttp1")
    signal_code = f"SIG-HTTP-{uuid.uuid4().hex[:8]}"

    # Unsigned open attempt is blocked.
    unsigned = await client.post(
        "/postmarket/v1/signals",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "signal_code": signal_code,
            "detection_source": "REVIEWER", "trigger_refs": [{"kind": "manual"}], "population_definition": {"product": "x"},
            "case_ids_for_snapshot": [str(case_receipt.aggregate_id)], "rationale": "manual review flagged a cluster",
        },
        headers=auth_headers(token),
    )
    assert unsigned.status_code == 428, unsigned.text
    assert unsigned.json()["code"] == "MISSING_SIGNATURE"

    open_challenge = (
        await client.post("/postmarket/v1/signals/signature-challenges", json={"signal_code": signal_code}, headers=auth_headers(token))
    ).json()
    assert open_challenge["meaning"] == "Approved"
    open_resp = await client.post(
        "/postmarket/v1/signals",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "signal_code": signal_code,
            "detection_source": "REVIEWER", "trigger_refs": [{"kind": "manual"}], "population_definition": {"product": "x"},
            "case_ids_for_snapshot": [str(case_receipt.aggregate_id)], "rationale": "manual review flagged a cluster",
            "challenge_id": open_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert open_resp.status_code == 200, open_resp.text
    signal_id = open_resp.json()["aggregate_id"]
    signal = await _get_fresh(db, SafetySignal, signal_id)
    assert signal.state == "DETECTED"

    # DETECTED -> TRIAGE -> ASSESSMENT -> CONFIRMED, each step signed through the new endpoint.
    for next_state in ("TRIAGE", "ASSESSMENT", "CONFIRMED"):
        challenge = (
            await client.post(f"/postmarket/v1/signals/{signal_id}/assessment-signature-challenges", headers=auth_headers(token))
        ).json()
        assert challenge["meaning"] == "Approved"
        resp = await client.post(
            f"/postmarket/v1/signals/{signal_id}/assessments",
            json={
                "idempotency_key": idem(), "signal_id": signal_id, "expected_version": signal.version,
                "assessment": {"note": f"moving to {next_state}"}, "next_state": next_state,
                "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        signal = await _get_fresh(db, SafetySignal, signal_id)
        assert signal.state == next_state

    escalation_challenge = (
        await client.post(f"/postmarket/v1/signals/{signal_id}/escalation-signature-challenges", headers=auth_headers(token))
    ).json()
    assert escalation_challenge["meaning"] == "Approved"
    escalate_resp = await client.post(
        f"/postmarket/v1/signals/{signal_id}/escalations",
        json={
            "idempotency_key": idem(), "signal_id": signal_id, "expected_version": signal.version, "target_module": "FIELD_ACTION",
            "target_command": {
                "site_id": str(seeded["site_id"]), "action_number": f"FA-{uuid.uuid4().hex[:8]}",
                "action_type": "correction", "trigger_ref": {"source_type": "trend", "signal_id": signal_id},
            },
            "rationale": "confirmed device signal requires a field correction",
            "challenge_id": escalation_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert escalate_resp.status_code == 200, escalate_resp.text
    signal = await _get_fresh(db, SafetySignal, signal_id)
    assert len(signal.escalation_links) == 1
    fa = await _get_fresh(db, FieldAction, uuid.UUID(signal.escalation_links[0]["target_aggregate_id"]))
    assert fa is not None
