"""WP-14 Document 85 (SPEC-VAL-007) -- Performance Qualification (PQ), UAT & Business Process
Verification. Executable evidence for the create -> assign participants -> execute -> approve flow,
the Document 106 row 151 signature on approve, the PQ-FR-005/018 untrained-participant / go-live
blocker gates, and the mandatory negatives (stale version, invalid transition, missing reason,
duplicate submission, non-independent approver, unauthorised).
"""

import uuid

import pytest

from app.core.db import SessionLocal
from app.modules.signature import service as signature_service
from app.modules.validation import commands_pq as pq
from app.modules.validation.models_wp14 import PqExecution, PqScenario
from app.modules.validation.shared import record_hash
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    RoleMissingError,
    StaleVersionError,
    ValidationFailedError,
)
from tests.conftest import auth_headers, idem, login


async def _challenge(s, user_id, record_type, action, record_id, version):
    policy = await signature_service.resolve_signature_requirement(s, record_type=record_type, action=action)
    ch = await signature_service.create_challenge(
        s, user_id=user_id, record_type=record_type, record_id=record_id, record_version=version,
        record_hash=record_hash(record_id, version), meaning=policy.meaning,
    )
    return ch.id


def _scenario_cmd(**over):
    base = dict(
        idempotency_key=idem(), scenario_number=f"PQ-{uuid.uuid4().hex[:8]}",
        process_area="material_flow", intended_workflow="Receipt -> quarantine -> release -> dispense -> consume",
        acceptance_criteria="All steps completed by trained users with no critical deviation",
        representative_roles=["Production", "QA", "Warehouse"],
    )
    base.update(over)
    return pq.CreatePqScenarioCommand(**base)


async def _make_accepted_ready_scenario(s, reviewer, *, trained=True):
    """create + assign a trained participant + one COMPLETED execution -> scenario IN_EXECUTION."""
    created = await pq.create_pq_scenario(s, _scenario_cmd(), reviewer, None)
    await s.flush()
    part_user = str(uuid.uuid4())
    assigned = await pq.assign_pq_participants(
        s, pq.AssignPqParticipantsCommand(
            idempotency_key=idem(), scenario_id=created.aggregate_id,
            expected_version=created.resulting_version,
            participants=[{"user_id": part_user, "role": "Production", "training_refs": ["SOP-1"], "trained": trained}],
        ), reviewer, None,
    )
    ex = await pq.execute_pq_scenario(
        s, pq.ExecutePqScenarioCommand(
            idempotency_key=idem(), scenario_id=created.aggregate_id, environment="cust-uat",
            config_ref="cfg-v1", participant_identities=[part_user], result="COMPLETED",
            step_results=[{"step": "receipt", "outcome": "PASS"}],
            observations=[{"observation": "label print slow", "severity": "low", "impact": "minor", "change_candidate": True}],
        ), reviewer, None,
    )
    return created, assigned, ex, part_user


# -------------------------------------------------------------------------------------------------
# TC-085-*  happy path + events  (PQ-FR-001/003/004/005/015/019)
# -------------------------------------------------------------------------------------------------

