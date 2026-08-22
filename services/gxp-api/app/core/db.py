from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy import DateTime
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
