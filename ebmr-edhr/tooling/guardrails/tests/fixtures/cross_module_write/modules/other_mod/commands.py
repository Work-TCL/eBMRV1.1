from app.modules.owner_mod.models import OwnedThing


async def do_something_bad(session):
    # violation: other_mod constructs and writes owner_mod's model directly, bypassing owner_mod's
    # own command/service.
    session.add(OwnedThing(id="x"))
