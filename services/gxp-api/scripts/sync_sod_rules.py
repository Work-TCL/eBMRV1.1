"""Idempotently sync the Document 107 SoD matrix (standing role pairs + action-independence rules) into
an already-seeded deployment.

`scripts.seed` also upserts `iam.sod_rules` from SOD_STANDING_ROLE_PAIRS / SOD_ACTION_INDEPENDENCE, but
only as part of a run that unconditionally creates a fresh organization, site and demo-user set -- so it
cannot be re-run against a live database to pick up a new or changed SoD rule. This script is the
narrow, re-runnable half, the same precedent as `sync_permissions.py` and `sync_signature_policies.py`.

It upserts rows by `code` and creates any that are missing. It never deletes a row: removing an SoD rule
loosens a control, which is exactly the failure mode Document 107 exists to prevent by accident -- if a
platform-floor rule must be retired, that is a deliberate, reviewed change, not a side effect of a sync.

A customer's Quality org maintains its own SoD matrix on top of this floor by inserting/updating
`iam.sod_rules` rows directly (Document 107 §3 is a data model, not code): a rule this script does not
manage (its `code` is not in the seed lists) is left untouched.

Run with: .venv/bin/python -m scripts.sync_sod_rules
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.iam.models import SodRule
from scripts.seed import SOD_ACTION_INDEPENDENCE, SOD_STANDING_ROLE_PAIRS


async def sync() -> None:
    created = updated = 0
    async with SessionLocal() as session:
        async with session.begin():
            for code, role_a, role_b, severity, rationale in SOD_STANDING_ROLE_PAIRS:
                existing = (
                    await session.execute(select(SodRule).where(SodRule.code == code))
                ).scalar_one_or_none()
                if existing is None:
                    session.add(
                        SodRule(
                            code=code,
                            rule_type="STANDING_ROLE_PAIR",
                            role_a=role_a,
                            role_b=role_b,
                            severity=severity,
                            rationale=rationale,
                            source_reference="Document 107",
                            policy_source="PLATFORM_FLOOR",
                        )
                    )
                    created += 1
                else:
                    if (existing.role_a, existing.role_b, existing.severity, existing.rationale) != (
                        role_a,
                        role_b,
                        severity,
                        rationale,
                    ):
                        updated += 1
                    existing.role_a = role_a
                    existing.role_b = role_b
                    existing.severity = severity
                    existing.rationale = rationale

            for code, record_class, action, independent_of, severity, rationale in SOD_ACTION_INDEPENDENCE:
                existing = (
                    await session.execute(select(SodRule).where(SodRule.code == code))
                ).scalar_one_or_none()
                if existing is None:
                    session.add(
                        SodRule(
                            code=code,
                            rule_type="ACTION_INDEPENDENCE",
                            record_class=record_class,
                            action=action,
                            independent_of=independent_of,
                            severity=severity,
                            rationale=rationale,
                            source_reference="Document 107",
                            policy_source="PLATFORM_FLOOR",
                        )
                    )
                    created += 1
                else:
                    if (
                        existing.record_class,
                        existing.action,
                        existing.independent_of,
                        existing.severity,
                        existing.rationale,
                    ) != (record_class, action, independent_of, severity, rationale):
                        updated += 1
                    existing.record_class = record_class
                    existing.action = action
                    existing.independent_of = independent_of
                    existing.severity = severity
                    existing.rationale = rationale

    total = len(SOD_STANDING_ROLE_PAIRS) + len(SOD_ACTION_INDEPENDENCE)
    print(f"sod rules: {created} created, {updated} updated, {total} in platform floor")


if __name__ == "__main__":
    asyncio.run(sync())
