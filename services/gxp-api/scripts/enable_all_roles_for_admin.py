"""Demo-convenience: create every role in ROLE_NAMES that a live DB is missing, and assign all roles
to the `admin` demo user at the demo site so the whole application surface is exercisable.

Idempotent. Run with: .venv/bin/python -m scripts.enable_all_roles_for_admin

This does NOT touch permission grants -- run `scripts.sync_permissions` afterwards to reconcile
iam.role_permissions against ROLE_PERMISSIONS for the newly-created roles.
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.iam.models import Role, Site, User, UserSiteRole
from scripts.seed import ROLE_NAMES


async def run() -> None:
    created_roles = assigned = 0
    async with SessionLocal() as session:
        async with session.begin():
            existing = {
                r.name: r
                for r in (await session.execute(select(Role))).scalars().all()
            }
            for name in ROLE_NAMES:
                if name not in existing:
                    role = Role(name=name)
                    session.add(role)
                    existing[name] = role
                    created_roles += 1
            await session.flush()

            admin = (
                await session.execute(select(User).where(User.username == "admin"))
            ).scalar_one_or_none()
            if admin is None:
                print("no `admin` user -- run scripts.seed first")
                return
            site = (await session.execute(select(Site).limit(1))).scalar_one_or_none()
            if site is None:
                print("no site -- run scripts.seed first")
                return

            held = {
                usr.role_id
                for usr in (
                    await session.execute(
                        select(UserSiteRole).where(
                            UserSiteRole.user_id == admin.id, UserSiteRole.site_id == site.id
                        )
                    )
                ).scalars().all()
            }
            for name in ROLE_NAMES:
                rid = existing[name].id
                if rid not in held:
                    session.add(UserSiteRole(user_id=admin.id, site_id=site.id, role_id=rid))
                    assigned += 1

    print(f"roles: {created_roles} created ({len(ROLE_NAMES)} total)")
    print(f"admin @ {site.code}: {assigned} role(s) assigned")


if __name__ == "__main__":
    asyncio.run(run())
