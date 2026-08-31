"""WP-07 SG-126 item 1 — the automated master-data pull pipeline (`app/modules/erp/sync.py` +
`app/modules/erp/matching.py`): `fetch_changes()` -> normalize -> match -> propose/reconcile/suspend.

Closes TC-048-006-*/TC-048-007-* (ERP-ARC-006/007), TC-052-004-01/TC-052-S001 (MDS-FR-004), TC-052-005-01
(MDS-FR-005), TC-052-008-* (MDS-FR-008), TC-052-017-01 (MDS-FR-017), TC-052-024-*/TC-052-S008
(MDS-FR-024). Every adapter call runs against a local `httpx.MockTransport` (SG-125: no credentialed
ERPNext sandbox is reachable from this environment).
"""

import uuid

import httpx
from sqlalchemy import select

from app.modules.erp import commands as erp_commands
from app.modules.erp import sync as erp_sync
from app.modules.erp.adapters.erpnext import ERPNextAdapter
from app.modules.erp.models import ErpExternalMapping, ErpSyncCheckpoint
from app.modules.erp.provider import AdapterConfig
from app.modules.material.models import Material
from app.modules.supplier_quality.models import Supplier
from app.mutation.errors import InvalidTransitionError, ValidationFailedError


def _mock_adapter(handler) -> ERPNextAdapter:
    transport = httpx.MockTransport(handler)
    config = AdapterConfig(base_url="https://erpnext.demo.invalid", auth_method="API_KEY", auth_secret="k:s", contract_version="v14-resource-api", extra={"transport": transport})
    return ERPNextAdapter(config)


def _patch_adapter(monkeypatch, handler) -> None:
    adapter = _mock_adapter(handler)
    monkeypatch.setattr(erp_commands, "build_adapter", lambda instance: adapter)


async def test_sync_pulls_material_changes_and_proposes_explicit_and_fuzzy_matches(seeded, db, monkeypatch):
    """ERP-ARC-006, MDS-FR-005/008: fetch_changes() is now actually called by a real pipeline function --
    an exact code match is proposed EXPLICIT_ID, a near-miss name is proposed FUZZY_PROPOSED, and a record
    with no plausible internal match is left unmatched rather than guessed."""

    async with db.begin():
        db.add(Material(site_id=seeded["site_id"], code="RM-EXACT", name="Sodium Chloride USP", uom="kg", version=1))
        db.add(Material(site_id=seeded["site_id"], code="RM-FUZZY", name="Potassium Chloride Injection", uom="kg", version=1))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/resource/Item"
        return httpx.Response(200, json={"data": [
            {"name": "ITEM-EXACT", "item_name": "Whatever ERP calls it", "item_code": "RM-EXACT", "disabled": 0, "modified": "2026-01-01 00:00:00"},
            {"name": "ITEM-FUZZY", "item_name": "Potassium Chloride Injectn", "disabled": 0, "modified": "2026-01-02 00:00:00"},
            {"name": "ITEM-NOMATCH", "item_name": "Completely Unrelated Widget", "disabled": 0, "modified": "2026-01-03 00:00:00"},
        ]})

    _patch_adapter(monkeypatch, handler)
    actor_id = seeded["users"]["integration.admin"].id
    outcome = await erp_sync.sync_master_data(db, erp_instance_id=seeded["erp_instance"].id, entity_type="MATERIAL", actor_user_id=actor_id)

    assert outcome.fetched == 3
    assert outcome.proposed_explicit == 1
    assert outcome.proposed_fuzzy == 1
    assert outcome.unmatched == 1
    assert len(outcome.proposal_ids) == 2

    async with db.begin():
        exact = (await db.execute(select(ErpExternalMapping).where(ErpExternalMapping.external_id == "ITEM-EXACT"))).scalar_one()
        assert exact.match_method == "EXPLICIT_ID" and exact.mapping_status == "PROPOSED"
        fuzzy = (await db.execute(select(ErpExternalMapping).where(ErpExternalMapping.external_id == "ITEM-FUZZY"))).scalar_one()
        assert fuzzy.match_method == "FUZZY_PROPOSED" and fuzzy.mapping_status == "PROPOSED"
        no_match = (await db.execute(select(ErpExternalMapping).where(ErpExternalMapping.external_id == "ITEM-NOMATCH"))).scalar_one_or_none()
        assert no_match is None  # never guessed a link -- AG-15

    # A never-activated PROPOSED mapping never re-proposes on a subsequent poll (idempotent, ERP-ARC-006).
    outcome2 = await erp_sync.sync_master_data(db, erp_instance_id=seeded["erp_instance"].id, entity_type="MATERIAL", actor_user_id=actor_id)
    assert outcome2.proposed_explicit == 0 and outcome2.proposed_fuzzy == 0


