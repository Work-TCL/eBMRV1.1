"""Document 13 — the graph engine: node/edge creation (internal only -- no public write API exists,
Document 13 §8), correction, consistency/cycle rules, and the recursive-CTE traversal queries backing the
5 read-only APIs. Callers today are test setup code standing in for the domain-event consumers Document
13 §8 describes (MaterialConsumed, DrugBatchProduced, ...) -- none of which exist yet (SG-052).
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.genealogy.models import ANCESTRY_EDGE_TYPES, EDGE_TYPES, NODE_TYPES, GenealogyEdge, GenealogyNode
from app.modules.rules import service as rules_service
from app.mutation.errors import NotFoundError, UomUnknownError, ValidationFailedError
from app.mutation.gateway import write_audit_event, write_outbox_event

MAX_TRAVERSAL_DEPTH = 50  # GEN-FR-025: bounded traversal guard


async def _resolve_uom_id(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    """SG-146 (remainder, module 4 of 8), MIG-FR-004 expand step."""
    if not uom:
        return None
    try:
        row = await rules_service.resolve_uom(session, uom)
    except UomUnknownError:
        return None
    return row.uom_id


async def get_node(session: AsyncSession, node_id: uuid.UUID) -> GenealogyNode:
    node = await session.get(GenealogyNode, node_id)
    if node is None:
        raise NotFoundError("Genealogy node not found")
    return node


async def lookup(
    session: AsyncSession, site_id: uuid.UUID, *, node_type: str | None = None, business_ref: str | None = None
) -> list[GenealogyNode]:
    stmt = select(GenealogyNode).where(GenealogyNode.site_id == site_id)
    if node_type is not None:
        stmt = stmt.where(GenealogyNode.node_type == node_type)
    if business_ref is not None:
        stmt = stmt.where(GenealogyNode.business_ref == business_ref)
    return (await session.execute(stmt.order_by(GenealogyNode.created_at.desc()))).scalars().all()


async def _one_hop_ancestors(session: AsyncSession, node_id: uuid.UUID, edge_types: tuple[str, ...]) -> list[GenealogyEdge]:
    return (
        (
            await session.execute(
                select(GenealogyEdge).where(
                    GenealogyEdge.to_node_id == node_id, GenealogyEdge.state == "ACTIVE", GenealogyEdge.edge_type.in_(edge_types)
                )
            )
        )
        .scalars()
        .all()
    )


async def get_ancestors(session: AsyncSession, node_id: uuid.UUID, *, max_depth: int = MAX_TRAVERSAL_DEPTH) -> dict:
    """GEN-FR-004 backward trace: walks GenealogyEdge.to_node_id == current, moving to from_node_id,
    breadth-first with a visited set (GEN-FR-025 depth bound + cycle-safety even though ancestry edges
    are validated acyclic at write time, GEN-FR-024)."""
    await get_node(session, node_id)  # 404s cleanly if the root doesn't exist
    visited: dict[uuid.UUID, int] = {}
    edges_by_id: dict[uuid.UUID, GenealogyEdge] = {}
    frontier = {node_id}
    depth = 0
    truncated = False
    while frontier and depth < max_depth:
        edges: list[GenealogyEdge] = []
        for n in frontier:
            edges.extend(await _one_hop_ancestors(session, n, ANCESTRY_EDGE_TYPES))
        depth += 1
        next_frontier: set[uuid.UUID] = set()
        for e in edges:
            edges_by_id[e.id] = e
            if e.from_node_id not in visited:
                visited[e.from_node_id] = depth
                next_frontier.add(e.from_node_id)
        frontier = next_frontier
        if frontier and depth >= max_depth:
            truncated = True
    nodes = (
        (await session.execute(select(GenealogyNode).where(GenealogyNode.id.in_(visited.keys())))).scalars().all()
        if visited
        else []
    )
    return {
        "root_node_id": node_id,
        "nodes": nodes,
        "edge_ids": list(edges_by_id.keys()),
        "edges": list(edges_by_id.values()),
        "truncated": truncated,
    }


async def _one_hop_descendants(session: AsyncSession, node_id: uuid.UUID, edge_types: tuple[str, ...]) -> list[GenealogyEdge]:
    return (
        (
            await session.execute(
                select(GenealogyEdge).where(
                    GenealogyEdge.from_node_id == node_id, GenealogyEdge.state == "ACTIVE", GenealogyEdge.edge_type.in_(edge_types)
                )
            )
        )
        .scalars()
        .all()
    )


async def get_descendants(session: AsyncSession, node_id: uuid.UUID, *, max_depth: int = MAX_TRAVERSAL_DEPTH) -> dict:
    """GEN-FR-003 forward trace: mirror of get_ancestors, walking edges forward."""
    await get_node(session, node_id)
    visited: dict[uuid.UUID, int] = {}
    edges_by_id: dict[uuid.UUID, GenealogyEdge] = {}
    frontier = {node_id}
    depth = 0
    truncated = False
    while frontier and depth < max_depth:
        edges: list[GenealogyEdge] = []
        for n in frontier:
            edges.extend(await _one_hop_descendants(session, n, ANCESTRY_EDGE_TYPES))
        depth += 1
        next_frontier: set[uuid.UUID] = set()
        for e in edges:
            edges_by_id[e.id] = e
            if e.to_node_id not in visited:
                visited[e.to_node_id] = depth
                next_frontier.add(e.to_node_id)
        frontier = next_frontier
        if frontier and depth >= max_depth:
            truncated = True
    nodes = (
        (await session.execute(select(GenealogyNode).where(GenealogyNode.id.in_(visited.keys())))).scalars().all()
        if visited
        else []
    )
    return {
        "root_node_id": node_id,
        "nodes": nodes,
        "edge_ids": list(edges_by_id.keys()),
        "edges": list(edges_by_id.values()),
        "truncated": truncated,
    }


FINAL_PRODUCT_NODE_TYPES = (
    "device_unit",
    "combination_product_lot",
    "combination_product_serial",
    "package",
    "carton",
    "pallet",
    "distribution_reference",
)


async def full_trace(session: AsyncSession, site_id: uuid.UUID, serial: str) -> dict:
    """GEN-FR-004/010: given a serial's business_ref, return its full backward + forward trace."""
    node = (
        await session.execute(select(GenealogyNode).where(GenealogyNode.site_id == site_id, GenealogyNode.business_ref == serial))
    ).scalar_one_or_none()
    if node is None:
        raise NotFoundError("No genealogy node found for that serial")
    ancestors = await get_ancestors(session, node.id)
    descendants = await get_descendants(session, node.id)
    return {"root": node, "ancestors": ancestors, "descendants": descendants}


