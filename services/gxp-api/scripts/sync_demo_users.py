"""Idempotently sync DEMO_USERS into an already-seeded deployment.

`scripts.seed` also creates these, but only as part of a run that unconditionally creates a fresh
organization, site and demo-user set (no upsert) -- so it cannot be re-run against a live database just
to pick up newly-added demo personas (e.g. a role that existed with no login to demo it, same class of
gap `DEMO_USERS`' own comments already note for ddcp.operator2/ddcp.engineer). This script is the narrow,
re-runnable half, same precedent as `sync_permissions.py`/`sync_signature_policies.py`: for every entry
in `DEMO_USERS` missing from this deployment (matched by username), it creates the user and grants the
role at the deployment's site, and touches nothing else. Existing users are left untouched.

Assumes a single-site deployment (this codebase's only seeded topology so far) -- resolves the site as
whichever one row `iam.sites` has; fails loudly if that assumption doesn't hold rather than guessing.

Run with: .venv/bin/python -m scripts.sync_demo_users
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.modules.iam.models import Role, Site, User, UserSiteRole
from scripts.seed import DEMO_PASSWORD, DEMO_USERS


async def sync() -> None:
    created = skipped_existing = skipped_no_role = 0
    async with SessionLocal() as session:
        async with session.begin():
            sites = (await session.execute(select(Site))).scalars().all()
            if len(sites) != 1:
                raise RuntimeError(
                    f"Expected exactly one site in this deployment, found {len(sites)} -- "
                    "this script assumes the single-site topology scripts.seed() creates."
                )
            site = sites[0]

            for username, email, full_name, role_name in DEMO_USERS:
                existing = (
                    await session.execute(select(User).where(User.username == username))
                ).scalar_one_or_none()
                if existing is not None:
                    skipped_existing += 1
                    continue

                role = (
                    await session.execute(select(Role).where(Role.name == role_name))
                ).scalar_one_or_none()
                if role is None:
                    print(f"  skip (role not in this deployment): {username} -> {role_name}")
                    skipped_no_role += 1
                    continue

                user = User(
                    username=username, email=email, full_name=full_name,
                    password_hash=hash_password(DEMO_PASSWORD), status="active",
                )
                session.add(user)
                await session.flush()
                session.add(UserSiteRole(user_id=user.id, site_id=site.id, role_id=role.id))
                created += 1
                print(f"  created: {username} ({role_name})")

    print(f"demo users: {created} created, {skipped_existing} already existed, {skipped_no_role} skipped (role missing)")


if __name__ == "__main__":
    asyncio.run(sync())
