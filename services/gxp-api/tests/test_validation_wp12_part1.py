"""WP-12 Documents 79-83 (SPEC-VAL-001..005) -- Validation Master Plan/CSA, Intended Use/Risk
Classification, Requirements/Traceability, Test Strategy, Installation Qualification. Executable
evidence for the create/approve/release command flows, Document 111's risk derivation rule, and the
release-gate blocker check.
"""

import base64
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.evidence import commands as ev
from app.modules.evidence.store import LocalEvidenceStore, set_store, sha256_bytes
from app.modules.signature import service as signature_service
from app.modules.validation import commands_iq as iq
from app.modules.validation import commands_plan as plan
from app.modules.validation import commands_risk as risk
from app.modules.validation import commands_test as vtest
from app.modules.validation import commands_trace as trace
from app.modules.validation.models import FunctionRiskAssessment, ValidationMasterPlan
from app.modules.validation.shared import record_hash
from app.mutation.errors import ReleaseBlockersPresentError, StaleVersionError, ValidationFailedError
from tests.conftest import idem


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    set_store(LocalEvidenceStore(base_dir=str(tmp_path / "val_evstore")))
    yield
    set_store(LocalEvidenceStore())


async def _challenge(s, user_id, record_type, action, record_id, version):
    policy = await signature_service.resolve_signature_requirement(s, record_type=record_type, action=action)
    ch = await signature_service.create_challenge(
        s, user_id=user_id, record_type=record_type, record_id=record_id, record_version=version,
        record_hash=record_hash(record_id, version), meaning=policy.meaning,
    )
    return ch.id


# ---- Document 79: Validation Master Plan --------------------------------------------------------


