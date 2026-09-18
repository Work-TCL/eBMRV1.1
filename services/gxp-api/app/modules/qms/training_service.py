import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.qms.training_models import QualificationRecord, TrainingAssignment, TrainingRequirement, TrainingWaiver
from app.mutation.errors import NotFoundError


async def get_requirement(session: AsyncSession, requirement_id: uuid.UUID) -> TrainingRequirement:
    requirement = await session.get(TrainingRequirement, requirement_id)
    if requirement is None:
        raise NotFoundError("Training requirement not found")
    return requirement


async def get_assignment(session: AsyncSession, assignment_id: uuid.UUID) -> TrainingAssignment:
    assignment = await session.get(TrainingAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Training assignment not found")
    return assignment


async def get_assignments_for_subject(session: AsyncSession, subject_id: uuid.UUID) -> list[TrainingAssignment]:
    result = await session.execute(
        select(TrainingAssignment).where(TrainingAssignment.subject_id == subject_id).order_by(TrainingAssignment.assigned_at)
    )
    return list(result.scalars().all())


async def get_qualifications_for_subject(session: AsyncSession, subject_id: uuid.UUID) -> list[QualificationRecord]:
    result = await session.execute(
        select(QualificationRecord).where(QualificationRecord.subject_id == subject_id).order_by(QualificationRecord.effective_from)
    )
    return list(result.scalars().all())


async def list_distinct_qualification_codes(session: AsyncSession) -> list[str]:
    """Recipe Master's `required_qualification_code` (StepInput) has no catalog table to source a
    dropdown from -- SG-086 documents that `iam.qualifications` and `qms.qualification_record` are two
    competing, non-authoritative grant stores for the same concept, neither a controlled code list.
    Project-owner-directed (asked directly, chose qms.qualification_record): suggest codes that have
    actually been granted here, without asserting this is the authoritative catalog -- the caller keeps a
    free-text fallback for a code not yet granted to anyone."""
    result = await session.execute(select(QualificationRecord.qualification_code).distinct().order_by(QualificationRecord.qualification_code))
    return [row[0] for row in result.all()]


async def has_active_qualification(session: AsyncSession, subject_id: uuid.UUID, qualification_code: str) -> bool:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(QualificationRecord.id).where(
            QualificationRecord.subject_id == subject_id,
            QualificationRecord.qualification_code == qualification_code,
            QualificationRecord.state.in_(("QUALIFIED", "RENEWED")),
            QualificationRecord.effective_from <= now,
            (QualificationRecord.effective_to.is_(None)) | (QualificationRecord.effective_to > now),
        ).limit(1)
    )
    return result.first() is not None


async def get_requirements_for_site(session: AsyncSession, site_id: uuid.UUID) -> list[TrainingRequirement]:
    result = await session.execute(
        select(TrainingRequirement).where(TrainingRequirement.site_id == site_id, TrainingRequirement.status == "active")
    )
    return list(result.scalars().all())


async def get_assignments_for_requirement(session: AsyncSession, requirement_id: uuid.UUID) -> list[TrainingAssignment]:
    result = await session.execute(select(TrainingAssignment).where(TrainingAssignment.requirement_id == requirement_id))
    return list(result.scalars().all())


async def get_waiver(session: AsyncSession, waiver_id: uuid.UUID) -> TrainingWaiver:
    waiver = await session.get(TrainingWaiver, waiver_id)
    if waiver is None:
        raise NotFoundError("Training waiver not found")
    return waiver


async def get_waivers_for_subject(session: AsyncSession, subject_id: uuid.UUID) -> list[TrainingWaiver]:
    result = await session.execute(
        select(TrainingWaiver).where(TrainingWaiver.subject_id == subject_id).order_by(TrainingWaiver.created_at)
    )
    return list(result.scalars().all())
