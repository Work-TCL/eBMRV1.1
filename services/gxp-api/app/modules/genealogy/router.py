import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.genealogy import service as genealogy_service
from app.modules.policy.service import evaluate_policy

router = APIRouter(prefix="/genealogy/v1", tags=["genealogy"])


def _node_dict(node) -> dict:
    return {
        "node_id": str(node.id),
        "site_id": str(node.site_id),
        "node_type": node.node_type,
        "business_ref": node.business_ref,
        "authoritative_record_type": node.authoritative_record_type,
        "authoritative_record_id": str(node.authoritative_record_id) if node.authoritative_record_id else None,
        "authoritative_version": node.authoritative_version,
        "record_hash": node.record_hash,
    }


def _trace_dict(trace: dict) -> dict:
    return {
        "root_node_id": str(trace["root_node_id"]),
        "nodes": [_node_dict(n) for n in trace["nodes"]],
        "edge_ids": [str(e) for e in trace["edge_ids"]],
        "truncated": trace["truncated"],
    }


@router.get("/nodes/lookup")
async def get_nodes_lookup(
    site_id: uuid.UUID,
    node_type: str | None = None,
    business_ref: str | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="genealogy.view", site_id=None)
    nodes = await genealogy_service.lookup(session, site_id, node_type=node_type, business_ref=business_ref)
    return [_node_dict(n) for n in nodes]


@router.get("/nodes/{node_id}/ancestors")
async def get_node_ancestors(
    node_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="genealogy.view", site_id=None)
    return _trace_dict(await genealogy_service.get_ancestors(session, node_id))


@router.get("/nodes/{node_id}/descendants")
async def get_node_descendants(
    node_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="genealogy.view", site_id=None)
    return _trace_dict(await genealogy_service.get_descendants(session, node_id))


@router.get("/serial/{serial}/full-trace")
async def get_serial_full_trace(
    serial: str,
    site_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="genealogy.view", site_id=None)
    trace = await genealogy_service.full_trace(session, site_id, serial)
    return {
        "root": _node_dict(trace["root"]),
        "ancestors": _trace_dict(trace["ancestors"]),
        "descendants": _trace_dict(trace["descendants"]),
    }


@router.get("/material-lot/{lot}/affected-products")
async def get_material_lot_affected_products(
    lot: str,
    site_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="genealogy.view", site_id=None)
    result = await genealogy_service.affected_products(session, site_id, lot)
    return {
        "root": _node_dict(result["root"]),
        "affected_products": [_node_dict(n) for n in result["affected_products"]],
        "truncated": result["truncated"],
    }
