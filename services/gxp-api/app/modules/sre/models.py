"""Document 78 (SPEC-DATA-010) -- Performance, Capacity, Observability, SLOs & SRE Operations. New
`sre` PostgreSQL schema. Two owned entities per `04_DATA_MODEL_CATALOGUE.md`: `slo_definition` (5
fields) and `capacity_forecast` (7). **0 owned HTTP APIs** -- both are CI/SRE-tooling-populated,
same "no independent API" shape as Document 68's `release_security_evidence` (`commands.py` exposes
gateway commands with no router).

**Numbers are not guessed.** Document 109 (SPEC-DATA-012, APPROVED) `# 3. Performance SLOs by
operation class` supplies the p95/p99 targets for OC-1..OC-10; `# 4. Capacity baseline` supplies the
reference capacity dimensions. `registry.py::DOCUMENT_109_SLO_SEED` / `DOCUMENT_109_CAPACITY_SEED`
transcribe both tables verbatim.

No signature (Document 106 has no SPEC-DATA-010 row). No `tenant_id` (ADR-0006), no `site_id`
(platform-wide operation classes / capacity dimensions, not per-site). All numeric targets are
`BigInteger` milliseconds/counts -- never float.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class SloDefinition(Base):
    """Document 78 # 6 `slo_definition` -- one row per operation class / capability SLI, with p95/p99
    millisecond targets and the measurement window they apply to (SRE-FR-001/002/007)."""

    __tablename__ = "slo_definition"
    __table_args__ = (UniqueConstraint("operation_class"), {"schema": "sre"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_class: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "OC-1"
    sli_name: Mapped[str] = mapped_column(String(160), nullable=False)
    p95_target_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    p99_target_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    window: Mapped[str] = mapped_column(String(40), nullable=False, default="steady-state")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class CapacityForecast(Base):
    """Document 78 # 6 `capacity_forecast` -- one row per capacity dimension: current/reference value,
    growth assumption, forecast horizon and headroom (SRE-FR-005/006/033/034)."""

    __tablename__ = "capacity_forecast"
    __table_args__ = ({"schema": "sre"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dimension: Mapped[str] = mapped_column(String(120), nullable=False)
    reference_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_value: Mapped[int | None] = mapped_column(BigInteger)
    growth_rate_pct: Mapped[int | None] = mapped_column(BigInteger)  # basis points (1% = 100) -- integer, no float
    horizon_days: Mapped[int] = mapped_column(BigInteger, nullable=False, default=90)
    forecasted_value: Mapped[int | None] = mapped_column(BigInteger)
    headroom_pct: Mapped[int | None] = mapped_column(BigInteger)  # basis points
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
