"""Document 08 — read-side lookups shared by commands.py and the router."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rules.models import RuleDefinition, UnitOfMeasure, UomConversion
from app.mutation.errors import NotFoundError, UomConversionUnavailableError, UomUnknownError, ValidationFailedError


async def get_rule(session: AsyncSession, rule_object_id: uuid.UUID) -> RuleDefinition:
    rule = await session.get(RuleDefinition, rule_object_id)
    if rule is None:
        raise NotFoundError("Rule not found")
    return rule


async def list_released_rules(session: AsyncSession) -> list[dict]:
    """Read-only picker data: one row per `rule_id` that has a currently-effective released version
    (RUL-FR-003 — status=released, within the effective window). Same SG-081 read-side precedent as
    recipe_master's `GET /recipes/v2/families` and product_master's `GET /products/v1/business-ids`:
    a plain read-only GET listing does not conflict with any future write/CRUD contract, it only lets
    a caller (e.g. the Recipe Master dependency editor's `condition_rule_id` field) pick a real rule
    instead of hand-typing its identifier.
    """
    now = datetime.now(timezone.utc)
    rows = (
        (
            await session.execute(
                select(RuleDefinition)
                .where(
                    RuleDefinition.status == "released",
                    RuleDefinition.effective_from <= now,
                    (RuleDefinition.effective_to.is_(None)) | (RuleDefinition.effective_to > now),
                )
                .order_by(RuleDefinition.rule_id, RuleDefinition.effective_from)
            )
        )
        .scalars()
        .all()
    )
    latest: dict[str, RuleDefinition] = {}
    for row in rows:
        latest[row.rule_id] = row  # last wins => newest effective_from per rule_id
    return [
        {
            "rule_id": r.rule_id,
            "rule_type": r.rule_type,
            "semantic_version": r.semantic_version,
            "effective_from": r.effective_from.isoformat() if r.effective_from else None,
            "effective_to": r.effective_to.isoformat() if r.effective_to else None,
        }
        for r in sorted(latest.values(), key=lambda x: x.rule_id)
    ]


async def list_versions(session: AsyncSession, rule_id: str) -> list[RuleDefinition]:
    return (
        (
            await session.execute(
                select(RuleDefinition)
                .where(RuleDefinition.rule_id == rule_id)
                .order_by(RuleDefinition.created_at)
            )
        )
        .scalars()
        .all()
    )


async def get_effective_released_rule(session: AsyncSession, rule_id: str) -> RuleDefinition:
    """RUL-FR-003 — the currently effective released version: status=released, within effective
    window. Fail-closed if none resolves (same discipline as the signature-policy resolver — an
    unresolved rule is a hard stop, never an implicit pass)."""
    now = datetime.now(timezone.utc)
    candidates = (
        await session.execute(
            select(RuleDefinition).where(
                RuleDefinition.rule_id == rule_id,
                RuleDefinition.status == "released",
                RuleDefinition.effective_from <= now,
                (RuleDefinition.effective_to.is_(None)) | (RuleDefinition.effective_to > now),
            )
        )
    ).scalars().all()
    if not candidates:
        raise NotFoundError("No effective released version resolves for this rule", rule_id=rule_id)
    if len(candidates) > 1:
        # Defensive only — release_rule() rejects an overlapping effective window before release, so
        # this branch means the data itself is inconsistent, not a normal "not found" case.
        raise ValidationFailedError(
            "More than one effective released version resolves for this rule — overlapping effective "
            "windows are a data error, not a valid state",
            rule_id=rule_id,
        )
    return candidates[0]


async def resolve_uom(session: AsyncSession, code: str) -> UnitOfMeasure:
    """Document 110 §3/CALC-FR-006 — the latest *released* version of a UOM code. UOM_UNKNOWN (not
    NOT_FOUND) is the module-scoped code Document 110 §5 declares for this condition."""
    row = (
        await session.execute(
            select(UnitOfMeasure)
            .where(UnitOfMeasure.code == code, UnitOfMeasure.status == "released")
            .order_by(UnitOfMeasure.version.desc())
        )
    ).scalars().first()
    if row is None:
        raise UomUnknownError(f"No released UOM resolves for code {code!r}", code=code)
    return row


async def resolve_conversion(
    session: AsyncSession, from_code: str, to_code: str, as_of: datetime
) -> UomConversion:
    """Document 110 §3 — the released conversion effective as of `as_of`. Conversion is released,
    versioned data; the evaluator never derives a factor implicitly (§3)."""
    row = (
        await session.execute(
            select(UomConversion)
            .where(
                UomConversion.from_code == from_code,
                UomConversion.to_code == to_code,
                UomConversion.status == "released",
                UomConversion.effective_from <= as_of,
            )
            .order_by(UomConversion.version.desc())
        )
    ).scalars().first()
    if row is None:
        raise UomConversionUnavailableError(
            f"No released conversion from {from_code!r} to {to_code!r} resolves as of {as_of.isoformat()}",
            from_code=from_code,
            to_code=to_code,
        )
    return row
