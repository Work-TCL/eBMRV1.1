"""Document 79 (SPEC-VAL-001) Mutation Gateway command handlers -- Validation Master Plan & CSA
Strategy. Document 106 row 144: `release` requires a `Released` signature from an independent QA
Releaser, reason mandatory. `create` carries no Document 106 row of its own (a draft authoring action,
not itself a release/approval/verification family member per Document 106 section 8) -- RBAC-gated only,
same "no policy row = unsigned" precedent as every other module's genuinely-unsigned actions.

`validation_release_gate` has no dedicated write endpoint in Document 79's own API list (only a GET) --
the gate is evaluated and recorded as part of `release_master_plan()` itself, immediately before the
release decision, so the release action always has fresh gate evidence to act on. See
`app/modules/validation/models.py::ValidationReleaseGate` docstring.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import ValidationDeliverableRequirement, ValidationMasterPlan, ValidationReleaseGate
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    InvalidTransitionError,
    NotFoundError,
    ReleaseBlockersPresentError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_PLAN = "validation_master_plan"


class DeliverableInput(BaseModel):
    """A payload item nested inside `CreateOrUpdateMasterPlanCommand`, not a command in its own right --
    see `commands_trace.py::RequirementInput`'s docstring for why this must not inherit CommandEnvelope
    (a real bug this pass found and fixed)."""

    model_config = ConfigDict(extra="forbid")

    artifact_type: str
    risk_condition: str
    owner: str
    review_required: bool = False
    signature_required: bool = False
    evidence_type: str
    release_blocker: bool = True


class CreateOrUpdateMasterPlanCommand(CommandEnvelope):
    plan_id: uuid.UUID | None = None
    expected_version: int | None = None
    plan_number: str
    scope: str
    regulatory_profiles: list[str] = []
    methodology: str
    responsibilities: dict = {}
    retention_class: str | None = None
    new_deliverables: list[DeliverableInput] = []


async def create_or_update_master_plan(
    session: AsyncSession, cmd: CreateOrUpdateMasterPlanCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.plan_id is None:
        plan = ValidationMasterPlan(
            site_id=site_id, plan_number=cmd.plan_number, scope=cmd.scope,
            regulatory_profiles=cmd.regulatory_profiles, methodology=cmd.methodology,
            responsibilities=cmd.responsibilities, retention_class=cmd.retention_class,
            state="DRAFT", version=1,
        )
        session.add(plan)
        created = True
    else:
        plan = await session.get(ValidationMasterPlan, cmd.plan_id)
        if plan is None:
            raise NotFoundError("Validation master plan not found")
        if plan.state != "DRAFT":
            raise InvalidTransitionError("Only a DRAFT plan may be updated", current_state=plan.state)
        if cmd.expected_version is None or plan.version != cmd.expected_version:
            raise StaleVersionError("Master plan changed since this request was prepared", current_version=plan.version)
        plan.scope = cmd.scope
        plan.regulatory_profiles = cmd.regulatory_profiles
        plan.methodology = cmd.methodology
        plan.responsibilities = cmd.responsibilities
        plan.retention_class = cmd.retention_class
        plan.version += 1
        created = False
    await session.flush()

    for d in cmd.new_deliverables:
        session.add(
            ValidationDeliverableRequirement(
                plan_id=plan.id, artifact_type=d.artifact_type, risk_condition=d.risk_condition, owner=d.owner,
                review_required=d.review_required, signature_required=d.signature_required,
                evidence_type=d.evidence_type, release_blocker=d.release_blocker, state="REQUIRED", version=1,
            )
        )

    new_value = {"plan_number": plan.plan_number, "scope": plan.scope, "deliverables_added": len(cmd.new_deliverables)}
    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PLAN, aggregate_id=plan.id,
        version=plan.version, action="Created" if created else "Changed", actor_user_id=actor_user_id,
        reason=None, old_value=None, new_value=new_value, event_type="ValidationDeliverablesDerived",
        expected_version=None if created else cmd.expected_version, command_type="CreateOrUpdateMasterPlan",
        site_id=site_id,
    )


class ReleaseMasterPlanCommand(CommandEnvelope):
    plan_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def release_master_plan(
    session: AsyncSession, cmd: ReleaseMasterPlanCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    plan = await session.get(ValidationMasterPlan, cmd.plan_id)
    if plan is None:
        raise NotFoundError("Validation master plan not found")
    if plan.state != "DRAFT":
        raise InvalidTransitionError("Plan is not DRAFT", current_state=plan.state)
    if plan.version != cmd.expected_version:
        raise StaleVersionError("Master plan changed since this request was prepared", current_version=plan.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to release a Validation Master Plan")

    deliverables = (
        await session.execute(
            select(ValidationDeliverableRequirement).where(ValidationDeliverableRequirement.plan_id == plan.id)
        )
    ).scalars().all()
    blockers = [d.artifact_type for d in deliverables if d.release_blocker and d.state != "SATISFIED"]

    gate = ValidationReleaseGate(
        release_scope=plan.plan_number, environment="platform",
        required_artifact_refs=[d.artifact_type for d in deliverables],
        blockers=blockers, decision_refs={"plan_id": str(plan.id)},
        state="BLOCKED" if blockers else "PASSED", version=1,
    )
    session.add(gate)
    await session.flush()
    from app.mutation.gateway import write_outbox_event  # local import: secondary event, not the finalize() primary
    await write_outbox_event(
        session, event_type="ValidationReleaseGateEvaluated", aggregate_type="validation_release_gate",
        aggregate_id=gate.id, aggregate_version=1,
        payload={"plan_id": str(plan.id), "state": gate.state, "blockers": blockers},
        correlation_id=uuid.uuid4(),
    )
    if blockers:
        raise ReleaseBlockersPresentError("Outstanding release-blocking deliverables", blockers=blockers)

    policy = await resolve_signature(session, record_type=RECORD_TYPE_PLAN, action="release")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=plan.id, record_version=plan.version,
        )

    old_state = plan.state
    plan.state = "RELEASED"
    plan.released_by_user_id = actor_user_id
    plan.released_at = datetime.now(timezone.utc)
    plan.version += 1

    # Document 06 (VLT-FR-001/004): a released Validation Master Plan is a controlled document (VAL-FR-005
    # "Controlled plan") -- it gets an immutable vault snapshot in the same transaction as the release
    # itself, same "release_master is never itself signature-gated -- the caller already signed above"
    # shape as app/modules/batch/commands.py::release_batch.
    await vault_service.release_master(
        session, object_type="validation_master_plan", business_id=plan.plan_number, site_id=site_id,
        actor_user_id=actor_user_id, business_version_label=str(plan.version),
        canonical_payload={
            "plan_id": str(plan.id), "plan_number": plan.plan_number, "scope": plan.scope,
            "regulatory_profiles": plan.regulatory_profiles, "methodology": plan.methodology,
            "responsibilities": plan.responsibilities,
        },
        retention_class=plan.retention_class,
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PLAN, aggregate_id=plan.id,
        version=plan.version, action="Released", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"state": old_state}, new_value={"state": "RELEASED"}, event_type="ValidationMasterPlanReleased",
        expected_version=cmd.expected_version, command_type="ReleaseMasterPlan", site_id=site_id,
        signature_id=signature_id,
    )


async def get_release_gate(session: AsyncSession, plan_id: uuid.UUID) -> dict:
    """Read-only (Document 79 declares only a GET for this operation): recomputes the gate live from
    current deliverable state rather than returning a possibly-stale prior evaluation."""
    plan = await session.get(ValidationMasterPlan, plan_id)
    if plan is None:
        raise NotFoundError("Validation master plan not found")
    deliverables = (
        await session.execute(
            select(ValidationDeliverableRequirement).where(ValidationDeliverableRequirement.plan_id == plan.id)
        )
    ).scalars().all()
    blockers = [d.artifact_type for d in deliverables if d.release_blocker and d.state != "SATISFIED"]
    return {
        "plan_id": str(plan.id), "plan_state": plan.state, "blockers": blockers,
        "gate_state": "BLOCKED" if blockers else "PASSED",
        "required_artifacts": [d.artifact_type for d in deliverables],
    }


async def get_package(session: AsyncSession, scope: str) -> dict:
    """Read-only customer/vendor validation package view (VAL-FR-023): the effective plan for `scope`
    (a plan_number) plus its deliverables and current gate state."""
    plan = (
        await session.execute(
            select(ValidationMasterPlan)
            .where(ValidationMasterPlan.plan_number == scope)
            .order_by(ValidationMasterPlan.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if plan is None:
        raise NotFoundError("No validation master plan found for this scope")
    gate = await get_release_gate(session, plan.id)
    return {
        "plan_number": plan.plan_number, "state": plan.state, "scope": plan.scope,
        "methodology": plan.methodology, "gate": gate,
    }


async def _package_plan_and_deliverables(session: AsyncSession, scope: str):
    plan = (
        await session.execute(
            select(ValidationMasterPlan)
            .where(ValidationMasterPlan.plan_number == scope)
            .order_by(ValidationMasterPlan.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if plan is None:
        raise NotFoundError("No validation master plan found for this scope")
    deliverables = (
        await session.execute(
            select(ValidationDeliverableRequirement).where(ValidationDeliverableRequirement.plan_id == plan.id)
        )
    ).scalars().all()
    return plan, deliverables


async def export_package_csv(session: AsyncSession, scope: str) -> str:
    """VAL-FR-023: a real, generated CSV export of the vendor/customer validation package -- the plan
    header plus one row per deliverable requirement and its current satisfaction state."""
    import csv
    import io

    plan, deliverables = await _package_plan_and_deliverables(session, scope)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["plan_number", "plan_state", "scope", "methodology"])
    writer.writerow([plan.plan_number, plan.state, plan.scope, plan.methodology])
    writer.writerow([])
    writer.writerow(["artifact_type", "owner", "evidence_type", "release_blocker", "state"])
    for d in deliverables:
        writer.writerow([d.artifact_type, d.owner, d.evidence_type, d.release_blocker, d.state])
    return buf.getvalue()


async def export_package_pdf(session: AsyncSession, scope: str) -> bytes:
    """VAL-FR-023 (resolved SG-169, 2026-09-01): the same vendor/customer validation package as
    `export_package_csv()`, rendered as a paginated PDF via ReportLab. Same source query, same rows --
    a rendering choice, not a second data path."""
    from app.modules.validation.shared import render_pdf_report

    plan, deliverables = await _package_plan_and_deliverables(session, scope)
    header = ["Artifact Type", "Owner", "Evidence Type", "Release Blocker", "State"]
    rows = [[d.artifact_type, d.owner, d.evidence_type, "Yes" if d.release_blocker else "No", d.state] for d in deliverables]
    return render_pdf_report(
        title="Validation Package Export",
        subtitle=f"Plan {plan.plan_number} — state {plan.state} — scope: {plan.scope} — methodology: {plan.methodology}",
        sections=[("Deliverables", header, rows)],
    )