async def affected_products(session: AsyncSession, site_id: uuid.UUID, lot_business_ref: str) -> dict:
    """GEN-FR-003/018/020: forward trace from a material/supplier lot, filtered to final-product-shaped
    node types -- the 'affected final products' slice of GEN-FR-018's recall query. Quality-event
    cross-reference is not built (no quality module exists yet, SG-052)."""
    node = (
        await session.execute(
            select(GenealogyNode).where(GenealogyNode.site_id == site_id, GenealogyNode.business_ref == lot_business_ref)
        )
    ).scalar_one_or_none()
    if node is None:
        raise NotFoundError("No genealogy node found for that lot business_ref")
    descendants = await get_descendants(session, node.id)
    affected = [n for n in descendants["nodes"] if n.node_type in FINAL_PRODUCT_NODE_TYPES]
    return {"root": node, "affected_products": affected, "truncated": descendants["truncated"]}


# ---------------------------------------------------------------------------
# Internal write path (GEN-FR-001/002/006/007/008/016/017/023/024) -- no public command/router calls
# these; they stand in for the domain-event consumer Document 13 §8 describes.
# ---------------------------------------------------------------------------


async def create_node(
    session: AsyncSession,
    *,
    site_id: uuid.UUID,
    node_type: str,
    business_ref: str | None = None,
    authoritative_record_type: str | None = None,
    authoritative_record_id: uuid.UUID | None = None,
    authoritative_version: int | None = None,
    record_hash: str | None = None,
    actor_user_id: uuid.UUID,
) -> GenealogyNode:
    if node_type not in NODE_TYPES:
        raise ValidationFailedError("Unknown genealogy node_type", node_type=node_type, allowed=list(NODE_TYPES))

    node = GenealogyNode(
        site_id=site_id,
        node_type=node_type,
        business_ref=business_ref,
        authoritative_record_type=authoritative_record_type,
        authoritative_record_id=authoritative_record_id,
        authoritative_version=authoritative_version,
        record_hash=record_hash,
    )
    session.add(node)
    await session.flush()

    correlation_id = uuid.uuid4()
    await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="genealogy_node",
        aggregate_id=node.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"node_type": node_type, "business_ref": business_ref},
    )
    await write_outbox_event(
        session,
        event_type="GenealogyNodeCreated",
        aggregate_type="genealogy_node",
        aggregate_id=node.id,
        aggregate_version=1,
        payload={"id": str(node.id), "node_type": node_type},
        correlation_id=correlation_id,
    )
    return node


async def _would_close_cycle(session: AsyncSession, from_node_id: uuid.UUID, to_node_id: uuid.UUID) -> bool:
    """GEN-FR-024: adding from_node_id -> to_node_id closes a cycle iff from_node_id is already
    reachable as a descendant of to_node_id (i.e. a path to_node_id -> ... -> from_node_id already
    exists over ancestry edge types)."""
    if from_node_id == to_node_id:
        return True
    descendants = await get_descendants(session, to_node_id)
    return from_node_id in {n.id for n in descendants["nodes"]}


