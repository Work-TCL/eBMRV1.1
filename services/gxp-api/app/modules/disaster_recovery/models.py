"""Document 76 (SPEC-DATA-008) -- Backup, Restore, Point-in-Time Recovery & Disaster Recovery. New
`disaster_recovery` PostgreSQL schema. Three owned entities per `04_DATA_MODEL_CATALOGUE.md`:
`recovery_objective_profile`, `backup_inventory`, `restore_test`.

**RPO/RTO numbers are not guessed.** Document 109 (SPEC-DATA-012, APPROVED v1.0, closes SG-006/008/016)
supplies the platform-default recovery-tier table (`# 1. Component recovery tiers`): T0 regulated
authoritative (RPO 0 / RTO ≤4h), T1 immutable evidence (RPO 0 / RTO ≤8h), T2 application/UI (RPO ≤15min
/ RTO ≤8h), T3 orchestration (RPO ≤15min / RTO ≤8h), T4 derived (rebuildable, no RPO / RTO ≤24h), T5
edge (local durability ≥72h offline / RTO ≤4h to restore upstream). `registry.py::DOCUMENT_109_TIER_SEED`
transcribes exactly that table; `scripts/seed.py`/`tests/conftest.py` insert it as the platform-default
`recovery_objective_profile` baseline, overridable per deployment (DR-FR-001/009).

No signature (Document 106 has no SPEC-DATA-008 row) -- RBAC-gated + reason, same "no policy row =
unsigned" precedent as every prior unsigned module. No `tenant_id` (ADR-0006); `site_id` nullable
(T5 edge objectives are per-site). All durations are `BigInteger` seconds -- never float; sizes are
`BigInteger` bytes.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

RECOVERY_TIERS = ("T0", "T1", "T2", "T3", "T4", "T5")
BACKUP_TYPES = ("FULL", "INCREMENTAL", "WAL", "SNAPSHOT")
BACKUP_STATUSES = ("SUCCESS", "FAILED", "IN_PROGRESS")
RESTORE_RESULTS = ("PASS", "FAIL", "IN_PROGRESS")


class RecoveryObjectiveProfile(Base):
    """Document 76 # 6 `recovery_objective_profile` -- one row per component/capability, its recovery
    tier (Document 109 T0-T5) and the RPO/RTO that tier carries. `rpo_seconds`/`rto_seconds` are
    `None` only for T4 (explicitly "no RPO commitment, rebuildable")."""

    __tablename__ = "recovery_objective_profile"
    __table_args__ = (UniqueConstraint("component"), {"schema": "disaster_recovery"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    component: Mapped[str] = mapped_column(String(80), nullable=False)
    tier: Mapped[str] = mapped_column(String(4), nullable=False)
    rpo_seconds: Mapped[int | None] = mapped_column(BigInteger)
    rto_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False)
    approved_by: Mapped[str] = mapped_column(String(160), nullable=False, default="Document 109 platform default")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class BackupInventory(Base):
    """Document 76 # 6 `backup_inventory` -- one row per executed backup: type, window, size,
    checksum/manifest reference, encryption flag and status (DR-FR-005/013/015)."""

    __tablename__ = "backup_inventory"
    __table_args__ = (
        Index("ix_backup_inventory_component", "component"),
        {"schema": "disaster_recovery"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component: Mapped[str] = mapped_column(String(80), nullable=False)
    backup_type: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    checksum: Mapped[str | None] = mapped_column(String(160))
    manifest_ref: Mapped[str | None] = mapped_column(String(300))
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class RestoreTest(Base):
    """Document 76 # 6 `restore_test` -- one executed restore/PITR drill against a `backup_inventory`
    row: target environment, optional PITR target, achieved RPO/RTO, integrity checks and result
    (DR-FR-016/017/030). `rpo_achieved_seconds`/`rto_achieved_seconds` are the *measured* recovery,
    compared against the component's `recovery_objective_profile` at report time -- never invented."""

    __tablename__ = "restore_test"
    __table_args__ = (
        Index("ix_restore_test_backup_id", "backup_id"),
        {"schema": "disaster_recovery"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_environment: Mapped[str] = mapped_column(String(80), nullable=False)
    pitr_target: Mapped[datetime | None] = mapped_column()
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()
    rpo_achieved_seconds: Mapped[int | None] = mapped_column(BigInteger)
    rto_achieved_seconds: Mapped[int | None] = mapped_column(BigInteger)
    integrity_checks: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    evidence_ref: Mapped[str | None] = mapped_column(String(300))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
