"""WP-07 (Documents 48-53, SPEC-ERP-001..006) — Enterprise ERP Integration Architecture, adapter
contracts, master-data sync and the shared integration reliability model.

Every table below is a **provisional schema** (SG-121 / ADR-0009): the frozen Phase-0 data model
catalogue (`docs/generated/04_DATA_MODEL_CATALOGUE.md`) declares zero entities for all six WP-07
documents, and Document 112 (the approved addendum that exists to close exactly this class of gap for
other modules) does not cover ERP either. The shape here follows Document 70's universal aggregate
baseline (`id, site_id, state/status, version, created_at, updated_at`) and Document 112's own
completed-schema format, so a human amendment to Document 112 can reconcile onto it rather than starting
from nothing. `tenant_id` is dropped throughout (single-organization platform, ADR-0006), same as every
prior module.

One shared reliability backbone (`integration_commands`/`integration_command_attempts`/
`integration_inbound_events`/`integration_reconciliation_*`/`integration_circuit_breakers`) is used by
every vendor adapter (Documents 49/50/51) and by master-data sync (Document 52) — Document 53's own
scope statement ("one consistent integration reliability model across ERP, LIMS, Edge and other
enterprise adapters") built once, not once per vendor.

INT-FR-028 (retention): no Document 108 retention-class catalogue exists anywhere in this codebase for
any module (`docs/generated/` has no retention catalogue file at all -- a platform-wide gap, not specific
to WP-07, so not something this pass invents a mechanism for). The policy this pass *can* state without
guessing a duration: these integration ledger tables must be retained at least as long as the regulated
GxP records they support investigating and reconciling (the same principle AUD-FR-023 already states for
the audit ledger), since `integration_commands`/`integration_inbound_events` are frequently the only
record of what was actually sent to or received from the external ERP for a given regulated transaction.
No numeric duration is set here; none exists in the approved baseline to set it from.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# --- ERP-ARC-002/003/030 --------------------------------------------------------------------------
ERP_VENDORS = ("ERPNEXT", "SAP_S4HANA", "ORACLE_FUSION", "DYNAMICS_365", "GENERIC")
ERP_ENVIRONMENTS = ("PRODUCTION", "SANDBOX", "TEST")
ERP_INSTANCE_STATUSES = ("ACTIVE", "SUSPENDED", "DECOMMISSIONED")
ERP_AUTH_METHODS = ("API_KEY", "OAUTH2_CLIENT_CREDENTIALS", "BASIC")

# --- ERP-ARC-005/006..020, MDS-FR-001..017 --------------------------------------------------------
MAPPING_ENTITY_TYPES = (
    "MATERIAL", "PRODUCT", "SUPPLIER", "WAREHOUSE", "LOCATION", "UOM", "REASON_CODE", "CUSTOMER",
    "GL_ACCOUNT", "PRODUCTION_ORDER_REFERENCE",
    # ERP-ARC-020: preserve the vendor's own lot/serial reference alongside internal genealogy, which
    # stays authoritative (materials.material_lots/device serials never derive identity from these rows,
    # matching MATERIAL/PRODUCT's own "reference, not replacement" treatment above).
    "MATERIAL_LOT", "SERIAL",
)
MAPPING_STATUSES = ("UNMAPPED", "PROPOSED", "ACTIVE", "CONFLICT", "SUSPENDED", "RETIRED")
FIELD_OWNERSHIP = ("GXP", "ERP")
MATCH_METHODS = ("EXPLICIT_ID", "FUZZY_PROPOSED", "MANUAL")

# --- MDS-FR-018/019/020 ----------------------------------------------------------------------------
CONFLICT_STATUSES = ("OPEN", "RESOLVED", "REJECTED")

# --- ERP-ARC-021/023/024/026/027, INT-FR-001..016 --------------------------------------------------
COMMAND_STATES = ("PENDING", "DISPATCHED", "SUCCEEDED", "FAILED", "RETRY_WAIT", "DEAD_LETTER", "CANCELLED")
ERROR_CATEGORIES = (
    "AUTH", "CONFIG", "VALIDATION", "BUSINESS_REJECT", "CONFLICT", "RATE_LIMIT", "TRANSIENT_NETWORK",
    "SERVER_ERROR", "TIMEOUT_UNCERTAIN", "SCHEMA", "SECURITY", "MANUAL_REVIEW",
)
ATTEMPT_OUTCOMES = ("SUCCEEDED", "FAILED", "TIMEOUT_UNCERTAIN")

# --- ERP-ARC-022, INT-FR-010/011 --------------------------------------------------------------------
INBOUND_STATES = ("RECEIVED", "PROCESSED", "DUPLICATE", "SCHEMA_INVALID", "STALE_SUPERSEDED", "CONFLICT")

# --- ERP-ARC-025, INT-FR-017..021 -------------------------------------------------------------------
RECONCILIATION_RUN_STATUSES = ("RUNNING", "COMPLETED", "FAILED")
DIFFERENCE_TYPES = (
    "MISSING_EXTERNAL", "EXTRA_EXTERNAL", "VALUE_MISMATCH", "STATUS_MISMATCH", "REFERENCE_MISMATCH",
    "DUPLICATE_EXTERNAL", "STALE_MAPPING",
)
DIFFERENCE_RESOLUTION_STATUSES = ("OPEN", "AUTO_RESOLVED", "RESOLVED", "ESCALATED")

# --- INT-FR-022 ---------------------------------------------------------------------------------------
CIRCUIT_STATES = ("CLOSED", "OPEN", "HALF_OPEN")


class ErpInstance(Base):
    """ERP-ARC-002/003/028/030. `site_id=NULL` means an org-wide instance serving multiple sites.
    `auth_secret_ref` is an opaque reference into the platform secret manager (ERP-ARC-028) -- never a
    raw credential.

    `service_actor_user_id` (WP-11 Stage 4, migration 0103) mirrors `lims_instance.service_actor_user_id`
    exactly -- a stand-in for a dedicated machine-identity model, which does not exist anywhere in this
    codebase (SG-070 / LIMS-FR-013 -- `lims_instance.py`'s own docstring cites this as "SG-067", which is
    actually a different, unrelated NCR gap; SG-070 is the correct number). Nullable: an instance with
    no value is simply not eligible for the
    automated event-driven consumer path (`app/modules/erp/consumer.py`) yet."""

    __tablename__ = "erp_instances"
    __table_args__ = {"schema": "erp"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    instance_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    vendor: Mapped[str] = mapped_column(String(20), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False, default="SANDBOX")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    auth_method: Mapped[str] = mapped_column(String(40), nullable=False)
    auth_secret_ref: Mapped[str | None] = mapped_column(String(200))
    capabilities: Mapped[dict | None] = mapped_column(JSONB)
    contract_version: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    # MULTI-FR-024: a GENERIC (custom) instance cannot be used to post writes until explicitly
    # validated through a certification/acceptance profile (validate_erp_instance()) -- named-vendor
    # instances (ERPNext/SAP/Oracle/Dynamics) never go through this gate, their adapter code is this
    # codebase's own certification. Defaults false for every instance regardless of vendor; only
    # queue_erp_command's GENERIC-vendor check reads it.
    validated: Mapped[bool] = mapped_column(nullable=False, default=False)
    validated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    validated_at: Mapped[datetime | None] = mapped_column()
    service_actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ErpExternalMapping(Base):
    """ERP-ARC-005/006..020, MDS-FR-001..017/021. Internal identity may be keyed by `internal_id` (a real
    GxP aggregate id) or `internal_code` (a reference-data value with no owning row, e.g. a movement-type
    code) -- exactly one of the two is expected to be set, enforced in `commands.py`, not by a DB
    constraint (JSONB-adjacent flexibility precedent, same restraint as `sterile_input_refs` elsewhere).
    """

    __tablename__ = "erp_external_mappings"
    __table_args__ = (
        UniqueConstraint("erp_instance_id", "entity_type", "external_id", name="uq_erp_mapping_external"),
        Index("ix_erp_external_mappings_internal", "erp_instance_id", "entity_type", "internal_id"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    internal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    internal_code: Mapped[str | None] = mapped_column(String(120))
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    external_code: Mapped[str | None] = mapped_column(String(120))
    field_ownership: Mapped[str] = mapped_column(String(10), nullable=False, default="ERP")
    mapping_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROPOSED")
    match_method: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    confidence: Mapped[object | None] = mapped_column(Numeric(5, 4))
    # ERP-ARC-019: UOM/quantity conversion is a Decimal, never a binary float (AG-15).
    uom_conversion_factor: Mapped[object | None] = mapped_column(Numeric(24, 10))
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    mapping_hash: Mapped[str | None] = mapped_column(String(64))
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ErpMappingConflict(Base):
    """MDS-FR-006/018/019/020. `requires_qa_review` marks a quality-critical mapping conflict Document
    52 says "may require QA/validation" -- resolution is still a plain RBAC-gated action (SG-122), this
    flag is informational/routing only, not a signature gate."""

    __tablename__ = "erp_mapping_conflicts"
    __table_args__ = (
        Index("ix_erp_mapping_conflicts_mapping", "mapping_id"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mapping_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_external_mappings.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source_value: Mapped[dict | None] = mapped_column(JSONB)
    proposed_value: Mapped[dict | None] = mapped_column(JSONB)
    current_value: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    requires_qa_review: Mapped[bool] = mapped_column(nullable=False, default=False)
    resolution: Mapped[str | None] = mapped_column(String(400))
    resolution_reason: Mapped[str | None] = mapped_column(String(400))
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ErpSyncCheckpoint(Base):
    """MDS-FR-022/023. One row per (instance, entity_type) -- the resumable watermark/change-token."""

    __tablename__ = "erp_sync_checkpoints"
    __table_args__ = (
        UniqueConstraint("erp_instance_id", "entity_type", name="uq_erp_sync_checkpoint"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    cursor_value: Mapped[str | None] = mapped_column(String(200))
    last_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    last_synced_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class IntegrationCommand(Base):
    """ERP-ARC-021, INT-FR-001/006/007/009/013/014/015/016. The outbound command ledger every adapter
    (Documents 49/50/51) and master-data sync (Document 52) writes through -- Document 53's reliability
    model built once (module docstring). `correction_of_id` (INT-FR-014) links a corrected replacement
    command to the original without ever mutating the original's payload; `cancelled_reason` (INT-FR-015)
    is set only while `state='PENDING'`."""

    __tablename__ = "integration_commands"
    __table_args__ = (
        UniqueConstraint("erp_instance_id", "idempotency_key", name="uq_integration_command_idempotency"),
        Index("ix_integration_commands_state", "erp_instance_id", "state"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"), nullable=False)
    command_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_aggregate_type: Mapped[str | None] = mapped_column(String(80))
    source_aggregate_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    external_reference: Mapped[str | None] = mapped_column(String(200))
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column()
    last_error_category: Mapped[str | None] = mapped_column(String(30))
    last_error_detail: Mapped[dict | None] = mapped_column(JSONB)
    required_next_action: Mapped[str | None] = mapped_column(String(400))
    correction_of_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.integration_commands.id"))
    # INT-FR-016: an external reversal is a brand-new command, never a mutation of the original (same
    # discipline correction_of_id already applies) -- compensates_command_id links it to the SUCCEEDED
    # command it reverses; gxp_authorization_reference is the authorizing GxP correction/disposition
    # record (e.g. {"record_type": "qms_deviation", "record_id": ..., "action": "disposition"}),
    # required by commands.py whenever compensates_command_id is set.
    compensates_command_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.integration_commands.id"))
    gxp_authorization_reference: Mapped[dict | None] = mapped_column(JSONB)
    cancelled_reason: Mapped[str | None] = mapped_column(String(400))
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class IntegrationCommandAttempt(Base):
    """INT-FR-003/004/005/008/009. Append-only per-attempt history -- never updated, only inserted, same
    treatment as `AsepticEventTimeline` (no `version` column on a pure append-only child log)."""

    __tablename__ = "integration_command_attempts"
    __table_args__ = (
        Index("ix_integration_command_attempts_command", "command_id"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    command_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.integration_commands.id"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(30))
    error_detail: Mapped[dict | None] = mapped_column(JSONB)
    http_status: Mapped[int | None] = mapped_column()
    backoff_seconds: Mapped[int | None] = mapped_column()
    external_reference: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IntegrationInboundEvent(Base):
    """ERP-ARC-022, INT-FR-010/011/025. `(erp_instance_id, external_event_id)` unique -- a resubmission
    with a different `payload_hash` is a conflict (INT-FR-007/025), never a silent overwrite; handled in
    `commands.py::ingest_erp_event`, not by the DB constraint alone."""

    __tablename__ = "integration_inbound_events"
    __table_args__ = (
        UniqueConstraint("erp_instance_id", "external_event_id", name="uq_integration_inbound_event"),
        Index("ix_integration_inbound_events_entity", "erp_instance_id", "entity_type", "external_entity_id"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40))
    # INT-FR-011: the specific external record this event concerns (e.g. the vendor doc/item id), so a
    # later event for the *same* record can be compared for staleness -- external_event_id above is
    # unique per event, not per record, and cannot serve that purpose on its own.
    external_entity_id: Mapped[str | None] = mapped_column(String(200))
    source_version: Mapped[str | None] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_state: Mapped[str] = mapped_column(String(20), nullable=False, default="RECEIVED")
    error_category: Mapped[str | None] = mapped_column(String(30))
    error_detail: Mapped[dict | None] = mapped_column(JSONB)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IntegrationReconciliationRun(Base):
    """ERP-ARC-025, INT-FR-017/018/021. `mapping_version_snapshot` records the mapping row versions used
    (MDS-FR-021) so the run is reproducible."""

    __tablename__ = "integration_reconciliation_runs"
    __table_args__ = {"schema": "erp"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(80), nullable=False)
    reconciliation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    cutoff_at: Mapped[datetime] = mapped_column(nullable=False)
    query_keys: Mapped[dict | None] = mapped_column(JSONB)
    mapping_version_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()
    difference_count: Mapped[int] = mapped_column(nullable=False, default=0)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IntegrationReconciliationDifference(Base):
    """INT-FR-017/018/019/020. `resolution_status` starts `OPEN` always (SG-124: no auto-resolve rule
    exists) and requires an explicit human `resolveReconciliationDifference()` call."""

    __tablename__ = "integration_reconciliation_differences"
    __table_args__ = (
        Index("ix_integration_reconciliation_differences_run", "run_id"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.integration_reconciliation_runs.id"), nullable=False)
    difference_type: Mapped[str] = mapped_column(String(30), nullable=False)
    internal_ref: Mapped[dict | None] = mapped_column(JSONB)
    external_ref: Mapped[dict | None] = mapped_column(JSONB)
    field_name: Mapped[str | None] = mapped_column(String(80))
    internal_value: Mapped[dict | None] = mapped_column(JSONB)
    external_value: Mapped[dict | None] = mapped_column(JSONB)
    requires_qa_hold: Mapped[bool] = mapped_column(nullable=False, default=False)
    resolution_status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    resolution_reason: Mapped[str | None] = mapped_column(String(400))
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IntegrationCircuitBreaker(Base):
    """INT-FR-022. One row per (instance, operation). Provisional thresholds (SG-123) live in
    `reliability.py`, not in this row -- the row is pure runtime state."""

    __tablename__ = "integration_circuit_breakers"
    __table_args__ = (
        UniqueConstraint("erp_instance_id", "operation", name="uq_integration_circuit_breaker"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"), nullable=False)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="CLOSED")
    failure_count: Mapped[int] = mapped_column(nullable=False, default=0)
    opened_at: Mapped[datetime | None] = mapped_column()
    last_probe_at: Mapped[datetime | None] = mapped_column()
    # INT-FR-024/ERP-ARC-028: a proactive per-(instance, operation) quota window -- this row is already
    # the authoritative per-operation reliability state (module docstring), so the throttle window lives
    # here rather than in a new table. Provisional numeric quota (SG-123's own precedent) lives in
    # reliability.py, not on this row.
    rate_window_started_at: Mapped[datetime | None] = mapped_column()
    rate_window_count: Mapped[int] = mapped_column(nullable=False, default=0)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class IntegrationSecurityEvent(Base):
    """INT-FR-025. Same shape/precedent as `edge.EdgeSecurityEvent` (EDGE-FR-027): a payload-hash
    conflict, idempotency-key reuse with a different payload, or a source identity mismatch is a
    data-integrity/security signal, distinct from an ordinary business rejection -- recorded here rather
    than only in the GxP audit ledger (AUD-FR-027: "only failed actions with GxP significance need GxP
    audit"; this is the module-scoped security trail, not a regulated business record)."""

    __tablename__ = "integration_security_events"
    __table_args__ = (
        Index("ix_integration_security_events_instance", "erp_instance_id"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reported_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IntegrationBulkJob(Base):
    """INT-FR-023. Bulk import/export job tracking. Successes are counted (`succeeded_count`), not
    individually retained -- the record-level detail that actually matters for investigation is which
    records failed and why (`failed_records`, a bounded JSONB list: a healthy bulk job fails on a small
    minority of records, not most of them; a job that fails wholesale is a FAILED job, not a long
    per-record success list nobody will read). `resume_cursor` is the same watermark shape as
    `ErpSyncCheckpoint.cursor_value`, letting a resumed job skip already-processed records without a
    full per-record history table."""

    __tablename__ = "integration_bulk_jobs"
    __table_args__ = (
        UniqueConstraint("erp_instance_id", "idempotency_key", name="uq_integration_bulk_job_idempotency"),
        {"schema": "erp"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    erp_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RUNNING")
    total_records: Mapped[int | None] = mapped_column()
    succeeded_count: Mapped[int] = mapped_column(nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(nullable=False, default=0)
    resume_cursor: Mapped[str | None] = mapped_column(String(200))
    failed_records: Mapped[list | None] = mapped_column(JSONB)
    started_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


BULK_JOB_TYPES = ("IMPORT", "EXPORT")
BULK_JOB_STATUSES = ("RUNNING", "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED")


class ErpMigrationPackage(Base):
    """MDS-FR-028. Provenance record for a customer onboarding mapping/import package -- no dedicated
    workflow function exists in Document 52's own catalogue for this; the row is the requirement's full
    scope. `erp_instance_id` is nullable: an onboarding package can predate the target instance being
    registered."""

    __tablename__ = "erp_migration_packages"
    __table_args__ = {"schema": "erp"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"))
    erp_instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp.erp_instances.id"))
    package_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_types: Mapped[list | None] = mapped_column(JSONB)
    imported_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approval_reference: Mapped[str | None] = mapped_column(String(200))
    imported_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