async def test_sync_supplier_changes_pulled_by_same_pipeline(seeded, db, monkeypatch):
    """ERP-ARC-007: 'same gap as ERP-ARC-006' -- the pipeline is entity_type-generic, not material-only."""

    async with db.begin():
        db.add(Supplier(supplier_code="SUP-EXACT", legal_name="Acme Chemical Supply", role_type="supplier", status="approved"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/resource/Supplier"
        return httpx.Response(200, json={"data": [
            {"name": "VEND-001", "supplier_name": "irrelevant display", "supplier_code": "SUP-EXACT", "disabled": 0, "modified": "2026-01-01 00:00:00"},
        ]})

    _patch_adapter(monkeypatch, handler)
    actor_id = seeded["users"]["integration.admin"].id
    outcome = await erp_sync.sync_master_data(db, erp_instance_id=seeded["erp_instance"].id, entity_type="SUPPLIER", actor_user_id=actor_id)

    assert outcome.proposed_explicit == 1
    mapping = (await db.execute(select(ErpExternalMapping).where(ErpExternalMapping.external_id == "VEND-001"))).scalar_one()
    assert mapping.entity_type == "SUPPLIER" and mapping.match_method == "EXPLICIT_ID"


async def test_sync_bulk_initial_import_walks_multiple_pages(seeded, db, monkeypatch):
    """MDS-FR-004/TC-052-S001: 'a 100k-item import scenario is not constructible against propose_mapping's
    one-at-a-time endpoint'. This demonstrates the pipeline mechanism is genuinely constructible at scale
    without a human calling proposeMapping per record -- three 100-record pages (300 records) walked in
    one bulk-import call; a literal 100k-record load run is a separate performance-test exercise this
    pass does not claim to have executed (CLAUDE.md §5)."""

    pages = [
        [{"name": f"BULK-{page}-{i}", "item_name": f"Bulk Item {page}-{i}", "disabled": 0, "modified": f"2026-01-0{page + 1} 00:00:00"} for i in range(100)]
        for page in range(3)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        cursor = None
        params = dict(request.url.params)
        if "filters" in params:
            cursor = params["filters"]
        page_index = 0 if cursor is None else int(cursor.split("2026-01-0")[1][0])
        return httpx.Response(200, json={"data": pages[page_index]})

    _patch_adapter(monkeypatch, handler)
    actor_id = seeded["users"]["integration.admin"].id
    outcome = await erp_sync.sync_master_data(
        db, erp_instance_id=seeded["erp_instance"].id, entity_type="MATERIAL", actor_user_id=actor_id, max_pages=3,
    )

    assert outcome.pages_fetched == 3
    assert outcome.fetched == 300
    assert outcome.unmatched == 300  # none of these have an internal Material fixture -- correctly unmatched, not guessed
    checkpoint = (
        await db.execute(select(ErpSyncCheckpoint).where(ErpSyncCheckpoint.erp_instance_id == seeded["erp_instance"].id, ErpSyncCheckpoint.entity_type == "MATERIAL"))
    ).scalar_one()
    assert checkpoint.cursor_value == "2026-01-03 00:00:00"


async def test_sync_detects_external_deactivation_and_suspends_active_mapping(seeded, db, monkeypatch):
    """MDS-FR-017/024, TC-052-S008: an ERPNext 'disabled' flag on an already-ACTIVE mapping suspends the
    projection -- it is never deleted, and reactivation reuses the existing approve_mapping() path."""

    actor_id = seeded["users"]["integration.admin"].id
    async with db.begin():
        mapping = ErpExternalMapping(
            erp_instance_id=seeded["erp_instance"].id, entity_type="MATERIAL", internal_id=uuid.uuid4(),
            external_id="ITEM-DEACTIVATED", external_code="ITEM-DEACTIVATED", field_ownership="ERP",
            mapping_status="ACTIVE", match_method="MANUAL", version=1,
        )
        db.add(mapping)
        await db.flush()
        mapping_id = mapping.id

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [
            {"name": "ITEM-DEACTIVATED", "item_name": "Now Disabled In ERP", "disabled": 1, "modified": "2026-02-01 00:00:00"},
        ]})

    _patch_adapter(monkeypatch, handler)
    outcome = await erp_sync.sync_master_data(db, erp_instance_id=seeded["erp_instance"].id, entity_type="MATERIAL", actor_user_id=actor_id)

    assert outcome.suspended == 1
    mapping_after = await db.get(ErpExternalMapping, mapping_id)
    assert mapping_after.mapping_status == "SUSPENDED"
    assert mapping_after.version == 2

    # Reactivation reuses the existing approve_mapping() path -- exactly one entry/exit pair for this state.
    async with db.begin():
        await erp_commands.approve_mapping(
            db, erp_commands.ApproveMappingCommand(idempotency_key=str(uuid.uuid4()), mapping_id=mapping_id, expected_version=2), actor_id,
        )
    reactivated = await db.get(ErpExternalMapping, mapping_id)
    assert reactivated.mapping_status == "ACTIVE"


async def test_suspend_mapping_requires_reason_and_only_suspends_active(seeded, db):
    actor_id = seeded["users"]["integration.admin"].id
    async with db.begin():
        mapping = ErpExternalMapping(
            erp_instance_id=seeded["erp_instance"].id, entity_type="MATERIAL", internal_id=uuid.uuid4(),
            external_id="ITEM-SUSPEND-DIRECT", external_code="ITEM-SUSPEND-DIRECT", field_ownership="ERP",
            mapping_status="PROPOSED", match_method="MANUAL", version=1,
        )
        db.add(mapping)
        await db.flush()
        mapping_id = mapping.id

    async with db.begin():
        try:
            await erp_commands.suspend_mapping(
                db, erp_commands.SuspendMappingCommand(idempotency_key=str(uuid.uuid4()), mapping_id=mapping_id, expected_version=1, reason=""), actor_id,
            )
            raised_missing_reason = False
        except ValidationFailedError:
            raised_missing_reason = True
    assert raised_missing_reason

    async with db.begin():
        try:
            await erp_commands.suspend_mapping(
                db, erp_commands.SuspendMappingCommand(idempotency_key=str(uuid.uuid4()), mapping_id=mapping_id, expected_version=1, reason="operator test"), actor_id,
            )
            raised_wrong_state = False
        except InvalidTransitionError:
            raised_wrong_state = True
    assert raised_wrong_state  # PROPOSED (not ACTIVE) can never be suspended
