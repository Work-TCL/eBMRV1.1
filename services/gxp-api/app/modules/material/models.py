import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# MAT-009: automatic quarantine at receipt. MAT-011: QC disposition states.
# Document 19 (RCV-FR) extends this with the intermediate states from its own state diagram
# (sampling/testing/qc_disposition_pending/retest_due); the existing values and the existing
# `/material-lots/{id}/disposition` endpoint's `status == "quarantine"` precondition are unchanged.
LOT_STATES = (
    "quarantine",
    "sampling",
    "testing",
    "qc_disposition_pending",
    "retest_due",
    "released",
    "rejected",
    "consumed",
    "expired",
)
# States from which release_material_lot/reject_material_lot (Document 19 RCV-FR-026/027) may act --
# any pre-disposition state, not only "quarantine" (that narrower precondition stays on the legacy
# generic /disposition endpoint only).
PRE_DISPOSITION_LOT_STATES = ("quarantine", "sampling", "testing", "qc_disposition_pending", "retest_due")

RECEIPT_STATES = ("received", "examined", "discrepancy_hold")
SAMPLING_ORDER_STATES = ("requested", "collected", "cancelled")
QUALITY_DISPOSITION_DECISIONS = ("released", "rejected", "retest_due")

# Document 20 (SPEC-MAT-002B) section 5 -- captured, not DB-enumerated: no controlled code list exists
# beyond this prose list (same treatment as MaterialReceipt.discrepancy_type). SPILL/APPROVED_LOSS added
# in the Document 22 (SPEC-MAT-002D) session for CON-FR-009/010 -- this tuple is documentation only, never
# referenced as a DB CHECK constraint or validated against anywhere in commands.py.
INVENTORY_TRANSACTION_TYPES = (
    "RECEIPT", "TRANSFER", "RESERVE", "UNRESERVE", "ISSUE", "DISPENSE", "CONSUME", "RETURN", "SAMPLE",
    "REJECT", "DESTROY", "ADJUST_POSITIVE", "ADJUST_NEGATIVE", "INTERSITE_SHIP", "INTERSITE_RECEIVE",
    "SPILL", "APPROVED_LOSS",
)
CONTAINER_STATUSES = ("active", "split", "merged", "destroyed")
RESERVATION_STATES = ("active", "released", "consumed", "expired", "cancelled")