async def test_master_plan_create_release_blocked_then_released(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await plan.create_or_update_master_plan(
                s, plan.CreateOrUpdateMasterPlanCommand(
                    idempotency_key=idem(), plan_number="VMP-TEST-001", scope="Platform CSA scope",
                    methodology="Risk-based CSA per Document 79",
                    new_deliverables=[
                        plan.DeliverableInput(
                            artifact_type="Traceability Matrix", risk_condition="always",
                            owner="Validation Lead", evidence_type="report", release_blocker=True,
                        )
                    ],
                ), actor, None,
            )
        # release blocked: the one deliverable is still REQUIRED, not SATISFIED
        async with s.begin():
            with pytest.raises(ReleaseBlockersPresentError):
                await plan.release_master_plan(
                    s, plan.ReleaseMasterPlanCommand(
                        idempotency_key=idem(), plan_id=created.aggregate_id, expected_version=created.resulting_version,
                        reason="attempt release", challenge_id=uuid.uuid4(), reauth_password="x",
                    ), releaser, None,
                )
        async with SessionLocal() as s2:
            plan_row = await s2.get(ValidationMasterPlan, created.aggregate_id)
            assert plan_row.state == "DRAFT"  # blocked release never committed the transition

        # satisfy the deliverable directly, then release for real with a valid signature
        async with s.begin():
            from app.modules.validation.models import ValidationDeliverableRequirement
            deliverable = (
                await s.execute(select(ValidationDeliverableRequirement).where(ValidationDeliverableRequirement.plan_id == created.aggregate_id))
            ).scalar_one()
            deliverable.state = "SATISFIED"
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "validation_master_plan", "release", created.aggregate_id, created.resulting_version)
            released = await plan.release_master_plan(
                s, plan.ReleaseMasterPlanCommand(
                    idempotency_key=idem(), plan_id=created.aggregate_id, expected_version=created.resulting_version,
                    reason="deliverables satisfied", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    async with SessionLocal() as s:
        plan_row = await s.get(ValidationMasterPlan, created.aggregate_id)
        assert plan_row.state == "RELEASED"
        gate = await plan.get_release_gate(s, created.aggregate_id)
        assert gate["gate_state"] == "PASSED"
        # Document 06 (VLT-FR-001): the release created a real, immutable vault snapshot.
        from app.modules.vault.models import VaultObject
        vault_row = (
            await s.execute(
                select(VaultObject).where(
                    VaultObject.object_type == "validation_master_plan", VaultObject.business_id == "VMP-TEST-001"
                )
            )
        ).scalar_one()
        assert vault_row.status == "released" and vault_row.canonical_payload["scope"] == "Platform CSA scope"

    # VAL-FR-023: CSV and PDF exports of the released package (SG-169 resolved -- ReportLab).
    async with SessionLocal() as s:
        csv_text = await plan.export_package_csv(s, "VMP-TEST-001")
        assert "Traceability Matrix" in csv_text and "SATISFIED" in csv_text
        pdf_bytes = await plan.export_package_pdf(s, "VMP-TEST-001")
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 500  # a real rendered document, not an empty/error stub


async def test_master_plan_release_rejects_stale_version(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await plan.create_or_update_master_plan(
                s, plan.CreateOrUpdateMasterPlanCommand(
                    idempotency_key=idem(), plan_number="VMP-TEST-002", scope="scope", methodology="method",
                ), actor, None,
            )
        async with s.begin():
            with pytest.raises(StaleVersionError):
                await plan.release_master_plan(
                    s, plan.ReleaseMasterPlanCommand(
                        idempotency_key=idem(), plan_id=created.aggregate_id, expected_version=999,
                        reason="x", challenge_id=uuid.uuid4(), reauth_password="x",
                    ), actor, None,
                )


# ---- Document 80: Intended Use & Function Risk Classification -----------------------------------


async def test_function_risk_derivation_matches_document_111_rule(db, seeded):
    """Document 111 section 1: HIGHER-PROCESS-RISK iff release/disposition, signature, audit-
    immutability, or (calculation AND enforcement) is present -- exercised directly against the pure
    function, then through the full create+approve command flow."""
    higher, method = risk.derive_risk_category(
        automation_role="informational", has_release_or_disposition=False, has_signature_role=True,
        has_audit_immutability_role=False, has_enforcement_role=False,
    )
    assert higher == "HIGHER-PROCESS-RISK"
    standard, _ = risk.derive_risk_category(
        automation_role="advisory", has_release_or_disposition=False, has_signature_role=False,
        has_audit_immutability_role=False, has_enforcement_role=False,
    )
    assert standard == "STANDARD-RISK"
    calc_only, _ = risk.derive_risk_category(
        automation_role="calculation", has_release_or_disposition=False, has_signature_role=False,
        has_audit_immutability_role=False, has_enforcement_role=False,
    )
    assert calc_only == "STANDARD-RISK"  # calculation alone, without enforcement, is not HIGHER
    calc_and_enforce, _ = risk.derive_risk_category(
        automation_role="calculation", has_release_or_disposition=False, has_signature_role=False,
        has_audit_immutability_role=False, has_enforcement_role=True,
    )
    assert calc_and_enforce == "HIGHER-PROCESS-RISK"

    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            created = await risk.create_function_risk_assessment(
                s, risk.CreateFunctionRiskAssessmentCommand(
                    idempotency_key=idem(), function_ref="validation.exception.disposition", function_version="1",
                    detectability="LOW", automation_role="enforcement_gating", has_release_or_disposition=True,
                ), actor, None,
            )
        async with SessionLocal() as s2:
            row = await s2.get(FunctionRiskAssessment, created.aggregate_id)
            assert row.risk_category == "HIGHER-PROCESS-RISK"
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await risk.approve_function_risk_assessment(
                    s, risk.ApproveFunctionRiskAssessmentCommand(
                        idempotency_key=idem(), assessment_id=created.aggregate_id, expected_version=created.resulting_version,
                        reason="", challenge_id=uuid.uuid4(), reauth_password="x",
                    ), releaser, None,
                )  # empty reason rejected
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "function_risk_assessment", "approve", created.aggregate_id, created.resulting_version)
            approved = await risk.approve_function_risk_assessment(
                s, risk.ApproveFunctionRiskAssessmentCommand(
                    idempotency_key=idem(), assessment_id=created.aggregate_id, expected_version=created.resulting_version,
                    reason="risk accepted", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    async with SessionLocal() as s:
        row = await s.get(FunctionRiskAssessment, approved.aggregate_id)
        assert row.state == "APPROVED" and row.approved_by_user_id == releaser
        view = await risk.get_function_assurance(s, "validation.exception.disposition")
        assert view["risk_category"] == "HIGHER-PROCESS-RISK"


# ---- Document 81: Requirements & Traceability ----------------------------------------------------


async def test_requirement_ingest_supersession_and_baseline_gap_detection(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            await trace.ingest_requirements(
                s, trace.IngestRequirementsCommand(
                    idempotency_key=idem(), requirements=[
                        trace.RequirementInput(
                            requirement_code="WP12-TEST-001", source_document="Document 999",
                            source_section="1", text="v1 text", requirement_class="functional",
                        )
                    ],
                ), actor, None,
            )
        # re-ingest with changed text -> supersedes, version increments
        async with s.begin():
            await trace.ingest_requirements(
                s, trace.IngestRequirementsCommand(
                    idempotency_key=idem(), requirements=[
                        trace.RequirementInput(
                            requirement_code="WP12-TEST-001", source_document="Document 999",
                            source_section="1", text="v2 text -- changed", requirement_class="functional",
                        )
                    ],
                ), actor, None,
            )
        from app.modules.validation.models import ValidationRequirement
        async with SessionLocal() as s2:
            rows = (
                await s2.execute(select(ValidationRequirement).where(ValidationRequirement.requirement_code == "WP12-TEST-001"))
            ).scalars().all()
            assert len(rows) == 2
            assert {r.state for r in rows} == {"EFFECTIVE", "SUPERSEDED"}

        # freeze a baseline referencing this requirement with NO trace link -> gap detected
        async with s.begin():
            baseline = await trace.freeze_requirement_baseline(
                s, trace.FreezeRequirementBaselineCommand(
                    idempotency_key=idem(), release_scope="rel-test-1",
                    requirement_refs=[{"code": "WP12-TEST-001", "version": 2}],
                ), actor, None,
            )
        async with SessionLocal() as s2:
            from app.modules.validation.models import RequirementBaseline
            b = await s2.get(RequirementBaseline, baseline.aggregate_id)
            assert len(b.gaps_detected) == 1
            # REQ-FR-021 / Document 06: the freeze created a real vault snapshot, not just the bare hash.
            assert b.vault_object_id is not None
            from app.modules.vault.models import VaultObject
            vault_row = await s2.get(VaultObject, b.vault_object_id)
            assert vault_row.object_type == "requirement_baseline" and vault_row.digest is not None

        # add a TEST trace link, then the live gap report is empty
        async with s.begin():
            await trace.create_trace_link(
                s, trace.CreateTraceLinkCommand(
                    idempotency_key=idem(), source_type="validation_requirement", source_id="WP12-TEST-001",
                    source_version="2", target_type="validation_test_definition", target_id="TC-X", target_version="1",
                    relation_type="TEST",
                ), actor, None,
            )
        async with s.begin():
            gaps = await trace.get_traceability_gaps(s, baseline.aggregate_id)
            assert gaps["gaps"] == []

    # REQ-FR-022: CSV and PDF exports of the frozen baseline's traceability graph (SG-169 resolved).
    async with SessionLocal() as s:
        csv_text = await trace.export_traceability_csv(s, baseline.aggregate_id)
        assert "WP12-TEST-001" in csv_text and "rel-test-1" in csv_text
        pdf_bytes = await trace.export_traceability_pdf(s, baseline.aggregate_id)
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 500


# ---- Document 82: Test Strategy -------------------------------------------------------------------


async def test_test_definition_approve_and_execution_lifecycle(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            defn = await vtest.create_test_definition(
                s, vtest.CreateTestDefinitionCommand(
                    idempotency_key=idem(), test_code="WP12-TC-1", method="SCRIPTED_MANUAL",
                    procedure="Do the thing", expected_results="It works",
                ), actor, None,
            )
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "validation_test_definition", "approve", defn.aggregate_id, defn.resulting_version)
            approved = await vtest.approve_test_definition(
                s, vtest.ApproveTestDefinitionCommand(
                    idempotency_key=idem(), test_id=defn.aggregate_id, expected_version=defn.resulting_version,
                    reason="reviewed", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
        async with s.begin():
            started = await vtest.start_test_execution(
                s, vtest.StartTestExecutionCommand(idempotency_key=idem(), test_definition_id=approved.aggregate_id), actor, None,
            )
        async with s.begin():
            policy = await signature_service.resolve_signature_requirement(s, record_type="validation_test_execution", action="complete")
            assert policy.signature_required and policy.required_role_id is None  # "Qualified performer", no dedicated role
            challenge_id = await _challenge(s, actor, "validation_test_execution", "complete", started.aggregate_id, started.resulting_version)
            completed = await vtest.complete_test_execution(
                s, vtest.CompleteTestExecutionCommand(
                    idempotency_key=idem(), execution_id=started.aggregate_id, expected_version=started.resulting_version,
                    actual_result="Worked as expected", status="PASS", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), actor, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import ValidationTestExecution
        row = await s.get(ValidationTestExecution, completed.aggregate_id)
        assert row.status == "PASS" and row.completed_at is not None


async def test_test_execution_blocked_requires_reason(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            defn = await vtest.create_test_definition(
                s, vtest.CreateTestDefinitionCommand(
                    idempotency_key=idem(), test_code="WP12-TC-2", method="ANALYSIS",
                    procedure="Analyze", expected_results="Conclusion reached",
                ), actor, None,
            )
        async with s.begin():
            releaser = seeded["users"]["qa.releaser"].id
            challenge_id = await _challenge(s, releaser, "validation_test_definition", "approve", defn.aggregate_id, defn.resulting_version)
            approved = await vtest.approve_test_definition(
                s, vtest.ApproveTestDefinitionCommand(
                    idempotency_key=idem(), test_id=defn.aggregate_id, expected_version=defn.resulting_version,
                    reason="ok", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
        async with s.begin():
            started = await vtest.start_test_execution(
                s, vtest.StartTestExecutionCommand(idempotency_key=idem(), test_definition_id=approved.aggregate_id), actor, None,
            )
        async with s.begin():
            challenge_id = await _challenge(s, actor, "validation_test_execution", "complete", started.aggregate_id, started.resulting_version)
            with pytest.raises(ValidationFailedError):
                await vtest.complete_test_execution(
                    s, vtest.CompleteTestExecutionCommand(
                        idempotency_key=idem(), execution_id=started.aggregate_id, expected_version=started.resulting_version,
                        actual_result="could not run", status="BLOCKED", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), actor, None,
                )  # TST-FR-014: blocked_reason required


# ---- Document 83: Installation Qualification ------------------------------------------------------


async def test_iq_execution_deviation_and_independent_approval(db, seeded):
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            protocol = await iq.create_iq_protocol(
                s, iq.CreateIqProtocolCommand(
                    idempotency_key=idem(), environment="staging", release_ref="R1", deployment_profile="cloud",
                    expected_components=[{"name": "postgres", "version": "16.4"}], acceptance_criteria="all checks pass",
                ), actor, None,
            )
        async with s.begin():
            execution = await iq.start_iq_execution(
                s, iq.StartIqExecutionCommand(
                    idempotency_key=idem(), protocol_id=protocol.aggregate_id,
                    installed_inventory={"postgres": "16.2"},  # mismatch -> IQ-FR-018 deviation
                ), actor, None,
            )
        async with SessionLocal() as s2:
            from app.modules.validation.models import IqExecution
            row = await s2.get(IqExecution, execution.aggregate_id)
            assert len(row.deviations) == 1 and row.deviations[0]["component"] == "postgres"
        async with s.begin():
            challenge_id = await _challenge(s, actor, "iq_execution", "complete", execution.aggregate_id, execution.resulting_version)
            completed = await iq.complete_iq_execution(
                s, iq.CompleteIqExecutionCommand(
                    idempotency_key=idem(), execution_id=execution.aggregate_id, expected_version=execution.resulting_version,
                    result="PASS", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), actor, None,
            )
        # same performer cannot approve their own IQ execution (Document 106 row 148 independence)
        async with s.begin():
            challenge_id = await _challenge(s, actor, "iq_execution", "approve", completed.aggregate_id, completed.resulting_version)
            with pytest.raises(ValidationFailedError):
                await iq.approve_iq_execution(
                    s, iq.ApproveIqExecutionCommand(
                        idempotency_key=idem(), execution_id=completed.aggregate_id, expected_version=completed.resulting_version,
                        reason="deviation reviewed", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), actor, None,
                )
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "iq_execution", "approve", completed.aggregate_id, completed.resulting_version)
            approved = await iq.approve_iq_execution(
                s, iq.ApproveIqExecutionCommand(
                    idempotency_key=idem(), execution_id=completed.aggregate_id, expected_version=completed.resulting_version,
                    reason="deviation reviewed and accepted", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import IqExecution
        row = await s.get(IqExecution, approved.aggregate_id)
        assert row.approved_by_user_id == releaser


# ---- AG-12/OBJ-FR-004: evidence_manifest entries must reference a real, finalized Evidence Store object ----


async def test_complete_test_execution_rejects_unfinalized_evidence_ref(db, seeded):
    """A caller cannot cite an evidence_id that either doesn't exist or is still STAGED (not yet
    finalized) -- shared.verify_evidence_refs() rejects it before the execution can complete. A
    genuinely finalized evidence object is accepted."""
    actor = seeded["users"]["operator1"].id
    releaser = seeded["users"]["qa.releaser"].id
    async with SessionLocal() as s:
        async with s.begin():
            defn = await vtest.create_test_definition(
                s, vtest.CreateTestDefinitionCommand(
                    idempotency_key=idem(), test_code="WP12-TC-EVID", method="SCRIPTED_MANUAL",
                    procedure="Do the thing", expected_results="It works",
                ), actor, None,
            )
        async with s.begin():
            challenge_id = await _challenge(s, releaser, "validation_test_definition", "approve", defn.aggregate_id, defn.resulting_version)
            approved = await vtest.approve_test_definition(
                s, vtest.ApproveTestDefinitionCommand(
                    idempotency_key=idem(), test_id=defn.aggregate_id, expected_version=defn.resulting_version,
                    reason="reviewed", challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), releaser, None,
            )
        async with s.begin():
            started = await vtest.start_test_execution(
                s, vtest.StartTestExecutionCommand(idempotency_key=idem(), test_definition_id=approved.aggregate_id), actor, None,
            )

        # a random evidence_id that doesn't exist at all
        async with s.begin():
            challenge_id = await _challenge(s, actor, "validation_test_execution", "complete", started.aggregate_id, started.resulting_version)
            with pytest.raises(ValidationFailedError):
                await vtest.complete_test_execution(
                    s, vtest.CompleteTestExecutionCommand(
                        idempotency_key=idem(), execution_id=started.aggregate_id, expected_version=started.resulting_version,
                        actual_result="Worked", status="PASS", evidence_manifest=[{"evidence_id": str(uuid.uuid4())}],
                        challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), actor, None,
                )

        # a real evidence object that is still STAGED (not finalized)
        data = b"screenshot bytes"
        async with s.begin():
            staged = await ev.stage_evidence_upload(
                s, ev.StageEvidenceUploadCommand(
                    idempotency_key=idem(), owner_type="validation_test_execution", owner_id=started.aggregate_id,
                    filename="evidence.png", mime_type="image/png", expected_hash=sha256_bytes(data), reason="capture",
                ), actor,
            )
        async with s.begin():
            challenge_id = await _challenge(s, actor, "validation_test_execution", "complete", started.aggregate_id, started.resulting_version)
            with pytest.raises(ValidationFailedError):
                await vtest.complete_test_execution(
                    s, vtest.CompleteTestExecutionCommand(
                        idempotency_key=idem(), execution_id=started.aggregate_id, expected_version=started.resulting_version,
                        actual_result="Worked", status="PASS", evidence_manifest=[{"evidence_id": str(staged.aggregate_id)}],
                        challenge_id=challenge_id, reauth_password="ChangeMe123!",
                    ), actor, None,
                )

        # finalize it, then completion succeeds with the same evidence_id
        async with s.begin():
            await ev.finalize_evidence_upload(
                s, ev.FinalizeEvidenceUploadCommand(
                    idempotency_key=idem(), evidence_id=staged.aggregate_id, expected_version=1,
                    content_base64=base64.b64encode(data).decode(), reason="capture",
                ), actor,
            )
        async with s.begin():
            challenge_id = await _challenge(s, actor, "validation_test_execution", "complete", started.aggregate_id, started.resulting_version)
            completed = await vtest.complete_test_execution(
                s, vtest.CompleteTestExecutionCommand(
                    idempotency_key=idem(), execution_id=started.aggregate_id, expected_version=started.resulting_version,
                    actual_result="Worked", status="PASS", evidence_manifest=[{"evidence_id": str(staged.aggregate_id)}],
                    challenge_id=challenge_id, reauth_password="ChangeMe123!",
                ), actor, None,
            )
    async with SessionLocal() as s:
        from app.modules.validation.models import ValidationTestExecution
        row = await s.get(ValidationTestExecution, completed.aggregate_id)
        assert row.status == "PASS" and row.evidence_manifest[0]["evidence_id"] == str(staged.aggregate_id)
