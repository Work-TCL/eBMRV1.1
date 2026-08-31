"""MDS-FR-005/008/024 — vendor raw-record normalization and internal-entity matching for the automated
master-data sync pipeline (`sync.py`).

Field extraction here is deliberately the *shared* identity/name/active-flag surface each adapter's real
documented `fetch_changes()` resource already returns (Item/Supplier for ERPNext, A_Product/A_Supplier for
SAP, items/suppliers for Oracle Fusion, ReleasedProducts/VendorsV2 for Dynamics 365) — deep per-vendor
field mapping (custom fields, $batch, BAPI/RFC) stays the separate, out-of-scope item SG-126 already
records; this module only needs enough of each vendor's real shape to identify a record and detect an
explicit vendor-side deactivation signal.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.material.models import Material
from app.modules.supplier_quality.models import Supplier

# MDS-FR-008: no numeric name-similarity threshold is declared anywhere in the baseline -- same class of
# gap as SG-123/SG-124. 0.72 is a conservative, documented, fully-code-level-overridable default; it only
# ever changes whether a *candidate* is proposed, never whether one auto-activates (a match_internal_entity
# result always still requires the existing human approve_mapping() call -- SG-124's "never silently
# accept" posture applied here to identity matching instead of reconciliation tolerance).
FUZZY_MATCH_MIN_SCORE = 0.72


@dataclass(frozen=True)
class NormalizedMasterRecord:
    external_id: str
    external_code: str | None
    display_name: str | None
    is_active: bool | None  # None == this vendor/entity_type combination exposes no deactivation signal
    raw: dict[str, Any]


# One row per (vendor, entity_type) this pass's adapters actually implement (erpnext.py/sap.py/
# oracle_fusion.py/dynamics365.py _SYNC_* tables) -- "id"/"code" name the field holding the vendor's
# primary identifier, "display_name" the human-readable name, and exactly one of "disabled"/"status"/
# "blocked" the field (if any) carrying a real deactivation signal for that vendor's resource.
_FIELD_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("ERPNEXT", "MATERIAL"): {"id": "name", "code": "item_code", "display_name": "item_name", "disabled": "disabled"},
    ("ERPNEXT", "SUPPLIER"): {"id": "name", "code": "supplier_code", "display_name": "supplier_name", "disabled": "disabled"},
    ("ERPNEXT", "WAREHOUSE"): {"id": "name", "code": "name", "display_name": "warehouse_name", "disabled": "disabled"},
    ("ERPNEXT", "UOM"): {"id": "name", "code": "name", "display_name": "name"},
    ("SAP_S4HANA", "MATERIAL"): {"id": "Product", "code": "Product", "display_name": "ProductDescription"},
    ("SAP_S4HANA", "SUPPLIER"): {"id": "Supplier", "code": "Supplier", "display_name": "SupplierName"},
    ("ORACLE_FUSION", "MATERIAL"): {"id": "ItemNumber", "code": "ItemNumber", "display_name": "Description", "status": "ItemStatus"},
    ("ORACLE_FUSION", "SUPPLIER"): {"id": "Supplier", "code": "Supplier", "display_name": "SupplierName", "status": "Status"},
    ("DYNAMICS_365", "MATERIAL"): {"id": "ItemNumber", "code": "ItemNumber", "display_name": "ProductName"},
    ("DYNAMICS_365", "SUPPLIER"): {"id": "VendorAccountNumber", "code": "VendorAccountNumber", "display_name": "VendorOrganizationName", "blocked": "Blocked"},
}
_GENERIC_ID_KEYS = ("external_id", "id", "code")
_GENERIC_CODE_KEYS = ("code", "external_id", "id")
_GENERIC_NAME_KEYS = ("display_name", "name")


def normalize_master_record(vendor: str, entity_type: str, raw: dict[str, Any]) -> NormalizedMasterRecord | None:
    """Extracts identity/name/active-flag from one raw `fetch_changes()` record. Returns `None` when the
    record carries no recognizable identifier -- surfaced by the caller as a counted, auditable
    "skipped_unrecognized" outcome, never silently dropped (AG-15)."""

    fields = _FIELD_MAP.get((vendor, entity_type))
    if fields is None:
        return _normalize_generic(raw)

    external_id = raw.get(fields["id"])
    if external_id in (None, ""):
        return None
    external_code = raw.get(fields.get("code", fields["id"]), external_id)
    display_name = raw.get(fields["display_name"]) if fields.get("display_name") else None
    return NormalizedMasterRecord(
        external_id=str(external_id),
        external_code=str(external_code) if external_code not in (None, "") else None,
        display_name=display_name,
        is_active=_resolve_active_flag(raw, fields),
        raw=raw,
    )


def _resolve_active_flag(raw: dict[str, Any], fields: dict[str, str]) -> bool | None:
    if "disabled" in fields and fields["disabled"] in raw:
        value = raw.get(fields["disabled"])
        return not bool(value)
    if "blocked" in fields and fields["blocked"] in raw:
        return not bool(raw.get(fields["blocked"]))
    if "status" in fields and fields["status"] in raw:
        status_value = str(raw.get(fields["status"]) or "").strip().upper()
        return status_value not in ("INACTIVE", "OBSOLETE", "DISCONTINUED", "BLOCKED")
    return None


def _normalize_generic(raw: dict[str, Any]) -> NormalizedMasterRecord | None:
    def first(keys: tuple[str, ...]) -> Any:
        for key in keys:
            if raw.get(key) not in (None, ""):
                return raw[key]
        return None

    external_id = first(_GENERIC_ID_KEYS)
    if external_id in (None, ""):
        return None
    external_code = first(_GENERIC_CODE_KEYS) or external_id
    display_name = first(_GENERIC_NAME_KEYS)
    active_raw = raw.get("active", raw.get("is_active"))
    return NormalizedMasterRecord(
        external_id=str(external_id), external_code=str(external_code), display_name=display_name,
        is_active=bool(active_raw) if active_raw is not None else None, raw=raw,
    )


@dataclass(frozen=True)
class MatchCandidate:
    internal_id: UUID
    internal_code: str
    display_name: str
    score: float
    match_method: str  # EXPLICIT_ID | FUZZY_PROPOSED -- app.modules.erp.models.MATCH_METHODS


async def match_internal_entity(
    session: AsyncSession, *, entity_type: str, site_id: UUID | None, external_code: str | None, display_name: str | None,
) -> MatchCandidate | None:
    """MDS-FR-008: "Prefer explicit external IDs; name/fuzzy match only proposes mapping for human
    review." An exact internal-code match is returned as `EXPLICIT_ID`; otherwise the best name-similarity
    candidate at or above `FUZZY_MATCH_MIN_SCORE` is returned as `FUZZY_PROPOSED`. Either way this function
    only ever returns a *candidate* for `propose_mapping()` -- it never creates or activates anything
    itself, so a wrong match is always caught by the existing human `approve_mapping()` step."""

    if entity_type in ("MATERIAL", "PRODUCT"):
        stmt = select(Material.id, Material.code, Material.name)
        if site_id is not None:
            stmt = stmt.where(Material.site_id == site_id)
        rows = (await session.execute(stmt)).all()
    elif entity_type == "SUPPLIER":
        rows = (await session.execute(select(Supplier.id, Supplier.supplier_code, Supplier.legal_name))).all()
    else:
        # MDS-FR-008/SG-126: no internal master-data table exists yet for this entity_type (e.g.
        # WAREHOUSE/UOM/LOCATION) -- identity matching for those stays a manual `proposeMapping()` call.
        return None

    if external_code:
        needle = external_code.strip().lower()
        for internal_id, code, name in rows:
            if code and code.strip().lower() == needle:
                return MatchCandidate(internal_id=internal_id, internal_code=code, display_name=name, score=1.0, match_method="EXPLICIT_ID")

    if not display_name:
        return None
    needle_name = display_name.strip().lower()
    best: MatchCandidate | None = None
    for internal_id, code, name in rows:
        score = difflib.SequenceMatcher(None, needle_name, (name or "").strip().lower()).ratio()
        if score >= FUZZY_MATCH_MIN_SCORE and (best is None or score > best.score):
            best = MatchCandidate(internal_id=internal_id, internal_code=code, display_name=name, score=score, match_method="FUZZY_PROPOSED")
    return best