class Material(Base):
    """Raw material / component master (MAT-001-adjacent — the regulated identity a lot is received
    against). Mirrors ebmr.products in shape deliberately: same kind of master-data aggregate."""

    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("site_id", "code"), {"schema": "materials"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # Document 21 (SPEC-MAT-002C) DSP-FR-018: material half of "independent verification required where
    # the material or step is flagged critical" -- the step half has no data source anywhere in the
    # actually-used BatchStep -> ebmr.recipe_steps path (SG-090); conditional-independence enforcement
    # itself is deferred, this flag is captured for a future pass.
    critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialLot(Base):
    """One received lot/container. Authoritative quality-status aggregate for MAT-009/011/013."""

    __tablename__ = "material_lots"
    __table_args__ = (UniqueConstraint("internal_lot"), {"schema": "materials"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.materials.id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    supplier_lot: Mapped[str | None] = mapped_column(String(100))
    manufacturer_lot: Mapped[str | None] = mapped_column(String(100))
    internal_lot: Mapped[str] = mapped_column(String(100), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="quarantine")
    expiry_date: Mapped[date | None] = mapped_column()
    retest_date: Mapped[date | None] = mapped_column()
    received_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    version: Mapped[int] = mapped_column(nullable=False, default=1)

    # Document 19 (SPEC-MAT-002A) `material_lot` extensions. `material_spec_version_id` carries no FK
    # constraint -- no "material specification version" entity exists anywhere in this codebase (SG-057);
    # same unenforced-reference treatment as `qc.QcTestDefinition.method_version`.
    material_spec_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    receipt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_receipts.id")
    )
    manufacture_date: Mapped[date | None] = mapped_column()
    released_at: Mapped[datetime | None] = mapped_column()
    release_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class MaterialLotDisposition(Base):
    """QC release/reject decision on a lot (MAT-011). Signed — same pattern as batch_reviews."""

    __tablename__ = "material_lot_dispositions"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # released | rejected
    reason: Mapped[str | None] = mapped_column(String(1000))
    signature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    disposed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    disposed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialIssue(Base):
    """Lot -> batch genealogy link (MAT-015/MAT-021 minimal form): which lot, how much, into which
    batch/step. This table *is* the batch's material genealogy trace for Phase 1."""

    __tablename__ = "material_issues"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    batch_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.batch_steps.id")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    issued_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialReceipt(Base):
    """Document 19 (SPEC-MAT-002A) `material_receipt` -- RCV-FR-001 (partial: no PO/transfer-expectation
    entity exists to load against, SG-057/058 -- `po_reference` stays a captured free-text field, not a
    validated lookup)/002/003/004/005/010/011/012/014/031. `examine_receipt` is the one command that
    reads/writes this row's exam and discrepancy fields and, on a clean examination, creates the
    `MaterialLot`/`MaterialContainer` rows below -- this row itself never becomes a quarantine/release
    aggregate; that stays `MaterialLot`'s job (AG-05, one authoritative owner per regulated entity)."""

    __tablename__ = "material_receipts"
    __table_args__ = (UniqueConstraint("site_id", "receipt_number"), {"schema": "materials"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(120), nullable=False)
    po_reference: Mapped[str | None] = mapped_column(String(160))
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.materials.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.supplier.id"))
    manufacturer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.supplier.id"))
    supplier_lot: Mapped[str | None] = mapped_column(String(200))
    manufacturer_lot: Mapped[str | None] = mapped_column(String(200))
    carrier_reference: Mapped[str | None] = mapped_column(String(160))
    received_gross_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    received_net_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    accepted_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    manufacture_date: Mapped[date | None] = mapped_column()
    expiry_date: Mapped[date | None] = mapped_column()
    retest_date: Mapped[date | None] = mapped_column()
    shipment_condition_status: Mapped[str | None] = mapped_column(String(40))
    coa_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    coa_document_hash: Mapped[str | None] = mapped_column(String(128))
    receiver_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="received")
    labeling_ok: Mapped[bool | None] = mapped_column(Boolean)
    damage_observed: Mapped[bool | None] = mapped_column(Boolean)
    seal_broken: Mapped[bool | None] = mapped_column(Boolean)
    contamination_observed: Mapped[bool | None] = mapped_column(Boolean)
    examination_notes: Mapped[str | None] = mapped_column(String(2000))
    examined_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    examined_at: Mapped[datetime | None] = mapped_column()
    # RCV-FR-004/031: mismatch/discrepancy creates a hold, never a silent remapping. discrepancy_type is
    # one of "identity_mismatch" | "source_not_approved" | "damaged" | "seal_broken" | "contamination" |
    # "quantity_variance" -- captured, not enumerated as a DB constraint (no controlled code list exists
    # in the source spec beyond prose).
    discrepancy_type: Mapped[str | None] = mapped_column(String(60))
    discrepancy_reason: Mapped[str | None] = mapped_column(String(2000))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialContainer(Base):
    """Document 19 `material_container` -- RCV-FR-009/016/017/019/030. `location_zone` is free text, not
    validated against a real location master -- Document 20 (SPEC-MAT-002B, warehouse/location) is not yet
    built in this codebase."""

    __tablename__ = "material_containers"
    __table_args__ = (UniqueConstraint("material_lot_id", "container_code"), {"schema": "materials"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    container_code: Mapped[str] = mapped_column(String(120), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    location_zone: Mapped[str | None] = mapped_column(String(160))
    # Container-level quality status override for partial disposition (RCV-FR-030); null means the
    # container inherits its lot's quality_status (MaterialLot.status).
    quality_status_override: Mapped[str | None] = mapped_column(String(40))
    sampled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    seal_status: Mapped[str] = mapped_column(String(40), nullable=False, default="intact")
    # Document 20 (SPEC-MAT-002B) INV-FR-023/024 split/merge provenance. A split/merged-away container is
    # retired (container_status set), never deleted -- AG-08 append-only-history discipline.
    parent_container_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_containers.id")
    )
    source_container_ids: Mapped[dict | None] = mapped_column(JSONB)
    container_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class WarehouseLocation(Base):
    """Document 20 (SPEC-MAT-002B) `warehouse_location` -- INV-FR-001/002. No CRUD API exists anywhere in
    Document 20's own 8-op API list (SG-081) -- master/reference data, seeded like `iam.Site`/
    `iam.Organization`, never created through the app. `environment_profile_id` carries no FK constraint
    -- no environment-profile entity exists anywhere in this codebase (same unenforced-reference treatment
    as `MaterialLot.material_spec_version_id`)."""

    __tablename__ = "warehouse_locations"
    __table_args__ = (
        UniqueConstraint("site_id", "warehouse_code", "location_code"),
        {"schema": "materials"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    warehouse_code: Mapped[str] = mapped_column(String(100), nullable=False)
    location_code: Mapped[str] = mapped_column(String(120), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    environment_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class InventoryTransaction(Base):
    """Document 20 `inventory_transaction` -- INV-FR-006/007/032, section 5/8. Immutable ledger: no
    command in this module ever UPDATEs or DELETEs a row here (AG-08); the database privilege enforces it
    (migration 0028 grants SELECT/INSERT/TRUNCATE only, no UPDATE). `quantity` uses the spec's own explicit
    numeric(24,8) for this table family -- deliberately not this module's usual Numeric(18,6), which stays
    on the pre-existing MaterialLot/MaterialContainer quantity columns Document 18/19 already defined.
    `actor_id` is the spec's own declared varchar(255) polymorphic-actor field (mirrors
    `write_audit_event`'s actor_type/actor_id pair), not a `iam.users` FK."""

    __tablename__ = "inventory_transactions"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    container_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_containers.id")
    )
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    uom: Mapped[str] = mapped_column(String(40), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    from_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.warehouse_locations.id")
    )
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.warehouse_locations.id")
    )
    reference_type: Mapped[str | None] = mapped_column(String(60))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False, default="human")
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryBalanceProjection(Base):
    """Document 20 `inventory_balance_projection` -- INV-FR-003/004/007, section 2/8/10. Despite the name,
    this is Document 20's own transactionally-maintained aggregate (section 8: "balance/reservation cannot
    exceed available under transactional lock/version"), written in the *same* PostgreSQL transaction as
    the ledger row that changes it -- not an AG-11 rebuildable read-model despite the naming echo."""

    __tablename__ = "inventory_balance_projections"
    __table_args__ = (
        UniqueConstraint("material_lot_id", "container_id", "location_id"),
        {"schema": "materials"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    container_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_containers.id")
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.warehouse_locations.id"), nullable=False
    )
    on_hand: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal("0"))
    reserved: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal("0"))
    available: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal("0"))
    last_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.inventory_transactions.id")
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class InventoryReservation(Base):
    """Document 20 `inventory_reservation` -- INV-FR-010/011. Phase-1 scope: batch material requirement
    only -- the spec's prose "order" has no order entity anywhere in this codebase (same scope-narrowing
    precedent as every prior document). The signed `release` action (Document 106 row 46) is the only
    Document 20 signature -- see `release_inventory_reservation`."""

    __tablename__ = "inventory_reservations"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.materials.id"), nullable=False
    )
    material_lot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id")
    )
    container_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_containers.id")
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.warehouse_locations.id")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    expiry_at: Mapped[datetime | None] = mapped_column()
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    released_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    released_at: Mapped[datetime | None] = mapped_column()
    release_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SamplingOrder(Base):
    """Document 19 `sampling_order` -- RCV-FR-018/019/020/021/022. Materials-module-owned request/
    chain-of-custody record; the actual test evidence lives in `qc.QcSample`/`QcTestOrder`/`QcResult`
    (`qc_sample_id` links to the row created on collect via `qc.commands.create_sample(source_type=
    "material_lot")`, which already supports this source type)."""

    __tablename__ = "sampling_orders"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    sampling_plan_ref: Mapped[str | None] = mapped_column(String(160))
    selected_container_ids: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sample_quantities: Mapped[dict | None] = mapped_column(JSONB)
    assigned_sampler_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="requested")
    # RCV-FR-021: aseptic/sterile sampling evidence reference -- captured as an unenforced free-text/JSON
    # reference; no sterile-equipment qualification check exists (WP-06 Equipment, not built).
    aseptic_evidence_ref: Mapped[str | None] = mapped_column(String(200))
    qc_sample_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.qc_sample.id"))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialQualityDisposition(Base):
    """Document 19 `material_quality_disposition` -- RCV-FR-023/024/025/026/027/029/030. Deliberately a
    separate table from the pre-existing `MaterialLotDisposition` (Document 18-era, backing the legacy
    generic `/material-lots/{id}/disposition` endpoint, left untouched -- see SPEC_GAP on the signature
    policy mismatch): this table backs only the three Document 19 API operations (`release`/`reject`/
    `retest`) and their Document 106 rows 44/45 policy. Append-only (no UPDATE grant, AG-08)."""

    __tablename__ = "material_quality_dispositions"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    # RCV-FR-030 partial container disposition: null container_ids means the decision applies to the
    # whole lot; a non-null JSONB array scopes it to specific containers.
    container_ids: Mapped[dict | None] = mapped_column(JSONB)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # released | rejected | retest_due
    evidence_refs: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(String(2000))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    effective_at: Mapped[datetime] = mapped_column(server_default=func.now())
    disposed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


