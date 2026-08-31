"""Document 47 (SPEC-EDGE-005) — PLC/SCADA Data Acquisition, Evidence Mapping & Command Boundary.

Scope, per plan-mode sign-off (see `/root/.claude/plans/enumerated-swimming-dijkstra.md` and
`docs/generated/18_SPEC_GAPS.md` SG-127..SG-131): this is the **server-side** "Integration Gateway" layer
Document 43 §9's module-connections diagram places between Store & Forward's already-built
`accept_observation_batch()` (`app.modules.edge.models.EdgeObservation` — its own docstring says mapping
those rows into batch/equipment/EM/QC "is Document 47's job, out of scope here") and the GxP Mutation
Gateway. This module consumes `edge.edge_observations` rows by `event_id` (imported, never duplicated —
AG-05) and turns them into audited evidence of its own; it never writes a Batch/Equipment/EM/QC table
directly (AG-05/AG-06). Two things this document leaves genuinely unresolved by the baseline are recorded
as SPEC_GAPs rather than guessed:

- MAP-FR-016 is explicit that machine state "does not independently transition GxP batch state unless
  approved orchestration rule does" — no such rule mechanism exists anywhere in this codebase, and neither
  `batch.complete_step()` nor `equipment.hold_equipment()` can be satisfied by a machine/service identity
  (Doc 106 P7: service/device identities can never sign). So `MachineEvidenceCandidate`/`MachineAlarmEvent`
  are audited, QA-review-visible records only — this pass never calls `complete_step`/`hold_equipment` from
  here. A human acts on them through the existing signed commands (SG-130).
- The command boundary's on-prem half (`executeMachineCommandAtEdge()` — the actual protocol write) is the
  same on-prem deployable Document 44's driver `write()` belongs to; not built here. This module builds
  only the server-side authorization/allowlist/request/outcome half, which is exactly what Document 43
  left as `EDGE-FR-023 NOT_STARTED`.

No entries exist for Document 47 in `docs/generated/04_DATA_MODEL_CATALOGUE.md` /
`05_DATABASE_OWNERSHIP_MATRIX.md` (same empty/generic state Document 43's session found) — every table
below is this pass's own derivation from the spec's own §4 (`SignalMappingVersion`) and §7
(`MachineCommandProfile`) data models, adapted for what the server actually needs to authoritatively track.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# MAP-FR-002's `SignalMappingVersion.evidenceClass` enum, transcribed literally from spec §4.
EVIDENCE_CLASSES = (
    "HISTORIAN_ONLY", "STEP_RESULT", "PROCESS_EVIDENCE", "ALARM", "EQUIPMENT_STATE", "EM_RESULT", "CYCLE_DATA",
)
MAPPING_LIFECYCLE_STATES = ("draft", "tested", "released", "superseded", "suspended")
BATCH_CONTEXT_STATES = ("OPEN", "CLOSED")
EVIDENCE_CANDIDATE_STATES = ("CANDIDATE", "REVIEWED")
ALARM_SEVERITIES = ("INFO", "WARNING", "CRITICAL")
COMMAND_PROFILE_STATES = ("draft", "released", "suspended")
COMMAND_REQUEST_STATES = ("PENDING", "SENT", "COMPLETED", "READBACK_MISMATCH", "TIMEOUT", "FAILED", "DENIED")
REPLAY_MODES = ("BACKFILL", "REPLAY")
REPLAY_JOB_STATES = ("REQUESTED", "COMPLETED")


class MachineSource(Base):
    """MAP-FR-001. Machine/PLC/SCADA source identity. `equipment_id`/`gateway_id` are real FKs but this
    module only ever reads through them (AG-05) — `gateway_id` records which Document 43 `EdgeGateway`
    is responsible for this source, used to route a `MachineCommandRequest` and to authorize
    `finalize_machine_command`'s service-identity caller (same ownership-check shape as
    `accept_observation_batch`)."""

    __tablename__ = "machine_sources"
    __table_args__ = (UniqueConstraint("site_id", "source_code"), {"schema": "machine_integration"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    source_code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.equipment_assets.id"))
    gateway_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("edge.edge_gateways.id"))
    protocol_connector: Mapped[str | None] = mapped_column(String(120))
    line_or_area: Mapped[str | None] = mapped_column(String(120))
    # Optimistic-concurrency counter, bumped by every ingest_machine_evidence()/build_cycle_evidence_
    # manifest() call against this source -- same "aggregate + expected_version" shape as every other
    # command in this codebase (e.g. edge.EdgeGateway.version for accept_observation_batch).
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SignalMapping(Base):
    """MAP-FR-002..008/017/027/028. One row per released/draft version (`mapping_key` groups versions,
    `version` is the business version number) — a new version supersedes rather than overwrites, same
    "immutable once released" shape as `edge.EdgeConfigSnapshot`. No public draft-authoring endpoint
    exists this pass (spec §3 defines only `releaseSignalMapping()`) — same "no authoring API, seed/admin
    only" precedent as `EdgeConfigSnapshot`/`EdgeEnrollmentToken`; known limitation, not a SPEC_GAP.
    `row_version` is this row's own optimistic-concurrency counter for the draft/tested/review path before
    release freezes it.
    """

    __tablename__ = "signal_mappings"
    __table_args__ = (UniqueConstraint("mapping_key", "version"), {"schema": "machine_integration"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    mapping_key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.machine_sources.id"), nullable=False)
    source_address: Mapped[str] = mapped_column(String(255), nullable=False)
    native_type: Mapped[str] = mapped_column(String(60), nullable=False)
    domain_code: Mapped[str] = mapped_column(String(120), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(30), nullable=False)
    raw_unit: Mapped[str | None] = mapped_column(String(30))
    canonical_unit: Mapped[str | None] = mapped_column(String(30))
    conversion_rule_ref: Mapped[str | None] = mapped_column(String(120))
    quality_mapping_ref: Mapped[str | None] = mapped_column(String(120))
    timestamp_policy: Mapped[str | None] = mapped_column(String(60))
    sampling_policy: Mapped[dict | None] = mapped_column(JSONB)
    # MAP-FR-012/013: "REQUIRED" (fails closed with no active context), "NONE" (historian-only/no batch
    # binding needed), or "DETERMINISTIC" (resolved from the sole open context for this source).
    batch_context_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="REQUIRED")
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    effective_from: Mapped[datetime | None] = mapped_column()
    drafted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    released_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    row_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class BatchContext(Base):
    """MAP-FR-012/013/§6. Server-issued `operation_context_id` (this row's own `id`) registering that a
    `MachineSource` is currently associated with a batch/step. §6 step 1 ("batch/step issues the id") and
    step 2 ("Integration Gateway registers it") are combined into this one command this pass — Batch
    module itself is not modified (cross-module orchestration wiring so `start_step`/`complete_step`
    open/close this automatically is a known limitation, not built here). Ambiguity (more than one OPEN
    row for the same source) fails closed in `resolve_batch_context()` — never guessed from timestamp
    proximity (MAP-FR-013 / §14 prohibition)."""

    __tablename__ = "batch_contexts"
    __table_args__ = {"schema": "machine_integration"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.machine_sources.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"), nullable=False)
    batch_step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batch_steps.id"))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="OPEN")
    opened_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()
    # MAP-FR-027 (SG-127 follow-up): the SignalMapping version pinned by the first ingest_machine_evidence()
    # call that actually routed evidence for this context. Once set, every subsequent call for this same
    # OPEN context re-uses this exact version, even if a newer one is released mid-batch ("open batches
    # keep issued mapping version") -- never re-resolved to "latest released" after the first pin.
    mapping_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.signal_mappings.id"))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class MachineEvidenceCandidate(Base):
    """MAP-FR-009..014/030 (`evaluateEvidenceRouting()` + `createStepResultCandidate()`). Audited record
    referencing the source `edge.edge_observations.event_id` (not duplicated), the mapping version used,
    and the resolved batch context if any. Deliberately never calls `batch.complete_step()` — see the
    module docstring's boundary decision (SG-130); a human reviews this candidate (MAP-FR-030 review-by-
    exception) and performs the real signed step completion separately, optionally referencing
    `id` as evidence."""

    __tablename__ = "machine_evidence_candidates"
    __table_args__ = {"schema": "machine_integration"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edge.edge_observations.event_id"), nullable=False, unique=True)
    mapping_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.signal_mappings.id"), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(30), nullable=False)
    batch_context_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.batch_contexts.id"))
    domain_code: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict | None] = mapped_column(JSONB)
    quality: Mapped[str | None] = mapped_column(String(20))
    freshness: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CANDIDATE")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MachineAlarmEvent(Base):
    """MAP-FR-015. `createMachineAlarmEvent()` — audited record only this pass; the batch/equipment
    "impact rule" the spec assumes is undefined by the baseline (SG-130). No automatic
    `hold_equipment()`/batch-state change; QA review-by-exception (MAP-FR-030) is the surfacing
    mechanism."""

    __tablename__ = "machine_alarm_events"
    __table_args__ = {"schema": "machine_integration"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edge.edge_observations.event_id"), nullable=False, unique=True)
    mapping_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.signal_mappings.id"), nullable=False)
    alarm_code: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    batch_context_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.batch_contexts.id"))
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING_REVIEW")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CycleEvidenceManifest(Base):
    """MAP-FR-025/026. `buildCycleEvidenceManifest()` — immutable once written (no update path exposed),
    hash-covering the referenced observation event IDs and summary statistics. No historian/time-series
    system exists in this codebase; `raw_evidence_ref` is a captured, unenforced reference (same "captured,
    unenforced" precedent as `edge.EdgeGateway`'s `cert_chain` — known limitation, not a SPEC_GAP).

    `historian_instance_ref` (MAP-FR-024) and `aggregation_rule_ref` (MAP-FR-011) added on the SG-129
    follow-up pass: both captured references only, same "captured, unenforced" precedent above -- Document
    47 §9 places the actual aggregation rule/query-filter with the historian's own query, an external
    system this codebase does not have; `statistics` remains caller-supplied and is not independently
    recomputed from raw evidence here."""

    __tablename__ = "cycle_evidence_manifests"
    __table_args__ = (UniqueConstraint("source_id", "cycle_id"), {"schema": "machine_integration"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.machine_sources.id"), nullable=False)
    cycle_id: Mapped[str] = mapped_column(String(120), nullable=False)
    batch_context_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.batch_contexts.id"))
    mapping_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.signal_mappings.id"))
    cycle_start: Mapped[datetime | None] = mapped_column()
    cycle_end: Mapped[datetime | None] = mapped_column()
    # List of edge_observations.event_id (as strings) this manifest covers -- JSONB, same convention as
    # every other list-of-references field in this codebase (no ARRAY(UUID) precedent anywhere).
    event_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    statistics: Mapped[dict | None] = mapped_column(JSONB)
    raw_evidence_ref: Mapped[str | None] = mapped_column(Text)
    historian_instance_ref: Mapped[str | None] = mapped_column(String(200))
    aggregation_rule_ref: Mapped[str | None] = mapped_column(String(200))
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MachineCommandProfile(Base):
    """§7 `MachineCommandProfile` — the allowlist. No profile released for an operation = that operation
    is structurally impossible through `submit_approved_machine_command()`, a real "disabled by default"
    (MAP-FR-019), not the "trivially true from total absence" Document 43's own test-fill flagged as
    insufficient for `EDGE-FR-023`. No public authoring endpoint this pass (same "seed/admin only"
    precedent as `SignalMapping`) — known limitation, not a SPEC_GAP: nothing in spec §3 defines a create/
    release function for this entity either."""

    __tablename__ = "machine_command_profiles"
    __table_args__ = (UniqueConstraint("operation_code", "version"), {"schema": "machine_integration"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    operation_code: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    allowed_equipment_classes: Mapped[list | None] = mapped_column(JSONB)
    parameter_schema: Mapped[dict | None] = mapped_column(JSONB)
    required_role_name: Mapped[str | None] = mapped_column(String(100))
    allowed_batch_states: Mapped[list | None] = mapped_column(JSONB)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=30000)
    requires_readback: Mapped[bool] = mapped_column(nullable=False, default=True)
    local_interlock_code: Mapped[str | None] = mapped_column(String(120))
    mapping_key: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MachineCommandRequest(Base):
    """MAP-FR-018,021,022 (`submitApprovedMachineCommand()` + `finalizeMachineCommand()` merged onto one
    row — `id` is the correlation id MAP-FR-021 requires linking request/approval/write/ack/evidence).
    `executeMachineCommandAtEdge()` (the actual protocol write) is on-prem and not built — this row models
    only the server-side authorization request and, once it comes back, the outcome. Finalization never
    triggers a Batch/Equipment write itself (see module docstring's boundary decision); it is audit/
    evidence of an already-signed approval's outcome, cross-module wiring into equipment/batch history
    deferred as a known limitation."""

    __tablename__ = "machine_command_requests"
    __table_args__ = {"schema": "machine_integration"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    command_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.machine_command_profiles.id"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_integration.machine_sources.id"), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.batches.id"))
    parameters: Mapped[dict | None] = mapped_column(JSONB)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    native_response: Mapped[dict | None] = mapped_column(JSONB)
    evidence_ref: Mapped[str | None] = mapped_column(Text)
    finalized_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MachineReplayJob(Base):
    """MAP-FR-029 (`replayHistoricalEvidence()`). Integration Admin action, own idempotency namespace via
    the shared `check_idempotency()` kernel; tagged BACKFILL/REPLAY so downstream never mistakes it for
    live data (§14 prohibition)."""

    __tablename__ = "machine_replay_jobs"
    __table_args__ = {"schema": "machine_integration"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    event_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="REQUESTED")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
