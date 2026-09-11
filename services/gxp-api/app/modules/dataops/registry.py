"""Document 69 (SPEC-DATA-001) ownership-registry library.

Pure functions -- no request handlers. Used by the read router, the ownership-lint test
(`DATA-FR-030`), the data-dictionary generator (`DATA-FR-027`) and any repository/mutation layer that
wants to assert it owns what it is about to write (`assert_authoritative_write_allowed`, DATA-FR-025).

`OWNERSHIP_SEED` is transcribed from `ebmr-edhr/docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md`
(AG-05: one authoritative owner/store per regulated entity). It is *not* guessed -- every row's
authoritative store/service is what that matrix already records. `scripts/seed.py` and
`tests/conftest.py` insert exactly these rows into `dataops.data_ownership_registry`; the registry is
then the queryable, superseding source and the seed list is the change-controlled baseline.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dataops.models import DataOwnershipRegistry
from app.mutation.errors import DataOwnerUnknownError, ForbiddenDataOwnerWriteError

# GxP Core service that owns the largest share of regulated entities.
_GXP = "gxp-api"

# Every entry below: authoritative store + owning service exactly as 05_DATABASE_OWNERSHIP_MATRIX.md
# records it. `projection_targets` is the tiers the matrix's "Projection allowed" column permits
# ("Frappe read model" -> FRAPPE_MARIADB). `classification` per DATA-FR-021. Retention/encryption
# profile ids are left None here -- Document 108 numeric retention is the open gap SG-005; the registry
# carries the *reference*, populated per deployment, never a guessed duration.
#
# This is a representative, change-controlled baseline covering every storage tier and every bounded
# context, not yet an exhaustive per-table enumeration of all ~275 matrix rows (see the module's
# known-limitation note in the completion report). Adding the remaining rows is data entry against the
# same matrix, not a regulated-behaviour decision.
OWNERSHIP_SEED: list[dict] = [
    # ---- GxP Core kernel (SPEC-GXP-001/002/003/004/006, SPEC-IAM-001) -----------------------------
    {"entity_type": "command_receipt", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-GXP-001)"},
    {"entity_type": "outbox_event", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": [], "tenant_scoped": False, "site_scoped": False, "classification": "GXP",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-GXP-001 / SPEC-DATA-005: PG outbox authoritative, NATS transport)"},
    {"entity_type": "audit_event", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-GXP-003)"},
    {"entity_type": "signature", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-GXP-002)"},
    {"entity_type": "signature_challenge", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": [], "tenant_scoped": False, "site_scoped": True, "classification": "GXP",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-GXP-002)"},
    {"entity_type": "vault_object", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-GXP-004)"},
    {"entity_type": "rule_definition", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-GXP-006)"},
    {"entity_type": "iam_user", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "PII", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-IAM-001)"},
    {"entity_type": "iam_role_assignment", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-IAM-001)"},
    {"entity_type": "iam_qualification", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-IAM-001)"},
    # ---- eBMR / eDHR execution (SPEC-EBMR-000..008) ----------------------------------------------
    {"entity_type": "product_version", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH"], "tenant_scoped": False, "site_scoped": False,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-000)"},
    {"entity_type": "recipe_version", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH"], "tenant_scoped": False, "site_scoped": False,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-001)"},
    {"entity_type": "gxp_batch", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH", "ANALYTICS"], "tenant_scoped": False,
     "site_scoped": True, "classification": "GXP",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-002)"},
    {"entity_type": "gxp_batch_step", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-002)"},
    {"entity_type": "device_unit", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-003)"},
    {"entity_type": "genealogy_node", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-004)"},
    {"entity_type": "qa_review_package", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-005)"},
    {"entity_type": "release_decision", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-006)"},
    {"entity_type": "packaging_run", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-007)"},
    {"entity_type": "manufacturing_calculation", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EBMR-008)"},
    # ---- Materials / QC (SPEC-MAT-001..002D, SPEC-QC-001/003) ------------------------------------
    {"entity_type": "material_lot", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH", "ANALYTICS"], "tenant_scoped": False,
     "site_scoped": True, "classification": "GXP",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-MAT-002A)"},
    {"entity_type": "supplier", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-MAT-001)"},
    {"entity_type": "dispensing_order", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-MAT-002C)"},
    {"entity_type": "qc_result", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-QC-001)"},
    {"entity_type": "oos_record", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-QC-003)"},
    # ---- QMS (SPEC-QMS-001..012) ---------------------------------------------------------------
    {"entity_type": "deviation_record", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH", "ANALYTICS"], "tenant_scoped": False,
     "site_scoped": True, "classification": "GXP",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-QMS-001)"},
    {"entity_type": "capa_record", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH", "ANALYTICS"], "tenant_scoped": False,
     "site_scoped": True, "classification": "GXP",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-QMS-002)"},
    {"entity_type": "complaint_record", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "PII", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-QMS-009)"},
    {"entity_type": "controlled_document_version", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB", "SEARCH"], "tenant_scoped": False, "site_scoped": False,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-QMS-006)"},
    # ---- Equipment / sterile (SPEC-EQP-001..005) ----------------------------------------------
    {"entity_type": "equipment_asset", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EQP-001)"},
    {"entity_type": "process_cycle", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-EQP-005)"},
    # ---- Security (SPEC-SEC-001..008) --------------------------------------------------------
    {"entity_type": "security_incident", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "SECURITY", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-SEC-007)"},
    {"entity_type": "vulnerability_record", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "SECURITY", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-SEC-008)"},
    {"entity_type": "secret_metadata", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": [], "tenant_scoped": False, "site_scoped": False, "classification": "SECURITY",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-SEC-005; secret *reference* only, value in external secret manager)"},
    # ---- Postmarket / regulatory (SPEC-PM-001..003) -----------------------------------------
    {"entity_type": "safety_case", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "PII", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-PM-001)"},
    {"entity_type": "regulatory_report", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "GXP", "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-PM-002)"},
    # ---- Non-PostgreSQL storage tiers ------------------------------------------------------
    {"entity_type": "evidence_object", "authoritative_service": _GXP, "authoritative_store": "OBJECT",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-DATA-004: object store WORM authoritative, PG holds metadata/hash)"},
    {"entity_type": "edge_observation", "authoritative_service": _GXP, "authoritative_store": "HISTORIAN",
     "projection_targets": ["ANALYTICS"], "tenant_scoped": False, "site_scoped": True,
     "classification": "OPERATIONAL",
     "source_reference": "Document 69 DATA-FR-010: high-frequency telemetry -> historian/time-series; GxP holds intended-use evidence refs"},
    {"entity_type": "erp_external_mapping", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": True,
     "classification": "GXP",
     "source_reference": "05_DATABASE_OWNERSHIP_MATRIX.md (SPEC-ERP-001): internal mapping is PG-owned; the external record stays authoritative in the ERP (DATA-FR-015)"},
    {"entity_type": "frappe_ui_configuration", "authoritative_service": "ebmr_frappe", "authoritative_store": "MARIADB",
     "projection_targets": [], "tenant_scoped": False, "site_scoped": False, "classification": "CONFIG",
     "source_reference": "Document 69 DATA-FR-003: Frappe/MariaDB owns UI/application metadata, DocTypes and non-authoritative workflow conveniences"},
    # ---- This module's own entities (SPEC-DATA-001) --------------------------------------
    {"entity_type": "data_ownership_registry", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "CONFIG", "source_reference": "Document 69 # 6"},
    {"entity_type": "projection_checkpoint", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "OPERATIONAL", "source_reference": "Document 69 # 6"},
    {"entity_type": "migration_batch", "authoritative_service": _GXP, "authoritative_store": "POSTGRES",
     "projection_targets": ["FRAPPE_MARIADB"], "tenant_scoped": False, "site_scoped": False,
     "classification": "GXP", "source_reference": "Document 69 # 6"},
]


async def resolve_data_owner(session: AsyncSession, entity_type: str) -> DataOwnershipRegistry:
    """`resolveDataOwner()` -- DATA-FR-001. Returns the EFFECTIVE registry row for `entity_type`.
    Fail-closed: an entity type with no EFFECTIVE row raises `DataOwnerUnknownError`
    (`DATA_OWNER_UNKNOWN`) rather than a default/guess (AG-15)."""
    row = (
        await session.execute(
            select(DataOwnershipRegistry).where(
                DataOwnershipRegistry.entity_type == entity_type,
                DataOwnershipRegistry.state == "EFFECTIVE",
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise DataOwnerUnknownError(
            "No authoritative owner is declared for this entity type", entity_type=entity_type
        )
    return row


async def assert_authoritative_write_allowed(
    session: AsyncSession, *, service_identity: str, entity_type: str, operation: str
) -> DataOwnershipRegistry:
    """`assertAuthoritativeWriteAllowed()` -- DATA-FR-025 / DATA-FR-030. Confirms `service_identity`
    is the declared `authoritative_service` for `entity_type`. Any other service attempting a write
    (INSERT/UPDATE/DELETE/DDL) gets `ForbiddenDataOwnerWriteError` (`FORBIDDEN_DATA_OWNER_WRITE`).
    Read/query operations are always allowed by contract and are not gated here."""
    owner = await resolve_data_owner(session, entity_type)
    if operation.upper() in ("READ", "SELECT", "QUERY"):
        return owner
    if service_identity != owner.authoritative_service:
        raise ForbiddenDataOwnerWriteError(
            "Service is not the authoritative owner of this entity",
            entity_type=entity_type,
            requested_by=service_identity,
            authoritative_service=owner.authoritative_service,
            operation=operation,
        )
    return owner


async def build_data_dictionary(session: AsyncSession) -> dict:
    """`DATA-FR-027` -- machine-readable entity / owner / store / classification / retention-reference
    / projection dictionary generated from the live registry. This is the payload behind
    `GET /platform/v1/data-dictionary`."""
    rows = (
        await session.execute(
            select(DataOwnershipRegistry)
            .where(DataOwnershipRegistry.state == "EFFECTIVE")
            .order_by(DataOwnershipRegistry.entity_type)
        )
    ).scalars().all()
    entries = [
        {
            "entity_type": r.entity_type,
            "authoritative_service": r.authoritative_service,
            "authoritative_store": r.authoritative_store,
            "projection_targets": r.projection_targets,
            "tenant_scoped": r.tenant_scoped,
            "site_scoped": r.site_scoped,
            "classification": r.classification,
            "retention_policy_id": str(r.retention_policy_id) if r.retention_policy_id else None,
            "encryption_profile_id": str(r.encryption_profile_id) if r.encryption_profile_id else None,
            "source_reference": r.source_reference,
            "version": r.version,
        }
        for r in rows
    ]
    by_store: dict[str, int] = {}
    for e in entries:
        by_store[e["authoritative_store"]] = by_store.get(e["authoritative_store"], 0) + 1
    return {
        "generated_from": "dataops.data_ownership_registry",
        "entity_count": len(entries),
        "by_authoritative_store": by_store,
        "entries": entries,
    }


def lint_ownership_seed() -> list[str]:
    """`DATA-FR-030` static guard, callable from CI / a test without a database: every seed row has a
    single declared authoritative store from the allowed set, a service owner, and only permitted
    projection tiers. Returns a list of violation strings (empty == clean)."""
    from app.modules.dataops.models import AUTHORITATIVE_STORES, DATA_CLASSIFICATIONS, PROJECTION_TIERS

    violations: list[str] = []
    seen: set[str] = set()
    for row in OWNERSHIP_SEED:
        et = row["entity_type"]
        if et in seen:
            violations.append(f"{et}: duplicate registry row (would be a dual master)")
        seen.add(et)
        if row["authoritative_store"] not in AUTHORITATIVE_STORES:
            violations.append(f"{et}: authoritative_store {row['authoritative_store']!r} not in {AUTHORITATIVE_STORES}")
        if not row.get("authoritative_service"):
            violations.append(f"{et}: no authoritative_service declared")
        if row.get("classification") and row["classification"] not in DATA_CLASSIFICATIONS:
            violations.append(f"{et}: classification {row['classification']!r} not in {DATA_CLASSIFICATIONS}")
        for tier in row.get("projection_targets", []):
            if tier not in PROJECTION_TIERS:
                violations.append(f"{et}: projection tier {tier!r} not in {PROJECTION_TIERS}")
    return violations
