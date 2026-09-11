from sqlalchemy import select

from app.modules.owner_mod.models import OwnedThing


async def find_it(session, thing_id):
    # allowed: a read-only cross-module select, not a write.
    return (await session.execute(select(OwnedThing).where(OwnedThing.id == thing_id))).scalar_one_or_none()
