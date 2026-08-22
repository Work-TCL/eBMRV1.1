from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, create_access_token, get_current_actor
from app.modules.iam.models import Site
from app.modules.iam.service import authenticate, get_role_names

router = APIRouter(prefix="/auth", tags=["auth"])
sites_router = APIRouter(prefix="/sites", tags=["iam"])


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> dict:
    user = await authenticate(session, form_data.username, form_data.password)
    token = create_access_token(user.id, user.username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    sites = (await session.execute(select(Site))).scalars().all()
    roles_by_site = {
        str(site.id): sorted(await get_role_names(session, actor.user_id, site.id)) for site in sites
    }
    return {"user_id": str(actor.user_id), "username": actor.username, "roles_by_site": roles_by_site}


@sites_router.get("")
async def list_sites(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(select(Site))
    return [{"id": str(s.id), "code": s.code, "name": s.name} for s in result.scalars().all()]
