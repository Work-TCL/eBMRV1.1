"""Document 10 — read-side lookups, the dependency-graph algorithms (RCP-FR-007), and the completeness/
issue-eligibility/compare gates shared by commands.py and the router.
"""

import uuid
from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recipe_master.models import (
    RecipeEvidenceRequirement,
    RecipeParameter,
    RecipeSection,
    RecipeStep,
    RecipeStepDependency,
    RecipeVersion,
    STEP_TYPES,
)
from app.modules.rules import service as rules_service
from app.mutation.errors import NotFoundError


async def get_version(session: AsyncSession, recipe_version_id: uuid.UUID) -> RecipeVersion:
    version = await session.get(RecipeVersion, recipe_version_id)
    if version is None:
        raise NotFoundError("Recipe version not found")
    return version


async def list_versions_for_family(session: AsyncSession, recipe_family_id: uuid.UUID) -> list[RecipeVersion]:
    return (
        (
            await session.execute(
                select(RecipeVersion)
                .where(RecipeVersion.recipe_family_id == recipe_family_id)
                .order_by(RecipeVersion.version_no)
            )
        )
        .scalars()
        .all()
    )


async def get_graph(session: AsyncSession, recipe_version_id: uuid.UUID) -> dict:
    sections = (
        (await session.execute(select(RecipeSection).where(RecipeSection.recipe_version_id == recipe_version_id).order_by(RecipeSection.sequence)))
        .scalars()
        .all()
    )
    steps = (
        (await session.execute(select(RecipeStep).where(RecipeStep.recipe_version_id == recipe_version_id).order_by(RecipeStep.sequence_hint)))
        .scalars()
        .all()
    )
    step_ids = [s.id for s in steps]
    dependencies = []
    if step_ids:
        dependencies = (
            (await session.execute(select(RecipeStepDependency).where(RecipeStepDependency.predecessor_step_id.in_(step_ids))))
            .scalars()
            .all()
        )
    parameters = []
    evidence = []
    if step_ids:
        parameters = (await session.execute(select(RecipeParameter).where(RecipeParameter.step_id.in_(step_ids)))).scalars().all()
        evidence = (
            (await session.execute(select(RecipeEvidenceRequirement).where(RecipeEvidenceRequirement.step_id.in_(step_ids))))
            .scalars()
            .all()
        )
    return {"sections": sections, "steps": steps, "dependencies": dependencies, "parameters": parameters, "evidence": evidence}


def detect_cycles(steps: list[RecipeStep], dependencies: list[RecipeStepDependency]) -> list[str]:
    """RCP-FR-007: directed dependency graph must have no cycles (unless an explicitly modelled
    repeat/rework structure is used -- not built this pass, see SG-046). DFS with a recursion stack.
    Returns the stable_step_codes involved in a detected cycle, or [] if the graph is acyclic.
    """
    by_id = {s.id: s.stable_step_code for s in steps}
    adjacency: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for dep in dependencies:
        adjacency[dep.predecessor_step_id].append(dep.successor_step_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[uuid.UUID, int] = {s.id: WHITE for s in steps}
    path: list[uuid.UUID] = []

    def visit(node: uuid.UUID) -> list[uuid.UUID] | None:
        color[node] = GRAY
        path.append(node)
        for neighbor in adjacency.get(node, []):
            if color.get(neighbor) == GRAY:
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]
            if color.get(neighbor) == WHITE:
                result = visit(neighbor)
                if result is not None:
                    return result
        path.pop()
        color[node] = BLACK
        return None

    for step in steps:
        if color[step.id] == WHITE:
            cycle = visit(step.id)
            if cycle:
                return [by_id[n] for n in cycle]
    return []


