"""Document 68 (SPEC-SEC-008) REST surface, prefix `/security/v1`. The 4 operations Document 68 # 7
lists: register a vulnerability, assess its severity, approve a time-bounded exception (signed --
Document 106 row 141, currently fails closed per SG-165), and read a release's security-evidence bundle.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.security import supplychain_commands as commands
from app.modules.security.supplychain_models import ReleaseSecurityEvidence, VulnerabilityRecord
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/security/v1", tags=["security-supplychain"])


@router.post("/vulnerabilities", response_model=MutationReceipt)
async def post_register_vulnerability(
    cmd: commands.RegisterVulnerabilityCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="vulnerability.register", site_id=None)
        return await commands.register_vulnerability(session, cmd, actor.user_id)


@router.post("/vulnerabilities/{vulnerability_id}/assess", response_model=MutationReceipt)
async def post_assess_vulnerability(
    vulnerability_id: uuid.UUID, cmd: commands.AssessVulnerabilitySeverityCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.vulnerability_id != vulnerability_id:
        raise ValidationFailedError("vulnerability_id in path and body must match")
    async with session.begin():
        if await session.get(VulnerabilityRecord, vulnerability_id) is None:
            raise NotFoundError("Vulnerability record not found")
        await evaluate_policy(session, actor.user_id, action="vulnerability.assess", site_id=None)
        return await commands.assess_vulnerability_severity(session, cmd, actor.user_id)


@router.post("/vulnerabilities/{vulnerability_id}/exceptions", response_model=MutationReceipt)
async def post_approve_vulnerability_exception(
    vulnerability_id: uuid.UUID, cmd: commands.ApproveVulnerabilityExceptionCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.vulnerability_id != vulnerability_id:
        raise ValidationFailedError("vulnerability_id in path and body must match")
    async with session.begin():
        if await session.get(VulnerabilityRecord, vulnerability_id) is None:
            raise NotFoundError("Vulnerability record not found")
        await evaluate_policy(session, actor.user_id, action="vulnerability.exception", site_id=None)
        return await commands.approve_vulnerability_exception(session, cmd, actor.user_id)


@router.get("/releases/{release_id}/security-evidence")
async def get_release_security_evidence(
    release_id: str,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="release_security_evidence.view", site_id=None)
        row = (
            await session.execute(select(ReleaseSecurityEvidence).where(ReleaseSecurityEvidence.release_id == release_id))
        ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Release security evidence not found")
    return {
        "release_id": row.release_id, "commit_sha": row.commit_sha, "build_provenance": row.build_provenance,
        "sbom_ref": row.sbom_ref, "scan_reports": row.scan_reports, "pentest_refs": row.pentest_refs,
        "security_test_refs": row.security_test_refs, "accepted_exceptions": row.accepted_exceptions,
        "gate_result": row.gate_result, "artifact_digest": row.artifact_digest,
        "signature_ref": row.signature_ref, "version": row.version,
    }
