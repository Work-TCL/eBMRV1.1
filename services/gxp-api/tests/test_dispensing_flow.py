"""Document 21 (SPEC-MAT-002C) — Material Dispensing & Weighing. Builds on Document 20's put-away/release
chain: create order -> select-source (reuses a released, put-away lot) -> start (qualification gate) ->
manual-reading -> verify (independence-from-performer) -> complete (inventory consumption + dispensed-
container creation) -> cancel (independence-from-author, reason required, reservation returned)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.core.security import hash_password
from app.modules.genealogy import service as genealogy_service
from app.modules.iam.models import Role, User, UserSiteRole
from app.modules.material.models import (
    DispensedContainer,
    DispensingOrder,
    InventoryBalanceProjection,
    WeighingReading,
    WeighingSession,
)
from app.modules.material.models import MaterialContainer, MaterialLot
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_inventory_flow import _create_material, _put_away, _receive_and_examine, _release_lot


async def _receive_lot_for_material(client, db, token, site_id, material_id, internal_lot, quantity="100.000000"):
    """Like Document 20's `_receive_and_examine`, but against an *existing* material (needed for
    multi-lot dispensing, DSP-FR-017, where two lots share one material identity)."""
    receipt_id = (
        await client.post(
            "/materials/v1/receipts",
            json={
                "idempotency_key": idem(),
                "site_id": str(site_id),
                "receipt_number": f"RCPT-{internal_lot}",
                "material_id": material_id,
                "received_gross_quantity": quantity,
                "accepted_quantity": quantity,
                "uom": "kg",
            },
            headers=auth_headers(token),
        )
    ).json()["aggregate_id"]
    resp = await client.post(
        f"/materials/v1/receipts/{receipt_id}/examine",
        json={
            "idempotency_key": idem(),
            "receipt_id": receipt_id,
            "expected_version": 1,
            "labeling_ok": True,
            "damage_observed": False,
            "seal_broken": False,
            "contamination_observed": False,
            "identity_confirmed": True,
            "internal_lot": internal_lot,
            "container_count": 1,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    lot = (await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == internal_lot))).scalar_one()
    container = (
        await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot.id))
    ).scalar_one()
    return str(lot.id), str(container.id)


async def _create_batch_with_requirement(
    client, token, site_id, code, material_id, target_qty="30.000000", low="28.000000", high="32.000000", uom="kg"
):
    """Same batch-creation shape as test_inventory_flow.py::_create_batch, extended with a released
    `RecipeStep` + `RecipeMaterialRequirement` and a matching `BatchStep` -- SG-094 (project-owner-
    directed, Topic 5): `create_dispensing_order` now derives its target/tolerance from this chain
    instead of accepting caller-supplied values. Returns (batch_id, batch_step_id)."""
    import uuid as _uuid
    from decimal import Decimal as _Decimal

    from app.core.db import SessionLocal
    from app.modules.batch_execution.models import Batch as _GxpBatch, BatchStep as _BatchStep
    from app.modules.material_specification.models import (
        MaterialSpecificationVersion as _MaterialSpecificationVersion,
    )
    from app.modules.product_master.models import ProductVersion as _ProductVersion
    from app.modules.recipe_master.models import (
        RecipeFamily as _RecipeFamily,
        RecipeMaterialRequirement as _RecipeMaterialRequirement,
        RecipeSection as _RecipeSection,
        RecipeStep as _RecipeStep,
        RecipeVersion as _RecipeVersion,
    )

    site_uuid = site_id if isinstance(site_id, _uuid.UUID) else _uuid.UUID(str(site_id))
    material_uuid = material_id if isinstance(material_id, _uuid.UUID) else _uuid.UUID(str(material_id))
    tag = f"{code}-{_uuid.uuid4().hex[:8]}"
    async with SessionLocal() as s:
        async with s.begin():
            pv = _ProductVersion(
                product_business_id=f"PB-{tag}", version_no=1, product_code=f"PC-{tag}", name=code,
                manufacturing_profile_code="pharma", lifecycle_state="released", site_id=site_uuid,
            )
            s.add(pv)
            await s.flush()
            rf = _RecipeFamily(
                product_business_id=pv.product_business_id, recipe_code=f"RC-{tag}", site_id=site_uuid,
                manufacturing_profile_code="pharma",
            )
            s.add(rf)
            await s.flush()
            rv = _RecipeVersion(
                recipe_family_id=rf.id, version_no=1, product_version_id=pv.id, site_id=site_uuid,
                lifecycle_state="released",
            )
            s.add(rv)
            await s.flush()
            section = _RecipeSection(
                recipe_version_id=rv.id, stable_section_code=f"SEC-{tag}", name="Dispensing", sequence=1,
            )
            s.add(section)
            await s.flush()
            step = _RecipeStep(
                recipe_version_id=rv.id, stable_step_code=f"STEP-{tag}", section_id=section.id,
                step_type="dispensing", sequence_hint=1,
            )
            s.add(step)
            await s.flush()
            spec = _MaterialSpecificationVersion(
                material_spec_business_id=f"SPEC-{tag}", version_no=1, material_id=material_uuid,
                name=f"Spec {tag}", lifecycle_state="released", site_id=site_uuid,
            )
            s.add(spec)
            await s.flush()
            requirement = _RecipeMaterialRequirement(
                step_id=step.id, material_spec_version_id=spec.id,
                target_value=_Decimal(target_qty), min_value=_Decimal(low), max_value=_Decimal(high), uom=uom,
            )
            s.add(requirement)
            await s.flush()
            batch = _GxpBatch(
                site_id=site_uuid, batch_number=f"B-{tag}", product_version_id=pv.id,
                recipe_version_id=rv.id, target_qty=_Decimal("10"), target_uom="kg",
                state="in_execution", version=1,
            )
            s.add(batch)
            await s.flush()
            batch_step = _BatchStep(
                batch_id=batch.id, recipe_step_code=step.stable_step_code, state="pending", version=1,
            )
            s.add(batch_step)
            await s.flush()
            return str(batch.id), str(batch_step.id)


async def _create_order(client, token, site_id, batch_id, batch_step_id, material_id):
    resp = await client.post(
        "/dispensing/v1/orders",
        json={
            "idempotency_key": idem(),
            "site_id": str(site_id),
            "batch_id": batch_id,
            "batch_step_id": batch_step_id,
            "material_id": material_id,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _challenge(client, token, order_id, action):
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/signature-challenges",
        json={"action": action},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def _select_source(client, token, order_id, expected_version, material_lot_id, quantity="30.000000", reservation_id=None, container_id=None):
    challenge_id = await _challenge(client, token, order_id, "select_source")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/select-source",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "material_lot_id": material_lot_id,
            "container_id": container_id,
            "reservation_id": reservation_id,
            "quantity": quantity,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _start(client, token, order_id, expected_version):
    challenge_id = await _challenge(client, token, order_id, "start")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/start",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _manual_reading(client, token, order_id, expected_version, value, stable=True, reason="operator entry"):
    challenge_id = await _challenge(client, token, order_id, "manual_reading")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/manual-reading",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "reading_value": value,
            "uom": "kg",
            "stable": stable,
            "manual_reason": reason,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _verify(client, token, order_id, expected_version):
    challenge_id = await _challenge(client, token, order_id, "verify")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/verify",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _complete(client, token, order_id, expected_version, source_id, quantity, container_code):
    challenge_id = await _challenge(client, token, order_id, "complete")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/complete",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "actual_taken_quantities": {source_id: quantity},
            "container_code": container_code,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _cancel(client, token, order_id, expected_version, reason="operational change"):
    challenge_id = await _challenge(client, token, order_id, "cancel")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/cancel",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "reason": reason,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _prepared_lot(client, db, op_token, qa_token, site_id, code, internal_lot, quantity="100.000000"):
    """Receive -> examine -> release (QA Releaser signs, Document 106 rows 44/45), returning
    (material_id, lot_id, container_id). Caller still needs to put the container away (Document 20's
    `_put_away`) before it has any ledger balance."""
    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, code, internal_lot, quantity=quantity
    )
    await _release_lot(client, qa_token, lot_id)
    return material_id, lot_id, containers[0]


async def test_full_dispensing_flow_happy_path(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-DSP", "LOT-DSP")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "DSP", material_id)

    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    # SG-094 (Topic 5): target/tolerance/UOM are derived from the recipe's RecipeMaterialRequirement,
    # not caller-supplied.
    created_order = await db.get(DispensingOrder, uuid.UUID(order_id))
    assert created_order.target_from_recipe is True
    assert created_order.target_qty == Decimal("30.000000")
    assert created_order.tolerance_low == Decimal("28.000000")
    assert created_order.tolerance_high == Decimal("32.000000")
    assert created_order.target_uom == "kg"

    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text

    start_resp = await _start(client, op_token, order_id, 2)
    assert start_resp.status_code == 200, start_resp.text

    reading_resp = await _manual_reading(client, op_token, order_id, 3, "30.000000")
    assert reading_resp.status_code == 200, reading_resp.text

    verify_resp = await _verify(client, qc_token, order_id, 3)
    assert verify_resp.status_code == 200, verify_resp.text
    assert verify_resp.json()["signature_id"] is not None

    from app.modules.material.models import DispensingSource

    src = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalar_one()

    complete_resp = await _complete(client, op_token, order_id, 4, str(src.id), "30.000000", "DISP-CTR-1")
    assert complete_resp.status_code == 200, complete_resp.text

    db.expire_all()
    order = await db.get(DispensingOrder, uuid.UUID(order_id))
    assert order.state == "completed"

    dispensed = (
        await db.execute(select(DispensedContainer).where(DispensedContainer.dispensing_order_id == order_id))
    ).scalar_one()
    assert dispensed.actual_quantity == 30

    balance = (
        await db.execute(
            select(InventoryBalanceProjection).where(InventoryBalanceProjection.material_lot_id == uuid.UUID(lot_id))
        )
    ).scalar_one()
    assert balance.on_hand == 70


async def test_select_source_wrong_material_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-WRONG", "LOT-WRONG")
    other_material_id = await _create_material(client, site_id, code="RM-OTHER", name="Other")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "WRONGMAT", other_material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, other_material_id)

    resp = await _select_source(client, op_token, order_id, 1, lot_id)
    assert resp.status_code == 422
    assert resp.json()["code"] == "WRONG_MATERIAL"


async def test_create_order_without_recipe_requirement_rejected(client, db, seeded):
    """SG-094 (Topic 5): if the batch's recipe declares no `RecipeMaterialRequirement` for this
    material at this step, order creation hard-errors rather than falling back to a guessed target."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    material_id = await _create_material(client, site_id, code="RM-NOREQ", name="No requirement")
    other_material_id = await _create_material(client, site_id, code="RM-NOREQ-OTHER", name="Other")
    # Requirement is declared for other_material_id, not material_id.
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "NOREQ", other_material_id)

    resp = await client.post(
        "/dispensing/v1/orders",
        json={
            "idempotency_key": idem(),
            "site_id": str(site_id),
            "batch_id": batch_id,
            "batch_step_id": batch_step_id,
            "material_id": material_id,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_override_dispensing_order_target_requires_role_reason_and_created_state(client, db, seeded):
    """SG-094 (Topic 5) override path: Supervisor/Admin-only, mandatory reason, and only usable while
    the order is still `created` -- mirrors `batch_step.role_override`'s RBAC-only, no-signature shape."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    supervisor_token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-OVR", "LOT-OVR")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "OVR", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    # Operator holds no dispensing_order.override_target grant.
    forbidden_resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/override-target",
        json={
            "idempotency_key": idem(), "expected_version": 1,
            "target_qty": "31.000000", "target_uom": "kg",
            "tolerance_low": "29.000000", "tolerance_high": "33.000000",
            "override_reason": "Potency-adjusted target per batch record",
        },
        headers=auth_headers(op_token),
    )
    assert forbidden_resp.status_code == 403, forbidden_resp.text

    # Missing reason is rejected even for a Supervisor.
    no_reason_resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/override-target",
        json={
            "idempotency_key": idem(), "expected_version": 1,
            "target_qty": "31.000000", "target_uom": "kg",
            "tolerance_low": "29.000000", "tolerance_high": "33.000000",
            "override_reason": "   ",
        },
        headers=auth_headers(supervisor_token),
    )
    assert no_reason_resp.status_code == 422, no_reason_resp.text

    ok_resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/override-target",
        json={
            "idempotency_key": idem(), "expected_version": 1,
            "target_qty": "31.000000", "target_uom": "kg",
            "tolerance_low": "29.000000", "tolerance_high": "33.000000",
            "override_reason": "Potency-adjusted target per batch record",
        },
        headers=auth_headers(supervisor_token),
    )
    assert ok_resp.status_code == 200, ok_resp.text

    order = await db.get(DispensingOrder, uuid.UUID(order_id))
    assert order.target_from_recipe is False
    assert order.target_qty == Decimal("31.000000")
    assert order.tolerance_low == Decimal("29.000000")
    assert order.tolerance_high == Decimal("33.000000")
    assert order.override_reason == "Potency-adjusted target per batch record"
    assert order.overridden_by_user_id == seeded["users"]["supervisor1"].id

    # Once dispensing has started, the override path is no longer usable.
    select_resp = await _select_source(client, op_token, order_id, 2, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    await _start(client, op_token, order_id, 3)

    too_late_resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/override-target",
        json={
            "idempotency_key": idem(), "expected_version": 4,
            "target_qty": "31.000000", "target_uom": "kg",
            "tolerance_low": "29.000000", "tolerance_high": "33.000000",
            "override_reason": "Too late",
        },
        headers=auth_headers(supervisor_token),
    )
    assert too_late_resp.status_code == 409, too_late_resp.text
    assert too_late_resp.json()["code"] == "INVALID_TRANSITION"


async def test_select_source_insufficient_quantity_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(
        client, db, op_token, qa_token, site_id, "MAT-SHORT", "LOT-SHORT", quantity="5.000000"
    )
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "5.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "SHORT", material_id, target_qty="30.000000", low="28", high="32")
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    resp = await _select_source(client, op_token, order_id, 1, lot_id, quantity="30.000000", container_id=container_id)
    assert resp.status_code == 422
    assert resp.json()["code"] == "SOURCE_QUANTITY_INSUFFICIENT"


async def test_start_requires_current_qualification(client, db, seeded):
    """DSP-FR-005: iam.Qualification, wired up for real this pass — a second Operator-role user with no
    qualification row is blocked at `start`."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-NOQUAL", "LOT-NOQUAL")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "NOQUAL", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text

    unqualified = User(
        username="operator2", email="operator2@example.com", full_name="operator2",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(unqualified)
    await db.flush()
    operator_role = (await db.execute(select(Role).where(Role.name == "Operator"))).scalar_one()
    db.add(UserSiteRole(user_id=unqualified.id, site_id=seeded["site_id"], role_id=operator_role.id))
    await db.commit()

    op2_token = await login(client, "operator2")
    resp = await _start(client, op2_token, order_id, 2)
    assert resp.status_code == 403
    assert resp.json()["code"] == "QUALIFICATION_MISSING"


async def test_verify_requires_independence_from_performer(client, db, seeded):
    """DSP-FR-018 / Document 106 row 54: verifier MUST NOT be the performer. Only QC Reviewer holds
    dispensing_order.verify RBAC, and only Operator holds dispensing_order.start, so no single seeded
    account can legitimately reach both roles through the normal API -- performed_by_user_id is set
    directly via the db fixture to isolate the independence check from RBAC, the same technique already
    used for the qualification-gate test above."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-VERIFY", "LOT-VERIFY")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "VERIFYSELF", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    await _start(client, op_token, order_id, 2)

    order = await db.get(DispensingOrder, uuid.UUID(order_id))
    order.performed_by_user_id = seeded["users"]["qc.reviewer"].id
    await db.commit()

    resp = await _verify(client, qc_token, order_id, 3)
    assert resp.status_code == 428
    assert resp.json()["code"] == "VERIFIER_REQUIRED"


async def test_complete_out_of_tolerance_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-TOL", "LOT-TOL")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "TOLFAIL", material_id, target_qty="30.000000", low="28", high="32")
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, quantity="50.000000", container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    await _start(client, op_token, order_id, 2)

    from app.modules.material.models import DispensingSource

    src = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalar_one()

    resp = await _complete(client, op_token, order_id, 3, str(src.id), "50.000000", "DISP-CTR-TOL")
    assert resp.status_code == 422
    assert resp.json()["code"] == "WEIGHT_OUT_OF_TOLERANCE"


async def test_complete_critical_material_requires_verification_first(client, db, seeded):
    """SG-095 (project-owner-directed, Topic 10): a critical material's dispense cannot complete on the
    performer's own reading alone -- it must pass through the independent `verify` step first, even
    though a non-critical material may complete straight from `started` (Document 21's original
    behavior, left unchanged for that case)."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-CRIT", "LOT-CRIT")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")

    from app.modules.material.models import Material

    material = await db.get(Material, uuid.UUID(material_id))
    material.critical = True
    await db.commit()

    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "CRIT", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    start_resp = await _start(client, op_token, order_id, 2)
    assert start_resp.status_code == 200, start_resp.text
    reading_resp = await _manual_reading(client, op_token, order_id, 3, "30.000000")
    assert reading_resp.status_code == 200, reading_resp.text

    from app.modules.material.models import DispensingSource

    src = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalar_one()

    # order.state is still "started" (never verified) -- completion must be blocked.
    blocked_resp = await _complete(client, op_token, order_id, 3, str(src.id), "30.000000", "DISP-CRIT-CTR")
    assert blocked_resp.status_code == 428, blocked_resp.text
    assert blocked_resp.json()["code"] == "VERIFIER_REQUIRED"

    verify_resp = await _verify(client, qc_token, order_id, 3)
    assert verify_resp.status_code == 200, verify_resp.text

    complete_resp = await _complete(client, op_token, order_id, 4, str(src.id), "30.000000", "DISP-CRIT-CTR")
    assert complete_resp.status_code == 200, complete_resp.text


async def test_locked_location_blocks_dispensing_completion(client, db, seeded):
    """Client Topic 7 Q14 (SG-084): a location locked for a physical count blocks the stock movement
    `complete_dispensing` performs, the same choke point `create_inventory_transfer` already enforces."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    supervisor_token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-LOCKDSP", "LOT-LOCKDSP")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "LOCKDSP", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    start_resp = await _start(client, op_token, order_id, 2)
    assert start_resp.status_code == 200, start_resp.text
    reading_resp = await _manual_reading(client, op_token, order_id, 3, "30.000000")
    assert reading_resp.status_code == 200, reading_resp.text

    lock_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{released_location_id}/lock",
        json={"idempotency_key": idem(), "expected_version": 1, "reason": "physical count"},
        headers=auth_headers(supervisor_token),
    )
    assert lock_resp.status_code == 200, lock_resp.text

    from app.modules.material.models import DispensingSource

    src = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalar_one()

    blocked_resp = await _complete(client, op_token, order_id, 3, str(src.id), "30.000000", "DISP-LOCKDSP-CTR")
    assert blocked_resp.status_code == 409, blocked_resp.text
    assert blocked_resp.json()["code"] == "LOCATION_LOCKED"

    unlock_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{released_location_id}/unlock",
        json={"idempotency_key": idem(), "expected_version": 2, "reason": "count complete"},
        headers=auth_headers(supervisor_token),
    )
    assert unlock_resp.status_code == 200, unlock_resp.text

    complete_resp = await _complete(client, op_token, order_id, 3, str(src.id), "30.000000", "DISP-LOCKDSP-CTR")
    assert complete_resp.status_code == 200, complete_resp.text


async def test_cancel_requires_reason(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-CANCELREASON", name="X")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "CANCELREASON", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    resp = await _cancel(client, qa_token, order_id, 1, reason="")
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_cancel_requires_independence_from_author(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-CANCELSOD", name="X")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "CANCELSOD", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    # Admin has dispensing_order.cancel but is also not the author here — use the author's own token
    # (operator1), which does NOT have dispensing_order.cancel granted, to prove SoD is enforced
    # independently of RBAC (an author who somehow held cancel permission would still be blocked).
    resp = await _cancel(client, op_token, order_id, 1)
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_cancel_returns_active_reservation(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-CANCELRES", "LOT-CANCELRES")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "CANCELRES", material_id)

    reservation_id = (
        await client.post(
            "/inventory/v1/reservations",
            json={
                "idempotency_key": idem(),
                "batch_id": batch_id,
                "material_id": material_id,
                "site_id": str(site_id),
                "quantity": "30.000000",
                "uom": "kg",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, None, quantity="30.000000", reservation_id=reservation_id)
    assert select_resp.status_code == 200, select_resp.text

    resp = await _cancel(client, qa_token, order_id, 2)
    assert resp.status_code == 200, resp.text

    from app.modules.material.models import InventoryReservation

    reservation = await db.get(InventoryReservation, uuid.UUID(reservation_id))
    assert reservation.status == "released"

    availability = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(qa_token),
        )
    ).json()
    assert availability["items"][0]["available"] == "100.00000000"


async def test_queue_lists_noncompleted_orders(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-QUEUE", name="X")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "QUEUE", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    queue = (await client.get("/dispensing/v1/queue", headers=auth_headers(op_token))).json()
    ids = [item["id"] for item in queue["items"]]
    assert order_id in ids


async def test_duplicate_create_order_idempotency_key_returns_same_receipt(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-IDEM21", name="X")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "IDEM21", material_id)

    key = idem()
    body = {
        "idempotency_key": key, "site_id": str(site_id), "batch_id": batch_id, "batch_step_id": batch_step_id,
        "material_id": material_id,
    }
    first = await client.post("/dispensing/v1/orders", json=body, headers=auth_headers(op_token))
    second = await client.post("/dispensing/v1/orders", json=body, headers=auth_headers(op_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


async def test_select_source_stale_version_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-STALE21", name="X")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "STALE21", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    resp = await _select_source(client, op_token, order_id, 999, None, quantity="1.000000")
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_unauthenticated_create_order_rejected(client):
    resp = await client.post(
        "/dispensing/v1/orders",
        json={
            "idempotency_key": idem(),
            "site_id": "00000000-0000-0000-0000-000000000000",
            "batch_id": "00000000-0000-0000-0000-000000000000",
            "batch_step_id": "00000000-0000-0000-0000-000000000000",
            "material_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert resp.status_code == 401


async def test_weighing_reading_update_refused_at_privilege_level(client, db, seeded):
    """Migration 0029 grants the runtime app role SELECT/INSERT/TRUNCATE only on weighing_readings (no
    UPDATE/DELETE) -- the same append-only discipline as inventory_transactions (migration 0028) and
    material_quality_dispositions (migration 0027), matching DSP-FR-014's "original reading retained"."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-READPRIV", "LOT-READPRIV")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "READPRIV", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    await _start(client, op_token, order_id, 2)
    await _manual_reading(client, op_token, order_id, 3, "30.000000")

    weighing = (
        await db.execute(select(WeighingSession).where(WeighingSession.dispensing_order_id == order_id))
    ).scalar_one()
    reading = (
        await db.execute(select(WeighingReading).where(WeighingReading.weighing_session_id == weighing.id))
    ).scalars().first()

    with pytest.raises(DBAPIError, match="(?i)permission denied|insufficient"):
        await db.execute(
            WeighingReading.__table__.update()
            .where(WeighingReading.id == reading.id)
            .values(reading_value=Decimal("1.00000000"))
        )
        await db.flush()
    await db.rollback()


async def test_cancel_without_valid_signature_challenge_rejected(client, db, seeded):
    """Every signed dispensing action shares the same `_dispensing_sign` -> `signature_service.
    consume_challenge` code path Document 19/20 already tested dedicatedly (e.g. test_inventory_flow.py::
    test_reservation_release_without_signature_rejected) -- this test exercises that shared mechanism
    through this module's own endpoint rather than duplicating it."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-NOSIG21", name="X")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "NOSIG21", material_id)
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/cancel",
        json={
            "idempotency_key": idem(),
            "expected_version": 1,
            "reason": "test",
            "challenge_id": str(uuid.uuid4()),
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_CHALLENGE_INVALID"


async def test_multiple_readings_preserve_history_and_sum_accepted_net(client, db, seeded):
    """DSP-FR-013: incremental weigh additions preserve every reading and accumulate the accepted net --
    both readings stay in the append-only weighing_readings table (DSP-FR-014's "original reading
    retained" rule)."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-MULTIREAD", "LOT-MULTIREAD")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "MULTIREAD", material_id, target_qty="30.000000", low="28", high="32")
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    start_resp = await _start(client, op_token, order_id, 2)
    assert start_resp.status_code == 200, start_resp.text

    first = await _manual_reading(client, op_token, order_id, 3, "18.000000")
    assert first.status_code == 200, first.text
    second = await _manual_reading(client, op_token, order_id, 3, "12.000000")
    assert second.status_code == 200, second.text

    weighing = (
        await db.execute(select(WeighingSession).where(WeighingSession.dispensing_order_id == order_id))
    ).scalar_one()
    readings = (
        await db.execute(
            select(WeighingReading)
            .where(WeighingReading.weighing_session_id == weighing.id)
            .order_by(WeighingReading.sequence)
        )
    ).scalars().all()
    assert [r.reading_value for r in readings] == [Decimal("18.000000"), Decimal("12.000000")]
    assert weighing.final_accepted_net == 30

    from app.modules.material.models import DispensingSource

    src = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalar_one()
    complete_resp = await _complete(client, op_token, order_id, 3, str(src.id), "30.000000", "DISP-MULTIREAD-CTR")
    assert complete_resp.status_code == 200, complete_resp.text


async def test_multi_lot_dispensing_conserves_genealogy_per_source(client, db, seeded):
    """DSP-FR-017: multiple approved lots contribute to one order, each source's exact quantity traced
    separately (dispensing_sources rows), no hidden pooling into a single undifferentiated total."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id = await _create_material(client, site_id, code="RM-MULTILOT", name="Multi-lot material")
    lot1_id, container1_id = await _receive_lot_for_material(client, db, op_token, site_id, material_id, "LOT-MULTILOT-1", quantity="20.000000")
    await _release_lot(client, qa_token, lot1_id)
    await _put_away(client, op_token, lot1_id, container1_id, released_location_id, "20.000000")
    lot2_id, container2_id = await _receive_lot_for_material(client, db, op_token, site_id, material_id, "LOT-MULTILOT-2", quantity="20.000000")
    await _release_lot(client, qa_token, lot2_id)
    await _put_away(client, op_token, lot2_id, container2_id, released_location_id, "20.000000")

    batch_id, batch_step_id = await _create_batch_with_requirement(client, op_token, site_id, "MULTILOT", material_id, target_qty="30.000000", low="28", high="32")
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    select1 = await _select_source(client, op_token, order_id, 1, lot1_id, quantity="15.000000", container_id=container1_id)
    assert select1.status_code == 200, select1.text
    select2 = await _select_source(client, op_token, order_id, 2, lot2_id, quantity="15.000000", container_id=container2_id)
    assert select2.status_code == 200, select2.text

    start_resp = await _start(client, op_token, order_id, 3)
    assert start_resp.status_code == 200, start_resp.text
    reading_resp = await _manual_reading(client, op_token, order_id, 4, "30.000000")
    assert reading_resp.status_code == 200, reading_resp.text

    from app.modules.material.models import DispensingSource

    sources = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalars().all()
    assert len(sources) == 2
    assert {str(s.material_lot_id) for s in sources} == {lot1_id, lot2_id}

    # _complete() only accepts one (source_id -> qty) pair; exercise the real multi-source contract
    # directly against the endpoint since DSP-FR-017 requires every source represented in one call.
    challenge_id = await _challenge(client, op_token, order_id, "complete")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/complete",
        json={
            "idempotency_key": idem(),
            "expected_version": 4,
            "actual_taken_quantities": {str(sources[0].id): "15.000000", str(sources[1].id): "15.000000"},
            "container_code": "DISP-MULTILOT-CTR",
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    dispensed = (
        await db.execute(select(DispensedContainer).where(DispensedContainer.dispensing_order_id == order_id))
    ).scalar_one()
    assert dispensed.actual_quantity == 30

    # SG-096 DSP-FR-023 (Task 2, 2026-09-23): "Create source lot/container -> dispensed container" is
    # DERIVED_FROM, not SPLIT_FROM, precisely because (as here) a dispensed container can be derived from
    # multiple different source lots at once (DSP-FR-017) -- a many-to-one relationship.
    [dispensed_node] = await genealogy_service.lookup(db, site_id, business_ref="DISP-MULTILOT-CTR")
    ancestors = await genealogy_service.get_ancestors(db, dispensed_node.id)
    ancestor_record_ids = {n.authoritative_record_id for n in ancestors["nodes"]}
    assert ancestor_record_ids == {uuid.UUID(lot1_id), uuid.UUID(lot2_id)}
    assert all(e.edge_type == "DERIVED_FROM" for e in ancestors["edges"])
    assert {e.quantity for e in ancestors["edges"]} == {Decimal("15.000000")}
