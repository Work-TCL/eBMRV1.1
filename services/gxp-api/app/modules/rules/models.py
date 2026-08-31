import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class RuleDefinition(Base):
    """Document 08 (SPEC-GXP-006) — `gxp_rule_definition`. Lifecycle: draft -> validated -> released
    (immutable once released, RUL-FR-002) -> superseded/retired. `rounding_policy`/`precision_policy`/
    `unit_policy` are required at draft time (never optional) — see app/modules/rules/commands.py for
    why this sidesteps the still-open default-numeric-policy SPEC_GAP entirely."""

    __tablename__ = "gxp_rule_definition"
    __table_args__ = (
        UniqueConstraint("rule_id", "semantic_version"),
        {"schema": "rules"},
    )

    rule_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[str] = mapped_column(String(160), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(60), nullable=False)
    semantic_version: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1")
    scope: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    expression_ast: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_contract: Mapped[dict] = mapped_column(JSONB, nullable=False)
    output_contract: Mapped[dict] = mapped_column(JSONB, nullable=False)
    unit_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    precision_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rounding_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason_codes: Mapped[dict | None] = mapped_column(JSONB)
    engine_compatibility: Mapped[str | None] = mapped_column(String(80))
    released_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RuleEvaluation(Base):
    """`gxp_rule_evaluation` — append-only persisted result of evaluating a released rule (RUL-FR-022):
    a historical result is never recomputed under a later rule version, only re-read from here."""

    __tablename__ = "gxp_rule_evaluation"
    __table_args__ = {"schema": "rules"}

    evaluation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.gxp_rule_definition.rule_object_id"), nullable=False
    )
    aggregate_type: Mapped[str | None] = mapped_column(String(100))
    aggregate_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    aggregate_version: Mapped[int | None] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    inputs_or_refs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1")
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Document 110 (SG-143) CALC-FR-002/004/008 — additive, nullable (migration 0047): null on every
    # evaluation recorded before this column existed, and on any COMPUTED-outcome-free evaluation whose
    # rule declares no precision_policy.calculation_class (RUL-FR-022 historical rows are never
    # rewritten). `raw_result` is the pre-rounding value at the presentation stage; `result` remains the
    # rounded value actually used for the outcome. `applied_policy_version` binds the exact Document 110
    # policy version consulted (CALC-FR-004) so a historic evaluation recomputes identically even after a
    # later policy change (§8 acceptance criterion 4).
    raw_result: Mapped[dict | None] = mapped_column(JSONB)
    applied_policy_version: Mapped[str | None] = mapped_column(String(40))


class UnitOfMeasure(Base):
    """Document 110 §3 — `uom(code, dimension, base_unit, factor, offset, precision_dp, status,
    version)`. Released, versioned reference data (CALC-FR-006/N6): `status='released'` is what makes a
    code usable by the evaluator's UOM validation; a draft/obsolete row is not. `base_unit` is the code
    of this dimension's base unit (a row for the base unit itself names its own code, factor=1,
    offset=0) — not a boolean flag — so a value in any unit of a dimension can be normalized to the same
    reference point.

    No author/release command or router exists for this table yet (deliberately out of scope this pass
    per the SG-143 task decision — see docs/generated/18_SPEC_GAPS.md); rows are written directly by a
    controlled migration/seed or by test fixtures until that command surface is built."""

    __tablename__ = "gxp_uom"
    __table_args__ = (UniqueConstraint("code", "version"), {"schema": "rules"})

    uom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    dimension: Mapped[str] = mapped_column(String(40), nullable=False)
    base_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    factor: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    offset: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False, default=Decimal("0"))
    precision_dp: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class UomConversion(Base):
    """Document 110 §3 — `uom_conversion(from_code, to_code, factor, rounding_stage, version,
    effective_from)`. A rule's `unit_policy` may declare a variable's captured unit and a distinct
    `convert_to` unit; the evaluator resolves the released conversion effective as of evaluation time
    and converts before the expression sees the value (UOM_CONVERSION_UNAVAILABLE if none resolves).
    Conversion never happens implicitly in a query, projection or UI (§3)."""

    __tablename__ = "gxp_uom_conversion"
    __table_args__ = (UniqueConstraint("from_code", "to_code", "version"), {"schema": "rules"})

    conversion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_code: Mapped[str] = mapped_column(String(20), nullable=False)
    to_code: Mapped[str] = mapped_column(String(20), nullable=False)
    factor: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    rounding_stage: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    effective_from: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
