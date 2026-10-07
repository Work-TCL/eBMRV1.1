"""SG-146 (remainder, module 2 of 8) — Document 23's UOM expand step. Same pattern
`tests/test_yield_reconciliation.py`'s dual-write/backfill tests establish, applied to
`ebmr.qc_sample.sample_uom_id`/`ebmr.qc_result.uom_id`/`ebmr.qc_test_definition.uom_id`.

`qc_sample` is mutable (backfillable); `qc_test_definition`/`qc_result` have no UPDATE grant
(append-only, AG-08) so only dual-write at creation is possible for those two — no backfill test exists
for them because there is nothing to backfill.
"""

import uuid
from decimal import Decimal

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.qc.models import QcSample
from app.modules.qc.uom_backfill import backfill_qc_samples
from app.modules.rules.models import UnitOfMeasure
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username):
    user = User(
        username=username, email=f"{username}@example.com", full_name="Test Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


async def test_create_sample_dual_writes_sample_uom_id_when_a_released_uom_resolves(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.qcuom1")
        db.add(UnitOfMeasure(code="mL-qc1", dimension="VOLUME", base_unit="mL-qc1", factor=Decimal("1"), precision_dp=4, status="released"))
    token = await login(client, "admin.qcuom1")

    resp = await client.post(
        "/qc/v1/samples",
        json={
            "idempotency_key": idem(), "sample_number": "SAMPLE-UOM-1", "sample_type": "finished_product",
            "source_type": "reserve", "sample_quantity": "10.0", "sample_uom": "mL-qc1",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    sample = await db.get(QcSample, uuid.UUID(resp.json()["aggregate_id"]))
    assert sample.sample_uom == "mL-qc1"
    assert sample.sample_uom_id is not None


async def test_create_sample_rejects_unresolvable_uom(client, seeded, db):
    """Client requirements #2/#3 (2026-09-21): sample creation now hardens sample_uom resolution via
    `_resolve_uom_id_strict` since the UI only ever submits a code drawn from the released list --
    superseding the old best-effort "leaves sample_uom_id null" behavior for this specific, now
    UI-enforced call site."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.qcuom2")
    token = await login(client, "admin.qcuom2")

    resp = await client.post(
        "/qc/v1/samples",
        json={
            "idempotency_key": idem(), "sample_number": "SAMPLE-UOM-2", "sample_type": "finished_product",
            "source_type": "reserve", "sample_quantity": "10.0", "sample_uom": "not-a-real-unit",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_backfill_qc_samples_is_idempotent_and_never_guesses(db, seeded):
    async with db.begin():
        site_id = seeded["site_id"]
        resolvable = QcSample(
            sample_number="BF-1", sample_type="finished_product", source_type="reserve",
            sample_quantity=Decimal("5"), sample_uom="g-qcbf", version=1,
        )
        unresolvable = QcSample(
            sample_number="BF-2", sample_type="finished_product", source_type="reserve",
            sample_quantity=Decimal("5"), sample_uom="not-a-real-unit", version=1,
        )
        db.add_all([resolvable, unresolvable])
        db.add(UnitOfMeasure(code="g-qcbf", dimension="MASS", base_unit="g-qcbf", factor=Decimal("1"), precision_dp=4, status="released"))
        await db.flush()
        resolvable_id, unresolvable_id = resolvable.id, unresolvable.id

    async with db.begin():
        result = await backfill_qc_samples(db, batch_size=500)
    assert result.matched >= 1
    assert result.unmatched >= 1

    matched_row = await db.get(QcSample, resolvable_id)
    unmatched_row = await db.get(QcSample, unresolvable_id)
    assert matched_row.sample_uom_id is not None
    assert unmatched_row.sample_uom_id is None

    async with db.begin():
        second = await backfill_qc_samples(db, batch_size=500)
    assert second.processed == second.unmatched
