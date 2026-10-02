"""Workflow Handoff Notifications (project-owner-directed; no Document/SPEC-xxx baseline id -- see
app/modules/notifications/models.py's module docstring). Drives each of the six Pass-1 target categories
(batch release, deviation disposition/close, CAPA plan/close, document release) through real state via the
existing HTTP flows in test_release.py/test_qms_deviation.py/test_qms_capa.py/test_qms_document_control.py
(reusing their `_setup`/`_create`/`_advance_to_*` helpers, same cross-file-import convention
test_dashboard_reminders.py already uses), then proves: correct audience resolution by RBAC permission
code, SoD exclusion of the triggering actor, category transition as the aggregate moves states,
resolution on leaving the pending state, idempotency (duplicate sync never duplicates a row), the
lazy self-heal on GET, rebuildability from scratch, the real NATS consumer wiring end to end for one
workflow (release_scope) -- not mocked, the same real-broker-or-skip pattern test_eventbus_consumer.py
already established -- and the signature-policy audience narrowing (SG-214 fix).

The second block of tests below (search "Pass 2") covers registry.py's later expansion to the QMS/QC/
Material batch (NCR, Complaint, Change Control, SCAR, Field Action, Internal Audit, Risk, Material Lot,
Supplier Qualification, OOS, OOT) -- one representative pending-state check per module, reusing each
module's own test file's `_setup`/`_create`/`_advance_to_*` helpers exactly as Pass 1 did, since SoD
exclusion, duplicate-sync idempotency and the self-heal/rebuild mechanics are already proven generically
above and are not module-specific code paths. OOS/OOT reuse test_qc_oos.py's own full lifecycle/evaluate
sequences verbatim (real sample -> test-order -> result -> OOS/OOT chain, including the independent-signer
SoD steps Document 106 rows 65-69 require) rather than a lighter shortcut, since those two aggregates have
no simpler reusable helper the way the other modules do.

The third block (search "Pass 3") covers registry.py's later expansion to the three master-data
draft-authoring modules -- Material Specification, Product Master, Recipe Master release -- found via a
real user report (a material spec draft sat with no releaser notification) rather than a planned pass.
Reuses each module's own test file's draft/submit/release bodies and a local `signature_required=False`
SignaturePolicy row, the same cheap-setup precedent test_recipe_master.py's own release tests already use,
since the signature ceremony itself is already exhaustively tested in those modules' own files.
"""

import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.eventbus import jetstream
from app.modules.iam.models import User, UserSiteRole
from app.modules.mutation.models import OutboxEvent
from app.modules.notifications import consumer as notifications_consumer
from app.modules.notifications.models import WorkflowNotification
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_qms_capa import _create as _create_capa
from tests.test_qms_capa import _setup as _capa_setup
from tests.test_qms_deviation import _advance_to_disposition
from tests.test_qms_deviation import _create as _create_deviation
from tests.test_qms_deviation import _setup as _deviation_setup
from tests.test_qms_document_control import _create as _create_document
from tests.test_qms_document_control import _setup as _document_setup
from tests.test_release import _setup as _release_setup

# Pass 2 (QMS/QC/Material batch) helper imports.
from tests.test_qms_ncr import _create as _create_ncr
from tests.test_qms_ncr import _segregate_and_evaluate as _ncr_segregate_and_evaluate
from tests.test_qms_ncr import _setup as _ncr_setup
from tests.test_qms_complaint import _create_complaint, _investigate, _investigation_decision, _triage
from tests.test_qms_complaint import _make_product as _complaint_make_product
from tests.test_qms_complaint import _setup as _complaint_setup
from tests.test_qms_change_control import _create as _create_change
from tests.test_qms_change_control import _impact_body
from tests.test_qms_change_control import _setup as _change_setup
from tests.test_qms_scar import _create_case, _issue_scar, _respond as _scar_respond
from tests.test_qms_scar import _create_supplier as _scar_create_supplier
from tests.test_qms_scar import _setup as _scar_setup
from tests.test_qms_field_action import _create_field_action, _define_scope, _reportability as _field_action_reportability
from tests.test_qms_field_action import _setup as _field_action_setup
from tests.test_qms_internal_audit import _add_finding, _create_audit, _start_audit
from tests.test_qms_internal_audit import _setup as _internal_audit_setup
from tests.test_qms_risk import _add_controls, _add_initial_assessment, _add_residual_assessment, _create_risk
from tests.test_qms_risk import _setup as _risk_setup
from tests.test_material_flow import _create_material, _receive_lot
from tests.test_supplier_quality import _create_qualification, _create_supplier as _sq_create_supplier
from tests.test_supplier_quality import _site_id_for as _sq_site_id_for
from tests.test_qc import _author_and_release_rule, _make_admin as _qc_make_admin, _make_user as _qc_make_user, _seed_product_version

# Pass 3 (master-data release) helper imports.
from tests.test_material_specification import _draft_body as _matspec_draft_body
from tests.test_material_specification import _make_material as _matspec_make_material
from tests.test_product_master import _draft_body as _product_draft_body
from tests.test_recipe_master import _make_product_version as _recipe_make_product_version
from tests.test_recipe_master import _two_step_body as _recipe_two_step_body