# Document 21 (SPEC-MAT-002C) states -- section 2's workflow diagram condensed into a linear state list;
# no branch/loop states are modeled beyond what's needed to drive the 9 declared API operations.
DISPENSING_ORDER_STATES = (
    "created", "source_selected", "started", "awaiting_verification", "completed", "cancelled",
)


class DispensingOrder(Base):
    """Document 21 `dispensing_order` -- DSP-FR-001. `batch_step_id`/`material_spec_version_id` carry no
    FK -- no `material_requirement` entity exists anywhere in this codebase (SG-089), same unenforced-
    reference treatment as `MaterialLot.material_spec_version_id`. `target_qty`/`target_uom`/
    `tolerance_low`/`tolerance_high` are caller-supplied captured values -- no target-calculation or
    tolerance-rule execution mode exists (SG-089); `tolerance_rule_id`'s spec-declared field is dropped in
    favor of the two explicit bound columns actually needed to evaluate against."""

    __tablename__ = "dispensing_orders"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    batch_step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.materials.id"), nullable=False
    )
    material_spec_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    target_qty: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    target_uom: Mapped[str] = mapped_column(String(40), nullable=False)
    target_uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    tolerance_low: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    tolerance_high: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="created")
    # Set at `start`; the independence baseline `verify` (must not be performer) and `cancel` (must be
    # independent of the author, checked against requested_by_user_id instead) evaluate against.
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DispensingSource(Base):
    """Document 21 `dispensing_source` -- DSP-FR-002/017/025. `reservation_id` reuses Document 20's
    `InventoryReservation` where one already exists (INV-FR-010) rather than duplicating reservation
    semantics; nullable because DSP-FR-002 doesn't mandate a reservation precede source selection."""

    __tablename__ = "dispensing_sources"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispensing_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.dispensing_orders.id"), nullable=False
    )
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    container_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_containers.id")
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.inventory_reservations.id")
    )
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    actual_taken_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    eligibility_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class WeighingSession(Base):
    """Document 21 `weighing_session` -- DSP-FR-006/007/009/010, 1:1 with a dispensing order. The many
    individual weight readings live in `WeighingReading` (append-only), not embedded here."""

    __tablename__ = "weighing_sessions"
    __table_args__ = (UniqueConstraint("dispensing_order_id"), {"schema": "materials"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispensing_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.dispensing_orders.id"), nullable=False
    )
    operator_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    booth_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.warehouse_locations.id")
    )
    tare_method: Mapped[str | None] = mapped_column(String(40))
    tare_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column()
    final_accepted_net: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    version: Mapped[int] = mapped_column(nullable=False, default=1)