async def create_edge(
    session: AsyncSession,
    *,
    from_node_id: uuid.UUID,
    to_node_id: uuid.UUID,
    edge_type: str,
    quantity: Decimal | None = None,
    uom: str | None = None,
    step_id: uuid.UUID | None = None,
    source_event_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID,
) -> GenealogyEdge:
    if edge_type not in EDGE_TYPES:
        raise ValidationFailedError("Unknown genealogy edge_type", edge_type=edge_type, allowed=list(EDGE_TYPES))
    if from_node_id == to_node_id:
        raise ValidationFailedError("Genealogy edges cannot self-reference (from_node_id == to_node_id)")

    # GEN-FR-023 (no duplicate exact edges) + idempotent-by-source-event-id (Document 13 §8): Postgres
    # treats NULL != NULL, so the DB's own UNIQUE(from,to,edge_type,source_event_id) constraint can't
    # catch two source-event-less duplicates on its own -- check explicitly against any existing ACTIVE
    # edge with the same (from, to, edge_type) regardless of source_event_id.
    existing = (
        await session.execute(
            select(GenealogyEdge).where(
                GenealogyEdge.from_node_id == from_node_id,
                GenealogyEdge.to_node_id == to_node_id,
                GenealogyEdge.edge_type == edge_type,
                GenealogyEdge.state == "ACTIVE",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if source_event_id is not None and existing.source_event_id == source_event_id:
            return existing  # idempotent replay of the same source event (Document 13 §8)
        raise ValidationFailedError(
            "Duplicate exact genealogy edge (same from/to/edge_type already exists)",
            from_node_id=str(from_node_id),
            to_node_id=str(to_node_id),
            edge_type=edge_type,
        )

    await get_node(session, from_node_id)
    await get_node(session, to_node_id)

    if edge_type in ANCESTRY_EDGE_TYPES and await _would_close_cycle(session, from_node_id, to_node_id):
        raise ValidationFailedError(
            "This edge would close an ancestry cycle", from_node_id=str(from_node_id), to_node_id=str(to_node_id)
        )

    edge = GenealogyEdge(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_type=edge_type,
        quantity=quantity,
        uom=uom,
        uom_id=await _resolve_uom_id(session, uom),
        step_id=step_id,
        source_event_id=source_event_id,
        state="ACTIVE",
    )
    session.add(edge)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ValidationFailedError(
            "Duplicate exact genealogy edge (same from/to/edge_type/source_event_id)",
            from_node_id=str(from_node_id),
            to_node_id=str(to_node_id),
            edge_type=edge_type,
        ) from exc

    correlation_id = uuid.uuid4()
    await write_audit_event(
        session,
        site_id=None,
        aggregate_type="genealogy_edge",
        aggregate_id=edge.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"from_node_id": str(from_node_id), "to_node_id": str(to_node_id), "edge_type": edge_type},
    )
    await write_outbox_event(
        session,
        event_type="GenealogyEdgeCreated",
        aggregate_type="genealogy_edge",
        aggregate_id=edge.id,
        aggregate_version=1,
        payload={"id": str(edge.id), "edge_type": edge_type},
        correlation_id=correlation_id,
    )
    return edge


async def correct_edge(
    session: AsyncSession,
    *,
    edge_id: uuid.UUID,
    correct_from_node_id: uuid.UUID,
    correct_to_node_id: uuid.UUID,
    correct_edge_type: str,
    reason: str,
    actor_user_id: uuid.UUID,
) -> GenealogyEdge:
    """GEN-FR-016/017: the original edge is never deleted or edited -- it's flagged SUPERSEDED and a new
    edge referencing it via supersedes_edge_id is created in the same transaction."""
    original = (
        await session.execute(select(GenealogyEdge).where(GenealogyEdge.id == edge_id).with_for_update())
    ).scalar_one_or_none()
    if original is None:
        raise NotFoundError("Genealogy edge not found")
    if original.state != "ACTIVE":
        raise ValidationFailedError("Only an ACTIVE edge can be corrected", current_state=original.state)

    original.state = "SUPERSEDED"

    correction = await create_edge(
        session,
        from_node_id=correct_from_node_id,
        to_node_id=correct_to_node_id,
        edge_type=correct_edge_type,
        actor_user_id=actor_user_id,
    )
    correction.supersedes_edge_id = original.id
    await session.flush()

    correlation_id = uuid.uuid4()
    await write_audit_event(
        session,
        site_id=None,
        aggregate_type="genealogy_edge",
        aggregate_id=original.id,
        aggregate_version=1,
        action="Corrected",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=reason,
        old_value={"state": "ACTIVE"},
        new_value={"state": "SUPERSEDED", "corrected_by_edge_id": str(correction.id)},
    )
    await write_outbox_event(
        session,
        event_type="GenealogyEdgeCorrected",
        aggregate_type="genealogy_edge",
        aggregate_id=original.id,
        aggregate_version=1,
        payload={"id": str(original.id), "corrected_by_edge_id": str(correction.id)},
        correlation_id=correlation_id,
    )
    return correction
