from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy import DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    # Every Mapped[datetime] column becomes TIMESTAMPTZ. Regulated timestamps are always UTC
    # (DATA-FR-018 / AUD-FR-003 equivalent) — a naive column would silently accept the wrong thing.
    type_annotation_map = {datetime: DateTime(timezone=True)}


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def assert_single_organization(session: AsyncSession) -> None:
    """REMEDIATION_R1 FIX 2 / ADR-0006: this deployment is single-tenant by design (isolation by
    deployment boundary, not row-level tenant scoping). Tenant isolation is therefore transitive
    (row -> site -> organization) rather than enforced by a tenant_id column a forgotten join could
    bypass — so a second organization appearing is the one way that assumption silently breaks. Make
    it loud instead: refuse to start rather than run with an isolation assumption that no longer holds.
    """
    from app.modules.iam.models import Organization

    count = (await session.execute(select(func.count()).select_from(Organization))).scalar_one()
    if count > 1:
        raise RuntimeError(
            "Single-tenant deployment (ADR-0006) but multiple organizations exist. "
            "Either revert the extra organization or adopt row-level tenancy (ADR-0006 Option B)."
        )
