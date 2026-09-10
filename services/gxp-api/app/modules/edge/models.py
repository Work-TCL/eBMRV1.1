"""Document 43 (SPEC-EDGE-001) — Edge Gateway Runtime Architecture. First document of WP-06's Edge/OT
half; no edge module existed before this pass. Scope, per plan-mode sign-off: the **server-side** half
of the architecture only — the 6 APIs in spec §8 (registry/enrollment/config-serve/observation-ingestion/
health/certificate-rotation/security-events). The on-prem gateway runtime itself (§12: supervisor,
connectors, plugins, local SQLite outbox, CLI) is a distinct future deployable and is not built here; the
`edge_gateway_state`/`edge_outbox`/etc. tables §7 suggests are that gateway's own local persistence, not
this schema.

Every table below is this pass's own derivation from §7's "starting point, not literal DDL-ready spec"
tables, adapted for what the *server* needs to authoritatively track (AG-03) rather than what the gateway
buffers locally. `tenant_id` dropped throughout (single-organization platform, ADR-0006), matching every
migration since 0002.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# §6's runtime state model describes the *gateway's own* self-reported operational state (RUNNING/
# DEGRADED/...). The server keeps that distinct from its own authoritative trust/lifecycle field below
# (EDGE-FR-001's "lifecycle state") — self-reported operational status is informational display only and
# never drives an authorization or trust decision (architecture principle: "Edge... is not the GxP system
# of record").
GATEWAY_LIFECYCLE_STATES = ("ENROLLED", "ACTIVE", "SUSPENDED", "SECURITY_HOLD", "DECOMMISSIONED")
GATEWAY_OPERATIONAL_STATES = (
    "RUNNING", "DEGRADED", "OFFLINE_UPSTREAM", "DISK_PRESSURE", "UPDATE_PENDING", "STOPPED",
)
ENROLLMENT_TOKEN_STATES = ("unused", "consumed", "expired")
CONFIG_SNAPSHOT_STATES = ("active", "superseded")
# EDGE-FR-012 canonical quality values, transcribed literally from §5.
OBSERVATION_QUALITIES = ("GOOD", "UNCERTAIN", "BAD", "STALE", "COMM_ERROR", "CLOCK_UNCERTAIN")
SECURITY_EVENT_SEVERITIES = ("INFO", "WARNING", "CRITICAL")


class EdgeGateway(Base):
    """EDGE-FR-001/002/003/017/025/026. The aggregate every Document 43 command mutates; `version` is
    bumped on every accepted mutation (enrollment, observation batch, health report, security event,
    certificate rotation) so `expected_version` optimistic concurrency (DATA-FR-017/PG-FR-008) applies
    uniformly, matching `docs/generated/06_API_CATALOGUE.yaml`'s declared `expected_version: required` on
    every one of the 5 mutating ops.
    """

    __tablename__ = "edge_gateways"
    __table_args__ = {"schema": "edge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    host_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    certificate_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    certificate_expires_at: Mapped[datetime | None] = mapped_column()
    # Doc 106 row 119's certificate-rotation signature independence check compares against this actor
    # (the closest thing this record has to "the production performer" -- the human who approved this
    # gateway's trust in the first place). An engineering-judgment reading of an underspecified term, same
    # class of scoping precedent as batch release's "independent of the reviewer" check.
    enrolled_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(30), nullable=False, default="ENROLLED")
    # Self-reported only (EDGE-FR-017) -- never authoritative, see module docstring.
    last_reported_operational_state: Mapped[str | None] = mapped_column(String(30))
    active_config_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("edge.edge_config_snapshots.id", use_alter=True)
    )
    last_health_at: Mapped[datetime | None] = mapped_column()
    last_observation_sequence: Mapped[int | None] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EdgeEnrollmentToken(Base):
    """EDGE-FR-002. Bootstrap token issued out-of-band (seed/admin) and consumed exactly once by
    `enroll_gateway`. No public "issue token" API exists in spec §8 -- known limitation, not a SPEC_GAP
    (§8 simply never defines that endpoint); tokens are seed/admin-issued only this pass.
    """

    __tablename__ = "edge_enrollment_tokens"
    __table_args__ = (UniqueConstraint("token_hash"), {"schema": "edge"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unused")
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    consumed_by_gateway_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("edge.edge_gateways.id")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EdgeConfigSnapshot(Base):
    """EDGE-FR-004/005/006. Immutable/versioned once written -- a new active version supersedes rather
    than overwrites. No public config-authoring API exists in spec §8 either (`GET .../configuration` only
    serves whatever is active) -- same known-limitation treatment as the enrollment token above.
    """

    __tablename__ = "edge_config_snapshots"
    __table_args__ = (UniqueConstraint("gateway_id", "config_version"), {"schema": "edge"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gateway_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edge.edge_gateways.id"), nullable=False)
    config_version: Mapped[str] = mapped_column(String(60), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    activated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EdgeObservation(Base):
    """EDGE-FR-009..016. Append-only acceptance record of the canonical §5 `EdgeObservationEnvelope`.
    `event_id` is the gateway-assigned UUIDv7 -- primary key, enforcing EDGE-FR-016 idempotency directly
    at the DB level; `(gateway_id, gateway_sequence)` is separately unique, enforcing EDGE-FR-015 ordered,
    exactly-once acknowledgement semantics. Never a source for a batch/equipment/EM/QC write (EDGE-FR-030)
    -- mapping into those tables is Document 47's job, out of scope here (see module docstring).
    """

    __tablename__ = "edge_observations"
    __table_args__ = (UniqueConstraint("gateway_id", "gateway_sequence"), {"schema": "edge"})

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    gateway_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edge.edge_gateways.id"), nullable=False)
    gateway_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    connector_id: Mapped[str | None] = mapped_column(String(120))
    device_id: Mapped[str | None] = mapped_column(String(120))
    mapping_id: Mapped[str | None] = mapped_column(String(120))
    mapping_version: Mapped[str | None] = mapped_column(String(60))
    source: Mapped[dict | None] = mapped_column(JSONB)
    source_timestamp: Mapped[datetime | None] = mapped_column()
    gateway_received_at: Mapped[datetime | None] = mapped_column()
    clock_quality: Mapped[dict | None] = mapped_column(JSONB)
    quality: Mapped[str] = mapped_column(String(20), nullable=False)
    raw: Mapped[dict | None] = mapped_column(JSONB)
    normalized: Mapped[dict | None] = mapped_column(JSONB)
    correlation_id: Mapped[str | None] = mapped_column(String(120))
    batch_context: Mapped[dict | None] = mapped_column(JSONB)
    accepted_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EdgeHealthSnapshot(Base):
    """EDGE-FR-017. Append-only history (EDGE-FR-027); `EdgeGateway.last_health_at`/
    `last_reported_operational_state` carry the latest for cheap reads."""

    __tablename__ = "edge_health_snapshots"
    __table_args__ = {"schema": "edge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gateway_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edge.edge_gateways.id"), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(server_default=func.now())
    operational_state: Mapped[str | None] = mapped_column(String(30))
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    clock_quality: Mapped[dict | None] = mapped_column(JSONB)
    cert_expiry_days: Mapped[int | None] = mapped_column(Integer)


class EdgeSecurityEvent(Base):
    """EDGE-FR-027 (security-relevant runtime events). A CRITICAL event moves the owning
    `EdgeGateway.lifecycle_state` to SECURITY_HOLD in the same transaction (`report_security_event`),
    the server-authoritative reaction to a self-reported signal -- same pattern as the runtime's own
    `quarantineConnector()`."""

    __tablename__ = "edge_security_events"
    __table_args__ = {"schema": "edge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gateway_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edge.edge_gateways.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    reported_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EdgeCertificateRotation(Base):
    """EDGE-FR-020/027. Document 106 row 119's signed operation -- the one signature-bearing history
    table in this module besides enrollment."""

    __tablename__ = "edge_certificate_rotations"
    __table_args__ = {"schema": "edge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gateway_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edge.edge_gateways.id"), nullable=False)
    old_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    new_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    rotated_at: Mapped[datetime] = mapped_column(server_default=func.now())
