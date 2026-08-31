"""Document 11 — read-side lookups and the predecessor-only readiness slice (BAT-FR-006) shared by
commands.py and the router.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch, BatchStep
from app.modules.recipe_master.models import RecipeStepDependency
from app.mutation.errors import NotFoundError


async def get_batch(session: AsyncSession, batch_id: uuid.UUID) -> Batch:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    return batch


async def get_steps(session: AsyncSession, batch_id: uuid.UUID) -> list[BatchStep]:
    return (
        (await session.execute(select(BatchStep).where(BatchStep.batch_id == batch_id)))
        .scalars()
        .all()
    )


async def get_step(session: AsyncSession, batch_id: uuid.UUID, step_id: uuid.UUID) -> BatchStep:
    step = await session.get(BatchStep, step_id)
    if step is None or step.batch_id != batch_id:
        raise NotFoundError("Batch step not found")
    return step


def compute_initial_step_states(
    step_codes: list[str], dependencies: list[RecipeStepDependency], code_by_step_id: dict[uuid.UUID, str]
) -> dict[str, str]:
    """BAT-FR-006 predecessor-only slice: a step with no predecessor is immediately 'ready'; every step
    with at least one predecessor starts 'pending' -- it can only become 'ready' once every predecessor is
    'completed', a state this pass never produces (step completion needs gxp_step_result, SG-047). This is
    a real, if narrow, readiness computation: it is honest about starting most steps un-runnable rather
    than guessing at the missing material/equipment/personnel/hold/quality-blocker gating BAT-FR-006 also
    describes (SG-048).
    """
    has_predecessor = {code_by_step_id[dep.successor_step_id] for dep in dependencies if dep.successor_step_id in code_by_step_id}
    return {code: ("pending" if code in has_predecessor else "ready") for code in step_codes}


async def list_batches(session: AsyncSession, site_id: uuid.UUID, state: str | None = None) -> list[Batch]:
    """BAT-FR-035 (partial): the 'active batches + holds' slice of the production dashboard. Bottlenecks,
    overdue timers and operator-assignment analytics are not built -- they depend on capabilities SG-048
    defers (exceptions, timers, equipment/personnel context)."""
    stmt = select(Batch).where(Batch.site_id == site_id)
    if state is not None:
        stmt = stmt.where(Batch.state == state)
    return (await session.execute(stmt.order_by(Batch.created_at.desc()))).scalars().all()


async def get_execution_view(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    batch = await get_batch(session, batch_id)
    steps = await get_steps(session, batch_id)
    return {
        "batch": batch,
        "steps": steps,
        "blockers": [
            {"step_id": str(s.id), "recipe_step_code": s.recipe_step_code, "reason": "predecessor not yet completed"}
            for s in steps
            if s.state == "pending"
        ],
    }
