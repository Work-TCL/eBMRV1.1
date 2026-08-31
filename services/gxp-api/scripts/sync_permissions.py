"""Idempotently sync the Document 07/107 permission catalogue and role grants into an already-seeded
deployment.

`scripts.seed` also upserts these, but only as part of a run that unconditionally creates a fresh
organization, site and demo-user set -- so it cannot be re-run against a live database just to pick up
new permission codes. This script is the narrow, re-runnable half: it upserts `iam.permissions` from
PERMISSION_CATALOG and reconciles `iam.role_permissions` against ROLE_PERMISSIONS for roles that already
exist, and touches nothing else.

Grants present in the database but no longer in ROLE_PERMISSIONS are revoked, so this file stays the
single source of truth for who may do what -- authorization is data, and drift between the catalogue and
the database is exactly the failure mode the policy engine exists to prevent.

Run with: .venv/bin/python -m scripts.sync_permissions
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.iam.models import Permission, Role, RolePermission
from scripts.seed import PERMISSION_CATALOG, ROLE_PERMISSIONS


async def sync() -> None:
    created = updated = granted = revoked = 0
    async with SessionLocal() as session:
        async with session.begin():
            permissions: dict[str, Permission] = {}
            for code, action, resource_type, description in PERMISSION_CATALOG:
                existing = (
                    await session.execute(select(Permission).where(Permission.code == code))
                ).scalar_one_or_none()
                if existing is None:
                    existing = Permission(
                        code=code, action=action, resource_type=resource_type, description=description
                    )
                    session.add(existing)
                    created += 1
                else:
                    if (existing.action, existing.resource_type, existing.description) != (
                        action,
                        resource_type,
                        description,
                    ):
                        updated += 1
                    existing.action = action
                    existing.resource_type = resource_type
                    existing.description = description
                permissions[code] = existing
            await session.flush()

            for role_name, codes in ROLE_PERMISSIONS.items():
                role = (
                    await session.execute(select(Role).where(Role.name == role_name))
                ).scalar_one_or_none()
                if role is None:
                    # A role this deployment hasn't created yet -- inert, not an error, same treatment as
                    # the SoD floor's forward-declared role names.
                    print(f"  skip (role not in this deployment): {role_name}")
                    continue

                wanted = {permissions[code].id for code in codes}
                held = {
                    row.permission_id: row
                    for row in (
                        await session.execute(
                            select(RolePermission).where(RolePermission.role_id == role.id)
                        )
                    ).scalars()
                }
                for permission_id in wanted - held.keys():
                    session.add(RolePermission(role_id=role.id, permission_id=permission_id))
                    granted += 1
                for permission_id in held.keys() - wanted:
                    await session.delete(held[permission_id])
                    revoked += 1

    print(
        f"permissions: {created} created, {updated} updated, {len(PERMISSION_CATALOG)} total\n"
        f"grants:      {granted} added, {revoked} revoked"
    )


if __name__ == "__main__":
    asyncio.run(sync())
