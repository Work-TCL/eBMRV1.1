import os
import uuid

# Point the app at the dedicated test database *before* anything imports app.core.config
# (Settings is instantiated once at import time).
os.environ.setdefault(
    "GXP_DATABASE_URL",
    "postgresql+asyncpg://ebmr_new_gxp_app:" + os.environ.get("GXP_TEST_DB_APP_PW", "")
    + "@localhost:5432/ebmr_new_gxp_test",
)

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.modules.iam.models import Organization, Role, Site, User, UserSiteRole
from app.modules.signature.models import SignaturePolicy

DEMO_PASSWORD = "ChangeMe123!"

APP_TABLES = [
    "materials.material_issues",
    "materials.material_lot_dispositions",
    "materials.material_lots",
    "materials.materials",
    "ebmr.batch_releases",
    "ebmr.batch_reviews",
    "ebmr.batch_steps",
    "ebmr.batches",
    "ebmr.recipe_steps",
    "ebmr.recipes",
    "ebmr.products",
    "signature.signatures",
    "signature.signature_challenges",
    "signature.signature_policies",
    "vault.vault_versions",
    "mutation.idempotency_keys",
    "mutation.outbox_events",
    "mutation.command_receipts",
    "audit.audit_events",
    "iam.user_site_roles",
    "iam.qualifications",
    "iam.sod_rules",
    "iam.users",
    "iam.roles",
    "iam.sites",
    "iam.organizations",
]


@pytest.fixture(autouse=True)
async def clean_database():
    """Full truncate between tests. Simple and correct beats clever for a small test suite."""
    async with SessionLocal() as session:
        async with session.begin():
            await session.execute(text(f"TRUNCATE {', '.join(APP_TABLES)} CASCADE"))
    yield


@pytest.fixture
async def db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
async def seeded(db: AsyncSession) -> dict:
    """Same reference data as scripts/seed.py, inlined so tests don't depend on a separate run."""
    async with db.begin():
        org = Organization(name="Test Org")
        db.add(org)
        await db.flush()

        site = Site(organization_id=org.id, code="T1", name="Test Site")
        db.add(site)
        await db.flush()

        roles = {}
        for name in ("Admin", "Operator", "Supervisor", "QA Reviewer", "QA Releaser", "QC Reviewer"):
            role = Role(name=name)
            db.add(role)
            roles[name] = role
        await db.flush()

        users = {}
        for username, role_name in (
            ("operator1", "Operator"),
            ("qa.reviewer", "QA Reviewer"),
            ("qa.releaser", "QA Releaser"),
            ("qc.reviewer", "QC Reviewer"),
        ):
            user = User(
                username=username,
                email=f"{username}@example.com",
                full_name=username,
                password_hash=hash_password(DEMO_PASSWORD),
                status="active",
            )
            db.add(user)
            await db.flush()
            db.add(UserSiteRole(user_id=user.id, site_id=site.id, role_id=roles[role_name].id))
            users[username] = user

        db.add(
            SignaturePolicy(
                record_type="batch",
                action="review",
                meaning="Reviewed",
                required_role_id=roles["QA Reviewer"].id,
                requires_independent_signer=False,
            )
        )
        db.add(
            SignaturePolicy(
                record_type="batch",
                action="release",
                meaning="Released",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
            )
        )

    return {"org_id": org.id, "site_id": site.id, "roles": roles, "users": users}


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def login(client: AsyncClient, username: str) -> str:
    resp = await client.post("/auth/token", data={"username": username, "password": DEMO_PASSWORD})
    resp.raise_for_status()
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def idem() -> str:
    return str(uuid.uuid4())