class WeighingReading(Base):
    """Document 21 `weighing_session.readings` -- DSP-FR-009/010/011/013/014: append-only, every reading
    kept including a later-corrected overweight one ("original overweight reading retained", DSP-FR-014).
    No command ever updates a row here -- AG-08, same discipline as `InventoryTransaction`. `source` is
    always 'manual' in practice -- no Edge/Balance device adapter exists (SG-088); the 'device' value and
    `device_id` column are captured-not-integrated placeholders."""

    __tablename__ = "weighing_readings"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    weighing_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.weighing_sessions.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    reading_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    uom: Mapped[str] = mapped_column(String(40), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    stable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # manual | device
    manual_reason: Mapped[str | None] = mapped_column(String(500))
    device_id: Mapped[str | None] = mapped_column(String(100))
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# Document 22 (SPEC-MAT-002D) status vocabulary for DispensedContainer.status -- prose-only, like
# INVENTORY_TRANSACTION_TYPES above, not a DB CHECK constraint.
DISPENSED_CONTAINER_STATUSES = ("active", "partially_consumed", "consumed", "returned", "destroyed")


class DispensedContainer(Base):
    """Document 21 `dispensed_container` -- DSP-FR-019/020/024. Distinct from `MaterialContainer` (whose
    identity is a supplier-lot concept) -- a dispensed container's identity is batch-scoped output
    material that can span multiple source lots (DSP-FR-017 multi-lot dispensing).

    `remaining_quantity` was added in the Document 22 (SPEC-MAT-002D) session -- CON-FR-004 "track
    remaining quantity in dispensed container". Document 21 never tracked post-dispense balance on this
    row; Document 22 is the first consumer. Same mutable-field precedent as `MaterialContainer.
    current_quantity` (Document 18/19): decremented directly, in the same transaction as each CONSUME/
    RETURN/SAMPLE/REJECT/DESTROY `InventoryTransaction` row that references this container via
    `reference_type="dispensed_container"` (the immutable ledger row is the audit trail; this column is
    the fast current-balance read, exactly like `MaterialContainer.current_quantity`)."""

    __tablename__ = "dispensed_containers"
    __table_args__ = (UniqueConstraint("container_code"), {"schema": "materials"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.materials.id"), nullable=False
    )
    dispensing_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.dispensing_orders.id"), nullable=False
    )
    container_code: Mapped[str] = mapped_column(String(120), nullable=False)
    actual_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    label_print_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal("0"))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