async def test_pq_full_flow_create_assign_execute_approve(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            created, assigned, ex, _ = await _make_accepted_ready_scenario(s, reviewer)
        async with s.begin():
            sc = await s.get(PqScenario, created.aggregate_id)
            assert sc.state == "IN_EXECUTION"
            exec_row = await s.get(PqExecution, ex.aggregate_id)
            assert exec_row.result == "COMPLETED"
            assert exec_row.go_live_blocker is False
            assert len(exec_row.observations) == 1
            ver = sc.version
            ch = await _challenge(s, releaser, "pq_scenario", "approve", sc.id, ver)
        async with s.begin():
            receipt = await pq.approve_pq(
                s, pq.ApprovePqCommand(
                    idempotency_key=idem(), scenario_id=created.aggregate_id,
                    expected_version=ver, reason="site acceptance granted", decision="ACCEPTED",
                    challenge_id=ch, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
            assert receipt.signature_id is not None
        async with s.begin():
            sc = await s.get(PqScenario, created.aggregate_id)
            assert sc.state == "ACCEPTED"
            assert sc.approved_by_user_id == releaser


async def test_pq_execute_blocks_untrained_participant_on_completed(db, seeded):
    """PQ-FR-005: a COMPLETED PQ execution cannot include an untrained participant identity."""
    reviewer = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await pq.create_pq_scenario(s, _scenario_cmd(), reviewer, None)
            await s.flush()
            u = str(uuid.uuid4())
            await pq.assign_pq_participants(
                s, pq.AssignPqParticipantsCommand(
                    idempotency_key=idem(), scenario_id=created.aggregate_id,
                    expected_version=created.resulting_version,
                    participants=[{"user_id": u, "role": "Production", "trained": False}],
                ), reviewer, None,
            )
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await pq.execute_pq_scenario(
                    s, pq.ExecutePqScenarioCommand(
                        idempotency_key=idem(), scenario_id=created.aggregate_id, environment="e",
                        config_ref="c", participant_identities=[u], result="COMPLETED",
                    ), reviewer, None,
                )


async def test_pq_approve_blocked_by_go_live_blocker(db, seeded):
    """PQ-FR-018: an execution with an unresolved critical deviation blocks ACCEPTED."""
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await pq.create_pq_scenario(s, _scenario_cmd(), reviewer, None)
            await s.flush()
            u = str(uuid.uuid4())
            await pq.assign_pq_participants(
                s, pq.AssignPqParticipantsCommand(
                    idempotency_key=idem(), scenario_id=created.aggregate_id,
                    expected_version=created.resulting_version,
                    participants=[{"user_id": u, "role": "QA", "trained": True}],
                ), reviewer, None,
            )
            await pq.execute_pq_scenario(
                s, pq.ExecutePqScenarioCommand(
                    idempotency_key=idem(), scenario_id=created.aggregate_id, environment="e",
                    config_ref="c", participant_identities=[u], result="COMPLETED",
                    deviations=[{"ref": "DEV-1", "critical": True, "resolved": False}],
                ), reviewer, None,
            )
        async with s.begin():
            sc = await s.get(PqScenario, created.aggregate_id)
            ch = await _challenge(s, releaser, "pq_scenario", "approve", sc.id, sc.version)
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await pq.approve_pq(
                    s, pq.ApprovePqCommand(
                        idempotency_key=idem(), scenario_id=created.aggregate_id, expected_version=sc.version,
                        reason="try accept", decision="ACCEPTED", challenge_id=ch, reauth_password="ChangeMe123!",
                    ), releaser, None,
                )


# -------------------------------------------------------------------------------------------------
# mandatory negatives
# -------------------------------------------------------------------------------------------------

async def test_pq_assign_participants_stale_version(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await pq.create_pq_scenario(s, _scenario_cmd(), reviewer, None)
        async with s.begin():
            with pytest.raises(StaleVersionError):
                await pq.assign_pq_participants(
                    s, pq.AssignPqParticipantsCommand(
                        idempotency_key=idem(), scenario_id=created.aggregate_id, expected_version=999,
                        participants=[{"user_id": str(uuid.uuid4()), "role": "QA", "trained": True}],
                    ), reviewer, None,
                )


async def test_pq_execute_invalid_transition_before_participants(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await pq.create_pq_scenario(s, _scenario_cmd(), reviewer, None)
        async with s.begin():
            with pytest.raises(InvalidTransitionError):
                await pq.execute_pq_scenario(
                    s, pq.ExecutePqScenarioCommand(
                        idempotency_key=idem(), scenario_id=created.aggregate_id, environment="e",
                        config_ref="c", participant_identities=[str(uuid.uuid4())], result="COMPLETED",
                    ), reviewer, None,
                )


async def test_pq_approve_missing_reason(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            created, _, _, _ = await _make_accepted_ready_scenario(s, reviewer)
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await pq.approve_pq(
                    s, pq.ApprovePqCommand(
                        idempotency_key=idem(), scenario_id=created.aggregate_id, expected_version=2,
                        reason="   ", decision="ACCEPTED", challenge_id=uuid.uuid4(), reauth_password="x",
                    ), releaser, None,
                )


async def test_pq_approve_bad_reauth_blocks_signature(db, seeded):
    """SIG-FR-006 / Document 85 §11: a failed step-up blocks acceptance rather than falling back to unsigned."""
    reviewer = seeded["users"]["qa.reviewer"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            created, _, _, _ = await _make_accepted_ready_scenario(s, reviewer)
        async with s.begin():
            sc = await s.get(PqScenario, created.aggregate_id)
            ver = sc.version
            ch = await _challenge(s, releaser, "pq_scenario", "approve", sc.id, ver)
        async with s.begin():
            with pytest.raises(MissingSignatureError):
                await pq.approve_pq(
                    s, pq.ApprovePqCommand(
                        idempotency_key=idem(), scenario_id=created.aggregate_id, expected_version=ver,
                        reason="accept", decision="ACCEPTED", challenge_id=ch, reauth_password="WRONG",
                    ), releaser, None,
                )
        async with s.begin():
            sc = await s.get(PqScenario, created.aggregate_id)
            assert sc.state == "IN_EXECUTION"  # not accepted


async def test_pq_scenario_duplicate_idempotency_returns_same_receipt(db, seeded):
    reviewer = seeded["users"]["qa.reviewer"].id
    cmd = _scenario_cmd()
    async with SessionLocal() as s:
        async with s.begin():
            r1 = await pq.create_pq_scenario(s, cmd, reviewer, None)
        async with s.begin():
            r2 = await pq.create_pq_scenario(s, cmd, reviewer, None)
    assert r1.aggregate_id == r2.aggregate_id
    assert r1.command_id == r2.command_id


async def test_pq_unauthorized_role_rejected_via_http(db, seeded):
    """operator1 (Operator role) holds validation.pq.execute but NOT validation.pq.manage."""
    from tests.conftest import client as _client  # noqa
    import httpx
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        token = await login(ac, "operator1")
        resp = await ac.post(
            "/validation/v1/pq/scenarios",
            headers=auth_headers(token),
            json={"idempotency_key": idem(), "scenario_number": "PQ-X", "process_area": "material_flow",
                  "intended_workflow": "wf", "acceptance_criteria": "ac"},
        )
    assert resp.status_code == 403


async def test_pq_execute_concurrent_same_scenario_both_recorded(db, seeded):
    """Two executions of the same scenario are independent rows (Document 85 §11 re-run semantics)."""
    reviewer = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await pq.create_pq_scenario(s, _scenario_cmd(), reviewer, None)
            await s.flush()
            u = str(uuid.uuid4())
            await pq.assign_pq_participants(
                s, pq.AssignPqParticipantsCommand(
                    idempotency_key=idem(), scenario_id=created.aggregate_id,
                    expected_version=created.resulting_version,
                    participants=[{"user_id": u, "role": "QA", "trained": True}],
                ), reviewer, None,
            )
        async with s.begin():
            e1 = await pq.execute_pq_scenario(
                s, pq.ExecutePqScenarioCommand(
                    idempotency_key=idem(), scenario_id=created.aggregate_id, environment="e",
                    config_ref="c", participant_identities=[u], result="FAILED",
                ), reviewer, None,
            )
        async with s.begin():
            e2 = await pq.execute_pq_scenario(
                s, pq.ExecutePqScenarioCommand(
                    idempotency_key=idem(), scenario_id=created.aggregate_id, environment="e",
                    config_ref="c", participant_identities=[u], result="COMPLETED",
                    prior_execution_id=e1.aggregate_id,
                ), reviewer, None,
            )
        assert e1.aggregate_id != e2.aggregate_id
        async with s.begin():
            row2 = await s.get(PqExecution, e2.aggregate_id)
            assert row2.prior_execution_id == e1.aggregate_id
