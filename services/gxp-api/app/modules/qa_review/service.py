"""Document 14 — the completeness computation (RBE-FR-005, partial) and the computed exceptions/dashboard
read views shared by commands.py and the router.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch
from app.modules.qa_review.models import QaReviewPackage
from app.modules.vault import service as vault_service
from app.mutation.errors import NotFoundError


async def get_package(session: AsyncSession, package_id: uuid.UUID) -> QaReviewPackage:
    package = await session.get(QaReviewPackage, package_id)
    if package is None:
        raise NotFoundError("QA review package not found")
    return package


async def get_package_for_batch(session: AsyncSession, batch_id: uuid.UUID) -> QaReviewPackage | None:
    return (
        await session.execute(select(QaReviewPackage).where(QaReviewPackage.batch_id == batch_id))
    ).scalar_one_or_none()


async def list_packages(session: AsyncSession, site_id: uuid.UUID, *, state: str | None = None) -> list[QaReviewPackage]:
    stmt = select(QaReviewPackage).where(QaReviewPackage.site_id == site_id)
    if state is not None:
        stmt = stmt.where(QaReviewPackage.state == state)
    return (await session.execute(stmt.order_by(QaReviewPackage.created_at.desc()))).scalars().all()


async def get_batch(session: AsyncSession, batch_id: uuid.UUID) -> Batch:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    return batch


async def get_batch_corrections(session: AsyncSession, batch_id: uuid.UUID) -> list[dict]:
    """RBE-FR-003/006/008 (partial): the 'corrections/audit-trail' slice of the exception index, drawn
    directly from real audit_events for the batch aggregate -- not persisted as its own qa_review_item
    rows. Filters on action == "Corrected" specifically (the vocabulary genealogy's correct_edge() also
    uses) -- ordinary lifecycle transitions (issue/start/hold/resume/abort) use action == "Changed" and
    are not exceptions. batch_execution has no correction command yet (BAT-FR-023 is gapped, SG-047/048),
    so this genuinely returns empty today; it's a forward-compatible hook, not a dead branch -- once a
    real correction command exists anywhere that writes "Corrected" against a "batch" aggregate, it
    surfaces here automatically. Only batch-level events are covered this pass; step-level audit events
    are not joined in -- see SG-054.
    """
    from app.modules.audit.models import AuditEvent

    rows = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.aggregate_type == "batch", AuditEvent.aggregate_id == batch_id, AuditEvent.action == "Corrected")
            .order_by(AuditEvent.occurred_at)
        )
    ).scalars().all()
    return [
        {
            "audit_event_id": str(r.id),
            "occurred_at": r.occurred_at.isoformat(),
            "actor_id": str(r.actor_id),
            "reason": r.reason,
            "old_value": r.old_value,
            "new_value": r.new_value,
        }
        for r in rows
    ]


async def compute_completeness(session: AsyncSession, batch: Batch, corrections: list[dict]) -> tuple[str, list[str]]:
    """RBE-FR-005/029 (partial): real signals only -- batch hold state and Vault execution-snapshot
    integrity. Everything the full completeness engine also checks (QC results, materials, equipment,
    environment, genealogy completeness, packaging, yield, signatures) depends on modules/entities this
    pass doesn't build -- see SG-054.
    """
    blockers: list[str] = []
    if batch.state == "on_hold":
        blockers.append("batch is on_hold")
    if batch.execution_snapshot_id is not None:
        integrity = await vault_service.verify_integrity(session, batch.execution_snapshot_id)
        if not integrity["digest_valid"] or not integrity["link_valid"]:
            blockers.append("execution snapshot integrity check failed")
    if blockers:
        return "blocked", blockers
    if corrections:
        return "has_exceptions", []
    return "complete", []


async def get_exceptions_view(session: AsyncSession, package: QaReviewPackage) -> dict:
    batch = await get_batch(session, package.batch_id)
    corrections = await get_batch_corrections(session, package.batch_id)
    integrity = None
    if batch.execution_snapshot_id is not None:
        integrity = await vault_service.verify_integrity(session, batch.execution_snapshot_id)
    return {
        "package_id": str(package.id),
        "batch_id": str(package.batch_id),
        "corrections": corrections,
        "integrity_check": integrity,
        "batch_on_hold": batch.state == "on_hold",
    }
