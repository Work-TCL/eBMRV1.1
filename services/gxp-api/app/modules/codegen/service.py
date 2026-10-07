"""next_code() -- the only entry point client requirement #1's auto-generation needs. Must always be
called inside the same transaction as the create command consuming the returned code (never pre-
reserved outside it), so a rolled-back command simply leaves a gap in the sequence -- an accepted,
standard property of a sequence, not a defect.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.codegen.models import NIL_SITE_ID, CodeSequenceCounter


async def next_code(
    session: AsyncSession, *, entity_type: str, prefix: str, site_id: uuid.UUID | None = None, pad: int = 6
) -> str:
    key_site_id = site_id if site_id is not None else NIL_SITE_ID

    await session.execute(
        pg_insert(CodeSequenceCounter)
        .values(id=uuid.uuid4(), entity_type=entity_type, site_id=key_site_id, prefix=prefix, last_value=0)
        .on_conflict_do_nothing(index_elements=["entity_type", "site_id", "prefix"])
    )
    result = await session.execute(
        select(CodeSequenceCounter)
        .where(
            CodeSequenceCounter.entity_type == entity_type,
            CodeSequenceCounter.site_id == key_site_id,
            CodeSequenceCounter.prefix == prefix,
        )
        .with_for_update()
    )
    counter = result.scalar_one()
    counter.last_value += 1
    await session.flush()
    return f"{prefix}-{counter.last_value:0{pad}d}"
