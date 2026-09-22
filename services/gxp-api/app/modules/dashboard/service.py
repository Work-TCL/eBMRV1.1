"""Client requirement #4 (Expiry / Retest / Important Date Reminders). A pure read-side aggregator over
dates already captured by their owning modules -- material lot expiry/retest (Document 19), equipment
calibration/maintenance/qualification due dates (Document 38), and supplier qualification expiry
(Document 18). Advisory only (AG-14): this never blocks or gates anything by itself. The "already expired"
case is already hard-enforced elsewhere (e.g. the FEFO eligibility gate's expiry/retest-overdue exclusion,
MAT-013); this covers the "coming due" case, which nothing surfaced proactively before this pass.

Deliberately reads three other modules' ORM models directly rather than calling each module's own
query interface -- same precedent as `batch_execution/record_service.py::build_batch_record()`, a
read-only cross-module reporting aggregator, not a write path (AG-05/AG-06 govern mutations, not reads;
AG-11 permits a rebuildable, non-authoritative read view like this one to cross module boundaries freely).

Not scoped by site_id, same simplification `GET /sites` already makes for a cross-cutting summary any
signed-in user should see -- a real per-site/per-role scoping decision is left for later if requested.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equipment.models import EquipmentAsset
from app.modules.material.models import Material, MaterialLot
from app.modules.supplier_quality.models import Supplier, SupplierQualification, SupplierSite

# MaterialLot states that mean the lot is no longer in active use -- a reminder about an already-consumed,
# already-rejected or already-fully-expired lot would be noise, not a heads-up (the FEFO gate already
# blocks these; nothing left to warn anyone about).
_LOT_TERMINAL_STATES = ("consumed", "rejected", "expired")


async def list_upcoming_reminders(session: AsyncSession, *, within_days: int = 30) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    horizon = today + timedelta(days=within_days)
    reminders: list[dict] = []

    lot_rows = (
        await session.execute(
            select(MaterialLot, Material.code, Material.name)
            .join(Material, Material.id == MaterialLot.material_id)
            .where(MaterialLot.status.notin_(_LOT_TERMINAL_STATES))
        )
    ).all()
    for lot, material_code, material_name in lot_rows:
        for field, category in (("expiry_date", "material_lot_expiry"), ("retest_date", "material_lot_retest")):
            due = getattr(lot, field)
            if due is not None and due <= horizon:
                reminders.append(
                    {
                        "category": category,
                        "entity_type": "material_lot",
                        "entity_id": str(lot.id),
                        "site_id": str(lot.site_id),
                        "label": f"{material_code} — {material_name} (lot {lot.internal_lot})",
                        "due_date": due.isoformat(),
                        "days_remaining": (due - today).days,
                    }
                )

    asset_rows = (
        (await session.execute(select(EquipmentAsset).where(EquipmentAsset.state != "RETIRED")))
        .scalars()
        .all()
    )
    for asset in asset_rows:
        for field, category in (
            ("next_calibration_due_date", "equipment_calibration"),
            ("next_maintenance_due_date", "equipment_maintenance"),
            ("qualification_expiry_date", "equipment_qualification"),
        ):
            due = getattr(asset, field)
            if due is not None and due <= horizon:
                reminders.append(
                    {
                        "category": category,
                        "entity_type": "equipment_asset",
                        "entity_id": str(asset.id),
                        "site_id": str(asset.site_id),
                        "label": asset.equipment_code,
                        "due_date": due.isoformat(),
                        "days_remaining": (due - today).days,
                    }
                )

    qual_rows = (
        await session.execute(
            select(SupplierQualification, Supplier.legal_name)
            .join(SupplierSite, SupplierSite.id == SupplierQualification.supplier_site_id)
            .join(Supplier, Supplier.id == SupplierSite.supplier_id)
            .where(SupplierQualification.status.in_(("approved", "conditional")))
        )
    ).all()
    for qual, supplier_name in qual_rows:
        if qual.expires_at is None:
            continue
        due = qual.expires_at.date() if isinstance(qual.expires_at, datetime) else qual.expires_at
        if due <= horizon:
            reminders.append(
                {
                    "category": "supplier_qualification",
                    "entity_type": "supplier_qualification",
                    "entity_id": str(qual.id),
                    "site_id": None,
                    "label": supplier_name,
                    "due_date": due.isoformat(),
                    "days_remaining": (due - today).days,
                }
            )

    reminders.sort(key=lambda r: r["due_date"])
    return reminders
