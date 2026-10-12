"""Shared shaping helpers for the WP-05 QMS read side.

Every QMS aggregate lists the same way -- filter by site, optionally by workflow state, free-text search
on the human-facing record number, then hand off to the standard `paginate()` envelope so the frontend's
DataTable talks to all of them identically. This module holds that one filter builder plus the datetime/
UUID shaping every `_dict()` needs, rather than repeating both in ten routers.

These are non-authoritative reads (AG-11): they exist so a reviewer can find a record. Every regulated
decision still reads the owning aggregate through its command path.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.pagination import PageParams


def iso(value: datetime | None) -> str | None:
    """ISO-8601 or None -- the shape every existing `_dict()` in this codebase emits for a timestamp."""
    return value.isoformat() if value else None


def sid(value: uuid.UUID | None) -> str | None:
    """UUID as a string, preserving None (JSON has no UUID type and `str(None)` would emit "None")."""
    return str(value) if value else None


async def resolve_user_names(
    session: AsyncSession, user_ids: set[uuid.UUID | str | None]
) -> dict[str, tuple[str, str]]:
    """Batch-resolves a set of `iam.users.id` references to `(full_name, username)` -- generalizes the
    pattern `ncr_router.py::_resolve_ncr_user_refs` established (2026-10 UUID-display audit): a GET detail
    endpoint collects every user id it shows (owner, performer, verified_by, ...), resolves them all in
    one query, and returns `{id_key}_full_name`/`{id_key}_username` fields alongside the raw ids -- the
    raw id is never removed, only a resolved sibling is added, so nothing that already reads the raw
    field breaks. `None`/falsy entries in `user_ids` are dropped so callers can pass optional fields
    (`record.some_user_id`) directly into the set without a guard."""
    ids = {str(u) for u in user_ids if u}
    if not ids:
        return {}
    from app.modules.iam.models import User

    rows = (await session.execute(select(User.id, User.full_name, User.username).where(User.id.in_(ids)))).all()
    return {str(row.id): (row.full_name, row.username) for row in rows}


async def resolve_vault_object_label(session: AsyncSession, object_id: uuid.UUID | None) -> str | None:
    """`vault.gxp_vault_object.object_id` references show up across several modules (release,
    recipe-master, batch-execution) as a raw id with no resolved label -- this gives every caller the
    same `"{object_type} {business_id} v{internal_version}"` shape (2026-10 UUID-display audit)."""
    if object_id is None:
        return None
    from app.modules.vault.models import VaultObject

    obj = await session.get(VaultObject, object_id)
    if obj is None:
        return None
    return f"{obj.object_type} {obj.business_id} v{obj.internal_version}"


async def resolve_vault_object_labels(session: AsyncSession, object_ids: set[uuid.UUID | str | None]) -> dict[str, str]:
    """Batch form of `resolve_vault_object_label` for list endpoints that would otherwise issue one
    `session.get` per row (e.g. a batch list showing both `recipe_vault_object_id` and
    `execution_snapshot_id` per row)."""
    ids = {str(i) for i in object_ids if i}
    if not ids:
        return {}
    from app.modules.vault.models import VaultObject

    rows = (await session.execute(select(VaultObject).where(VaultObject.object_id.in_(ids)))).scalars().all()
    return {str(obj.object_id): f"{obj.object_type} {obj.business_id} v{obj.internal_version}" for obj in rows}


async def resolve_source_label(session: AsyncSession, source_type: str | None, source_id: uuid.UUID | str | None) -> str | None:
    """Resolves a polymorphic `source_type`/`source_id` pair (NCR-FR-002, CAPA-FR-001) to the human-
    facing number of the record it names -- `source_type` is a free string naming one of several
    unrelated tables, each with its own business-number column, so this is a type dispatch rather than
    a join (2026-10 UUID-display audit). Deliberately returns `None` (falls back to the raw id) for
    `source_type`s with no backing entity (`test`, `inspection`, `security`) or no human-facing number
    on the target row (`oot`, `trend` -- `OotRecord` has no business-number column) or an ambiguous
    target (`validation` -- several validation entities could be meant, not guessed per CLAUDE.md's
    SPEC_GAP rule) -- never invented, only ever read from the row that already exists."""
    if source_id is None or not source_type:
        return None

    if source_type == "deviation":
        from app.modules.qms.models import DeviationRecord

        row = await session.get(DeviationRecord, source_id)
        return row.deviation_number if row else None
    if source_type == "oos":
        from app.modules.qc.models import OosRecord

        row = await session.get(OosRecord, source_id)
        return row.oos_number if row else None
    if source_type == "ncr":
        from app.modules.qms.ncr_models import NonconformanceRecord

        row = await session.get(NonconformanceRecord, source_id)
        return row.ncr_number if row else None
    if source_type == "capa":
        from app.modules.qms.capa_models import CapaRecord

        row = await session.get(CapaRecord, source_id)
        return row.capa_number if row else None
    if source_type == "scar":
        from app.modules.qms.scar_models import SupplierQualityCase

        row = await session.get(SupplierQualityCase, source_id)
        return row.case_number if row else None
    if source_type == "complaint":
        from app.modules.qms.complaint_models import ComplaintRecord

        row = await session.get(ComplaintRecord, source_id)
        return row.complaint_number if row else None
    if source_type == "audit":
        from app.modules.qms.internal_audit_models import InternalAudit

        row = await session.get(InternalAudit, source_id)
        return row.audit_number if row else None
    if source_type == "supplier":
        from app.modules.supplier_quality.models import Supplier

        row = await session.get(Supplier, source_id)
        return f"{row.legal_name} ({row.supplier_code})" if row else None
    if source_type == "risk":
        from app.modules.qms.risk_models import RiskRecord

        row = await session.get(RiskRecord, source_id)
        return row.risk_number if row else None
    if source_type == "change_control":
        from app.modules.qms.change_models import ChangeControl

        row = await session.get(ChangeControl, source_id)
        return row.change_number if row else None
    if source_type == "field_action":
        from app.modules.qms.field_action_models import FieldAction

        row = await session.get(FieldAction, source_id)
        return row.action_number if row else None
    if source_type == "batch":
        from app.modules.batch_execution.models import Batch

        row = await session.get(Batch, source_id)
        return row.batch_number if row else None
    if source_type == "qc_result":
        label = (await resolve_qc_result_samples(session, {source_id})).get(str(source_id))
        return f"Sample {label}" if label else None
    # genealogy's own `authoritative_record_type` vocabulary (app/modules/genealogy/service.py callers)
    # -- a different polymorphic reference from NCR/CAPA's `source_type` above, but the same shape, so
    # reused here rather than duplicated.
    if source_type == "material_lot":
        from app.modules.material.models import MaterialLot

        row = await session.get(MaterialLot, source_id)
        return row.internal_lot if row else None
    if source_type == "material_container":
        from app.modules.material.models import MaterialContainer

        row = await session.get(MaterialContainer, source_id)
        return row.container_code if row else None
    if source_type == "dispensed_container":
        from app.modules.material.models import DispensedContainer

        row = await session.get(DispensedContainer, source_id)
        return row.container_code if row else None
    if source_type == "package_node":
        from app.modules.packaging.models import PackageNode

        row = await session.get(PackageNode, source_id)
        return row.business_ref if row else None
    if source_type == "device_assembly_record":
        from app.modules.ddcp.models import DeviceAssemblyRecord

        row = await session.get(DeviceAssemblyRecord, source_id)
        return f"Unit {row.unit_identifier}" if row and row.unit_identifier else None
    if source_type == "process_cycle":
        from app.modules.equipment.sterilization_models import ProcessCycle

        row = await session.get(ProcessCycle, source_id)
        return f"{row.process_type} cycle {row.controller_cycle_id}" if row and row.controller_cycle_id else None
    return None


async def resolve_qc_result_samples(session: AsyncSession, result_ids: set) -> dict[str, str]:
    """Resolves `qc_result.id` to the `sample_number` of the sample it was run on -- `qc_result` has no
    direct sample reference of its own, so this is a 2-hop join (`test_order_id` -> `QcTestOrder.
    sample_id` -> `QcSample.sample_number`). Same join `qc/router.py::_resolve_qc_result_samples`
    already does for OOS/OOT detail views -- centralized here so `resolve_source_label` (NCR's
    `source_type == "qc_result"`) can reuse it without importing the qc router."""
    ids = {str(r) for r in result_ids if r}
    if not ids:
        return {}
    from app.modules.qc.models import QcResult, QcSample, QcTestOrder

    rows = (
        await session.execute(
            select(QcResult.id, QcSample.sample_number)
            .join(QcTestOrder, QcTestOrder.id == QcResult.test_order_id)
            .join(QcSample, QcSample.id == QcTestOrder.sample_id)
            .where(QcResult.id.in_(ids))
        )
    ).all()
    return {str(row.id): row.sample_number for row in rows}


def filtered(
    model: Any,
    params: PageParams,
    *,
    search_column: Column,
    site_id: uuid.UUID | list[uuid.UUID] | None = None,
    state: str | None = None,
    state_column: Column | None = None,
) -> Select:
    """Base statement for a QMS list endpoint: site scope, optional workflow state, free-text search.

    `site_id` is normally a list resolved by `policy.service.resolve_site_scope` (the actor's own
    assigned site, or all sites they hold the relevant `view` permission at) -- a bare scalar is
    still accepted for direct/internal callers. `None` applies no site filter at all and must never
    be reached from a caller-facing list endpoint (that is exactly the cross-site leak SG-213-class
    gap this signature closes).

    Returns a statement carrying filters only -- no order_by/limit/offset -- which is exactly what
    `paginate()` requires of its `base_stmt`.
    """
    from sqlalchemy import select

    stmt = select(model)
    if isinstance(site_id, list):
        stmt = stmt.where(model.site_id.in_(site_id))
    elif site_id is not None:
        stmt = stmt.where(model.site_id == site_id)
    if state:
        column = state_column if state_column is not None else model.state
        stmt = stmt.where(column == state)
    if params.q:
        stmt = stmt.where(search_column.ilike(f"%{params.q}%"))
    return stmt
