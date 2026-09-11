from app.modules.owner_mod.models import OwnedThing


async def create_it(session):
    # allowed: owner_mod writes its own model.
    session.add(OwnedThing(id="x"))