async def _extra_role_user(db, seeded, username, role_name):
    async with db.begin():
        user = User(
            username=username, email=f"{username}@example.com", full_name="Test User",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


async def _latest_envelope(db, *, aggregate_type, aggregate_id) -> dict:
    row = (
        await db.execute(
            select(OutboxEvent)
            .where(OutboxEvent.aggregate_type == aggregate_type, OutboxEvent.aggregate_id == uuid.UUID(aggregate_id))
            .order_by(OutboxEvent.occurred_at.desc())
            .limit(1)
        )
    ).scalars().first()
    assert row is not None, f"no outbox event found for {aggregate_type}/{aggregate_id}"
    return {
        "event_id": str(row.id), "event_type": row.event_type, "aggregate_type": row.aggregate_type,
        "aggregate_id": str(row.aggregate_id), "aggregate_version": row.aggregate_version, "payload": row.payload,
    }


async def _sync(db, *, aggregate_type, aggregate_id) -> dict:
    """Drives the same generic handler the real NATS consumer uses, called directly against the real
    database (no mocks) -- exactly `test_eventbus_consumer.py`'s own established shortcut for proving
    handler logic without needing to publish/fetch a real broker message every time. `_latest_envelope`'s
    own bare read already autobegins a transaction on `db` (SQLAlchemy 2.0 autobegin), so this commits
    that same ambient transaction rather than opening a second one with `async with db.begin()`."""
    envelope = await _latest_envelope(db, aggregate_type=aggregate_type, aggregate_id=aggregate_id)
    result = await notifications_consumer.handle_workflow_event(db, envelope)
    await db.commit()
    return result


async def _notification_row(db, *, aggregate_type, aggregate_id, category) -> WorkflowNotification | None:
    return await db.scalar(
        select(WorkflowNotification).where(
            WorkflowNotification.aggregate_type == aggregate_type,
            WorkflowNotification.aggregate_id == uuid.UUID(aggregate_id),
            WorkflowNotification.category == category,
        )
    )


async def _workflow_actions(client, token) -> dict:
    resp = await client.get("/dashboard/v1/workflow-actions", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_batch_release_pending_excludes_triggering_admin_and_notifies_independent_qa_releaser(client, seeded, db):
    admin_token, batch_id = await _release_setup(db, client, seeded, "wn1")
    indep_releaser = await _extra_role_user(db, seeded, "qa.releaser.wn1", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn1")
    operator_token = await login(client, "operator1")

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    result = await _sync(db, aggregate_type="release_scope", aggregate_id=scope_id)
    assert result["active_category"] == "batch_release_pending"

    row = await _notification_row(db, aggregate_type="release_scope", aggregate_id=scope_id, category="batch_release_pending")
    assert row is not None
    assert row.excluded_actor_id is not None  # the admin who ran evaluate()

    admin_view = await _workflow_actions(client, admin_token)
    assert not any(i["aggregate_id"] == scope_id for i in admin_view["items"])  # SoD: excluded from own trigger

    releaser_view = await _workflow_actions(client, releaser_token)
    matching = [i for i in releaser_view["items"] if i["aggregate_id"] == scope_id]
    assert len(matching) == 1
    assert matching[0]["category"] == "batch_release_pending"
    assert matching[0]["read"] is False

    operator_view = await _workflow_actions(client, operator_token)
    assert not any(i["aggregate_id"] == scope_id for i in operator_view["items"])  # no release.release permission

    # Releasing resolves it for everyone.
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    await _sync(db, aggregate_type="release_scope", aggregate_id=scope_id)

    releaser_view_after = await _workflow_actions(client, releaser_token)
    assert not any(i["aggregate_id"] == scope_id for i in releaser_view_after["items"])
    resolved_row = await _notification_row(db, aggregate_type="release_scope", aggregate_id=scope_id, category="batch_release_pending")
    assert resolved_row.resolved_at is not None


async def test_signature_policy_role_narrows_audience_beyond_the_rbac_permission(client, seeded, db):
    """SG-214 fix: two users can both hold the RBAC permission (`release.release`) but only one of them
    holds the *narrower* role Document 106's signature policy actually requires to complete the write.
    `qa_releaser_b` proves the narrowing (RBAC yes, signer role no -> excluded, and not via the separate
    SoD/excluded_actor_id path since they never touched this record); `admin_token` proves inclusion
    still works (RBAC yes, signer role yes, not the trigger)."""
    from app.modules.signature.models import SignaturePolicy

    admin_token, batch_id = await _release_setup(db, client, seeded, "wn10")
    await _extra_role_user(db, seeded, "qa.releaser.wn10a", "QA Releaser")
    await _extra_role_user(db, seeded, "qa.releaser.wn10b", "QA Releaser")
    trigger_token = await login(client, "qa.releaser.wn10a")  # holds release.evaluate + release.release
    bystander_token = await login(client, "qa.releaser.wn10b")  # holds release.release, never touches the scope

    async with db.begin():
        policy = await db.scalar(
            select(SignaturePolicy).where(SignaturePolicy.record_type == "release_scope", SignaturePolicy.action == "release")
        )
        policy.required_role_id = seeded["roles"]["Admin"].id  # narrower than "anyone with release.release"

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(trigger_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]
    await _sync(db, aggregate_type="release_scope", aggregate_id=scope_id)

    admin_view = await _workflow_actions(client, admin_token)
    assert any(i["aggregate_id"] == scope_id for i in admin_view["items"])  # RBAC + narrowed signer role, not the trigger

    bystander_view = await _workflow_actions(client, bystander_token)
    assert not any(i["aggregate_id"] == scope_id for i in bystander_view["items"])  # RBAC yes, signer role no

    trigger_view = await _workflow_actions(client, trigger_token)
    assert not any(i["aggregate_id"] == scope_id for i in trigger_view["items"])  # SoD: excluded as the trigger


async def test_mark_read_is_per_viewer_and_does_not_touch_the_regulated_batch(client, seeded, db):
    admin_token, batch_id = await _release_setup(db, client, seeded, "wn2")
    await _extra_role_user(db, seeded, "qa.releaser.wn2", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn2")

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    await _sync(db, aggregate_type="release_scope", aggregate_id=scope_id)

    view = await _workflow_actions(client, releaser_token)
    notification_id = next(i["id"] for i in view["items"] if i["aggregate_id"] == scope_id)
    assert view["unread_count"] >= 1

    resp = await client.post(f"/dashboard/v1/workflow-actions/{notification_id}/read", headers=auth_headers(releaser_token))
    assert resp.status_code == 200, resp.text

    view_after = await _workflow_actions(client, releaser_token)
    row = next(i for i in view_after["items"] if i["id"] == notification_id)
    assert row["read"] is True

    # The regulated batch/scope itself is untouched by mark-as-read.
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "eligible"


async def test_deviation_category_transitions_from_disposition_pending_to_close_pending(client, seeded, db):
    owner = await _deviation_setup(db, seeded, "wn3", signed=False)
    token = await login(client, "admin.devwn3")
    await _extra_role_user(db, seeded, "qa.releaser.wn3", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn3")

    deviation_id = await _create_deviation(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)

    await _sync(db, aggregate_type="deviation_record", aggregate_id=deviation_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == deviation_id and i["category"] == "deviation_disposition_pending" for i in view["items"])

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact found", "capa_required": False,
            "capa_rationale": "n/a",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    await _sync(db, aggregate_type="deviation_record", aggregate_id=deviation_id)

    view_after = await _workflow_actions(client, releaser_token)
    categories = {i["category"] for i in view_after["items"] if i["aggregate_id"] == deviation_id}
    assert categories == {"deviation_close_pending"}  # disposition_pending resolved, close_pending opened

    old_row = await _notification_row(db, aggregate_type="deviation_record", aggregate_id=deviation_id, category="deviation_disposition_pending")
    assert old_row.resolved_at is not None


async def test_capa_plan_pending_then_close_pending(client, seeded, db):
    owner = await _capa_setup(db, seeded, "wn4", signed=False)
    token = await login(client, "admin.capawn4")
    await _extra_role_user(db, seeded, "qa.releaser.wn4", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn4")

    capa_id = await _create_capa(client, token, seeded, owner.id)
    await _sync(db, aggregate_type="capa_record", aggregate_id=capa_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == capa_id and i["category"] == "capa_plan_pending" for i in view["items"])

    from tests.test_qms_capa import _advance_to_effectiveness_review
    await _advance_to_effectiveness_review(client, db, token, capa_id, owner.id)
    await _sync(db, aggregate_type="capa_record", aggregate_id=capa_id)

    view_after = await _workflow_actions(client, releaser_token)
    categories = {i["category"] for i in view_after["items"] if i["aggregate_id"] == capa_id}
    assert categories == {"capa_close_pending"}


async def test_document_review_pending_resolves_on_release(client, seeded, db):
    owner = await _document_setup(db, seeded, "wn5", signed=False)
    token = await login(client, "admin.docwn5")
    await _extra_role_user(db, seeded, "qa.releaser.wn5", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn5")

    version_id = await _create_document(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/submit",
        json={
            "idempotency_key": idem(), "document_version_id": version_id, "expected_version": 1,
            "reviewers": [{"role": "technical", "subject_id": str(uuid.uuid4())}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    await _sync(db, aggregate_type="controlled_document_version", aggregate_id=version_id)

    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == version_id and i["category"] == "document_release_pending" for i in view["items"])

    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 2, "review_completed": True},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    await _sync(db, aggregate_type="controlled_document_version", aggregate_id=version_id)

    view_after = await _workflow_actions(client, releaser_token)
    assert not any(i["aggregate_id"] == version_id for i in view_after["items"])


async def test_duplicate_sync_never_duplicates_the_row(client, seeded, db):
    admin_token, batch_id = await _release_setup(db, client, seeded, "wn6")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]

    await _sync(db, aggregate_type="release_scope", aggregate_id=scope_id)
    await _sync(db, aggregate_type="release_scope", aggregate_id=scope_id)
    await _sync(db, aggregate_type="release_scope", aggregate_id=scope_id)

    rows = (
        await db.execute(
            select(WorkflowNotification).where(
                WorkflowNotification.aggregate_type == "release_scope",
                WorkflowNotification.aggregate_id == uuid.UUID(scope_id),
                WorkflowNotification.category == "batch_release_pending",
            )
        )
    ).scalars().all()
    assert len(rows) == 1


async def test_get_workflow_actions_self_heals_when_consumer_never_ran(client, seeded, db):
    """The consumer never runs at all in this test -- the notification row is inserted directly to
    simulate one that was already open, then the underlying release_scope is released out from under it
    (bypassing the consumer entirely). The plain GET must still stop showing it and must persist the
    resolution, proving the UI-side self-heal is real and not merely a display-time filter."""
    admin_token, batch_id = await _release_setup(db, client, seeded, "wn7")
    await _extra_role_user(db, seeded, "qa.releaser.wn7", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn7")

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    await _sync(db, aggregate_type="release_scope", aggregate_id=scope_id)

    # Release it directly through the real command (not the consumer) -- the notification row is now
    # stale relative to release_scope's real state, exactly as if the consumer had crashed.
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text

    row_before = await _notification_row(db, aggregate_type="release_scope", aggregate_id=scope_id, category="batch_release_pending")
    assert row_before.resolved_at is None  # still stale -- consumer never ran

    view = await _workflow_actions(client, releaser_token)
    assert not any(i["aggregate_id"] == scope_id for i in view["items"])

    # The GET above resolved this row through its own request-scoped session (a different session than
    # `db`); `db`'s identity map still holds the object loaded by `row_before` above with the stale
    # resolved_at=None value (app/core/db.py::SessionLocal sets expire_on_commit=False, so `db` never
    # learns about another session's commit on its own) -- force a real re-read, same
    # `populate_existing=True` fix test_postmarket_flow.py's own `_get_fresh()` already established for
    # this identical cross-session-staleness situation.
    row_after = await db.get(WorkflowNotification, row_before.id, populate_existing=True)
    assert row_after.resolved_at is not None  # the GET itself persisted the resolution


async def test_rebuild_rescans_from_scratch_and_is_permission_gated(client, seeded, db):
    admin_token, batch_id = await _release_setup(db, client, seeded, "wn8")
    operator_token = await login(client, "operator1")

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]

    resp = await client.post("/dashboard/v1/workflow-actions:rebuild", headers=auth_headers(operator_token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"

    from sqlalchemy import text

    # The app DB role has no DELETE grant on notifications.workflow_notification (same "superseded via
    # UPDATE/TRUNCATE, never hard-deleted through generic CRUD" convention as readmodels.* -- see the
    # migration's own grant comment) -- TRUNCATE is what's actually granted, and is exactly what
    # simulating "the projection was lost/rebuilt from scratch" calls for anyway.
    async with db.begin():
        await db.execute(text("TRUNCATE notifications.workflow_notification CASCADE"))
    assert await _notification_row(db, aggregate_type="release_scope", aggregate_id=scope_id, category="batch_release_pending") is None

    resp = await client.post("/dashboard/v1/workflow-actions:rebuild", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["rescanned"]["release_scope"] >= 1

    row = await _notification_row(db, aggregate_type="release_scope", aggregate_id=scope_id, category="batch_release_pending")
    assert row is not None
    assert row.resolved_at is None


async def _nats_reachable() -> bool:
    try:
        await jetstream.connect()
        return jetstream.is_connected()
    except Exception:  # noqa: BLE001 - genuinely "not reachable", not a test failure
        return False


async def test_consumer_wiring_via_real_broker_end_to_end(client, seeded, db):
    """Not a unit-level shortcut like the other tests above -- publishes a real envelope to the real NATS
    JetStream broker, fetches it with a real durable pull consumer, and runs it through the exact
    `consume_event_idempotently` + `handle_workflow_event` path `consumer.py::run()` uses in production
    (skips, rather than fakes, if no broker is reachable -- matching test_eventbus_consumer.py's own
    established precedent)."""
    import json
    from datetime import datetime, timezone

    from app.modules.eventbus import consumer as eventbus_consumer
    from app.modules.eventbus.models import ConsumerInbox

    if not await _nats_reachable():
        import pytest
        pytest.skip("No live NATS JetStream broker reachable -- skipping, not faking")

    admin_token, batch_id = await _release_setup(db, client, seeded, "wn9")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    envelope = await _latest_envelope(db, aggregate_type="release_scope", aggregate_id=scope_id)

    unique = uuid.uuid4().hex[:10]
    subject = f"gxp.v1.release_scope.WnTest_{unique}"
    durable = f"test-workflow-notifications-{unique}"
    envelope = {**envelope, "event_type": f"WnTest_{unique}"}
    await jetstream.publish(subject, json.dumps(envelope).encode("utf-8"), msg_id=envelope["event_id"])

    sub = await jetstream.pull_subscribe(subject, durable_name=durable)
    msgs = await sub.fetch(1, timeout=5)
    assert len(msgs) == 1
    await eventbus_consumer._process_one_message(
        msgs[0], consumer_name=durable, handler=notifications_consumer.handle_workflow_event, max_deliver=6,
    )

    row = await _notification_row(db, aggregate_type="release_scope", aggregate_id=scope_id, category="batch_release_pending")
    assert row is not None
    assert row.resolved_at is None

    inbox = await db.scalar(
        select(ConsumerInbox).where(ConsumerInbox.consumer_name == durable, ConsumerInbox.event_id == uuid.UUID(envelope["event_id"]))
    )
    assert inbox.result == "PROCESSED"


# ---------------------------------------------------------------------------------------------------
# Pass 2 -- QMS/QC/Material batch (registry.py's later expansion). One representative pending-state check
# per module; SoD exclusion, idempotency and self-heal are already proven generically above.
# ---------------------------------------------------------------------------------------------------


async def test_ncr_disposition_pending_then_collapses_five_states_into_one_verification_category(client, seeded, db):
    """Also proves the multi-state-to-one-category collapse (registry.py maps REWORK/REPAIR/RETURN/
    SCRAP/USE_AS_IS all onto "ncr_verification_pending") and the category transition when disposition()
    resolves ncr_disposition_pending and opens ncr_verification_pending in its place."""
    owner = await _ncr_setup(db, seeded, "wn20", signed=False)
    token = await login(client, "admin.ncrwn20")
    await _extra_role_user(db, seeded, "qa.releaser.wn20", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn20")

    ncr_id = await _create_ncr(client, token, seeded["site_id"], owner.id)
    next_version = await _ncr_segregate_and_evaluate(client, token, ncr_id)  # -> EVALUATION
    await _sync(db, aggregate_type="nonconformance_record", aggregate_id=ncr_id)

    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == ncr_id and i["category"] == "ncr_disposition_pending" for i in view["items"])

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "USE_AS_IS", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "Cosmetic defect only, no functional impact.", "use_as_is_authorized_by": str(owner.id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    await _sync(db, aggregate_type="nonconformance_record", aggregate_id=ncr_id)

    old_row = await _notification_row(db, aggregate_type="nonconformance_record", aggregate_id=ncr_id, category="ncr_disposition_pending")
    assert old_row.resolved_at is not None
    new_row = await _notification_row(db, aggregate_type="nonconformance_record", aggregate_id=ncr_id, category="ncr_verification_pending")
    assert new_row is not None and new_row.resolved_at is None


async def test_complaint_reportability_pending(client, seeded, db):
    owner = await _complaint_setup(db, seeded, "wn21", signed=False)
    token = await login(client, "admin.cmpwn21")
    await _extra_role_user(db, seeded, "qa.releaser.wn21", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn21")

    async with db.begin():
        product_id = await _complaint_make_product(db, seeded)
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    resp = await _triage(client, token, complaint_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2
    resp = await _investigation_decision(client, token, complaint_id, 2, investigation_required=True)
    assert resp.status_code == 200, resp.text  # 2 -> 3
    resp = await _investigate(client, token, complaint_id, 3)
    assert resp.status_code == 200, resp.text  # 3 -> 4, REPORTABILITY_ASSESSMENT

    await _sync(db, aggregate_type="complaint_record", aggregate_id=complaint_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == complaint_id and i["category"] == "complaint_reportability_pending" for i in view["items"])


async def test_change_control_approval_pending(client, seeded, db):
    owner = await _change_setup(db, seeded, "wn22", signed=False)
    token = await login(client, "admin.chgwn22")
    await _extra_role_user(db, seeded, "qa.releaser.wn22", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn22")

    change_id = await _create_change(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact", json=_impact_body(change_id, 1), headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # 1 -> 2, IMPACT_ASSESSMENT

    await _sync(db, aggregate_type="change_control", aggregate_id=change_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == change_id and i["category"] == "change_approval_pending" for i in view["items"])


async def test_scar_review_pending(client, seeded, db):
    owner = await _scar_setup(db, seeded, "wn23", signed=False)
    token = await login(client, "admin.scarwn23")
    # "scar.review" is held by "QA Reviewer", not "QA Releaser" (scripts/seed.py's own role grants --
    # QA Releaser only holds scar.effectiveness/scar.close, the later steps in this same SCAR lifecycle).
    await _extra_role_user(db, seeded, "qa.reviewer.wn23", "QA Reviewer")
    reviewer_token = await login(client, "qa.reviewer.wn23")

    supplier_id = await _scar_create_supplier(client, token, "SUP-WN23")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)
    resp = await _scar_respond(client, token, scar_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2, SUPPLIER_RESPONSE

    await _sync(db, aggregate_type="scar_record", aggregate_id=scar_id)
    view = await _workflow_actions(client, reviewer_token)
    assert any(i["aggregate_id"] == scar_id and i["category"] == "scar_review_pending" for i in view["items"])
    # /supplier-cases/[id] is keyed by the case, not the SCAR id.
    matching = next(i for i in view["items"] if i["aggregate_id"] == scar_id)
    assert matching["link_path"] == f"/supplier-cases/{case_id}"


async def test_field_action_approval_pending(client, seeded, db):
    owner, product_id, risk_id = await _field_action_setup(db, seeded, "wn24", signed=False)
    token = await login(client, "admin.farwn24")
    await _extra_role_user(db, seeded, "qa.releaser.wn24", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn24")

    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    resp = await _define_scope(client, token, field_action_id, 1, product_id)
    assert resp.status_code == 200, resp.text  # 1 -> 2, SCOPE_DEFINITION
    resp = await _field_action_reportability(client, token, field_action_id, 2, decision="reportable")
    assert resp.status_code == 200, resp.text  # 2 -> 3, REGULATORY_DECISION

    await _sync(db, aggregate_type="field_action", aggregate_id=field_action_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == field_action_id and i["category"] == "field_action_approval_pending" for i in view["items"])


async def test_internal_audit_close_pending(client, seeded, db):
    owner = await _internal_audit_setup(db, seeded, "wn25", signed=False)
    token = await login(client, "admin.auditwn25")
    await _extra_role_user(db, seeded, "qa.releaser.wn25", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn25")

    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    resp = await _start_audit(client, token, audit_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2, IN_PROGRESS
    resp = await _add_finding(client, token, audit_id, 2, owner.id)
    assert resp.status_code == 200, resp.text  # audit 2 -> 3, FINDINGS_OPEN

    await _sync(db, aggregate_type="internal_audit", aggregate_id=audit_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == audit_id and i["category"] == "internal_audit_close_pending" for i in view["items"])


async def test_risk_acceptance_pending(client, seeded, db):
    owner, methodology_id = await _risk_setup(db, seeded, "wn26", signed=False)
    token = await login(client, "admin.riskwn26")
    await _extra_role_user(db, seeded, "qa.releaser.wn26", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn26")

    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id, methodology_id=methodology_id)
    resp = await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)
    assert resp.status_code == 200, resp.text  # 1 -> 2
    resp = await _add_controls(client, token, risk_id, 2)
    assert resp.status_code == 200, resp.text  # 2 -> 3
    resp = await _add_residual_assessment(client, token, risk_id, 3)
    assert resp.status_code == 200, resp.text  # 3 -> 4, RESIDUAL_ASSESSMENT

    await _sync(db, aggregate_type="risk_record", aggregate_id=risk_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == risk_id and i["category"] == "risk_acceptance_pending" for i in view["items"])


async def test_material_lot_release_pending(client, seeded, db):
    """The real receiving flow only reaches "quarantine" (not "qc_disposition_pending") without also
    driving sampling/testing, which this test file has no reusable helper for -- the lot is moved to
    "qc_disposition_pending" directly via the DB, same "set up state directly, then prove the
    notification layer reacts to it" shortcut test_dashboard_reminders.py's own
    test_reminders_excludes_consumed_lots already uses for MaterialLot.status."""
    from app.modules.material.models import MaterialLot

    await _extra_role_user(db, seeded, "qa.releaser.wn27", "QA Releaser")
    releaser_token = await login(client, "qa.releaser.wn27")
    op_token = await login(client, "operator1")

    material_id = await _create_material(client, seeded["site_id"], code="RM-WN27")
    lot_id = await _receive_lot(client, op_token, material_id, seeded["site_id"], internal_lot="LOT-WN27")

    async with db.begin():
        lot = await db.get(MaterialLot, uuid.UUID(lot_id))
        lot.status = "qc_disposition_pending"

    await _sync(db, aggregate_type="material_lot", aggregate_id=lot_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == lot_id and i["category"] == "material_lot_release_pending" for i in view["items"])
    matching = next(i for i in view["items"] if i["aggregate_id"] == lot_id)
    assert matching["link_path"] == "/material-lots?q=LOT-WN27"  # DataTable's own q= search filter


async def test_supplier_qualification_approval_pending_is_visible_to_any_site(client, seeded, db):
    """SupplierQualification carries no site_id of its own, and the real
    `evaluate_policy("supplier_qualification.approve", site_id=None)` call site already treats it as
    platform-wide -- proves a QA Releaser whose *only* UserSiteRole is at a second, unrelated site (not
    the site the notification's SoD-triggering admin is seeded at) still sees it, the "any site" audience
    path service.py::list_visible_notifications() added alongside oot_record/oos_record support."""
    from app.modules.iam.models import Organization, Site

    pe_token = await login(client, "process.engineer")
    qa_releaser_token = await login(client, "qa.releaser")  # the seeded fixture's own QA Releaser

    async with db.begin():
        other_org = Organization(name="WN28 Other Org")
        db.add(other_org)
        await db.flush()
        other_site = Site(organization_id=other_org.id, code="WN28", name="WN28 Other Site")
        db.add(other_site)
        await db.flush()
        other_site_user = User(
            username="qa.releaser.wn28", email="qa.releaser.wn28@example.com", full_name="Other-Site QA Releaser",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(other_site_user)
        await db.flush()
        db.add(UserSiteRole(user_id=other_site_user.id, site_id=other_site.id, role_id=seeded["roles"]["QA Releaser"].id))
    other_site_token = await login(client, "qa.releaser.wn28")

    supplier_id = await _sq_create_supplier(client, pe_token, code="SUP-WN28")
    supplier_site_id = await _sq_site_id_for(db, supplier_id)
    qualification_id = await _create_qualification(client, pe_token, supplier_id, supplier_site_id)

    await _sync(db, aggregate_type="supplier_qualification", aggregate_id=qualification_id)

    same_org_view = await _workflow_actions(client, qa_releaser_token)
    assert any(
        i["aggregate_id"] == qualification_id and i["category"] == "supplier_qualification_approval_pending"
        for i in same_org_view["items"]
    )
    matching = next(i for i in same_org_view["items"] if i["aggregate_id"] == qualification_id)
    assert matching["link_path"] == f"/suppliers?supplier_id={supplier_id}"

    other_site_view = await _workflow_actions(client, other_site_token)
    assert any(
        i["aggregate_id"] == qualification_id and i["category"] == "supplier_qualification_approval_pending"
        for i in other_site_view["items"]
    )  # visible even though this user's only UserSiteRole is at a completely different site


async def test_oos_disposition_pending_then_close_pending(client, seeded, db):
    """Reuses test_qc_oos.py::test_full_oos_flow_no_assignable_cause's own sequence verbatim through
    "final_disposition" (real sample -> test-order -> OOS -> lab investigation -> no-assignable-cause ->
    signed extended investigation by an independent QA Reviewer -> retest/resample plans -> impact),
    since oos_record has no simpler reusable helper the way the other modules in this file do."""
    from app.modules.qc.models import OosRecord, QcTestDefinition

    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")
    qa_reviewer_token = await login(client, "qa.reviewer")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code="OOS-PROD-WN30")
        await _qc_make_admin(db, seeded, "admin.ooswn30")
        await _qc_make_user(db, seeded, "qa.reviewer.ooswn30", "QA Reviewer")
    admin_token = await login(client, "admin.ooswn30")
    qa_reviewer2_token = await login(client, "qa.reviewer.ooswn30")
    await _extra_role_user(db, seeded, "qa.releaser.wn30", "QA Releaser")
    releaser2_token = await login(client, "qa.releaser.wn30")

    await _author_and_release_rule(
        client, admin_token, db, rule_id="qc-acceptance:oos-wn30",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "OOS-SPEC-WN30", "scope_type": "product",
            "scope_version_id": str(product_version.id),
            "test_definitions": [{
                "test_code": "ASSAY", "test_name": "Assay", "result_data_type": "numeric_single",
                "uom": "mg", "acceptance_rule_business_id": "qc-acceptance:oos-wn30", "required": True, "release_blocking": True,
            }],
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    spec_id = resp.json()["aggregate_id"]
    spec_challenge = (
        await client.post(f"/qc/v1/specifications/{spec_id}/signature-challenges", json={"action": "release"}, headers=auth_headers(qa_releaser_token))
    ).json()
    resp = await client.post(
        f"/qc/v1/specifications/{spec_id}/release",
        json={
            "idempotency_key": idem(), "specification_id": spec_id, "expected_version": 1,
            "challenge_id": spec_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "OOS-SAMPLE-WN30", "sample_type": "finished_product", "source_type": "reserve"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    order_id = (
        await client.post(
            "/qc/v1/test-orders",
            json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    run_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/raw-data",
            json={"idempotency_key": idem(), "test_order_id": order_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    result_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/results",
            json={
                "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
                "result_type": "numeric_single", "value_decimal": "99.000000000000",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    resp = await client.post(
        f"/quality/oos/v1/from-result/{result_id}",
        json={"idempotency_key": idem(), "source_result_id": result_id, "oos_number": "OOS-WN30"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    oos_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/lab-investigation",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 1,
            "activity_type": "checklist_review", "response_text": "No obvious analyst/instrument error found",
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/classify-lab-cause",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 2, "assignable": False},
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text

    # Extended investigation must be signed by someone independent of the investigator (qa_reviewer_token).
    ext_challenge = (
        await client.post(f"/quality/oos/v1/{oos_id}/signature-challenges", json={"action": "extended_investigation"}, headers=auth_headers(qa_reviewer2_token))
    ).json()
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/extended-investigation",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 3,
            "challenge_id": ext_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_reviewer2_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/retest-plans",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "justification": "Confirm assay via retest",
            "number_of_retests": 2, "method_ref": "HPLC-1",
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/resample-plans",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "scientific_rationale": "Rule out sampling error"},
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/impact",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 4,
            "impact_text": "No confirmed impact to other batches; hold pending disposition", "hold_status": "hold",
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    oos = await db.get(OosRecord, oos_id)
    assert oos.state == "final_disposition"

    await _sync(db, aggregate_type="oos_record", aggregate_id=oos_id)
    view = await _workflow_actions(client, releaser2_token)
    assert any(i["aggregate_id"] == oos_id and i["category"] == "oos_disposition_pending" for i in view["items"])

    disp_challenge = (
        await client.post(f"/quality/oos/v1/{oos_id}/signature-challenges", json={"action": "disposition"}, headers=auth_headers(releaser2_token))
    ).json()
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/disposition",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 5,
            "final_classification": "laboratory_error", "challenge_id": disp_challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(releaser2_token),
    )
    assert resp.status_code == 200, resp.text  # -> qa_approval

    await _sync(db, aggregate_type="oos_record", aggregate_id=oos_id)
    old_row = await _notification_row(db, aggregate_type="oos_record", aggregate_id=oos_id, category="oos_disposition_pending")
    assert old_row.resolved_at is not None
    # releaser2_token just performed disposition() -- SoD excludes them from closing their own
    # disposition (matches the real close_oos() independence check); qa_releaser_token never touched the
    # OOS record itself (only an unrelated spec), so they're the one who should see oos_close_pending.
    view_after = await _workflow_actions(client, qa_releaser_token)
    assert any(i["aggregate_id"] == oos_id and i["category"] == "oos_close_pending" for i in view_after["items"])
    excluded_view = await _workflow_actions(client, releaser2_token)
    assert not any(i["aggregate_id"] == oos_id for i in excluded_view["items"])


async def test_oot_close_pending(client, seeded, db):
    """Reuses test_qc_oos.py::test_evaluate_oot_triggered_and_signed_close's own sequence verbatim
    through the "open" state (real sample -> test-order -> result -> trend-rule-triggered OOT), since
    oot_record has no simpler reusable helper either."""
    from app.modules.qc.models import OotRecord

    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code="OOT-PROD-WN31")
        await _qc_make_admin(db, seeded, "admin.ootwn31")
    admin_token = await login(client, "admin.ootwn31")
    await _extra_role_user(db, seeded, "qa.releaser.wn31", "QA Releaser")
    releaser2_token = await login(client, "qa.releaser.wn31")

    await _author_and_release_rule(
        client, admin_token, db, rule_id="qc-trend:oot-wn31",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "OOT-SPEC-WN31", "scope_type": "product",
            "scope_version_id": str(product_version.id),
            "test_definitions": [{
                "test_code": "ASSAY", "test_name": "Assay", "result_data_type": "numeric_single",
                "uom": "mg", "trend_rule_business_id": "qc-trend:oot-wn31", "required": True, "release_blocking": True,
            }],
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    spec_id = resp.json()["aggregate_id"]
    challenge = (
        await client.post(f"/qc/v1/specifications/{spec_id}/signature-challenges", json={"action": "release"}, headers=auth_headers(qa_releaser_token))
    ).json()
    resp = await client.post(
        f"/qc/v1/specifications/{spec_id}/release",
        json={
            "idempotency_key": idem(), "specification_id": spec_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    from app.modules.qc.models import QcTestDefinition
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "OOT-SAMPLE-WN31", "sample_type": "finished_product", "source_type": "reserve"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    order_id = (
        await client.post(
            "/qc/v1/test-orders",
            json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    run_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/raw-data",
            json={"idempotency_key": idem(), "test_order_id": order_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    result_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/results",
            json={
                "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
                "result_type": "numeric_single", "value_decimal": "99.000000000000",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    resp = await client.post(
        "/quality/oot/v1/evaluate",
        json={"idempotency_key": idem(), "source_result_id": result_id},
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    oot_id = resp.json()["aggregate_id"]
    oot = await db.get(OotRecord, oot_id)
    assert oot.state == "open"

    await _sync(db, aggregate_type="oot_record", aggregate_id=oot_id)
    view = await _workflow_actions(client, releaser2_token)
    assert any(i["aggregate_id"] == oot_id and i["category"] == "oot_close_pending" for i in view["items"])
    matching = next(i for i in view["items"] if i["aggregate_id"] == oot_id)
    assert matching["site_id"] is None  # oot_record has no site_id column -- the "any site" audience path


async def test_material_spec_release_pending_notifies_on_create_and_resolves_on_release(client, seeded, db):
    """Pass 3 -- the exact gap a real user report surfaced: a material specification draft sat with no
    releaser notification because material_specification_version was never in registry.py's scope. Unlike
    the other two Pass-3 modules below, a spec version is created directly into "draft" and stays there
    (no separate submit step) -- so the pending notification must fire on the very first Created event."""
    async with db.begin():
        material = await _matspec_make_material(db, seeded, "MAT-SPEC-WN20-001")
        db.add(
            SignaturePolicy(
                record_type="material_specification_version", action="release", meaning="Released",
                signature_required=False,
            )
        )
    await _extra_role_user(db, seeded, "process.engineer.wn20", "Process Engineer")
    await _extra_role_user(db, seeded, "qa.releaser.wn20", "QA Releaser")
    author_token = await login(client, "process.engineer.wn20")
    releaser_token = await login(client, "qa.releaser.wn20")

    resp = await client.post(
        "/material-specifications/v1/drafts",
        json=_matspec_draft_body(seeded["site_id"], material.id, "MATSPEC-WN20"),
        headers=auth_headers(author_token),
    )
    assert resp.status_code == 200, resp.text
    version_id = resp.json()["aggregate_id"]

    await _sync(db, aggregate_type="material_specification_version", aggregate_id=version_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == version_id and i["category"] == "material_spec_release_pending" for i in view["items"])
    matching = next(i for i in view["items"] if i["aggregate_id"] == version_id)
    assert matching["entity_label"] == "Material Spec MATSPEC-WN20 v1"
    assert matching["link_path"] == f"/material-specifications?material_spec_version_id={version_id}"

    resp = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "material_spec_version_id": version_id, "expected_version": 1},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    await _sync(db, aggregate_type="material_specification_version", aggregate_id=version_id)

    view_after = await _workflow_actions(client, releaser_token)
    assert not any(i["aggregate_id"] == version_id for i in view_after["items"])


async def test_product_release_pending_notifies_on_submit_and_resolves_on_release(client, seeded, db):
    """Pass 3 -- same gap class as the material-spec test above: product_version's own draft ->
    under_review -> released pipeline was never registered either."""
    async with db.begin():
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
    await _extra_role_user(db, seeded, "process.engineer.wn21", "Process Engineer")
    await _extra_role_user(db, seeded, "qa.releaser.wn21", "QA Releaser")
    author_token = await login(client, "process.engineer.wn21")
    releaser_token = await login(client, "qa.releaser.wn21")

    resp = await client.post(
        "/products/v1/drafts", json=_product_draft_body(seeded["site_id"], "PRD-WN21"), headers=auth_headers(author_token)
    )
    assert resp.status_code == 200, resp.text
    version_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/products/v1/drafts/{version_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": version_id, "expected_version": 1},
        headers=auth_headers(author_token),
    )
    assert resp.status_code == 200, resp.text

    await _sync(db, aggregate_type="product_version", aggregate_id=version_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == version_id and i["category"] == "product_release_pending" for i in view["items"])
    matching = next(i for i in view["items"] if i["aggregate_id"] == version_id)
    assert matching["entity_label"] == "Product PRD-WN21 v1"
    assert matching["link_path"] == f"/product-master?product_version_id={version_id}"

    resp = await client.post(
        f"/products/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "product_version_id": version_id, "expected_version": 2},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    await _sync(db, aggregate_type="product_version", aggregate_id=version_id)

    view_after = await _workflow_actions(client, releaser_token)
    assert not any(i["aggregate_id"] == version_id for i in view_after["items"])


async def test_recipe_release_pending_notifies_on_submit_and_resolves_on_release(client, seeded, db):
    """Pass 3 -- same gap class again: recipe_version's own draft -> under_review -> released pipeline
    was never registered either."""
    async with db.begin():
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    await _extra_role_user(db, seeded, "process.engineer.wn22", "Process Engineer")
    await _extra_role_user(db, seeded, "qa.releaser.wn22", "QA Releaser")
    author_token = await login(client, "process.engineer.wn22")
    releaser_token = await login(client, "qa.releaser.wn22")

    product_version_id = await _recipe_make_product_version(client, author_token, seeded["site_id"], "RCPPRD-WN22")
    resp = await client.post(
        "/recipes/v2/drafts",
        json=_recipe_two_step_body(product_version_id, seeded["site_id"], "RCP-WN22"),
        headers=auth_headers(author_token),
    )
    assert resp.status_code == 200, resp.text
    version_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/recipes/v2/drafts/{version_id}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": version_id, "expected_version": 1},
        headers=auth_headers(author_token),
    )
    assert resp.status_code == 200, resp.text

    await _sync(db, aggregate_type="recipe_version", aggregate_id=version_id)
    view = await _workflow_actions(client, releaser_token)
    assert any(i["aggregate_id"] == version_id and i["category"] == "recipe_release_pending" for i in view["items"])
    matching = next(i for i in view["items"] if i["aggregate_id"] == version_id)
    assert matching["entity_label"] == "Recipe RCP-WN22 v1"
    assert matching["link_path"] == f"/recipe-master?recipe_version_id={version_id}"

    resp = await client.post(
        f"/recipes/v2/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "recipe_version_id": version_id, "expected_version": 2},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    await _sync(db, aggregate_type="recipe_version", aggregate_id=version_id)

    view_after = await _workflow_actions(client, releaser_token)
    assert not any(i["aggregate_id"] == version_id for i in view_after["items"])


async def test_rebuild_covers_every_registered_aggregate_type(db):
    """Proves rebuild_all() runs cleanly end to end across all 18 registered aggregate types, including
    a run against a table with zero rows for a given type, without needing every module's own record
    present."""
    from app.modules.notifications import service as notifications_service
    from app.modules.notifications.registry import WORKFLOW_SPECS

    async with db.begin():
        result = await notifications_service.rebuild_all(db)
    assert set(result["rescanned"].keys()) == set(WORKFLOW_SPECS.keys())
    assert len(result["rescanned"]) == 18
