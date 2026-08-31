"""Document 15 — the eligibility computation (REL-FR-003, partial) and read views shared by commands.py
and the router.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch
from app.modules.qa_review import service as qa_review_service
from app.modules.release.models import ReleaseDecision, ReleaseEvaluation, ReleaseScope
from app.modules.vault import service as vault_service
from app.mutation.errors import NotFoundError


async def get_scope(session: AsyncSession, scope_id: uuid.UUID) -> ReleaseScope:
    scope = await session.get(ReleaseScope, scope_id)
    if scope is None:
        raise NotFoundError("Release scope not found")
    return scope


async def get_scope_for_target(session: AsyncSession, scope_type: str, scope_id: uuid.UUID) -> ReleaseScope | None:
    return (
        await session.execute(
            select(ReleaseScope).where(ReleaseScope.scope_type == scope_type, ReleaseScope.scope_id == scope_id)
        )
    ).scalar_one_or_none()


async def get_batch(session: AsyncSession, batch_id: uuid.UUID) -> Batch:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    return batch


async def get_current_evaluation(session: AsyncSession, scope: ReleaseScope) -> ReleaseEvaluation | None:
    if scope.current_evaluation_id is None:
        return None
    return await session.get(ReleaseEvaluation, scope.current_evaluation_id)


async def get_decisions(session: AsyncSession, scope_id: uuid.UUID) -> list[ReleaseDecision]:
    return (
        (
            await session.execute(
                select(ReleaseDecision).where(ReleaseDecision.release_scope_id == scope_id).order_by(ReleaseDecision.decision_time)
            )
        )
        .scalars()
        .all()
    )


def _blocker(code: str, severity: str, source_type: str, source_id: str | None, message_key: str, resolution_action: str) -> dict:
    """Document 15 §6's blocker contract."""
    return {
        "code": code,
        "severity": severity,
        "source_type": source_type,
        "source_id": source_id,
        "message_key": message_key,
        "resolution_action": resolution_action,
    }


async def evaluate_eligibility(session: AsyncSession, batch: Batch) -> tuple[list[dict], list[dict]]:
    """REL-FR-003/004/025 (partial): only two of the nine named eligibility categories have a real data
    source in this codebase -- QA review currency/completeness (Document 14) and Vault execution-snapshot
    integrity (Document 06). QC, QMS, materials, equipment, environment, packaging, genealogy and yield/
    reconciliation all depend on modules/entities that don't exist yet -- see SG-056; none of them can
    contribute a real blocker or warning this pass, so they are silently absent rather than guessed.
    """
    blockers: list[dict] = []

    package = await qa_review_service.get_package_for_batch(session, batch.id)
    if package is None:
        blockers.append(
            _blocker("QA_REVIEW_MISSING", "CRITICAL", "qa_review_package", None, "release.blocker.qa_review_missing", "CREATE_QA_REVIEW_PACKAGE")
        )
    else:
        if package.state != "REVIEW_COMPLETE":
            blockers.append(
                _blocker(
                    "REVIEW_NOT_CURRENT", "CRITICAL", "qa_review_package", str(package.id),
                    "release.blocker.review_not_complete", "COMPLETE_QA_REVIEW",
                )
            )
        elif package.batch_version != batch.version:
            blockers.append(
                _blocker(
                    "REVIEW_NOT_CURRENT", "CRITICAL", "qa_review_package", str(package.id),
                    "release.blocker.review_stale", "REINDEX_AND_RECOMPLETE_QA_REVIEW",
                )
            )

    if batch.state == "on_hold":
        blockers.append(_blocker("BATCH_ON_HOLD", "CRITICAL", "batch", str(batch.id), "release.blocker.batch_on_hold", "RESOLVE_BATCH_HOLD"))

    if batch.execution_snapshot_id is not None:
        integrity = await vault_service.verify_integrity(session, batch.execution_snapshot_id)
        if not integrity["digest_valid"] or not integrity["link_valid"]:
            blockers.append(
                _blocker(
                    "INTEGRITY_CHECK_FAILED", "CRITICAL", "vault_object", str(batch.execution_snapshot_id),
                    "release.blocker.integrity_failed", "INVESTIGATE_INTEGRITY_FAILURE",
                )
            )

    warnings: list[dict] = []
    return blockers, warnings
