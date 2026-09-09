"""Document 11 — read-side lookups and the readiness computation (BAT-FR-006) shared by commands.py and
the router. `compute_initial_step_states` runs once at issue; `recompute_readiness` runs after every
StepCompleted (SG-047 partial resolution, 2026-09-09) to advance the rest of the dependency graph.
"""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch, BatchStep, StepHold, StepResult
from app.modules.recipe_master import service as recipe_master_service
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


async def recompute_readiness(session: AsyncSession, batch: Batch) -> list[BatchStep]:
    """BAT-FR-006, runtime half (SG-047 partial resolution). Call after a step's state is already set to
    'complete' in this session (autoflush makes the change visible to the SELECT below even before commit).
    A 'pending' step becomes 'ready' once every one of its declared predecessors is 'complete'. Returns the
    steps this call flipped, for the caller to audit/emit events for -- it does not write audit/outbox
    itself (commands.py owns the regulated-mutation transaction boundary).
    """
    graph = await recipe_master_service.get_graph(session, batch.recipe_version_id)
    code_by_step_id = {s.id: s.stable_step_code for s in graph["steps"]}
    predecessors_of: dict[str, set[str]] = defaultdict(set)
    for dep in graph["dependencies"]:
        successor_code = code_by_step_id.get(dep.successor_step_id)
        predecessor_code = code_by_step_id.get(dep.predecessor_step_id)
        if successor_code and predecessor_code:
            predecessors_of[successor_code].add(predecessor_code)

    steps = await get_steps(session, batch.id)
    state_by_code = {s.recipe_step_code: s.state for s in steps}
    changed: list[BatchStep] = []
    for step in steps:
        if step.state != "pending":
            continue
        required_predecessors = predecessors_of.get(step.recipe_step_code, set())
        if required_predecessors and all(state_by_code.get(p) == "complete" for p in required_predecessors):
            step.state = "ready"
            step.version += 1
            changed.append(step)
    return changed


async def get_step_results(session: AsyncSession, step_id: uuid.UUID) -> list[StepResult]:
    return (
        (await session.execute(select(StepResult).where(StepResult.step_id == step_id).order_by(StepResult.received_at)))
        .scalars()
        .all()
    )


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

    # Recipe context (BAT-FR-005 "immutable parent instruction", Document 11 §9's execution-UI list:
    # instruction, required materials/equipment, target/limits) keyed by recipe_step_code so the caller
    # can join it onto each BatchStep without a second round trip. Reads the *live* recipe graph, not the
    # frozen execution snapshot's own copy (VLT-FR-006/007) -- the snapshot is Vault evidence, not a
    # queryable read path; this is display-only, not used for any regulated decision.
    graph = await recipe_master_service.get_graph(session, batch.recipe_version_id)
    code_by_step_id = {s.id: s.stable_step_code for s in graph["steps"]}
    step_by_code = {s.stable_step_code: s for s in graph["steps"]}
    section_by_id = {sec.id: sec for sec in graph["sections"]}

    parameters_by_code: dict[str, list] = defaultdict(list)
    for p in graph["parameters"]:
        code = code_by_step_id.get(p.step_id)
        if code:
            parameters_by_code[code].append(p)

    evidence_by_code: dict[str, list] = defaultdict(list)
    for e in graph["evidence"]:
        code = code_by_step_id.get(e.step_id)
        if code:
            evidence_by_code[code].append(e)

    predecessors_of: dict[str, list[str]] = defaultdict(list)
    successors_of: dict[str, list[str]] = defaultdict(list)
    for dep in graph["dependencies"]:
        successor_code = code_by_step_id.get(dep.successor_step_id)
        predecessor_code = code_by_step_id.get(dep.predecessor_step_id)
        if successor_code and predecessor_code:
            predecessors_of[successor_code].append(predecessor_code)
            successors_of[predecessor_code].append(successor_code)

    results_by_step_id: dict[uuid.UUID, list[StepResult]] = defaultdict(list)
    if steps:
        rows = (
            (await session.execute(select(StepResult).where(StepResult.step_id.in_([s.id for s in steps])).order_by(StepResult.received_at)))
            .scalars()
            .all()
        )
        for r in rows:
            results_by_step_id[r.step_id].append(r)

    # Active hold (released_at IS NULL) per step, for the "why is this on_hold" display -- at most one
    # active hold per step by construction (resume_step always closes the open row before a step can be
    # held again).
    active_hold_by_step_id: dict[uuid.UUID, StepHold] = {}
    if steps:
        hold_rows = (
            (
                await session.execute(
                    select(StepHold).where(StepHold.step_id.in_([s.id for s in steps]), StepHold.released_at.is_(None))
                )
            )
            .scalars()
            .all()
        )
        for h in hold_rows:
            active_hold_by_step_id[h.step_id] = h

    return {
        "batch": batch,
        "steps": steps,
        "step_by_code": step_by_code,
        "section_by_id": section_by_id,
        "parameters_by_code": parameters_by_code,
        "evidence_by_code": evidence_by_code,
        "predecessors_of": predecessors_of,
        "successors_of": successors_of,
        "results_by_step_id": results_by_step_id,
        "active_hold_by_step_id": active_hold_by_step_id,
        "blockers": [
            {"step_id": str(s.id), "recipe_step_code": s.recipe_step_code, "reason": "predecessor not yet completed"}
            for s in steps
            if s.state == "pending"
        ],
    }
