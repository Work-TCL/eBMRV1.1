import uuid

from fastapi import APIRouter, Depends

from app.modules.a_mod.commands import UpdateThingCommand, update_thing

router = APIRouter()


@router.patch("/{thing_id}", response_model=dict)
async def patch_thing_generic(thing_id: uuid.UUID, payload: dict, session=Depends(object)):
    # violation: no typed *Command parameter -- looks like generic CRUD.
    for field, value in payload.items():
        setattr(thing_id, field, value)
    return {}


@router.patch("/{thing_id}/typed", response_model=dict)
async def patch_thing_typed(thing_id: uuid.UUID, cmd: UpdateThingCommand, session=Depends(object)):
    # allowed: PATCH verb but backed by a typed Command through the Mutation Gateway.
    return await update_thing(session, cmd)
