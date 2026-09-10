import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms import training_service
from app.modules.qms.signature_support import (
    SignatureChallengeRequest,
    create_qms_signature_challenge,
    create_qms_signature_challenge_for_new_record,
)
from app.modules.qms.training_commands import (
    AssessTrainingAssignmentCommand,
    CompleteTrainingAssignmentCommand,
    CreateQualificationCommand,
    CreateTrainingAssignmentCommand,
    CreateTrainingRequirementCommand,
    CreateWaiverCommand,
    assess_assignment,
    complete_assignment,
    create_assignment,
    create_qualification,
    create_requirement,
    create_waiver,
)
from app.modules.qms.training_models import TrainingAssignment
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

training_router = APIRouter(prefix="/training/v1", tags=["qms-training-qualification"])

# Actions on an *existing* assignment (the normal case every other module's challenge endpoint covers).
TRAINING_ASSIGNMENT_SIGNATURE_ACTIONS = ("complete", "assess")
# "create" needs its own endpoint with no path id: the assignment row does not exist yet at challenge
# time. Fixed via create_qms_signature_challenge_for_new_record() -- see its docstring and
# post_create_assignment_signature_challenge() below. Previously this was a documented, deliberately
# unfixed gap (SG-138); now resolved.
TRAINING_ASSIGNMENT_CREATE_SIGNATURE_ACTIONS = ("create",)


def _assignment_dict(a) -> dict:
    return {
        "id": str(a.id), "subject_id": str(a.subject_id), "requirement_id": str(a.requirement_id),
        "state": a.state, "result": a.result, "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        "due_at": a.due_at.isoformat() if a.due_at else None,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        "score": float(a.score) if a.score is not None else None, "attempt_number": a.attempt_number,
        "version": a.version,
    }


def _qualification_dict(q) -> dict:
    return {
        "id": str(q.id), "subject_id": str(q.subject_id), "qualification_code": q.qualification_code,
        "state": q.state, "effective_from": q.effective_from.isoformat() if q.effective_from else None,
        "effective_to": q.effective_to.isoformat() if q.effective_to else None, "version": q.version,
    }


@training_router.post("/requirements", response_model=MutationReceipt)
async def post_create_requirement(
    cmd: CreateTrainingRequirementCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="training.requirement.create", site_id=cmd.site_id)
        return await create_requirement(session, cmd, actor.user_id)


@training_router.post("/assignments/signature-challenges")
async def post_create_assignment_signature_challenge(
    body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """SG-138 fix: the only "create"-action signature challenge in this codebase. No path id -- the
    assignment doesn't exist yet -- so a fresh id is generated here, bound to the challenge at version 1,
    and handed back to the caller as `assignment_id` to pass into the subsequent POST /assignments call
    (CreateTrainingAssignmentCommand.assignment_id). See
    create_qms_signature_challenge_for_new_record()'s docstring for why this is safe: the create command
    inserts its new row using that exact id, so the (id, version) pair matches what the challenge was
    issued against.
    """
    async with session.begin():
        new_id = uuid.uuid4()
        result = await create_qms_signature_challenge_for_new_record(
            session, actor_user_id=actor.user_id, record_type="training_assignment", record_id=new_id,
            action=body.action, allowed_actions=TRAINING_ASSIGNMENT_CREATE_SIGNATURE_ACTIONS,
        )
        return {**result, "assignment_id": str(new_id)}


@training_router.post("/assignments", response_model=MutationReceipt)
async def post_create_assignment(
    cmd: CreateTrainingAssignmentCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="training.assignment.create", site_id=None)
        return await create_assignment(session, cmd, actor.user_id)


@training_router.post("/assignments/{assignment_id}/complete", response_model=MutationReceipt)
async def post_complete_assignment(
    assignment_id: uuid.UUID, cmd: CompleteTrainingAssignmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.assignment_id != assignment_id:
        raise ValidationFailedError("assignment_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="training.assignment.complete", site_id=None)
        return await complete_assignment(session, cmd, actor.user_id)


@training_router.post("/assignments/{assignment_id}/assess", response_model=MutationReceipt)
async def post_assess_assignment(
    assignment_id: uuid.UUID, cmd: AssessTrainingAssignmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.assignment_id != assignment_id:
        raise ValidationFailedError("assignment_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="training.assignment.assess", site_id=None)
        return await assess_assignment(session, cmd, actor.user_id)


@training_router.post("/assignments/{assignment_id}/signature-challenges")
async def post_signature_challenge(
    assignment_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        assignment = await session.get(TrainingAssignment, assignment_id)
        if assignment is None:
            raise NotFoundError("Training assignment not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="training_assignment", record=assignment,
            action=body.action, allowed_actions=TRAINING_ASSIGNMENT_SIGNATURE_ACTIONS,
        )


@training_router.post("/qualifications", response_model=MutationReceipt)
async def post_create_qualification(
    cmd: CreateQualificationCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="training.qualification.create", site_id=cmd.site_id)
        return await create_qualification(session, cmd, actor.user_id)


@training_router.post("/waivers", response_model=MutationReceipt)
async def post_create_waiver(
    cmd: CreateWaiverCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="training.waiver.create", site_id=cmd.site_id)
        return await create_waiver(session, cmd, actor.user_id)


@training_router.get("/subjects/{subject_id}/status")
async def get_subject_status(
    subject_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="training.subject.view", site_id=None)
    assignments = await training_service.get_assignments_for_subject(session, subject_id)
    qualifications = await training_service.get_qualifications_for_subject(session, subject_id)
    return {
        "subject_id": str(subject_id),
        "assignments": [_assignment_dict(a) for a in assignments],
        "qualifications": [_qualification_dict(q) for q in qualifications],
    }


@training_router.get("/matrix")
async def get_matrix(
    site_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="training.matrix.view", site_id=site_id)
    requirements = await training_service.get_requirements_for_site(session, site_id)
    rows = []
    for requirement in requirements:
        assignments = await training_service.get_assignments_for_requirement(session, requirement.id)
        rows.append({
            "requirement_id": str(requirement.id), "title": requirement.title, "training_type": requirement.training_type,
            "assigned_count": len(assignments),
            "completed_count": sum(1 for a in assignments if a.state == "COMPLETED"),
            "failed_count": sum(1 for a in assignments if a.state == "FAILED"),
            "open_count": sum(1 for a in assignments if a.state in ("ASSIGNED", "ASSESSMENT_PENDING")),
        })
    return {"site_id": str(site_id), "requirements": rows}
