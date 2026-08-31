"""Document 40 (SPEC-EQP-003) thin slice: create operation -> readiness (real composed EM/line-clearance/
equipment/sterile-input checks) -> start (Document 106 row 113) -> interventions/events -> complete (row
112). The main lifecycle test is the manual verification the WP-06 plan called for: it proves the
dependency-order build sequence (39 -> 41 -> 42 -> 40) paid off by exercising the real Document 38/39/41/42
functions through Document 40's readiness composition, not stubs.
"""

import uuid

from sqlalchemy import select

from app.modules.equipment.sterilization_models import SterilizationLoadItem
from tests.conftest import auth_headers, idem, login


async def _create_and_qualify_equipment(client, site_id, code="EQP-ASP-1"):
    admin_token = await login(client, "equipment.admin")
    resp = await client.post(
        "/equipment/v1/assets", json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": code},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    asset_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/equipment/v1/{asset_id}/qualifications",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 1,
            "qualification_status": "qualified", "qualified": True,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return asset_id


async def _create_eligible_sterile_load_item(client, db, site_id, profile_id):
    op_token = await login(client, "sterilization.operator")
    qa_token = await login(client, "qa.reviewer")
    equipment_id = await _create_and_qualify_equipment(client, site_id, code="EQP-ASP-STR-1")

    resp = await client.post(
        "/sterilization/v1/cycles",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "process_type": "steam_autoclave",
            "equipment_id": equipment_id, "profile_version_id": profile_id,
            "load_items": [{"item_type": "component", "item_reference": "ASP-COMP-1"}],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    cycle_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(f"/sterilization/v1/cycles/{cycle_id}/signature-challenges", json={"action": "start"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/sterilization/v1/cycles/{cycle_id}/start",
        json={"idempotency_key": idem(), "cycle_id": cycle_id, "expected_version": 1, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/sterilization/v1/cycles/{cycle_id}/data",
        json={"idempotency_key": idem(), "cycle_id": cycle_id, "expected_version": 2, "parameter_data": {"temperature": 121}, "final": True},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    challenge = (
        await client.post(f"/sterilization/v1/cycles/{cycle_id}/signature-challenges", json={"action": "review"}, headers=auth_headers(qa_token))
    ).json()
    resp = await client.post(
        f"/sterilization/v1/cycles/{cycle_id}/review",
        json={"idempotency_key": idem(), "cycle_id": cycle_id, "expected_version": 3, "decision": "accept", "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 200, resp.text

    item = (
        await db.execute(select(SterilizationLoadItem).where(SterilizationLoadItem.cycle_id == uuid.UUID(cycle_id)))
    ).scalars().first()
    return equipment_id, str(item.id)


async def _clear_area(client, site_id, area_id):
    sanitation_token = await login(client, "sanitation.operator")
    resp = await client.post(
        "/line-clearance/v1",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id)},
        headers=auth_headers(sanitation_token),
    )
    assert resp.status_code == 200, resp.text
    clearance_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(f"/line-clearance/v1/{clearance_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(sanitation_token))
    ).json()
    resp = await client.post(
        f"/line-clearance/v1/{clearance_id}/complete",
        json={"idempotency_key": idem(), "clearance_id": clearance_id, "expected_version": 1, "passed": True, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(sanitation_token),
    )
    assert resp.status_code == 200, resp.text


async def _create_operation(client, site_id, area_id, profile_id, equipment_id, item_id, actor_token):
    resp = await client.post(
        "/aseptic/v1/operations",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id),
            "profile_version_id": profile_id, "equipment_ids": [equipment_id],
            "sterile_input_refs": [{"item_id": item_id, "item_kind": "sterilization_load_item"}],
        },
        headers=auth_headers(actor_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_full_operation_lifecycle_ready_area_starts_and_completes(client, seeded, db):
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-A"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")
    supervisor_token = await login(client, "aseptic.supervisor")

    equipment_id, item_id = await _create_eligible_sterile_load_item(client, db, site_id, str(seeded["sterilization_profile"].id))
    await _clear_area(client, site_id, area_id)

    operation_id = await _create_operation(client, site_id, area_id, profile_id, equipment_id, item_id, op_token)

    # Cross-module payoff: this composes real Document 41 EM readiness, the Document 39 line-clearance
    # helper added this pass, real Document 38 equipment eligibility and real Document 42 sterile-item
    # status -- not stubs.
    readiness = (await client.get(f"/aseptic/v1/operations/{operation_id}/readiness")).json()
    assert readiness["ready"] is True, readiness
    assert readiness["em_readiness"]["status"] == "READY"
    assert readiness["line_clearance"]["cleared"] is True
    assert readiness["equipment_checks"][0]["eligible"] is True
    assert readiness["sterile_input_checks"][0]["sterile_status"] == "eligible"

    challenge = (
        await client.post(f"/aseptic/v1/operations/{operation_id}/signature-challenges", json={"action": "start"}, headers=auth_headers(supervisor_token))
    ).json()
    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/start",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(supervisor_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/aseptic/v1/operations/{operation_id}")).json()
    assert detail["state"] == "EXECUTION"

    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/interventions",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 2, "intervention_type": "routine", "planned": True, "location": "Fill line A"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/events",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 3, "event_type": "gowning_check", "severity": "info"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    challenge = (
        await client.post(f"/aseptic/v1/operations/{operation_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/complete",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 4, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/aseptic/v1/operations/{operation_id}")).json()
    assert detail["state"] == "ASEPTIC_COMPLETE"

    summary = (await client.get(f"/aseptic/v1/operations/{operation_id}/review-summary")).json()
    assert summary["state"] == "ASEPTIC_COMPLETE"
    assert summary["requires_deviation"] is False
    assert summary["unplanned_intervention_count"] == 0


async def test_start_with_unready_area_rejected(client, seeded):
    """Codex rule / test catalogue: 'start with failed area readiness' -- an unqualified equipment asset
    and an uncleared area both leave the composition not-ready, and start refuses to transition."""
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")
    supervisor_token = await login(client, "aseptic.supervisor")

    admin_token = await login(client, "equipment.admin")
    resp = await client.post(
        "/equipment/v1/assets", json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-ASP-UNQUAL"},
        headers=auth_headers(admin_token),
    )
    equipment_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/aseptic/v1/operations",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id),
            "profile_version_id": profile_id, "equipment_ids": [equipment_id], "sterile_input_refs": [],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    operation_id = resp.json()["aggregate_id"]

    readiness = (await client.get(f"/aseptic/v1/operations/{operation_id}/readiness")).json()
    assert readiness["ready"] is False
    assert readiness["equipment_checks"][0]["eligible"] is False

    challenge = (
        await client.post(f"/aseptic/v1/operations/{operation_id}/signature-challenges", json={"action": "start"}, headers=auth_headers(supervisor_token))
    ).json()
    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/start",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(supervisor_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] in ("ASEPTIC_AREA_NOT_READY", "STERILE_COMPONENT_INELIGIBLE")


async def test_unplanned_intervention_holds_operation(client, seeded):
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")

    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(op_token),
    )
    operation_id = resp.json()["aggregate_id"]

    # Force the operation directly into EXECUTION via the DB so this test isolates the intervention
    # behaviour from the readiness/start path already covered above.
    from sqlalchemy import update
    from app.core.db import SessionLocal
    from app.modules.equipment.aseptic_models import AsepticOperation
    async with SessionLocal() as db2:
        async with db2.begin():
            await db2.execute(update(AsepticOperation).where(AsepticOperation.id == uuid.UUID(operation_id)).values(state="EXECUTION"))

    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/interventions",
        json={
            "idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1,
            "intervention_type": "non_routine", "planned": False, "reason": "Unplanned line stoppage",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/aseptic/v1/operations/{operation_id}")).json()
    assert detail["state"] == "HOLD"
    assert detail["requires_deviation"] is True


async def test_critical_event_holds_operation(client, seeded):
    """ASP-FR-021/022 + spec test catalogue 'pressure excursion' (S007): a critical-severity event (EM/
    HVAC/pressure excursion or operator/gown breach) holds the operation and requires a deviation, same
    treatment as an unplanned intervention."""
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")

    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(op_token),
    )
    operation_id = resp.json()["aggregate_id"]

    from sqlalchemy import update
    from app.core.db import SessionLocal
    from app.modules.equipment.aseptic_models import AsepticOperation
    async with SessionLocal() as db2:
        async with db2.begin():
            await db2.execute(update(AsepticOperation).where(AsepticOperation.id == uuid.UUID(operation_id)).values(state="EXECUTION"))

    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/events",
        json={
            "idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1,
            "event_type": "pressure_excursion", "source": "hvac_monitor", "severity": "critical",
            "payload": {"differential_pressure_pa": -5},
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/aseptic/v1/operations/{operation_id}")).json()
    assert detail["state"] == "HOLD"
    assert detail["requires_deviation"] is True


async def test_complete_denied_while_deviation_unresolved(client, seeded):
    """ASP-FR-026 + spec test catalogue 'completion with unresolved event denied' (S010): an operation
    cannot complete while `requires_deviation` is set (e.g. from a prior critical event/unplanned
    intervention)."""
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")

    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(op_token),
    )
    operation_id = resp.json()["aggregate_id"]

    from sqlalchemy import update
    from app.core.db import SessionLocal
    from app.modules.equipment.aseptic_models import AsepticOperation
    async with SessionLocal() as db2:
        async with db2.begin():
            await db2.execute(
                update(AsepticOperation).where(AsepticOperation.id == uuid.UUID(operation_id))
                .values(state="EXECUTION", requires_deviation=True)
            )

    challenge = (
        await client.post(f"/aseptic/v1/operations/{operation_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/complete",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_unplanned_intervention_without_reason_rejected(client, seeded):
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")

    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(op_token),
    )
    operation_id = resp.json()["aggregate_id"]

    from sqlalchemy import update
    from app.modules.equipment.aseptic_models import AsepticOperation
    from app.core.db import SessionLocal
    async with SessionLocal() as db2:
        async with db2.begin():
            await db2.execute(update(AsepticOperation).where(AsepticOperation.id == uuid.UUID(operation_id)).values(state="EXECUTION"))

    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/interventions",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1, "intervention_type": "non_routine", "planned": False},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_stale_version_rejected(client, seeded):
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")
    supervisor_token = await login(client, "aseptic.supervisor")

    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(op_token),
    )
    operation_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(f"/aseptic/v1/operations/{operation_id}/signature-challenges", json={"action": "start"}, headers=auth_headers(supervisor_token))
    ).json()
    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/start",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 99, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(supervisor_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_create_operation_requires_role(client, seeded):
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_start_requires_supervisor_role(client, seeded):
    """Row 113 is granted to Aseptic Supervisor, not Aseptic Operator -- the operator who created the
    operation cannot also authorize its start."""
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")

    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(op_token),
    )
    operation_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(f"/aseptic/v1/operations/{operation_id}/signature-challenges", json={"action": "start"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/start",
        json={"idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_unauthenticated_create_rejected(client, seeded):
    resp = await client.post(
        "/aseptic/v1/operations",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "area_id": str(seeded["areas"]["AREA-GRADE-C"].id),
            "profile_version_id": str(seeded["aseptic_profile"].id), "equipment_ids": [], "sterile_input_refs": [],
        },
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# SG-117 follow-up: ASP-FR-018/019.
# ---------------------------------------------------------------------------


async def test_media_fill_reference_captured_at_creation(client, seeded):
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")

    media_fill_reference = {"media_fill_id": "MF-2026-03", "personnel_qualification_ref": "PQ-OP-142"}
    resp = await client.post(
        "/aseptic/v1/operations",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id),
            "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": [],
            "media_fill_reference": media_fill_reference,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    operation_id = resp.json()["aggregate_id"]
    detail = (await client.get(f"/aseptic/v1/operations/{operation_id}")).json()
    assert detail["media_fill_reference"] == media_fill_reference


async def _create_qc_test_order(db, site_id):
    import uuid as uuid_mod

    from app.modules.qc.models import QcSample, QcTestDefinition, QcTestOrder, QcTestSpecification

    async with db.begin():
        spec = QcTestSpecification(spec_code="SPEC-ASP-1", scope_type="product", scope_version_id=uuid_mod.uuid4())
        db.add(spec)
        await db.flush()
        definition = QcTestDefinition(
            specification_id=spec.id, test_code="STERILITY", test_name="Sterility test", result_data_type="text",
        )
        db.add(definition)
        await db.flush()
        sample = QcSample(sample_number=f"QC-ASP-{uuid_mod.uuid4().hex[:8]}", sample_type="sterility", source_type="reserve")
        db.add(sample)
        await db.flush()
        order = QcTestOrder(sample_id=sample.id, test_definition_id=definition.id)
        db.add(order)
        await db.flush()
        return order.id


async def test_complete_rejects_unknown_qc_references(client, seeded):
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")

    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(op_token),
    )
    operation_id = resp.json()["aggregate_id"]

    from sqlalchemy import update
    from app.core.db import SessionLocal
    from app.modules.equipment.aseptic_models import AsepticOperation
    async with SessionLocal() as db2:
        async with db2.begin():
            await db2.execute(update(AsepticOperation).where(AsepticOperation.id == uuid.UUID(operation_id)).values(state="EXECUTION"))

    challenge = (
        await client.post(f"/aseptic/v1/operations/{operation_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/complete",
        json={
            "idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1,
            "qc_test_order_id": str(uuid.uuid4()),
            "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "NOT_FOUND"


async def test_complete_captures_qc_test_order_linkage(client, seeded, db):
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    op_token = await login(client, "aseptic.operator")

    order_id = await _create_qc_test_order(db, site_id)

    resp = await client.post(
        "/aseptic/v1/operations",
        json={"idempotency_key": idem(), "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []},
        headers=auth_headers(op_token),
    )
    operation_id = resp.json()["aggregate_id"]

    from sqlalchemy import update
    from app.core.db import SessionLocal
    from app.modules.equipment.aseptic_models import AsepticOperation
    async with SessionLocal() as db2:
        async with db2.begin():
            await db2.execute(update(AsepticOperation).where(AsepticOperation.id == uuid.UUID(operation_id)).values(state="EXECUTION"))

    challenge = (
        await client.post(f"/aseptic/v1/operations/{operation_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/aseptic/v1/operations/{operation_id}/complete",
        json={
            "idempotency_key": idem(), "operation_id": operation_id, "expected_version": 1,
            "qc_test_order_id": str(order_id),
            "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/aseptic/v1/operations/{operation_id}")).json()
    assert detail["qc_test_order_id"] == str(order_id)


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded):
    op_token = await login(client, "aseptic.operator")
    site_id = seeded["site_id"]
    area_id = seeded["areas"]["AREA-GRADE-C"].id
    profile_id = str(seeded["aseptic_profile"].id)
    key = idem()
    payload = {"idempotency_key": key, "site_id": str(site_id), "area_id": str(area_id), "profile_version_id": profile_id, "equipment_ids": [], "sterile_input_refs": []}
    first = await client.post("/aseptic/v1/operations", json=payload, headers=auth_headers(op_token))
    second = await client.post("/aseptic/v1/operations", json=payload, headers=auth_headers(op_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]