# ---------------------------------------------------------------------------
# Document 22 (SPEC-MAT-002D) -- Material Consumption, Return, Adjustment, Destruction & Reconciliation.
# Owner: services/gxp-api/app/modules/material (same module as Documents 18-21; AG-05 single owner).
# ---------------------------------------------------------------------------

# CON-FR-005/006: unsuitable return condition routes to quarantine rather than back to available stock.
# Captured, not DB-enumerated -- same treatment as every other status-prose tuple in this file.
MATERIAL_RETURN_RESULTING_STATUSES = ("released", "quarantine", "rejected")

# CON-FR-013/014: routine cycle counts stay on the pre-existing unsigned `create_cycle_count` path
# (Document 20). This status machine is the *exceptional* adjustment Document 22 itself declares, gated
# by the Document 106 row 55 signed `approve` action.
INVENTORY_ADJUSTMENT_REQUEST_STATUSES = ("requested", "approved", "rejected")

# CON-FR-015/016/017: request -> (optional witness-bearing) authorization -> execute. Document 106 row 56
# registers exactly one signature point (`execute`, `Performed`, count=1, no independence, no reason) --
# `witnesses` below is a captured JSONB list of user references, not a second regulated signature; Doc106
# is the authoritative signature-policy source and declares none for destruction beyond the performer.
DESTRUCTION_RECORD_STATUSES = ("requested", "authorized", "executed")

# CON-FR-019/020: ACCEPTABLE/VARIANCE per the lifecycle diagram in Document 22 section 2. `tolerance_value`
# on the row is caller-supplied captured input -- Document 17 (yield/reconciliation released tolerance
# rule) is not built in this codebase and Document 08's rules engine has no material-reconciliation
# tolerance entry (SG-098, same class of gap as SG-094's dispensing-tolerance treatment).
MATERIAL_RECONCILIATION_OUTCOMES = ("ACCEPTABLE", "VARIANCE")


