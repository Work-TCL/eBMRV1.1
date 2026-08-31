"""Document 16 — read helpers, duplicate-serial detection (PKG-FR-008, partial) and the internal
package_node hierarchy (PKG-FR-018/019, no public write API) shared by commands.py and the router.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch
from app.modules.packaging.models import LabelIssue, LabelReconciliation, PackageNode, PackagingRun
from app.mutation.errors import NotFoundError, ValidationFailedError


async def get_run(session: AsyncSession, run_id: uuid.UUID) -> PackagingRun:
    run = await session.get(PackagingRun, run_id)
    if run is None:
        raise NotFoundError("Packaging run not found")
    return run


async def get_batch(session: AsyncSession, batch_id: uuid.UUID) -> Batch:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    return batch


async def get_label_issues(session: AsyncSession, run_id: uuid.UUID) -> list[LabelIssue]:
    return (
        (await session.execute(select(LabelIssue).where(LabelIssue.packaging_run_id == run_id).order_by(LabelIssue.issued_at)))
        .scalars()
        .all()
    )


async def get_reconciliations(session: AsyncSession, run_id: uuid.UUID) -> list[LabelReconciliation]:
    return (
        (await session.execute(select(LabelReconciliation).where(LabelReconciliation.packaging_run_id == run_id).order_by(LabelReconciliation.created_at)))
        .scalars()
        .all()
    )


async def assert_no_duplicate_serials(session: AsyncSession, product_version_id: uuid.UUID, serial_range: dict | None) -> None:
    """PKG-FR-008 (partial): only checks explicit serial lists (`serial_range={"serials": [...]}`) against
    other label_issue rows already issued for packaging runs of the same product_version -- numeric
    range-based allocation dedup is not built this pass (SG-056)."""
    if not serial_range or "serials" not in serial_range:
        return
    new_serials = set(serial_range["serials"])
    if not new_serials:
        return
    rows = (
        await session.execute(
            select(LabelIssue.serial_range)
            .join(PackagingRun, PackagingRun.id == LabelIssue.packaging_run_id)
            .where(PackagingRun.product_version_id == product_version_id, LabelIssue.serial_range.isnot(None))
        )
    ).scalars().all()
    existing_serials: set[str] = set()
    for sr in rows:
        if sr and "serials" in sr:
            existing_serials.update(sr["serials"])
    conflict = new_serials & existing_serials
    if conflict:
        raise ValidationFailedError("Duplicate serial(s) already issued for this product", duplicate_serials=sorted(conflict))


async def get_label_reconciliation_source(session: AsyncSession, run_id: uuid.UUID) -> dict:
    """Document 16's query interface for YLD-FR-012: Document 17's LABEL reconciliation consumes these
    counts instead of accepting them from its caller. Packaging owns `label_issue`/`label_reconciliation`
    (AG-05); this returns the *latest* reconciliation row for the run alongside the run's own batch, so
    Document 17 never selects from packaging's tables itself
    (`.claude/rules/00-architecture-non-negotiables.md`: a module calls the owning module's interface).

    Fails closed if the run has not been reconciled yet -- YLD-FR-012 is defined as consuming Document 16's
    counts, so there is no "no counts yet" reading to fall back on.
    """
    run = await get_run(session, run_id)
    rows = await get_reconciliations(session, run_id)
    if not rows:
        raise NotFoundError(
            "Packaging run has no label reconciliation to consume (PKG-FR-013 must run first)",
            packaging_run_id=str(run_id),
        )
    latest = rows[-1]
    return {
        "packaging_run_id": str(run.id),
        "batch_id": run.batch_id,
        "site_id": run.site_id,
        "label_reconciliation_id": str(latest.id),
        "issued": latest.issued,
        "applied": latest.applied,
        "returned": latest.returned,
        "destroyed": latest.destroyed,
        "rejected": latest.rejected,
        "samples": latest.samples,
        "calculated_variance": latest.calculated_variance,
        "result": latest.result,
    }


def compute_reconciliation(issued: int, applied: int, returned: int, destroyed: int, rejected: int, samples: int) -> tuple[int, str]:
    """PKG-FR-013/017 + Document 16 §10: the packaging module supplies source quantities; the real
    tolerance-rule evaluation is delegated to Document 08 (Rules Engine), but no released rule exists for
    this yet (SG-056), so this pass applies the only non-guessed default: exact balance (variance == 0)."""
    variance = issued - (applied + returned + destroyed + rejected + samples)
    result = "balanced" if variance == 0 else "discrepancy"
    return variance, result


async def create_package_node(
    session: AsyncSession, *, package_level: str, batch_id: uuid.UUID, business_ref: str | None = None, parent_package_id: uuid.UUID | None = None
) -> PackageNode:
    node = PackageNode(package_level=package_level, batch_id=batch_id, business_ref=business_ref, parent_package_id=parent_package_id, state="created")
    session.add(node)
    await session.flush()
    return node


async def get_package_children(session: AsyncSession, parent_package_id: uuid.UUID) -> list[PackageNode]:
    return (
        (await session.execute(select(PackageNode).where(PackageNode.parent_package_id == parent_package_id)))
        .scalars()
        .all()
    )
