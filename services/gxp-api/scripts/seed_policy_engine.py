"""Idempotent-safe companion to scripts/seed.py for environments that already have an org/site/users
seeded (scripts/seed.py's org/site/user creation is NOT idempotent — re-running it creates a second
organization, which trips assert_single_organization's startup guard). This script only upserts the
Document 07/107 permission catalog, role->permission grants and SoD floor against whatever roles already
exist — safe to re-run any number of times.

Run with: .venv/bin/python -m scripts.seed_policy_engine
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.iam.models import Permission, Role, RolePermission, SodRule
from scripts.seed import PERMISSION_CATALOG, ROLE_PERMISSIONS, SOD_ACTION_INDEPENDENCE, SOD_STANDING_ROLE_PAIRS


async def seed_policy_engine() -> None:
    async with SessionLocal() as session:
        async with session.begin():
            roles = {r.name: r for r in (await session.execute(select(Role))).scalars().all()}

            permissions = {}
            for code, action, resource_type, description in PERMISSION_CATALOG:
                existing_permission = (
                    await session.execute(select(Permission).where(Permission.code == code))
                ).scalar_one_or_none()
                if existing_permission is None:
                    existing_permission = Permission(
                        code=code, action=action, resource_type=resource_type, description=description
                    )
                    session.add(existing_permission)
                    await session.flush()
                else:
                    existing_permission.action = action
                    existing_permission.resource_type = resource_type
                    existing_permission.description = description
                permissions[code] = existing_permission

            for role_name, codes in ROLE_PERMISSIONS.items():
                if role_name not in roles:
                    print(f"skip: role '{role_name}' does not exist in this deployment yet")
                    continue
                for code in codes:
                    existing_grant = (
                        await session.execute(
                            select(RolePermission).where(
                                RolePermission.role_id == roles[role_name].id,
                                RolePermission.permission_id == permissions[code].id,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing_grant is None:
                        session.add(
                            RolePermission(role_id=roles[role_name].id, permission_id=permissions[code].id)
                        )

            for code, role_a, role_b, severity, rationale in SOD_STANDING_ROLE_PAIRS:
                existing_rule = (
                    await session.execute(select(SodRule).where(SodRule.code == code))
                ).scalar_one_or_none()
                if existing_rule is None:
                    session.add(
                        SodRule(
                            code=code, rule_type="STANDING_ROLE_PAIR", role_a=role_a, role_b=role_b,
                            severity=severity, rationale=rationale, source_reference="Document 107",
                            policy_source="PLATFORM_FLOOR",
                        )
                    )

            for code, record_class, action, independent_of, severity, rationale in SOD_ACTION_INDEPENDENCE:
                existing_rule = (
                    await session.execute(select(SodRule).where(SodRule.code == code))
                ).scalar_one_or_none()
                if existing_rule is None:
                    session.add(
                        SodRule(
                            code=code, rule_type="ACTION_INDEPENDENCE", record_class=record_class,
                            action=action, independent_of=independent_of, severity=severity,
                            rationale=rationale, source_reference="Document 107",
                            policy_source="PLATFORM_FLOOR",
                        )
                    )

        print(f"Seeded {len(permissions)} permissions, SoD floor, and role grants for: {list(roles)}")


if __name__ == "__main__":
    asyncio.run(seed_policy_engine())
