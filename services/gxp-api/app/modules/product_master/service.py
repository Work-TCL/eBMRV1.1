"""Document 09 — read-side lookups and the two structural gates (PRD-FR-031 completeness, PRD-FR-032
profile admission) shared by commands.py and the router.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equipment import aseptic_commands as aseptic_service
from app.modules.equipment.aseptic_models import AsepticProfileVersion
from app.modules.product_master.models import (
    STERILE_REQUIRED_PROFILES,
    ProductConstituent,
    ProductVersion,
)
from app.mutation.errors import NotFoundError

# PRD-FR-009: the only manufacturing profiles this pass recognizes as controlled/supported. Anything else
# is an unsupported specialist context and fails closed at draft-release time (PRD-FR-032) rather than
# silently accepting a profile no rule or checklist actually understands.
SUPPORTED_MANUFACTURING_PROFILES = {
    "injectable_ddcp",
    "inhalation_ddcp",
    "drug_eluting_device",
    "device",
    "pharma",
}


async def get_version(session: AsyncSession, product_version_id: uuid.UUID) -> ProductVersion:
    version = await session.get(ProductVersion, product_version_id)
    if version is None:
        raise NotFoundError("Product version not found")
    return version


async def list_versions_for_business_id(session: AsyncSession, product_business_id: str) -> list[ProductVersion]:
    return (
        (
            await session.execute(
                select(ProductVersion)
                .where(ProductVersion.product_business_id == product_business_id)
                .order_by(ProductVersion.version_no)
            )
        )
        .scalars()
        .all()
    )


async def get_constituents(session: AsyncSession, product_version_id: uuid.UUID) -> list[ProductConstituent]:
    return (
        (
            await session.execute(
                select(ProductConstituent)
                .where(ProductConstituent.product_version_id == product_version_id)
                .order_by(ProductConstituent.sequence_no)
            )
        )
        .scalars()
        .all()
    )


async def list_product_business_ids(session: AsyncSession) -> list[ProductVersion]:
    """Read-only picker data for any field that references *another* Product Master record by its own
    Business ID (e.g. this module's own Constituent editor — PRD-FR-004/006's "meal kit" model: the drug
    substance and the device component are themselves Product Master versions). Document 09 declares no
    "list all products" operation in its own API list (docs/generated/06_API_CATALOGUE.yaml) — same
    SG-081 read-side precedent as `GET /inventory/v1/warehouse-locations` and
    `GET /material-lots/{id}/containers`: a plain read-only GET listing does not conflict with any future
    write/CRUD contract, it only replaces free-text Business-ID entry with a real picker. Returns one row
    per distinct product_business_id — the highest version_no for that id — so callers get a name and
    lifecycle_state to show without a second round trip; the caller still uses
    `GET /products/v1/{business_id}/versions` to resolve the *specific* version to reference."""
    rows = (
        (
            await session.execute(
                select(ProductVersion).order_by(ProductVersion.product_business_id, ProductVersion.version_no.desc())
            )
        )
        .scalars()
        .all()
    )
    latest: dict[str, ProductVersion] = {}
    for row in rows:
        latest.setdefault(row.product_business_id, row)
    return sorted(latest.values(), key=lambda v: v.product_business_id)


async def list_sterile_profiles(session: AsyncSession, site_id: uuid.UUID) -> list[AsepticProfileVersion]:
    """Real picker data for the draft/edit forms' Sterile process profile ID field — thin wrapper around
    `aseptic_commands.list_released_profile_versions`, the equipment module's own cross-module query
    interface (AG-02/AG-05) for Document 40's `equipment.aseptic_profile_versions` registry, restricted to
    this site's RELEASED rows. Backs the PRD-FR-010 existence/state check
    `commands.py::_validate_sterile_profile` enforces at draft create/update."""
    return await aseptic_service.list_released_profile_versions(session, site_id)


def validate_completeness(version: ProductVersion, constituents: list[ProductConstituent]) -> list[str]:
    """PRD-FR-031: structural completeness only (fields required by the version's own declared profile) —
    never a regulatory judgment about whether the profile itself is correct for the product.
    Returns a list of human-readable findings; empty means complete.
    """
    findings: list[str] = []

    if version.manufacturing_profile_code not in SUPPORTED_MANUFACTURING_PROFILES:
        findings.append(
            f"manufacturing_profile_code '{version.manufacturing_profile_code}' is not a supported "
            "profile (PRD-FR-032 profile admission gate)"
        )
    if version.manufacturing_profile_code in STERILE_REQUIRED_PROFILES and version.sterile_profile_id is None:
        findings.append("sterile_profile_id is required for this manufacturing profile (PRD-FR-010)")
    if version.udi_applicable and not version.device_model_code:
        findings.append("device_model_code is required when udi_applicable is set (PRD-FR-012)")
    if version.combination_product_type and not constituents:
        findings.append("a combination product must declare at least one constituent (PRD-FR-004/PRD-FR-006)")

    return findings


def check_issue_eligibility(version: ProductVersion, findings: list[str]) -> dict:
    """PRD-FR-032 issue-eligibility check. site_admission is always reported not_implemented — see
    SG-043 (product_site_admission has no DDL-ready schema in the source baseline this pass)."""
    lifecycle_ok = version.lifecycle_state == "released"
    return {
        "eligible": lifecycle_ok and not findings,
        "checks": {
            "lifecycle_state": version.lifecycle_state,
            "lifecycle_ok": lifecycle_ok,
            "completeness_findings": findings,
            "site_admission": "not_implemented",
        },
    }