class MaterialConsumption(Base):
    """Document 22 `material_consumption` -- CON-FR-002/003(manual)/004/027/031. Schema is the spec's own
    literal DDL (section 4). Append-only: no command ever UPDATEs or DELETEs a row here (AG-08, same
    DB-privilege enforcement as `InventoryTransaction`); a correction is a reversal + new consumption
    (CON-FR-023/024), never an edit."""

    __tablename__ = "material_consumptions"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batch_steps.id"))
    dispensed_container_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.dispensed_containers.id"), nullable=False
    )
    material_lot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.material_lots.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    uom: Mapped[str] = mapped_column(String(40), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    # CON-FR-003: "manual" (built) vs "automatic" (not built -- no edge/rules-engine source exists, SG-098).
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.inventory_transactions.id"), nullable=False
    )
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialReturn(Base):
    """Document 22 `material_return` -- CON-FR-005/006/007. Append-only (AG-08)."""

    __tablename__ = "material_returns"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    dispensed_container_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.dispensed_containers.id"), nullable=False
    )
    material_lot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.material_lots.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    uom: Mapped[str] = mapped_column(String(40), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    container_condition: Mapped[str] = mapped_column(String(60), nullable=False)
    # CON-FR-007: exposure/opening/temperature-excursion evidence captured as JSONB -- no controlled
    # code list exists in the source spec beyond prose (same treatment as MaterialReceipt exam fields).
    storage_exposure_evidence: Mapped[dict | None] = mapped_column(JSONB)
    target_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.warehouse_locations.id")
    )
    resulting_status: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.inventory_transactions.id"), nullable=False
    )
    returned_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class InventoryAdjustmentRequest(Base):
    """Document 22 `inventory_adjustment_request` -- CON-FR-013/014. Distinct from Document 20's unsigned
    `create_cycle_count` (routine counting): this is the exceptional, controlled-reason, independently
    approved adjustment path with its own Document 106 row 55 signature (`approve`, `Approved`, MUST be
    independent of the author, reason required). `requested`/`approved`/`rejected` mutate in place
    (mutable aggregate, like `DispensingOrder`) -- the immutable evidence is the `InventoryTransaction`
    row created on approval, not this row's own history."""

    __tablename__ = "inventory_adjustment_requests"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_lots.id"), nullable=False
    )
    container_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_containers.id")
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.warehouse_locations.id"), nullable=False
    )
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    observed_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    variance: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested")
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resulting_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.inventory_transactions.id")
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DestructionRecord(Base):
    """Document 22 `destruction_record` -- CON-FR-015/016/017/018. `certificate_vault_object_id` reuses
    the same vault-evidence-reference pattern as `MaterialReceipt.coa_vault_object_id`. `witnesses` is a
    captured JSONB list of user references (CON-FR-016's "witness where policy requires") -- not a second
    Part 11 signature; Document 106 row 56 registers exactly one signer for `execute`."""

    __tablename__ = "destruction_records"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    material_lot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.material_lots.id"))
    container_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.material_containers.id")
    )
    dispensed_container_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.dispensed_containers.id")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    uom: Mapped[str] = mapped_column(String(40), nullable=False)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))  # SG-146 (remainder)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    method: Mapped[str | None] = mapped_column(String(200))
    # CON-FR-018: third-party destruction vendor/manifest/certificate/chain-of-custody.
    vendor_name: Mapped[str | None] = mapped_column(String(200))
    manifest_reference: Mapped[str | None] = mapped_column(String(200))
    certificate_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    witnesses: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested")
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.inventory_transactions.id")
    )
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    executed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    executed_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MaterialReconciliation(Base):
    """Document 22 `material_reconciliation` -- CON-FR-019/020/021(partial, SG-098)/022(partial,
    SG-098)/023/024. Scoped to `batch_id` (+ optional `material_id`) rather than the spec's prose
    "material requirement" -- no `material_requirement` entity exists anywhere in this codebase (SG-094
    precedent, same scope-narrowing this module has used since Document 21). CON-FR-023's correction
    pattern: re-evaluation never edits a row here -- it inserts a new row; `version` is the sequence
    number across a batch's (+material_id's) reconciliation history, not an in-place-updated aggregate
    version."""

    __tablename__ = "material_reconciliations"
    __table_args__ = {"schema": "materials"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.materials.id"))
    dispensed_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    consumed_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    returned_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    sampled_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    rejected_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    destroyed_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    approved_loss_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    unexplained_variance: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    # CON-FR-021 placeholder (SG-098): caller-supplied, not a released Document 08/17 tolerance rule.
    tolerance_value: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    calculation_rule_version: Mapped[str] = mapped_column(String(40), nullable=False, default="CC-4-v1")
    # CON-FR-022 partial (SG-098): populated only when the caller supplies severity/owner on VARIANCE;
    # no auto-derived severity/owner and no batch-completion-gate enforcement this pass.
    linked_deviation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.deviation_record.id"))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    evaluated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
