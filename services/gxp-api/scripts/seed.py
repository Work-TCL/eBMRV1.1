"""Seed the minimum reference data Phase 1 needs to be usable: one org/site, the five baseline roles,
the two global signature policies (review/release), and one demo user per role so the E2E walkthrough
can exercise segregation of duties (reviewer != releaser).

Run with: .venv/bin/python -m scripts.seed
"""

import asyncio

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.modules.iam.models import Organization, Role, Site, User, UserSiteRole
from app.modules.signature.models import SignaturePolicy

ROLE_NAMES = ["Admin", "Operator", "Supervisor", "QA Reviewer", "QA Releaser", "QC Reviewer"]

DEMO_USERS = [
    ("admin", "admin@example.com", "Admin User", "Admin"),
    ("operator1", "operator1@example.com", "Olivia Operator", "Operator"),
    ("qa.reviewer", "qa.reviewer@example.com", "Rita Reviewer", "QA Reviewer"),
    ("qa.releaser", "qa.releaser@example.com", "Ray Releaser", "QA Releaser"),
    ("qc.reviewer", "qc.reviewer@example.com", "Quinn QC", "QC Reviewer"),
]

DEMO_PASSWORD = "ChangeMe123!"


async def seed() -> None:
    async with SessionLocal() as session:
        async with session.begin():
            org = Organization(name="Demo Manufacturing Co.")
            session.add(org)
            await session.flush()

            site = Site(organization_id=org.id, code="SITE1", name="Demo Site 1")
            session.add(site)
            await session.flush()

            roles = {}
            for name in ROLE_NAMES:
                role = Role(name=name)
                session.add(role)
                roles[name] = role
            await session.flush()

            for username, email, full_name, role_name in DEMO_USERS:
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(DEMO_PASSWORD),
                    status="active",
                )
                session.add(user)
                await session.flush()
                session.add(UserSiteRole(user_id=user.id, site_id=site.id, role_id=roles[role_name].id))

            session.add(
                SignaturePolicy(
                    record_type="batch",
                    action="review",
                    meaning="Reviewed",
                    required_role_id=roles["QA Reviewer"].id,
                    requires_independent_signer=False,
                )
            )
            session.add(
                SignaturePolicy(
                    record_type="batch",
                    action="release",
                    meaning="Released",
                    required_role_id=roles["QA Releaser"].id,
                    requires_independent_signer=True,
                )
            )

        print(f"Seeded org={org.id} site={site.id} ({site.code})")
        print(f"Demo users (password '{DEMO_PASSWORD}' for all): {[u[0] for u in DEMO_USERS]}")
        print(f"site_id for API calls: {site.id}")


if __name__ == "__main__":
    asyncio.run(seed())
