import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.read_support import iso as _iso
from app.modules.signature.service import create_challenge
from app.modules.supplier_quality.commands import (
    ApproveSupplierQualificationCommand,
    CreateSupplierCommand,
    CreateSupplierQualificationCommand,
    approve_supplier_qualification,
    create_supplier,
    create_supplier_qualification,
    qualification_record_hash,
)
from app.modules.supplier_quality.models import (
    Supplier,
    SupplierQualification,
    SupplierQualificationEvidence,
    SupplierSite,
)
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

# Document 18 §7 declares these exact paths verbatim (including the literal "v1"/"{id}" segments).
router = APIRouter(tags=["supplier_quality"])


@router.post("/suppliers/v1", response_model=MutationReceipt)
async def post_create_supplier(
    cmd: CreateSupplierCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        # 2026-09-18, project-owner-directed: create_supplier() had no evaluate_policy() call at all —
        # matching material.create's resolution (same session, same decision), Process Engineer + Admin.
        await evaluate_policy(session, actor.user_id, action="supplier.create", site_id=None)
        return await create_supplier(session, cmd, actor.user_id)


@router.post("/suppliers/{supplier_id}/qualifications", response_model=MutationReceipt)
async def post_create_supplier_qualification(
    supplier_id: str,
    cmd: CreateSupplierQualificationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.supplier_id) != supplier_id:
        raise ValidationFailedError("supplier_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="supplier_qualification.create", site_id=None)
        return await create_supplier_qualification(session, cmd, actor.user_id)


class QualificationSignatureChallengeRequest(BaseModel):
    action: str  # "approve"


@router.post("/supplier-qualifications/{qualification_id}/signature-challenges")
async def post_qualification_signature_challenge(
    qualification_id: str,
    body: QualificationSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        qualification = await session.get(SupplierQualification, qualification_id)
        if qualification is None:
            raise NotFoundError("Supplier qualification not found")
        if body.action != "approve":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="supplier_qualification",
            record_id=qualification.id,
            record_version=qualification.version,
            record_hash=qualification_record_hash(qualification),
            meaning="Approved",
        )
        return {
            "challenge_id": str(challenge.id),
            "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/supplier-qualifications/{qualification_id}/approve", response_model=MutationReceipt)
async def post_approve_supplier_qualification(
    qualification_id: str,
    cmd: ApproveSupplierQualificationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.qualification_id) != qualification_id:
        raise ValidationFailedError("qualification_id in path and body must match")
    async with session.begin():
        return await approve_supplier_qualification(session, cmd, actor.user_id)


# --- Read side (Document 18) -------------------------------------------------------------------

SUPPLIER_SORTABLE = {
    "supplier_code": Supplier.supplier_code,
    "legal_name": Supplier.legal_name,
    "status": Supplier.status,
    "created_at": Supplier.created_at,
}


def _supplier_dict(supplier: Supplier) -> dict:
    return {
        "id": str(supplier.id),
        "supplier_code": supplier.supplier_code,
        "legal_name": supplier.legal_name,
        "role_type": supplier.role_type,
        "status": supplier.status,
        "country": supplier.country,
        "external_mappings": supplier.external_mappings,
        "version": supplier.version,
        "created_at": _iso(supplier.created_at),
    }


def _qualification_dict(qualification: SupplierQualification) -> dict:
    return {
        "id": str(qualification.id),
        "supplier_site_id": str(qualification.supplier_site_id),
        "requested_by_user_id": str(qualification.requested_by_user_id),
        "scope": qualification.scope,
        "risk_class": qualification.risk_class,
        "status": qualification.status,
        "justification": qualification.justification,
        "effective_from": _iso(qualification.effective_from),
        "expires_at": _iso(qualification.expires_at),
        "quality_agreement_vault_id": str(qualification.quality_agreement_vault_id)
        if qualification.quality_agreement_vault_id
        else None,
        "approval_signatures": qualification.approval_signatures,
        "version": qualification.version,
        "created_at": _iso(qualification.created_at),
    }


@router.get("/suppliers/v1")
async def list_suppliers(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    status: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="supplier.view", site_id=None)
    stmt = select(Supplier)
    if status:
        stmt = stmt.where(Supplier.status == status)
    if params.q:
        stmt = stmt.where(
            or_(Supplier.supplier_code.ilike(f"%{params.q}%"), Supplier.legal_name.ilike(f"%{params.q}%"))
        )
    rows, envelope = await paginate(
        session, stmt, params, sortable=SUPPLIER_SORTABLE, default_sort=Supplier.created_at
    )
    return {**envelope, "items": [_supplier_dict(s) for (s,) in rows]}


@router.get("/suppliers/v1/{supplier_id}")
async def get_supplier(
    supplier_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFoundError("Supplier not found")
    await evaluate_policy(session, actor.user_id, action="supplier.view", site_id=None)
    sites = (
        await session.execute(select(SupplierSite).where(SupplierSite.supplier_id == supplier_id))
    ).scalars().all()
    site_ids = [s.id for s in sites]
    qualifications = (
        (
            await session.execute(
                select(SupplierQualification).where(SupplierQualification.supplier_site_id.in_(site_ids))
            )
        ).scalars().all()
        if site_ids
        else []
    )
    return {
        **_supplier_dict(supplier),
        "sites": [
            {
                "id": str(s.id),
                "site_name": s.site_name,
                "address_line1": s.address_line1,
                "address_line2": s.address_line2,
                "city": s.city,
                "state_province": s.state_province,
                "postal_code": s.postal_code,
                "country": s.country,
                "manufacturer_flag": s.manufacturer_flag,
                "certification_refs": s.certification_refs,
                "status": s.status,
                "version": s.version,
            }
            for s in sites
        ],
        "qualifications": [_qualification_dict(q) for q in qualifications],
    }


@router.get("/supplier-qualifications/{qualification_id}")
async def get_supplier_qualification(
    qualification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    qualification = await session.get(SupplierQualification, qualification_id)
    if qualification is None:
        raise NotFoundError("Supplier qualification not found")
    await evaluate_policy(session, actor.user_id, action="supplier.view", site_id=None)
    evidence = (
        await session.execute(
            select(SupplierQualificationEvidence).where(
                SupplierQualificationEvidence.supplier_qualification_id == qualification_id
            )
        )
    ).scalars().all()
    return {
        **_qualification_dict(qualification),
        "evidence": [
            {
                "id": str(e.id),
                "vault_object_id": str(e.vault_object_id),
                "evidence_category": e.evidence_category,
                "added_at": _iso(e.added_at),
            }
            for e in evidence
        ],
    }
