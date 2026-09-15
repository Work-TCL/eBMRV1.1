"""Document 61 (SPEC-SEC-001, SEC-THR-001..028): threat model version creation, threat registration,
control mapping (catalog get-or-create), risk calculation/history, residual-risk acceptance and security
exception request/approval. SG-161 RESOLVED_APPROVED 2026-09-14 (project-owner-directed): both now
require a real "Security Risk Approver" signature, independent of whoever's judgment is being approved
(the risk calculator, or the exception requester). See docs/generated/18_SPEC_GAPS.md SG-161 and
app/modules/security/commands.py's module docstring for the request/approve split that makes the
independence check meaningful.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.security import commands as sec_commands
from app.modules.security.models import SecurityControl, SecurityException, SecurityThreat, SecurityThreatModelVersion
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    MissingSignatureError,
    NotFoundError,
    RoleMissingError,
    SecurityRiskInputIncompleteError,
    SodIndependenceRequiredError,
    StaleVersionError,
    ThreatScopeInvalidError,
    ValidationFailedError,
)
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_security_risk_approver(db, seeded, tag):
    user = User(
        username=f"sec.approver{tag}", email=f"sec.approver{tag}@example.com", full_name="Security Risk Approver",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Security Risk Approver"].id))
    return user


async def _sign(db, *, actor_id, record_type, record_version, record_hash):
    challenge = await signature_service.create_challenge(
        db, user_id=actor_id, record_type=record_type, record_id=uuid.uuid4(),
        record_version=record_version, record_hash=record_hash, meaning="Approved",
    )
    await db.flush()
    return challenge.id


async def _make_admin(db, seeded, tag):
    user = User(
        username=f"sec.admin{tag}", email=f"sec.admin{tag}@example.com", full_name="Security Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


async def _get(db, model, obj_id):
    async with db.begin():
        return await db.get(model, obj_id)


async def _create_threat_model(db, owner_id, **overrides):
    cmd = sec_commands.CreateThreatModelVersionCommand(
        idempotency_key=idem(), system_version="platform-1.0", methodology_version="STRIDE-v1",
        deployment_profile="CLOUD", **overrides,
    )
    return await sec_commands.create_threat_model_version(db, cmd, owner_id)


async def _register_threat(db, owner_id, tmv_id, **overrides):
    cmd = sec_commands.RegisterThreatCommand(
        idempotency_key=idem(), threat_model_version_id=tmv_id, asset_or_boundary="Mutation Gateway API",
        threat_type="TAMPERING", abuse_case="Attacker replays a captured command to duplicate a mutation",
        **overrides,
    )
    return await sec_commands.register_threat(db, cmd, owner_id)


@pytest.mark.asyncio
async def test_create_threat_model_version_rejects_bad_deployment_profile_then_succeeds(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "1")

    async with db.begin():
        with pytest.raises(ThreatScopeInvalidError):
            await sec_commands.create_threat_model_version(
                db, sec_commands.CreateThreatModelVersionCommand(
                    idempotency_key=idem(), system_version="platform-1.0", methodology_version="STRIDE-v1",
                    deployment_profile="NOT_A_PROFILE",
                ), owner.id,
            )

    async with db.begin():
        receipt = await _create_threat_model(db, owner.id)
    tmv = await _get(db, SecurityThreatModelVersion, receipt.aggregate_id)
    assert tmv.state == "DRAFT"
    assert tmv.deployment_profile == "CLOUD"
    assert tmv.version == 1


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_same_receipt(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "2")
    key = idem()
    cmd = sec_commands.CreateThreatModelVersionCommand(
        idempotency_key=key, system_version="platform-1.0", methodology_version="STRIDE-v1", deployment_profile="ON_PREM",
    )
    async with db.begin():
        first = await sec_commands.create_threat_model_version(db, cmd, owner.id)
    async with db.begin():
        second = await sec_commands.create_threat_model_version(db, cmd, owner.id)
    assert first.aggregate_id == second.aggregate_id


@pytest.mark.asyncio
async def test_register_threat_rejects_unknown_threat_type_and_missing_parent(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "3")
        tmv_receipt = await _create_threat_model(db, owner.id)

    async with db.begin():
        with pytest.raises(NotFoundError):
            await _register_threat(db, owner.id, uuid.uuid4())

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await sec_commands.register_threat(
                db, sec_commands.RegisterThreatCommand(
                    idempotency_key=idem(), threat_model_version_id=tmv_receipt.aggregate_id,
                    asset_or_boundary="Object store", threat_type="NOT_A_STRIDE_CATEGORY", abuse_case="x",
                ), owner.id,
            )

    async with db.begin():
        threat_receipt = await _register_threat(db, owner.id, tmv_receipt.aggregate_id)
    threat = await _get(db, SecurityThreat, threat_receipt.aggregate_id)
    assert threat.state == "OPEN"
    assert threat.threat_type == "TAMPERING"


@pytest.mark.asyncio
async def test_map_control_creates_catalog_entry_and_appends_mapping_then_stale_version_rejected(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "4")
        tmv_receipt = await _create_threat_model(db, owner.id)
        threat_receipt = await _register_threat(db, owner.id, tmv_receipt.aggregate_id)

    async with db.begin():
        await sec_commands.map_security_control(
            db, sec_commands.MapSecurityControlCommand(
                idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=1,
                control_code="CTRL-MUTATION-IDEMPOTENCY", mapping_type="PREVENTIVE",
                implementation_refs={"module": "app.mutation.gateway"}, objective="Reject duplicate commands",
                implementation_owner="Platform Engineering", evidence_source="app/mutation/gateway.py",
                test_owner="QA",
            ), owner.id,
        )
    threat = await _get(db, SecurityThreat, threat_receipt.aggregate_id)
    assert len(threat.control_mappings) == 1
    assert threat.control_mappings[0]["control_code"] == "CTRL-MUTATION-IDEMPOTENCY"
    assert threat.version == 2

    async with db.begin():
        control = (
            await db.execute(
                select(SecurityControl).where(SecurityControl.control_code == "CTRL-MUTATION-IDEMPOTENCY")
            )
        ).scalar_one()
        assert control.implementation_owner == "Platform Engineering"

    # A second mapping call with the now-stale expected_version=1 is rejected (optimistic concurrency).
    async with db.begin():
        with pytest.raises(StaleVersionError):
            await sec_commands.map_security_control(
                db, sec_commands.MapSecurityControlCommand(
                    idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=1,
                    control_code="CTRL-MUTATION-IDEMPOTENCY", mapping_type="DETECTIVE",
                ), owner.id,
            )

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await sec_commands.map_security_control(
                db, sec_commands.MapSecurityControlCommand(
                    idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=2,
                    control_code="CTRL-X", mapping_type="NOT_A_TYPE",
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_calculate_risk_never_overwrites_history_then_accept_fails_closed(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "5")
        tmv_receipt = await _create_threat_model(db, owner.id)
        threat_receipt = await _register_threat(db, owner.id, tmv_receipt.aggregate_id)

    async with db.begin():
        with pytest.raises(SecurityRiskInputIncompleteError):
            await sec_commands.calculate_security_risk(
                db, sec_commands.CalculateSecurityRiskCommand(
                    idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=1,
                    risk_stage="INHERENT", impact_inputs={}, likelihood_inputs={}, methodology="v1", rating={},
                ), owner.id,
            )

    async with db.begin():
        await sec_commands.calculate_security_risk(
            db, sec_commands.CalculateSecurityRiskCommand(
                idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=1,
                risk_stage="INHERENT", impact_inputs={"impact": "high"}, likelihood_inputs={"likelihood": "medium"},
                methodology="v1", rating={"level": "HIGH"},
            ), owner.id,
        )
    threat = await _get(db, SecurityThreat, threat_receipt.aggregate_id)
    assert threat.inherent_risk["rating"] == {"level": "HIGH"}
    assert threat.risk_calculation_history == []
    assert threat.version == 2

    # Recalculating the same stage appends the prior value rather than discarding it.
    async with db.begin():
        await sec_commands.calculate_security_risk(
            db, sec_commands.CalculateSecurityRiskCommand(
                idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=2,
                risk_stage="INHERENT", impact_inputs={"impact": "medium"}, likelihood_inputs={"likelihood": "low"},
                methodology="v1", rating={"level": "MEDIUM"},
            ), owner.id,
        )
    threat = await _get(db, SecurityThreat, threat_receipt.aggregate_id)
    assert threat.inherent_risk["rating"] == {"level": "MEDIUM"}
    assert len(threat.risk_calculation_history) == 1
    assert threat.risk_calculation_history[0]["rating"] == {"level": "HIGH"}

    async with db.begin():
        await sec_commands.calculate_security_risk(
            db, sec_commands.CalculateSecurityRiskCommand(
                idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=3,
                risk_stage="RESIDUAL", impact_inputs={"impact": "low"}, likelihood_inputs={"likelihood": "low"},
                methodology="v1", rating={"level": "LOW"},
            ), owner.id,
        )
    threat = await _get(db, SecurityThreat, threat_receipt.aggregate_id)
    assert threat.residual_risk["rating"] == {"level": "LOW"}

    # SG-161 RESOLVED_APPROVED 2026-09-14: security_threat.accept_risk now requires the "Security Risk
    # Approver" role -- an Admin-only actor without that role is rejected, not silently accepted.
    async with db.begin():
        with pytest.raises(RoleMissingError):
            await sec_commands.accept_residual_security_risk(
                db, sec_commands.AcceptResidualSecurityRiskCommand(
                    idempotency_key=idem(), risk_id=threat.id, expected_version=threat.version,
                    rationale="Compensating control mitigates residual exposure",
                ), owner.id,
            )
    # Rejection leaves the aggregate unchanged.
    threat_after = await _get(db, SecurityThreat, threat_receipt.aggregate_id)
    assert threat_after.state == "OPEN"
    assert threat_after.version == threat.version


@pytest.mark.asyncio
async def test_accept_residual_risk_transitions_state_when_approver_is_independent(db, seeded):
    """SG-161 RESOLVED_APPROVED 2026-09-14: a "Security Risk Approver" distinct from whoever calculated
    the residual risk signs, and acceptance actually records the decision and transitions the threat to
    RISK_ACCEPTED."""
    async with db.begin():
        owner = await _make_admin(db, seeded, "6b")
        approver = await _make_security_risk_approver(db, seeded, "6b")
        tmv_receipt = await _create_threat_model(db, owner.id)
        threat_receipt = await _register_threat(db, owner.id, tmv_receipt.aggregate_id)

    async with db.begin():
        await sec_commands.calculate_security_risk(
            db, sec_commands.CalculateSecurityRiskCommand(
                idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=1,
                risk_stage="RESIDUAL", impact_inputs={"impact": "low"}, likelihood_inputs={"likelihood": "low"},
                methodology="v1", rating={"level": "LOW"},
            ), owner.id,
        )
    async with db.begin():
        threat = await db.get(SecurityThreat, threat_receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=approver.id, record_type="security_threat", record_version=threat.version, record_hash=sec_commands._threat_hash(threat))
        await sec_commands.accept_residual_security_risk(
            db, sec_commands.AcceptResidualSecurityRiskCommand(
                idempotency_key=idem(), risk_id=threat_receipt.aggregate_id, expected_version=2,
                rationale="Low residual exposure, compensating control in place",
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), approver.id,
        )
    threat = await _get(db, SecurityThreat, threat_receipt.aggregate_id)
    assert threat.state == "RISK_ACCEPTED"
    assert threat.residual_risk_acceptance["rationale"] == "Low residual exposure, compensating control in place"
    assert threat.version == 3


@pytest.mark.asyncio
async def test_accept_residual_risk_rejects_the_calculator_as_signer(db, seeded):
    """SG-161: the same person who calculated the residual risk cannot also accept it -- Document 106's
    independence requirement, now actually enforced (not merely stated)."""
    async with db.begin():
        approver = await _make_security_risk_approver(db, seeded, "6c")
        tmv_receipt = await _create_threat_model(db, approver.id)
        threat_receipt = await _register_threat(db, approver.id, tmv_receipt.aggregate_id)
        await sec_commands.calculate_security_risk(
            db, sec_commands.CalculateSecurityRiskCommand(
                idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=1,
                risk_stage="RESIDUAL", impact_inputs={"impact": "low"}, likelihood_inputs={"likelihood": "low"},
                methodology="v1", rating={"level": "LOW"},
            ), approver.id,
        )

    async with db.begin():
        threat = await db.get(SecurityThreat, threat_receipt.aggregate_id)
        with pytest.raises(SodIndependenceRequiredError):
            await sec_commands.accept_residual_security_risk(
                db, sec_commands.AcceptResidualSecurityRiskCommand(
                    idempotency_key=idem(), risk_id=threat_receipt.aggregate_id, expected_version=threat.version,
                    rationale="Self-accepting my own calculation",
                ), approver.id,
            )
    threat_after = await _get(db, SecurityThreat, threat_receipt.aggregate_id)
    assert threat_after.state == "OPEN"


@pytest.mark.asyncio
async def test_request_then_approve_security_exception_by_independent_approver(db, seeded):
    """SG-161 RESOLVED_APPROVED 2026-09-14: request_security_exception() is unsigned and records the
    requester; approve_security_exception() is signed by a "Security Risk Approver" independent of that
    requester and moves the record to OPEN."""
    async with db.begin():
        owner = await _make_admin(db, seeded, "7b")
        approver = await _make_security_risk_approver(db, seeded, "7b")
        receipt = await sec_commands.request_security_exception(
            db, sec_commands.RequestSecurityExceptionCommand(
                idempotency_key=idem(), control_or_requirement="CTRL-MFA-PRIVILEGED",
                reason="Vendor migration in progress", expiry=datetime.now(timezone.utc) + timedelta(days=30),
                compensating_controls={"interim": "manual dual-control review"},
            ), owner.id,
        )
    exception = await _get(db, SecurityException, receipt.aggregate_id)
    assert exception.state == "PENDING_APPROVAL"
    assert exception.opened_by == owner.id

    async with db.begin():
        exception = await db.get(SecurityException, receipt.aggregate_id)
        challenge_id = await _sign(db, actor_id=approver.id, record_type="security_exception", record_version=exception.version, record_hash=sec_commands._exception_hash(exception))
        await sec_commands.approve_security_exception(
            db, exception.id, sec_commands.ApproveSecurityExceptionCommand(
                idempotency_key=idem(), expected_version=exception.version,
                challenge_id=challenge_id, reauth_password=DEMO_PASSWORD,
            ), approver.id,
        )
    exception = await _get(db, SecurityException, receipt.aggregate_id)
    assert exception.state == "OPEN"
    assert exception.control_or_requirement == "CTRL-MFA-PRIVILEGED"
    assert exception.compensating_controls == {"interim": "manual dual-control review"}
    assert exception.expiry > datetime.now(timezone.utc)
    assert len(exception.approvers) == 1


@pytest.mark.asyncio
async def test_approve_security_exception_rejects_the_requester_as_approver(db, seeded):
    """SG-161: the person who requested the exception cannot also approve it -- Document 106 row 133's
    "MUST be independent of the requester", now actually enforced."""
    async with db.begin():
        approver = await _make_security_risk_approver(db, seeded, "7c")
        receipt = await sec_commands.request_security_exception(
            db, sec_commands.RequestSecurityExceptionCommand(
                idempotency_key=idem(), control_or_requirement="CTRL-MFA-PRIVILEGED",
                reason="Vendor migration in progress", expiry=datetime.now(timezone.utc) + timedelta(days=30),
            ), approver.id,
        )

    async with db.begin():
        exception = await db.get(SecurityException, receipt.aggregate_id)
        with pytest.raises(SodIndependenceRequiredError):
            await sec_commands.approve_security_exception(
                db, exception.id, sec_commands.ApproveSecurityExceptionCommand(
                    idempotency_key=idem(), expected_version=exception.version,
                ), approver.id,
            )
    exception_after = await _get(db, SecurityException, receipt.aggregate_id)
    assert exception_after.state == "PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_approve_security_exception_requires_a_real_signature(db, seeded):
    """SG-161: a correctly-independent Security Risk Approver still cannot approve without completing a
    real signature challenge -- role/independence correctness alone is not a signature (AG-07)."""
    async with db.begin():
        owner = await _make_admin(db, seeded, "7d")
        approver = await _make_security_risk_approver(db, seeded, "7d")
        receipt = await sec_commands.request_security_exception(
            db, sec_commands.RequestSecurityExceptionCommand(
                idempotency_key=idem(), control_or_requirement="CTRL-MFA-PRIVILEGED",
                reason="Vendor migration in progress", expiry=datetime.now(timezone.utc) + timedelta(days=30),
            ), owner.id,
        )

    async with db.begin():
        exception = await db.get(SecurityException, receipt.aggregate_id)
        with pytest.raises(MissingSignatureError):
            await sec_commands.approve_security_exception(
                db, exception.id, sec_commands.ApproveSecurityExceptionCommand(
                    idempotency_key=idem(), expected_version=exception.version,
                ), approver.id,
            )
    exception_after = await _get(db, SecurityException, receipt.aggregate_id)
    assert exception_after.state == "PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_accept_residual_risk_requires_residual_risk_calculated_first(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "6")
        tmv_receipt = await _create_threat_model(db, owner.id)
        threat_receipt = await _register_threat(db, owner.id, tmv_receipt.aggregate_id)

    async with db.begin():
        with pytest.raises(SecurityRiskInputIncompleteError):
            await sec_commands.accept_residual_security_risk(
                db, sec_commands.AcceptResidualSecurityRiskCommand(
                    idempotency_key=idem(), risk_id=threat_receipt.aggregate_id, expected_version=1,
                    rationale="No residual risk calculated yet",
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_request_security_exception_rejects_past_expiry(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "7")

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await sec_commands.request_security_exception(
                db, sec_commands.RequestSecurityExceptionCommand(
                    idempotency_key=idem(), control_or_requirement="CTRL-MFA-PRIVILEGED",
                    reason="Vendor migration in progress", expiry=datetime.now(timezone.utc) - timedelta(days=1),
                ), owner.id,
            )
    count = (await db.execute(select(SecurityException))).scalars().all()
    assert count == []


@pytest.mark.asyncio
async def test_trigger_threat_model_review_appends_history_and_stale_version_rejected(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "8")
        tmv_receipt = await _create_threat_model(db, owner.id)

    async with db.begin():
        await sec_commands.trigger_threat_model_review(
            db, sec_commands.TriggerThreatModelReviewCommand(
                idempotency_key=idem(), threat_model_version_id=tmv_receipt.aggregate_id, expected_version=1,
                change_id="CHG-0042", trigger_type="NEW_EXTERNAL_ENDPOINT", affected_modules=["gxp-api"],
            ), owner.id,
        )
    tmv = await _get(db, SecurityThreatModelVersion, tmv_receipt.aggregate_id)
    assert len(tmv.review_triggers) == 1
    assert tmv.review_triggers[0]["trigger_type"] == "NEW_EXTERNAL_ENDPOINT"
    assert tmv.version == 2

    # Two writers racing on the same aggregate: the second, now-stale, submission is rejected.
    async with db.begin():
        with pytest.raises(StaleVersionError):
            await sec_commands.trigger_threat_model_review(
                db, sec_commands.TriggerThreatModelReviewCommand(
                    idempotency_key=idem(), threat_model_version_id=tmv_receipt.aggregate_id, expected_version=1,
                    change_id="CHG-0043", trigger_type="NEW_AUTH_MODE",
                ), owner.id,
            )


@pytest.mark.asyncio
async def test_generate_security_control_matrix_reflects_mappings_and_residual_risk(db, seeded):
    async with db.begin():
        owner = await _make_admin(db, seeded, "9")
        tmv_receipt = await _create_threat_model(db, owner.id)
        threat_receipt = await _register_threat(db, owner.id, tmv_receipt.aggregate_id)

    async with db.begin():
        await sec_commands.map_security_control(
            db, sec_commands.MapSecurityControlCommand(
                idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=1,
                control_code="CTRL-AUDIT-HASH-CHAIN", mapping_type="DETECTIVE",
                implementation_owner="Platform Engineering", evidence_source="app/mutation/gateway.py",
            ), owner.id,
        )
    async with db.begin():
        await sec_commands.calculate_security_risk(
            db, sec_commands.CalculateSecurityRiskCommand(
                idempotency_key=idem(), threat_id=threat_receipt.aggregate_id, expected_version=2,
                risk_stage="RESIDUAL", impact_inputs={"impact": "medium"}, likelihood_inputs={"likelihood": "low"},
                methodology="v1", rating={"level": "LOW"},
            ), owner.id,
        )

    async with db.begin():
        matrix = await sec_commands.generate_security_control_matrix(db, tmv_receipt.aggregate_id, "CLOUD")
    assert matrix["deployment_profile"] == "CLOUD"
    assert len(matrix["entries"]) == 1
    entry = matrix["entries"][0]
    assert entry["control_code"] == "CTRL-AUDIT-HASH-CHAIN"
    assert entry["mapping_type"] == "DETECTIVE"
    assert entry["residual_risk"]["rating"] == {"level": "LOW"}
    assert entry["implementation_owner"] == "Platform Engineering"

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await sec_commands.generate_security_control_matrix(db, tmv_receipt.aggregate_id, "ON_PREM")

    async with db.begin():
        with pytest.raises(NotFoundError):
            await sec_commands.generate_security_control_matrix(db, uuid.uuid4(), None)


@pytest.mark.asyncio
async def test_create_threat_model_via_http_requires_auth(client, db, seeded):
    async with db.begin():
        await _make_admin(db, seeded, "10")
    resp = await client.post(
        "/security/v1/threat-models",
        json={
            "idempotency_key": idem(), "system_version": "platform-1.0", "methodology_version": "STRIDE-v1",
            "deployment_profile": "CLOUD",
        },
    )
    assert resp.status_code == 401

    token = await login(client, "sec.admin10")
    resp = await client.post(
        "/security/v1/threat-models",
        json={
            "idempotency_key": idem(), "system_version": "platform-1.0", "methodology_version": "STRIDE-v1",
            "deployment_profile": "CLOUD",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
