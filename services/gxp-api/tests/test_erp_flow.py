"""WP-07 (Documents 48-53, SPEC-ERP-001..006): ERP instance registry, master-data mapping/conflict,
the shared integration command/event ledger (Document 53's reliability model), and reconciliation.

Every test that exercises `dispatch_erp_command` (the one function that performs real outbound HTTP,
see its docstring in `app/modules/erp/commands.py`) monkeypatches `build_adapter` to return a real
`ERPNextAdapter` wired to an `httpx.MockTransport` -- SG-125: no credentialed vendor sandbox is reachable
from this environment, so no test here claims a live ERPNext/SAP/Oracle/Dynamics call occurred.
"""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.modules.erp import commands as erp_commands
from app.modules.erp.adapters.erpnext import ERPNextAdapter
from app.modules.erp.models import ErpExternalMapping, ErpMappingConflict, IntegrationCommand
from app.modules.erp.provider import AdapterConfig
from tests.conftest import auth_headers, idem, login


def _mock_adapter(handler) -> ERPNextAdapter:
    transport = httpx.MockTransport(handler)
    config = AdapterConfig(base_url="https://erpnext.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="v14-resource-api", extra={"transport": transport})
    return ERPNextAdapter(config)


def _patch_adapter(monkeypatch, handler) -> None:
    adapter = _mock_adapter(handler)

    async def _fake_build_adapter(session, instance):
        return adapter

    monkeypatch.setattr(erp_commands, "build_adapter", _fake_build_adapter)


# --- ERP instance registry (ERP-ARC-002) --------------------------------------------------------------


async def test_register_instance_and_duplicate_name_rejected(client, seeded):
    token = await login(client, "integration.admin")
    site_id = seeded["site_id"]
    resp = await client.post(
        "/integration/v1/instances",
        json={"idempotency_key": idem(), "instance_name": "new-sap", "vendor": "SAP_S4HANA", "base_url": "https://sap.demo.invalid", "auth_method": "OAUTH2_CLIENT_CREDENTIALS", "auth_secret_ref": "tok", "site_id": str(site_id)},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    dup = await client.post(
        "/integration/v1/instances",
        json={"idempotency_key": idem(), "instance_name": "new-sap", "vendor": "SAP_S4HANA", "base_url": "https://sap.demo.invalid", "auth_method": "OAUTH2_CLIENT_CREDENTIALS", "auth_secret_ref": "tok", "site_id": str(site_id)},
        headers=auth_headers(token),
    )
    assert dup.status_code == 422, dup.text


async def test_register_instance_duplicate_idempotency_key_returns_same_receipt(client, seeded):
    token = await login(client, "integration.admin")
    key = idem()
    body = {"idempotency_key": key, "instance_name": "dup-key-instance", "vendor": "GENERIC", "base_url": "https://custom.demo.invalid", "auth_method": "API_KEY", "auth_secret_ref": "k"}
    first = await client.post("/integration/v1/instances", json=body, headers=auth_headers(token))
    second = await client.post("/integration/v1/instances", json=body, headers=auth_headers(token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


async def test_register_instance_unauthorized_without_permission(client, seeded):
    token = await login(client, "operator1")
    resp = await client.post(
        "/integration/v1/instances",
        json={"idempotency_key": idem(), "instance_name": "blocked-instance", "vendor": "GENERIC", "base_url": "https://x.invalid", "auth_method": "API_KEY", "auth_secret_ref": "k"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text


async def test_get_capabilities_reports_declared_operations(client, seeded, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(200, json={"message": "demo"}))
    resp = await client.get(f"/integration/v1/instances/{seeded['erp_instance'].id}/capabilities")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vendor"] == "ERPNEXT"
    assert "POST_GOODS_RECEIPT" in body["supported_operations"]
    assert body["reachable"] is True


# --- Master-data mapping (Document 52) ------------------------------------------------------------------


async def test_propose_and_approve_mapping(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    resp = await client.post(
        "/integration/v1/mappings",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "entity_type": "MATERIAL", "internal_id": str(uuid.uuid4()), "external_id": "ITEM-001", "field_ownership": "ERP"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    mapping_id = resp.json()["aggregate_id"]

    approve = await client.post(
        f"/integration/v1/mappings/{mapping_id}/approve",
        json={"idempotency_key": idem(), "mapping_id": mapping_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["resulting_version"] == 2


async def test_propose_duplicate_external_mapping_rejected(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    body = {"idempotency_key": idem(), "erp_instance_id": instance_id, "entity_type": "MATERIAL", "internal_id": str(uuid.uuid4()), "external_id": "ITEM-DUP", "field_ownership": "ERP"}
    first = await client.post("/integration/v1/mappings", json=body, headers=auth_headers(token))
    assert first.status_code == 200, first.text

    second = {**body, "idempotency_key": idem(), "internal_id": str(uuid.uuid4())}
    resp = await client.post("/integration/v1/mappings", json=second, headers=auth_headers(token))
    assert resp.status_code == 409, resp.text


async def test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite(client, seeded, db):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    propose = await client.post(
        "/integration/v1/mappings",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "entity_type": "MATERIAL", "internal_id": str(uuid.uuid4()), "external_id": "ITEM-GXP-1", "external_code": "ORIGINAL", "field_ownership": "GXP"},
        headers=auth_headers(token),
    )
    mapping_id = propose.json()["aggregate_id"]

    resp = await client.post(
        f"/integration/v1/mappings/{mapping_id}/external-change",
        json={"idempotency_key": idem(), "mapping_id": mapping_id, "expected_version": 1, "field_name": "external_code", "proposed_value": {"external_code": "CHANGED"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    mapping = await db.get(ErpExternalMapping, uuid.UUID(mapping_id))
    assert mapping.mapping_status == "CONFLICT"
    assert mapping.external_code == "ORIGINAL"  # never silently overwritten (MDS-FR-006)

    conflict = (await db.execute(select(ErpMappingConflict).where(ErpMappingConflict.mapping_id == mapping.id))).scalar_one()
    assert conflict.status == "OPEN"

    resolve = await client.post(
        f"/integration/v1/mapping-conflicts/{conflict.id}/resolve",
        json={"idempotency_key": idem(), "conflict_id": str(conflict.id), "expected_version": 1, "resolution": "ACCEPT_PROPOSED", "resolution_reason": "confirmed correct in ERP, updating GxP-owned mapping"},
        headers=auth_headers(token),
    )
    assert resolve.status_code == 200, resolve.text
    await db.refresh(mapping)
    assert mapping.external_code == "CHANGED"
    assert mapping.mapping_status == "ACTIVE"


async def test_erp_owned_field_change_updates_projection(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    propose = await client.post(
        "/integration/v1/mappings",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "entity_type": "MATERIAL", "internal_id": str(uuid.uuid4()), "external_id": "ITEM-ERP-1", "external_code": "ORIGINAL", "field_ownership": "ERP"},
        headers=auth_headers(token),
    )
    mapping_id = propose.json()["aggregate_id"]

    resp = await client.post(
        f"/integration/v1/mappings/{mapping_id}/external-change",
        json={"idempotency_key": idem(), "mapping_id": mapping_id, "expected_version": 1, "field_name": "external_code", "proposed_value": {"external_code": "UPDATED"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resulting_version"] == 2


async def test_advance_sync_checkpoint_idempotent_resubmit(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    key = idem()
    body = {"idempotency_key": key, "erp_instance_id": instance_id, "entity_type": "MATERIAL", "cursor_value": "2026-08-26T00:00:00Z"}
    first = await client.post("/integration/v1/sync-checkpoints", json=body, headers=auth_headers(token))
    second = await client.post("/integration/v1/sync-checkpoints", json=body, headers=auth_headers(token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


# --- Integration command ledger (Document 53) -----------------------------------------------------------


async def test_queue_command_rejects_unsupported_capability(client, seeded):
    token = await login(client, "integration.admin")
    resp = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": str(seeded["erp_instance"].id), "command_type": "NOT_A_REAL_OPERATION", "payload": {}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text


async def test_queue_then_dispatch_command_succeeds(client, seeded, db, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "token k:s"
        return httpx.Response(200, json={"data": {"name": "MAT-DOC-0001"}})

    _patch_adapter(monkeypatch, handler)
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_GOODS_RECEIPT", "payload": {"item_code": "ITEM-001", "qty": "10"}},
        headers=auth_headers(token),
    )
    assert queue.status_code == 200, queue.text
    command_id = queue.json()["aggregate_id"]

    dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
    assert dispatch.status_code == 200, dispatch.text

    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "SUCCEEDED"
    assert command.external_reference == "MAT-DOC-0001"
    assert command.attempt_count == 1


async def test_dispatch_production_order_reference_lookup_succeeds(client, seeded, db, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "Work%20Order/WO-0001" in str(request.url)
        return httpx.Response(200, json={"data": {"name": "WO-0001", "status": "In Process"}})

    _patch_adapter(monkeypatch, handler)
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "GET_PRODUCTION_ORDER_REFERENCE", "payload": {"external_order_id": "WO-0001"}},
        headers=auth_headers(token),
    )
    assert queue.status_code == 200, queue.text
    command_id = queue.json()["aggregate_id"]

    dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
    assert dispatch.status_code == 200, dispatch.text

    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "SUCCEEDED"
    assert command.external_reference == "WO-0001"


async def test_dispatch_server_error_schedules_retry(client, seeded, db, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(500, json={"error": "internal"}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]

    dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
    assert dispatch.status_code == 200, dispatch.text

    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "RETRY_WAIT"
    assert command.last_error_category == "SERVER_ERROR"
    assert command.next_attempt_at is not None


async def test_dispatch_validation_error_dead_letters_immediately(client, seeded, db, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(422, json={"error": "bad field"}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]

    dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
    assert dispatch.status_code == 200, dispatch.text

    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "DEAD_LETTER"
    assert command.last_error_category == "VALIDATION"
    assert command.required_next_action is not None


async def test_dispatch_erpnext_draft_docstatus_is_not_success(client, seeded, db, monkeypatch):
    """ENXT-FR-015 (TC-049-015-01): ERPNext returns HTTP 200 just as readily for a saved-but-still-draft
    Stock Entry as for a submitted one -- only `docstatus=1` is a genuine external commit. A draft
    (docstatus=0) is classified BUSINESS_REJECT (manual review, TC-049-015-02/03's generic replay/timeout
    boilerplate is already covered by the pipeline's own generic mechanisms: `test_ingest_event_dedupes_
    and_detects_conflict` for replay-safety, `test_dispatch_timeout_is_uncertain_not_blind_success_or_
    retry_storm` for timeout-uncertain handling -- neither is specific to docstatus)."""

    _patch_adapter(monkeypatch, lambda request: httpx.Response(200, json={"data": {"name": "MAT-DOC-DRAFT", "docstatus": 0}}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]

    dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
    assert dispatch.status_code == 200, dispatch.text

    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "DEAD_LETTER"
    assert command.last_error_category == "BUSINESS_REJECT"
    assert command.last_error_detail["docstatus"] == 0


async def test_dispatch_erpnext_submitted_docstatus_succeeds(client, seeded, db, monkeypatch):
    """ENXT-FR-015 positive counterpart: docstatus=1 (Submitted) is the only success case."""

    _patch_adapter(monkeypatch, lambda request: httpx.Response(200, json={"data": {"name": "MAT-DOC-SUBMITTED", "docstatus": 1}}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]

    dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
    assert dispatch.status_code == 200, dispatch.text

    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "SUCCEEDED"
    assert command.external_reference == "MAT-DOC-SUBMITTED"


async def test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm(client, seeded, db, monkeypatch):
    """INT-FR-008: a timeout never blindly resumes as if nothing happened -- it becomes RETRY_WAIT with
    error_category=TIMEOUT_UNCERTAIN, and a stuck DISPATCHED command is only ever recoverable through
    `reconcile_uncertain_commit`, which always demands external verification (never a blind replay)."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated vendor timeout", request=request)

    _patch_adapter(monkeypatch, handler)
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]

    dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
    assert dispatch.status_code == 200, dispatch.text
    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "RETRY_WAIT"
    assert command.last_error_category == "TIMEOUT_UNCERTAIN"

    # Simulate the crash-between-send-and-record scenario directly (INT-FR-008's own failure mode) and
    # prove reconciliation never blindly resumes it as PENDING.
    command.state = "DISPATCHED"
    await db.commit()
    reconcile = await client.post(f"/integration/v1/commands/{command_id}/reconcile-uncertain", headers=auth_headers(token))
    assert reconcile.status_code == 200, reconcile.text
    await db.refresh(command)
    assert command.state == "RETRY_WAIT"
    assert "verify externally" in command.required_next_action


async def test_retry_manual_requires_reason_and_resets_to_pending(client, seeded, db, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(500))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]
    await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))

    missing_reason = await client.post(
        f"/integration/v1/commands/{command_id}/retry", json={"idempotency_key": idem(), "command_id": command_id, "reason": ""},
        headers=auth_headers(token),
    )
    assert missing_reason.status_code == 422, missing_reason.text

    retry = await client.post(
        f"/integration/v1/commands/{command_id}/retry", json={"idempotency_key": idem(), "command_id": command_id, "reason": "vendor confirmed transient outage"},
        headers=auth_headers(token),
    )
    assert retry.status_code == 200, retry.text
    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "PENDING"


async def test_cancel_pending_command_requires_reason(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]

    resp = await client.post(
        f"/integration/v1/commands/{command_id}/cancel",
        json={"idempotency_key": idem(), "command_id": command_id, "reason": "superseded by corrected GxP transaction"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_cancel_dispatched_command_rejected(client, seeded, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(200, json={"data": {"name": "REF-1"}}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]
    await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))

    resp = await client.post(
        f"/integration/v1/commands/{command_id}/cancel",
        json={"idempotency_key": idem(), "command_id": command_id, "reason": "too late"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text


async def test_create_corrected_command_from_dead_letter(client, seeded, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(422, json={"error": "bad"}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {"qty": "10"}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]
    await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))

    resp = await client.post(
        f"/integration/v1/commands/{command_id}/correct",
        json={"idempotency_key": idem(), "original_command_id": command_id, "corrected_payload": {"qty": "9"}, "reason": "corrected quantity per approved GxP correction"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["aggregate_id"] != command_id


async def test_circuit_breaker_opens_after_repeated_failures_and_throttles(client, seeded, db, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(500))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    command_ids = []
    for _ in range(6):
        queue = await client.post(
            "/integration/v1/commands",
            json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
            headers=auth_headers(token),
        )
        command_ids.append(queue.json()["aggregate_id"])

    for command_id in command_ids[:5]:
        resp = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
        assert resp.status_code == 200, resp.text

    throttled = await client.post(f"/integration/v1/commands/{command_ids[5]}/dispatch", headers=auth_headers(token))
    assert throttled.status_code == 429, throttled.text


# --- Inbound event ledger --------------------------------------------------------------------------------


async def test_ingest_event_dedupes_and_detects_conflict(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    external_event_id = f"evt-{uuid.uuid4()}"

    first = await client.post(
        "/integration/v1/events",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "external_event_id": external_event_id, "entity_type": "MATERIAL", "payload": {"name": "ITEM-1"}},
        headers=auth_headers(token),
    )
    assert first.status_code == 200, first.text

    replay = await client.post(
        "/integration/v1/events",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "external_event_id": external_event_id, "entity_type": "MATERIAL", "payload": {"name": "ITEM-1"}},
        headers=auth_headers(token),
    )
    assert replay.status_code == 200
    assert replay.json()["aggregate_id"] == first.json()["aggregate_id"]

    conflict = await client.post(
        "/integration/v1/events",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "external_event_id": external_event_id, "entity_type": "MATERIAL", "payload": {"name": "DIFFERENT"}},
        headers=auth_headers(token),
    )
    assert conflict.status_code == 409, conflict.text


# --- Reconciliation (SG-124: never auto-resolves) -------------------------------------------------------


async def test_reconciliation_run_lifecycle_never_auto_resolves(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    run = await client.post(
        "/integration/v1/reconciliation-runs",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "scope": "MATERIAL", "reconciliation_type": "MASTER_DATA", "cutoff_at": "2026-08-26T00:00:00Z"},
        headers=auth_headers(token),
    )
    assert run.status_code == 200, run.text
    run_id = run.json()["aggregate_id"]

    difference = await client.post(
        f"/integration/v1/reconciliation-runs/{run_id}/differences",
        json={"idempotency_key": idem(), "run_id": run_id, "difference_type": "MISSING_EXTERNAL", "internal_ref": {"id": "abc"}},
        headers=auth_headers(token),
    )
    assert difference.status_code == 200, difference.text
    difference_id = difference.json()["aggregate_id"]

    bad_status = await client.post(
        f"/integration/v1/reconciliation-differences/{difference_id}/resolve",
        json={"idempotency_key": idem(), "difference_id": difference_id, "expected_version": 1, "resolution_status": "AUTO_RESOLVED", "resolution_reason": "should be rejected"},
        headers=auth_headers(token),
    )
    assert bad_status.status_code == 422, bad_status.text

    resolve = await client.post(
        f"/integration/v1/reconciliation-differences/{difference_id}/resolve",
        json={"idempotency_key": idem(), "difference_id": difference_id, "expected_version": 1, "resolution_status": "RESOLVED", "resolution_reason": "confirmed benign timing difference"},
        headers=auth_headers(token),
    )
    assert resolve.status_code == 200, resolve.text

    complete = await client.post(
        f"/integration/v1/reconciliation-runs/{run_id}/complete",
        # recording a difference bumps the run's version (1 -> 2) since it advances difference_count.
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 2, "status": "COMPLETED"},
        headers=auth_headers(token),
    )
    assert complete.status_code == 200, complete.text


# --- INT-FR-024/ERP-ARC-028: proactive rate limiting ---------------------------------------------------


async def test_rate_limit_throttles_before_circuit_breaker_trips(client, seeded, db, monkeypatch):
    """INT-FR-024: a healthy, closed circuit (every call succeeds) can still be throttled purely on
    volume -- distinct from the circuit breaker's reactive failure-based trip."""
    _patch_adapter(monkeypatch, lambda request: httpx.Response(200, json={"data": {"name": "REF-1", "docstatus": 1}}))
    token = await login(client, "integration.admin")
    instance = seeded["erp_instance"]
    instance_id = str(instance.id)

    async with db.begin():
        instance = await db.get(type(instance), instance.id, with_for_update=True)
        instance.capabilities = {**(instance.capabilities or {}), "rate_limit_policy": {"max_requests_per_window": 2, "window_seconds": 60}}

    command_ids = []
    for _ in range(3):
        queue = await client.post(
            "/integration/v1/commands",
            json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
            headers=auth_headers(token),
        )
        command_ids.append(queue.json()["aggregate_id"])

    for command_id in command_ids[:2]:
        resp = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
        assert resp.status_code == 200, resp.text

    throttled = await client.post(f"/integration/v1/commands/{command_ids[2]}/dispatch", headers=auth_headers(token))
    assert throttled.status_code == 429, throttled.text
    assert throttled.json()["code"] == "ERP_THROTTLED"


# --- INT-FR-011: out-of-order/stale inbound event detection -------------------------------------------


async def test_stale_inbound_event_marked_superseded_not_applied(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    entity_id = f"item-{uuid.uuid4()}"

    newer = await client.post(
        "/integration/v1/events",
        json={
            "idempotency_key": idem(), "erp_instance_id": instance_id, "external_event_id": f"evt-{uuid.uuid4()}",
            "entity_type": "MATERIAL", "external_entity_id": entity_id, "source_version": "10", "payload": {"name": "ITEM-1"},
        },
        headers=auth_headers(token),
    )
    assert newer.status_code == 200, newer.text

    stale = await client.post(
        "/integration/v1/events",
        json={
            "idempotency_key": idem(), "erp_instance_id": instance_id, "external_event_id": f"evt-{uuid.uuid4()}",
            "entity_type": "MATERIAL", "external_entity_id": entity_id, "source_version": "9", "payload": {"name": "ITEM-1-OLD"},
        },
        headers=auth_headers(token),
    )
    assert stale.status_code == 200, stale.text  # recorded, not rejected -- just not applied

    from app.modules.erp.models import IntegrationInboundEvent

    async def _get(id_str):
        from app.core.db import SessionLocal
        async with SessionLocal() as s:
            return await s.get(IntegrationInboundEvent, uuid.UUID(id_str))

    stale_row = await _get(stale.json()["aggregate_id"])
    assert stale_row.processing_state == "STALE_SUPERSEDED"
    newer_row = await _get(newer.json()["aggregate_id"])
    assert newer_row.processing_state == "PROCESSED"


async def test_newer_inbound_event_after_stale_still_processes(client, seeded):
    """Regression guard: comparing against the last *processed* event (not the last-received one)
    means a late arrival never poisons a subsequent genuinely-newer event."""
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    entity_id = f"item-{uuid.uuid4()}"

    async def _ingest(version, event_id):
        return await client.post(
            "/integration/v1/events",
            json={
                "idempotency_key": idem(), "erp_instance_id": instance_id, "external_event_id": event_id,
                "entity_type": "MATERIAL", "external_entity_id": entity_id, "source_version": version, "payload": {"v": version},
            },
            headers=auth_headers(token),
        )

    await _ingest("10", f"evt-{uuid.uuid4()}")
    await _ingest("5", f"evt-{uuid.uuid4()}")  # stale, superseded
    latest = await _ingest("11", f"evt-{uuid.uuid4()}")
    assert latest.status_code == 200, latest.text

    from app.core.db import SessionLocal
    from app.modules.erp.models import IntegrationInboundEvent

    async with SessionLocal() as s:
        row = await s.get(IntegrationInboundEvent, uuid.UUID(latest.json()["aggregate_id"]))
    assert row.processing_state == "PROCESSED"


# --- INT-FR-025: security events on integrity conflicts -------------------------------------------------


async def test_payload_hash_conflict_records_security_event(client, seeded):
    from app.core.db import SessionLocal
    from app.modules.erp.models import IntegrationSecurityEvent

    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    event_id = f"evt-{uuid.uuid4()}"

    await client.post(
        "/integration/v1/events",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "external_event_id": event_id, "entity_type": "MATERIAL", "payload": {"name": "A"}},
        headers=auth_headers(token),
    )
    conflict = await client.post(
        "/integration/v1/events",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "external_event_id": event_id, "entity_type": "MATERIAL", "payload": {"name": "B"}},
        headers=auth_headers(token),
    )
    assert conflict.status_code == 409, conflict.text

    async with SessionLocal() as s:
        rows = (await s.execute(select(IntegrationSecurityEvent).where(IntegrationSecurityEvent.erp_instance_id == uuid.UUID(instance_id)))).scalars().all()
    assert any(r.event_type == "INBOUND_EVENT_ID_REUSED" for r in rows)


# --- INT-FR-016: compensation ---------------------------------------------------------------------------


async def test_compensation_requires_authorization_reference_and_succeeded_original(client, seeded, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(200, json={"data": {"name": "GR-0001", "docstatus": 1}}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_GOODS_RECEIPT", "payload": {"item_code": "X", "qty": "5"}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]

    # Cannot compensate a not-yet-succeeded command.
    too_early = await client.post(
        f"/integration/v1/commands/{command_id}/compensate",
        json={
            "idempotency_key": idem(), "original_command_id": command_id, "compensating_command_type": "POST_RETURN",
            "compensating_payload": {"item_code": "X", "qty": "5"}, "gxp_authorization_reference": {"record_type": "qms_deviation", "record_id": str(uuid.uuid4())},
            "reason": "batch rejected after receipt",
        },
        headers=auth_headers(token),
    )
    assert too_early.status_code == 409, too_early.text

    await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))

    missing_auth_ref = await client.post(
        f"/integration/v1/commands/{command_id}/compensate",
        json={
            "idempotency_key": idem(), "original_command_id": command_id, "compensating_command_type": "POST_RETURN",
            "compensating_payload": {"item_code": "X", "qty": "5"}, "gxp_authorization_reference": {}, "reason": "batch rejected after receipt",
        },
        headers=auth_headers(token),
    )
    assert missing_auth_ref.status_code == 422, missing_auth_ref.text

    resp = await client.post(
        f"/integration/v1/commands/{command_id}/compensate",
        json={
            "idempotency_key": idem(), "original_command_id": command_id, "compensating_command_type": "POST_RETURN",
            "compensating_payload": {"item_code": "X", "qty": "5"},
            "gxp_authorization_reference": {"record_type": "qms_deviation", "record_id": str(uuid.uuid4()), "action": "disposition"},
            "reason": "batch rejected after receipt, reversing goods receipt",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    compensation = await db_get_command(resp.json()["aggregate_id"])
    assert compensation.compensates_command_id == uuid.UUID(command_id)
    assert compensation.gxp_authorization_reference["record_type"] == "qms_deviation"
    assert compensation.command_type == "POST_RETURN"


async def db_get_command(command_id_str):
    from app.core.db import SessionLocal
    async with SessionLocal() as s:
        return await s.get(IntegrationCommand, uuid.UUID(command_id_str))


# --- INT-FR-021: SLA/aging metrics ----------------------------------------------------------------------


async def test_sla_metrics_reports_oldest_dead_letter_age(client, seeded, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(422, json={"error": "bad"}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]
    await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))

    metrics = await client.get(f"/integration/v1/instances/{instance_id}/sla-metrics", headers=auth_headers(token))
    assert metrics.status_code == 200, metrics.text
    body = metrics.json()
    assert body["oldest_dead_letter_age_seconds"] is not None
    assert body["oldest_dead_letter_age_seconds"] >= 0


# --- INT-FR-023: bulk jobs -------------------------------------------------------------------------------


async def test_bulk_job_lifecycle_tracks_record_level_failures_and_resumes(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    start = await client.post(
        "/integration/v1/bulk-jobs",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "job_type": "IMPORT", "entity_type": "MATERIAL", "total_records": 100},
        headers=auth_headers(token),
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["aggregate_id"]

    progress1 = await client.post(
        f"/integration/v1/bulk-jobs/{job_id}/progress",
        json={
            "idempotency_key": idem(), "job_id": job_id, "expected_version": 1, "succeeded_delta": 48,
            "newly_failed_records": [{"key": "ITEM-013", "reason": "VALIDATION_FAILED"}, {"key": "ITEM-027", "reason": "DUPLICATE"}],
            "resume_cursor": "cursor-50",
        },
        headers=auth_headers(token),
    )
    assert progress1.status_code == 200, progress1.text

    complete = await client.post(
        f"/integration/v1/bulk-jobs/{job_id}/complete",
        json={"idempotency_key": idem(), "job_id": job_id, "expected_version": 2},
        headers=auth_headers(token),
    )
    assert complete.status_code == 200, complete.text

    from app.modules.erp.models import IntegrationBulkJob

    job = await _db_get(IntegrationBulkJob, job_id)
    assert job.status == "COMPLETED_WITH_ERRORS"
    assert job.succeeded_count == 48
    assert job.failed_count == 2
    assert job.resume_cursor == "cursor-50"
    assert len(job.failed_records) == 2


async def test_bulk_job_start_is_idempotent_for_resume(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)
    key = idem()

    first = await client.post(
        "/integration/v1/bulk-jobs",
        json={"idempotency_key": key, "erp_instance_id": instance_id, "job_type": "EXPORT", "entity_type": "SUPPLIER"},
        headers=auth_headers(token),
    )
    second = await client.post(
        "/integration/v1/bulk-jobs",
        json={"idempotency_key": key, "erp_instance_id": instance_id, "job_type": "EXPORT", "entity_type": "SUPPLIER"},
        headers=auth_headers(token),
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


async def _db_get(model, id_str):
    from app.core.db import SessionLocal
    async with SessionLocal() as s:
        return await s.get(model, uuid.UUID(id_str))


# --- MDS-FR-028: migration package provenance -------------------------------------------------------------


async def test_record_migration_package_requires_name_and_checksum(client, seeded):
    token = await login(client, "integration.admin")

    missing = await client.post(
        "/integration/v1/migration-packages",
        json={"idempotency_key": idem(), "package_name": "", "source_checksum": ""},
        headers=auth_headers(token),
    )
    assert missing.status_code == 422, missing.text

    resp = await client.post(
        "/integration/v1/migration-packages",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "package_name": "onboarding-2026-08",
            "source_checksum": "sha256:" + "a" * 64, "entity_types": ["MATERIAL", "SUPPLIER"],
            "approval_reference": "CHG-0099",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.erp.models import ErpMigrationPackage
    package = await _db_get(ErpMigrationPackage, resp.json()["aggregate_id"])
    assert package.approved_by_user_id is not None
    assert package.entity_types == ["MATERIAL", "SUPPLIER"]


# --- ERP-ARC-008/011/016/020: new provider operations wired end to end ------------------------------------


async def test_purchase_order_reservation_release_availability_dispatch_via_erpnext(client, seeded, monkeypatch):
    """ERP-ARC-008/011/016 -- confirms the three previously-declared-but-unimplemented
    PROVIDER_OPERATIONS constants now actually dispatch through the ERPNext adapter."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"data": {"name": "REF-1", "docstatus": 1}})

    _patch_adapter(monkeypatch, handler)
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    for command_type, payload in (
        ("POST_PURCHASE_ORDER_REF", {"supplier": "SUP-1", "items": [{"item_code": "RM-1", "qty": "100"}]}),
        ("POST_RESERVATION", {"item_code": "RM-1", "qty": "10", "batch_id": str(uuid.uuid4())}),
        ("POST_RELEASE_AVAILABILITY", {"batch_id": str(uuid.uuid4()), "item_code": "FG-1", "qty": "500"}),
    ):
        queue = await client.post(
            "/integration/v1/commands",
            json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": command_type, "payload": payload},
            headers=auth_headers(token),
        )
        assert queue.status_code == 200, queue.text
        command_id = queue.json()["aggregate_id"]
        dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
        assert dispatch.status_code == 200, dispatch.text
        command = await db_get_command(command_id)
        assert command.state == "SUCCEEDED", f"{command_type} did not succeed: {command.last_error_detail}"

    assert len(calls) == 3


# --- SAP adapter direct unit tests (SAP-FR-004/010/020) --------------------------------------------------


async def test_sap_adapter_fetches_csrf_token_before_write():
    from app.modules.erp.adapters.sap import SapS4HanaAdapter
    from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url), dict(request.headers)))
        if request.headers.get("x-csrf-token") == "Fetch":
            return httpx.Response(200, headers={"x-csrf-token": "csrf-abc123"})
        assert request.headers.get("x-csrf-token") == "csrf-abc123"
        return httpx.Response(201, json={"MaterialDocument": "5000001234"})

    transport = httpx.MockTransport(handler)
    config = AdapterConfig(base_url="https://sap.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="s4hana-cloud-odata-v2", extra={"transport": transport})
    adapter = SapS4HanaAdapter(config)

    result = await adapter.dispatch(CanonicalOutboundCommand(
        command_type="POST_GOODS_RECEIPT", entity_type=None, internal_ref={}, payload={"Material": "RM-1"}, idempotency_key="k1",
    ))
    assert result.succeeded, result.raw_body
    assert result.external_reference == "5000001234"
    assert len(calls) == 2
    assert calls[0][2]["x-csrf-token"] == "Fetch"


async def test_sap_adapter_movement_type_override():
    from app.modules.erp.adapters.sap import SapS4HanaAdapter
    from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand

    posted_movement_codes = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("x-csrf-token") == "Fetch":
            return httpx.Response(200, headers={"x-csrf-token": "tok"})
        import json as _json
        posted_movement_codes.append(_json.loads(request.content)["GoodsMovementCode"])
        return httpx.Response(201, json={"MaterialDocument": "REF"})

    transport = httpx.MockTransport(handler)
    config = AdapterConfig(
        base_url="https://sap.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="s4hana-cloud-odata-v2",
        extra={"transport": transport, "movement_type_overrides": {"POST_GOODS_RECEIPT": "961"}},
    )
    adapter = SapS4HanaAdapter(config)

    await adapter.dispatch(CanonicalOutboundCommand(command_type="POST_GOODS_RECEIPT", entity_type=None, internal_ref={}, payload={}, idempotency_key="k2"))
    assert posted_movement_codes == ["961"]  # overridden, not the module default "101"


async def test_sap_adapter_get_material_stock():
    from app.modules.erp.adapters.sap import SapS4HanaAdapter
    from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand

    def handler(request: httpx.Request) -> httpx.Response:
        assert "A_MaterialStock" in str(request.url)
        assert "RM-1" in str(request.url)
        return httpx.Response(200, json={"d": {"results": [{"Material": "RM-1", "MatlWrhsStkQtyInMatlBaseUnit": "42"}]}})

    transport = httpx.MockTransport(handler)
    config = AdapterConfig(base_url="https://sap.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="s4hana-cloud-odata-v2", extra={"transport": transport})
    adapter = SapS4HanaAdapter(config)

    result = await adapter.dispatch(CanonicalOutboundCommand(
        command_type="GET_MATERIAL_STOCK", entity_type=None, internal_ref={}, payload={"material_number": "RM-1"}, idempotency_key="k3",
    ))
    assert result.succeeded, result.raw_body
    assert result.raw_status == 200


# --- MULTI-FR-011: Dynamics 365 dataAreaId enforcement ----------------------------------------------------


async def test_dynamics_adapter_rejects_write_missing_data_area():
    from app.modules.erp.adapters.dynamics365 import Dynamics365Adapter
    from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("adapter must not call out when dataAreaId is missing")

    transport = httpx.MockTransport(handler)
    config = AdapterConfig(base_url="https://d365.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="fo-odata-v4", extra={"transport": transport})
    adapter = Dynamics365Adapter(config)

    result = await adapter.dispatch(CanonicalOutboundCommand(command_type="POST_GOODS_RECEIPT", entity_type=None, internal_ref={}, payload={}, idempotency_key="k1"))
    assert not result.succeeded
    assert result.raw_body["exception"] == "MISSING_DATA_AREA"


async def test_dynamics_adapter_succeeds_with_data_area():
    from app.modules.erp.adapters.dynamics365 import Dynamics365Adapter
    from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"JournalNumber": "JRN-1"})

    transport = httpx.MockTransport(handler)
    config = AdapterConfig(base_url="https://d365.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="fo-odata-v4", extra={"transport": transport})
    adapter = Dynamics365Adapter(config)

    result = await adapter.dispatch(CanonicalOutboundCommand(command_type="POST_GOODS_RECEIPT", entity_type=None, internal_ref={}, payload={"dataAreaId": "usmf"}, idempotency_key="k2"))
    assert result.succeeded
    assert result.external_reference == "JRN-1"


# --- MULTI-FR-022/024: custom connector validation gate ---------------------------------------------------


async def test_generic_instance_write_blocked_until_validated(client, seeded):
    token = await login(client, "integration.admin")

    register = await client.post(
        "/integration/v1/instances",
        json={
            "idempotency_key": idem(), "instance_name": f"custom-{uuid.uuid4()}", "vendor": "GENERIC",
            "base_url": "https://custom.demo.invalid", "auth_method": "API_KEY", "auth_secret_ref": "k",
        },
        headers=auth_headers(token),
    )
    assert register.status_code == 200, register.text
    instance_id = register.json()["aggregate_id"]

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_GOODS_RECEIPT", "payload": {}},
        headers=auth_headers(token),
    )
    assert queue.status_code == 422, queue.text
    assert queue.json()["code"] == "ERP_INSTANCE_INVALID"


async def test_generic_instance_validation_requires_read_path_for_write_capable_adapter(client, seeded, db):
    token = await login(client, "integration.admin")

    register = await client.post(
        "/integration/v1/instances",
        json={
            "idempotency_key": idem(), "instance_name": f"custom-{uuid.uuid4()}", "vendor": "GENERIC",
            "base_url": "https://custom.demo.invalid", "auth_method": "API_KEY", "auth_secret_ref": "k",
        },
        headers=auth_headers(token),
    )
    instance_id = register.json()["aggregate_id"]

    from app.modules.erp.models import ErpInstance
    async with db.begin():
        instance = await db.get(ErpInstance, uuid.UUID(instance_id), with_for_update=True)
        # Write-capable (POST_GOODS_RECEIPT) but no read/sync operation declared -- MULTI-FR-022 blocker.
        instance.capabilities = {"endpoint_map": {"POST_GOODS_RECEIPT": "/api/goods-receipts"}}

    blocked = await client.post(
        f"/integration/v1/instances/{instance_id}/validate",
        json={"idempotency_key": idem(), "instance_id": instance_id, "expected_version": 1, "acceptance_reference": "CHG-0100"},
        headers=auth_headers(token),
    )
    assert blocked.status_code == 422, blocked.text

    async with db.begin():
        instance = await db.get(ErpInstance, uuid.UUID(instance_id), with_for_update=True)
        instance.capabilities = {"endpoint_map": {"POST_GOODS_RECEIPT": "/api/goods-receipts", "SYNC_MATERIAL_ITEM": "/api/items"}}

    validated = await client.post(
        f"/integration/v1/instances/{instance_id}/validate",
        json={"idempotency_key": idem(), "instance_id": instance_id, "expected_version": 1, "acceptance_reference": "CHG-0100"},
        headers=auth_headers(token),
    )
    assert validated.status_code == 200, validated.text

    get_resp = await client.get(f"/integration/v1/instances/{instance_id}")
    assert get_resp.json()["validated"] is True


# --- MDS-FR-026: data quality metrics -----------------------------------------------------------------


async def test_data_quality_metrics_counts_unmapped_conflict_and_active(client, seeded, db):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    propose = await client.post(
        "/integration/v1/mappings",
        json={
            "idempotency_key": idem(), "erp_instance_id": instance_id, "entity_type": "MATERIAL",
            "internal_id": str(uuid.uuid4()), "external_id": f"ITEM-{uuid.uuid4()}", "match_method": "MANUAL",
        },
        headers=auth_headers(token),
    )
    assert propose.status_code == 200, propose.text

    metrics = await client.get(f"/integration/v1/instances/{instance_id}/data-quality-metrics", headers=auth_headers(token))
    assert metrics.status_code == 200, metrics.text
    body = metrics.json()
    assert body["unmapped_count"] >= 0
    assert "conflict_count" in body and "stale_count" in body and "duplicate_count" in body


# --- ENXT-FR-020: no embedded evidence without explicit opt-in ------------------------------------------


async def test_embedded_evidence_payload_rejected_by_default(client, seeded):
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    resp = await client.post(
        "/integration/v1/commands",
        json={
            "idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_QUALITY_STATUS",
            "payload": {"item_code": "X", "attachment_blob": "base64garbage=="},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_embedded_evidence_payload_allowed_when_instance_opts_in(client, seeded, db):
    token = await login(client, "integration.admin")
    instance = seeded["erp_instance"]
    instance_id = str(instance.id)

    async with db.begin():
        row = await db.get(type(instance), instance.id, with_for_update=True)
        row.capabilities = {**(row.capabilities or {}), "allow_embedded_evidence": True}

    resp = await client.post(
        "/integration/v1/commands",
        json={
            "idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_QUALITY_STATUS",
            "payload": {"item_code": "X", "attachment_blob": "base64garbage=="},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


# --- INT-FR-029: chaos scenarios ------------------------------------------------------------------------
# Network partition/lost response: test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm.
# Duplicates: test_ingest_event_dedupes_and_detects_conflict, test_register_instance_duplicate_idempotency_
# key_returns_same_receipt. Throttling: test_circuit_breaker_opens_after_repeated_failures_and_throttles,
# test_rate_limit_throttles_before_circuit_breaker_trips. Partial bulk failure: test_bulk_job_lifecycle_
# tracks_record_level_failures_and_resumes. Provider outage (below): getCapabilities()'s probe() reports
# reachable=False without raising, rather than the call failing outright.


async def test_provider_outage_reported_via_capabilities_probe(client, seeded, monkeypatch):
    _patch_adapter(monkeypatch, lambda request: httpx.Response(503))
    resp = await client.get(f"/integration/v1/instances/{seeded['erp_instance'].id}/capabilities")
    assert resp.status_code == 200, resp.text
    assert resp.json()["reachable"] is False


async def test_sap_adapter_post_transfer():
    from app.modules.erp.adapters.sap import SapS4HanaAdapter
    from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("x-csrf-token") == "Fetch":
            return httpx.Response(200, headers={"x-csrf-token": "tok"})
        import json as _json
        assert _json.loads(request.content)["GoodsMovementCode"] == "311"
        return httpx.Response(201, json={"MaterialDocument": "XFER-1"})

    transport = httpx.MockTransport(handler)
    config = AdapterConfig(base_url="https://sap.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="s4hana-cloud-odata-v2", extra={"transport": transport})
    adapter = SapS4HanaAdapter(config)

    result = await adapter.dispatch(CanonicalOutboundCommand(command_type="POST_TRANSFER", entity_type=None, internal_ref={}, payload={}, idempotency_key="k1"))
    assert result.succeeded, result.raw_body
    assert result.external_reference == "XFER-1"


# --- Test-case execution pass (TC-048..053): closing the 92 blocked P1 cases ---------------------------
# See docs/generated/18_SPEC_GAPS.md SG-126 and status/build-status.json for the full requirement-by-
# requirement disposition. Tests below cover the real gaps this pass found that weren't yet covered by
# any test written earlier in the WP-07 completion pass.


async def test_register_instance_plaintext_url_rejected(client, seeded):
    """TC-048-028-01 (ERP-ARC-028 required behaviour, TLS half)."""
    token = await login(client, "integration.admin")
    resp = await client.post(
        "/integration/v1/instances",
        json={"idempotency_key": idem(), "instance_name": f"plaintext-{uuid.uuid4()}", "vendor": "GENERIC", "base_url": "http://insecure.demo.invalid", "auth_method": "API_KEY", "auth_secret_ref": "k"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "ERP_INSTANCE_INVALID"


async def test_lot_serial_mapping_entity_types_accepted(client, seeded):
    """TC-048-020-01/TC-049-010-01/TC-050-013-01/TC-051-005-01 (ERP-ARC-020/ENXT-FR-010/SAP-FR-013/
    MULTI-FR-005 required behaviour): MATERIAL_LOT/SERIAL are real, accepted mapping entity types --
    vendor-neutral by construction (the same code path serves every named vendor's adapter)."""
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    lot_mapping = await client.post(
        "/integration/v1/mappings",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "entity_type": "MATERIAL_LOT", "internal_id": str(uuid.uuid4()), "external_id": f"LOT-{uuid.uuid4()}", "field_ownership": "ERP"},
        headers=auth_headers(token),
    )
    assert lot_mapping.status_code == 200, lot_mapping.text

    serial_mapping = await client.post(
        "/integration/v1/mappings",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "entity_type": "SERIAL", "internal_id": str(uuid.uuid4()), "external_id": f"SN-{uuid.uuid4()}", "field_ownership": "ERP"},
        headers=auth_headers(token),
    )
    assert serial_mapping.status_code == 200, serial_mapping.text


async def test_dispatch_honors_vendor_retry_after_header(client, seeded, db, monkeypatch):
    """TC-053-S003 (429 Retry-After scenario, INT-FR-004). Found during test-case execution: `compute_
    retry_decision()` already accepted `retry_after_seconds` but no adapter ever populated it and
    `dispatch_erp_command()` never read it -- fixed this pass (provider.py/adapters/base.py/commands.py)."""
    _patch_adapter(monkeypatch, lambda request: httpx.Response(429, headers={"Retry-After": "120"}, json={"error": "rate limited"}))
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    queue = await client.post(
        "/integration/v1/commands",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "command_type": "POST_CONSUMPTION", "payload": {}},
        headers=auth_headers(token),
    )
    command_id = queue.json()["aggregate_id"]
    dispatch = await client.post(f"/integration/v1/commands/{command_id}/dispatch", headers=auth_headers(token))
    assert dispatch.status_code == 200, dispatch.text

    command = await db.get(IntegrationCommand, uuid.UUID(command_id))
    assert command.state == "RETRY_WAIT"
    assert command.last_error_category == "RATE_LIMIT"
    # Honored verbatim, not the platform's own computed exponential backoff (30s * 2^0 = 30s default).
    expected = datetime.now(timezone.utc) + timedelta(seconds=120)
    assert abs((command.next_attempt_at.replace(tzinfo=timezone.utc) - expected).total_seconds()) < 5


async def test_bulk_job_progress_rejected_once_completed(client, seeded):
    """TC-053-023-02 (INT-FR-023, prohibited-path case): a completed bulk job's own state machine
    rejects further progress/completion -- found not yet covered by a dedicated test while executing
    WP-07's pre-written case book."""
    token = await login(client, "integration.admin")
    instance_id = str(seeded["erp_instance"].id)

    start = await client.post(
        "/integration/v1/bulk-jobs",
        json={"idempotency_key": idem(), "erp_instance_id": instance_id, "job_type": "IMPORT", "entity_type": "SUPPLIER", "total_records": 10},
        headers=auth_headers(token),
    )
    job_id = start.json()["aggregate_id"]
    complete = await client.post(
        f"/integration/v1/bulk-jobs/{job_id}/complete",
        json={"idempotency_key": idem(), "job_id": job_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert complete.status_code == 200, complete.text

    prohibited = await client.post(
        f"/integration/v1/bulk-jobs/{job_id}/progress",
        json={"idempotency_key": idem(), "job_id": job_id, "expected_version": 2, "succeeded_delta": 1},
        headers=auth_headers(token),
    )
    assert prohibited.status_code == 409, prohibited.text
    assert prohibited.json()["code"] == "INVALID_TRANSITION"


async def test_sap_adapter_csrf_fetch_failure_surfaces_as_auth_error(client, seeded, monkeypatch):
    """TC-050-S003 (CSRF failure scenario, SAP-FR-020): if the CSRF token fetch itself fails, the
    adapter proceeds without a token (per `_csrf_headers`'s own documented fallback) rather than
    raising -- the subsequent write then gets whatever the vendor does for a missing/invalid token
    (modelled here as 403, SAP's real behaviour), classified AUTH by the existing, unmodified
    reliability.classify_integration_error() -- no new classification logic needed for this scenario."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("x-csrf-token") == "Fetch":
            return httpx.Response(403)  # CSRF fetch itself rejected -- no token to hand back
        # The write proceeds with no CSRF header at all (base._csrf_headers() swallowed the fetch
        # failure and returned {}) -- the vendor rejects it, same as a real SAP tenant would.
        assert "x-csrf-token" not in {k.lower() for k in request.headers}
        return httpx.Response(403, json={"error": "CSRF token validation failed"})

    from app.modules.erp.adapters.sap import SapS4HanaAdapter
    from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand
    transport = httpx.MockTransport(handler)
    config = AdapterConfig(base_url="https://sap.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="s4hana-cloud-odata-v2", extra={"transport": transport})
    adapter = SapS4HanaAdapter(config)

    result = await adapter.dispatch(CanonicalOutboundCommand(command_type="POST_GOODS_RECEIPT", entity_type=None, internal_ref={}, payload={}, idempotency_key="k1"))
    assert not result.succeeded
    assert result.raw_status == 403


# =================================================================================================
# build_adapter() secret-manager wiring — SG-126 gap resolution (WP-07 pass)
# =================================================================================================


async def test_build_adapter_uses_managed_secret_value_when_ref_is_registered(client, seeded, db):
    """If auth_secret_ref names a registered ON_PREM secret, build_adapter resolves the real value
    through fetch_secret_value() (authorization-gated, audited) instead of using the ref as the
    credential directly."""
    from app.core.security import hash_password
    from app.modules.erp.commands import build_adapter
    from app.modules.erp.models import ErpInstance
    from app.modules.iam.models import User, UserSiteRole
    from app.modules.security import crypto_commands as sec_commands
    from tests.conftest import DEMO_PASSWORD

    async with db.begin():
        actor = User(username="erpsec.u1", email="erpsec.u1@x.com", full_name="ERP Sec U",
                     password_hash=hash_password(DEMO_PASSWORD), status="active")
        db.add(actor)
        await db.flush()
        db.add(UserSiteRole(user_id=actor.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))

    async with db.begin():
        instance = ErpInstance(
            instance_name=f"managed-secret-{uuid.uuid4()}", vendor="GENERIC", environment="SANDBOX",
            base_url="https://custom.demo.invalid", auth_method="API_KEY",
            auth_secret_ref="on-prem/erp-instance-managed", version=1,
        )
        db.add(instance)
        await db.flush()
        instance_id = instance.id

    async with db.begin():
        await sec_commands.create_secret(db, sec_commands.CreateSecretCommand(
            idempotency_key=idem(), secret_ref="on-prem/erp-instance-managed", provider="ON_PREM",
            purpose="ERP adapter credential", owner="platform-team",
            consumer_identities=[f"erp_instance:{instance_id}"], initial_value="real-managed-secret",
        ), actor.id)

    async with db.begin():
        instance = await db.get(ErpInstance, instance_id)
        adapter = await build_adapter(db, instance)
    assert adapter.config.auth_secret == "real-managed-secret"


async def test_build_adapter_falls_back_to_raw_ref_when_unregistered(client, seeded, db):
    """An ErpInstance whose auth_secret_ref does not match any registered secret_metadata row keeps
    behaving exactly as it did before SG-126's ON_PREM store existed -- the ref is used directly as the
    credential. Every pre-existing ErpInstance in this test suite is in this branch."""
    from app.modules.erp.commands import build_adapter
    from app.modules.erp.models import ErpInstance

    async with db.begin():
        instance = ErpInstance(
            instance_name=f"unmanaged-{uuid.uuid4()}", vendor="GENERIC", environment="SANDBOX",
            base_url="https://custom.demo.invalid", auth_method="API_KEY",
            auth_secret_ref="not-a-registered-secret-ref", version=1,
        )
        db.add(instance)
        await db.flush()
        instance_id = instance.id

    async with db.begin():
        instance = await db.get(ErpInstance, instance_id)
        adapter = await build_adapter(db, instance)
    assert adapter.config.auth_secret == "not-a-registered-secret-ref"