def find_unreachable_steps(steps: list[RecipeStep], dependencies: list[RecipeStepDependency]) -> list[str]:
    """A step with no predecessor is a root. Any step never reached by forward traversal from a root
    (and that isn't itself a root) is unreachable -- an authoring mistake, not a valid parallel branch."""
    step_ids = {s.id for s in steps}
    has_predecessor = {dep.successor_step_id for dep in dependencies}
    roots = [sid for sid in step_ids if sid not in has_predecessor]

    adjacency: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for dep in dependencies:
        adjacency[dep.predecessor_step_id].append(dep.successor_step_id)

    visited: set[uuid.UUID] = set()
    queue = deque(roots)
    visited.update(roots)
    while queue:
        node = queue.popleft()
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    by_id = {s.id: s.stable_step_code for s in steps}
    return sorted(by_id[sid] for sid in step_ids - visited)


async def validate_completeness(session: AsyncSession, recipe_version_id: uuid.UUID) -> list[str]:
    """RCP-FR-030: graph validity, missing rules, unsupported step types. Never a regulatory judgment
    about whether the recipe content itself is correct -- purely structural."""
    findings: list[str] = []
    graph = await get_graph(session, recipe_version_id)
    steps: list[RecipeStep] = graph["steps"]
    dependencies: list[RecipeStepDependency] = graph["dependencies"]
    parameters: list[RecipeParameter] = graph["parameters"]

    if not steps:
        findings.append("recipe has no steps")
        return findings

    for step in steps:
        if step.step_type not in STEP_TYPES:
            findings.append(f"step '{step.stable_step_code}' has an unsupported step_type '{step.step_type}'")

    cycle = detect_cycles(steps, dependencies)
    if cycle:
        findings.append(f"dependency graph contains a cycle: {' -> '.join(cycle)}")

    unreachable = find_unreachable_steps(steps, dependencies)
    for code in unreachable:
        findings.append(f"step '{code}' is unreachable from any root step")

    rule_refs: set[tuple[str, str | None]] = set()
    for dep in dependencies:
        if dep.condition_rule_id:
            rule_refs.add((dep.condition_rule_id, dep.condition_rule_version))
    for param in parameters:
        if param.rule_id:
            rule_refs.add((param.rule_id, param.rule_version))

    for rule_id, _rule_version in rule_refs:
        try:
            await rules_service.get_effective_released_rule(session, rule_id=rule_id)
        except NotFoundError:
            findings.append(f"referenced rule '{rule_id}' has no effective released version")

    return findings


def check_issue_eligibility(version: RecipeVersion, findings: list[str]) -> dict:
    lifecycle_ok = version.lifecycle_state == "released"
    return {
        "eligible": lifecycle_ok and not findings,
        "checks": {
            "lifecycle_state": version.lifecycle_state,
            "lifecycle_ok": lifecycle_ok,
            "completeness_findings": findings,
        },
    }


async def compare_versions(session: AsyncSession, version_id: uuid.UUID, other_version_id: uuid.UUID) -> dict:
    """RCP-FR-034: semantic diff by stable_section_code/stable_step_code -- added/removed/changed."""
    graph_a = await get_graph(session, version_id)
    graph_b = await get_graph(session, other_version_id)

    sections_a = {s.stable_section_code: s for s in graph_a["sections"]}
    sections_b = {s.stable_section_code: s for s in graph_b["sections"]}
    steps_a = {s.stable_step_code: s for s in graph_a["steps"]}
    steps_b = {s.stable_step_code: s for s in graph_b["steps"]}

    def diff_map(a: dict, b: dict, fields: list[str]) -> dict:
        added = sorted(set(b) - set(a))
        removed = sorted(set(a) - set(b))
        changed = []
        for key in sorted(set(a) & set(b)):
            deltas = {f: (getattr(a[key], f), getattr(b[key], f)) for f in fields if getattr(a[key], f) != getattr(b[key], f)}
            if deltas:
                changed.append({"code": key, "changes": {f: {"from": str(old), "to": str(new)} for f, (old, new) in deltas.items()}})
        return {"added": added, "removed": removed, "changed": changed}

    return {
        "sections": diff_map(sections_a, sections_b, ["name", "sequence"]),
        "steps": diff_map(steps_a, steps_b, ["step_type", "instruction_text", "is_critical", "required_role_code"]),
    }
