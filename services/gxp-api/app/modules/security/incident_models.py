"""Document 67 (SPEC-SEC-007) -- Security Logging, Monitoring, Incident Response & Forensic Evidence.
Same `security` PostgreSQL schema Documents 61-66 created; adds the 2 owned entities the approved
`04_DATA_MODEL_CATALOGUE.md` lists: `security_incident`, `forensic_evidence`.

**`security_event` is NOT an owned table.** Document 67 # 6 calls it a "central telemetry schema" but
the approved data-model catalogue owns only `security_incident` + `forensic_evidence` for this module.
Security telemetry is the transactional outbox (`emitSecurityEvent()` -> `write_outbox_event`,
`aggregate_type="security_event"`), kept distinct from the GxP audit ledger (MON-FR-002 / Document 67
# 14: "Never replace GxP audit ledger with SIEM logs"). Every other Document 67 module (detection
rules, alerts, metrics) is SIEM-side and not modelled as a GxP table here.

**Signature: only `close` is Part 11 signed** -- Document 106 row 140 (`incidents/{id}/close` ->
`Approved`, "QA Approver for the record class", MUST be independent of the investigator/owner, Reason:
yes). Resolved to the existing **QA Releaser** role, the same non-QMS mapping as Document 63's
`privileged_session.close` (row 136 -- identical shape). `open` / `containment` / `evidence` /
`gxp-impact` have no Document 106 row -> RBAC-gated + mandatory reason, no signature. The QMS
linkage of the GxP-impact assessment (creating a real deviation/CAPA -- MON-FR-016/030) is a
cross-module concern deferred this pass; `gxp_impact` is recorded on the incident and its state gate
still blocks closure (Document 67 # 14).

**No `site_id` column.** Affected scope (including sites) is a JSONB value (`affected_scope`), not a
column -- platform-level, same as every other `security.*` table. `tenant_id` dropped (ADR-0006).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
INCIDENT_STATES = ("OPEN", "CONTAINED", "RECOVERED", "GXP_IMPACT_ASSESSED", "CLOSED")
GXP_IMPACT_STATES = ("NOT_ASSESSED", "NO_IMPACT", "IMPACT_CONFIRMED")
# MON-FR-015: the entire containment allowlist. Each is a typed, recorded action.
CONTAINMENT_COMMANDS = (
    "REVOKE_SESSIONS", "REVOKE_CERTIFICATE", "ROTATE_SECRET", "ISOLATE_SERVICE",
    "BLOCK_INTEGRATION", "FREEZE_ACCOUNT", "DISABLE_FEATURE",
)


class SecurityIncident(Base):
    """Document 67 # 6 `security_incident` -- the formal incident record with its timeline. State:
    OPEN -> CONTAINED -> (RECOVERED) -> GXP_IMPACT_ASSESSED -> CLOSED. `containment_actions` is an
    append-only JSONB log (same "history on the parent aggregate" precedent as Document 63's
    `privileged_session.actions`)."""

    __tablename__ = "security_incident"
    __table_args__ = (
        UniqueConstraint("incident_number"),
        Index("ix_security_incident_state", "state"),
        {"schema": "security"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_number: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    # MON-FR-012: affected tenants/sites/systems/data classes + alert/evidence refs.
    affected_scope: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    alert_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # MON-FR-013 timeline stamps.
    detected_at: Mapped[datetime] = mapped_column(nullable=False)
    contained_at: Mapped[datetime | None] = mapped_column()
    recovered_at: Mapped[datetime | None] = mapped_column()
    closed_at: Mapped[datetime | None] = mapped_column()
    # MON-FR-013/018: append-only containment action log (command, target, outcome, actor, at).
    containment_actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    gxp_impact_state: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_ASSESSED")
    gxp_impact: Mapped[dict | None] = mapped_column(JSONB)
    # MON-FR-021: postmortem root cause + corrective actions + residual risk, frozen at closure.
    root_cause: Mapped[str | None] = mapped_column(Text)
    corrective_actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    residual_risk: Mapped[str | None] = mapped_column(String(200))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ForensicEvidence(Base):
    """Document 67 # 6 `forensic_evidence` -- one preserved evidence item with chain-of-custody
    (MON-FR-014). `digest`/`hash_algorithm` bind the immutable content; `chain_of_custody` is an
    append-only JSONB list of custody events. Never deleted on incident closure (Document 67 # 14)."""

    __tablename__ = "forensic_evidence"
    __table_args__ = (
        Index("ix_forensic_evidence_incident", "incident_id"),
        {"schema": "security"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("security.security_incident.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    acquisition_at: Mapped[datetime] = mapped_column(nullable=False)
    acquired_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    hash_algorithm: Mapped[str] = mapped_column(String(20), nullable=False, default="SHA-256")
    digest: Mapped[str] = mapped_column(String(128), nullable=False)
    object_ref: Mapped[str | None] = mapped_column(String(300))  # protected/WORM store or Vault ref
    chain_of_custody: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
