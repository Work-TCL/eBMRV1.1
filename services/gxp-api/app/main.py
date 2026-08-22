import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.batch.router import router as batch_router
from app.modules.iam.router import router as iam_router
from app.modules.iam.router import sites_router
from app.modules.material.router import lots_router as material_lots_router
from app.modules.material.router import router as material_router
from app.modules.mutation.models import OutboxEvent
from app.modules.product.router import router as product_router
from app.modules.recipe.router import router as recipe_router
from app.mutation.errors import GxPError

logger = logging.getLogger("gxp_api.outbox")


async def outbox_publisher_loop() -> None:
    """Phase 1 stand-in for a real bus (NATS in the original design). Reads committed, unpublished
    outbox rows and marks them published, logging instead of actually publishing anywhere — the
    transactional-outbox *pattern* (write in the same DB transaction as the domain change, publish only
    after commit) is what matters for the regulated guarantee; the transport is swappable later.
    """
    while True:
        try:
            async with SessionLocal() as session:
                async with session.begin():
                    result = await session.execute(
                        select(OutboxEvent)
                        .where(OutboxEvent.published_at.is_(None))
                        .order_by(OutboxEvent.occurred_at)
                        .limit(50)
                        .with_for_update(skip_locked=True)
                    )
                    pending = result.scalars().all()
                    for event in pending:
                        logger.info(
                            "publishing %s aggregate=%s/%s version=%s",
                            event.event_type,
                            event.aggregate_type,
                            event.aggregate_id,
                            event.aggregate_version,
                        )
                        event.published_at = datetime.now(timezone.utc)
        except Exception:  # noqa: BLE001 - never let the poller die the process
            logger.exception("outbox publisher iteration failed")
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(outbox_publisher_loop())
    yield
    task.cancel()


app = FastAPI(title="eBMR GxP Core", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Dev-only: the frontend can be reached via localhost, a LAN IP, or a public IP/hostname
    # depending on how this box is accessed, so match any origin on its port rather than one
    # fixed hostname. Tighten this to an explicit allowlist before any non-dev deployment.
    allow_origin_regex=r"^https?://[^/]+:4101$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(GxPError)
async def gxp_error_handler(request: Request, exc: GxPError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


app.include_router(iam_router)
app.include_router(sites_router)
app.include_router(product_router)
app.include_router(recipe_router)
app.include_router(batch_router)
app.include_router(material_router)
app.include_router(material_lots_router)
