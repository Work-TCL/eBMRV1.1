"""Document 81 (SPEC-VAL-003) Mutation Gateway command handlers -- Requirements, Design Inputs &
Validation Traceability Management. Document 106 has no row for any SPEC-VAL-003 action -- every
operation here is RBAC-gated only, same "no policy row = unsigned" precedent as every other genuinely
unsigned module (e.g. `app/modules/disaster_recovery`).
"""

from __future__ import annotations

import hashlib
import json
import uuid

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import RequirementBaseline, TraceLink, ValidationRequirement
from app.modules.validation.shared import finalize, receipt_from_existing
from app.modules.vault import service as vault_service
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


class RequirementInput(BaseModel):
    """A payload item nested inside `IngestRequirementsCommand`, not a command in its own right -- it
    must not inherit CommandEnvelope's `idempotency_key` (a bug this pass found and fixed: a nested
    per-item idempotency_key that varies between calls destabilizes the *outer* command's payload hash,
    breaking MUT-FR-010 dedup for an otherwise byte-identical retry, and the committed OpenAPI contract
    never declared this field on this schema either)."""

    model_config = ConfigDict(extra="forbid")

    requirement_code: str
    source_document: str
    source_section: str
    text: str
    requirement_class: str
    regulatory_source: str | None = None
    binding_status: str = "BINDING"
    acceptance_criteria: str | None = None


class IngestRequirementsCommand(CommandEnvelope):
    requirements: list[RequirementInput]


async def ingest_requirements(
    session: AsyncSession, cmd: IngestRequirementsCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if not cmd.requirements:
        raise ValidationFailedError("requirements must not be empty")

    ingested_ids: list[str] = []
    for r in cmd.requirements:
        current = (
            await session.execute(
                select(ValidationRequirement)
                .where(ValidationRequirement.requirement_code == r.requirement_code, ValidationRequirement.state == "EFFECTIVE")
            )
        ).scalar_one_or_none()
        next_version = 1
        if current is not None:
            if current.text == r.text and current.requirement_class == r.requirement_class:
                ingested_ids.append(str(current.id))
                continue  # unchanged -- no new version (REQ-FR-011 retains history, doesn't churn it)
            current.state = "SUPERSEDED"  # REQ-FR-011: superseded requirements remain retained, never deleted
            next_version = current.version + 1
        row = ValidationRequirement(
            requirement_code=r.requirement_code, source_document=r.source_document, source_section=r.source_section,
            text=r.text, requirement_class=r.requirement_class, regulatory_source=r.regulatory_source,
            binding_status=r.binding_status, acceptance_criteria=r.acceptance_criteria, state="EFFECTIVE",
            version=next_version,
        )
        session.add(row)
        await session.flush()
        ingested_ids.append(str(row.id))

    new_value = {"count": len(cmd.requirements), "requirement_ids": ingested_ids}
    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="validation_requirement",
        aggregate_id=uuid.UUID(ingested_ids[0]), version=1, action="Created", actor_user_id=actor_user_id,
        reason=None, old_value=None, new_value=new_value, event_type="RequirementIngested",
        expected_version=None, command_type="IngestRequirements", site_id=site_id,
    )


class CreateTraceLinkCommand(CommandEnvelope):
    source_type: str
    source_id: str
    source_version: str
    target_type: str
    target_id: str
    target_version: str
    relation_type: str


async def create_trace_link(
    session: AsyncSession, cmd: CreateTraceLinkCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    from app.modules.validation.models import TRACE_LINK_TYPES
    if cmd.relation_type not in TRACE_LINK_TYPES:
        raise ValidationFailedError(f"relation_type must be one of {TRACE_LINK_TYPES}")

    row = TraceLink(
        source_type=cmd.source_type, source_id=cmd.source_id, source_version=cmd.source_version,
        target_type=cmd.target_type, target_id=cmd.target_id, target_version=cmd.target_version,
        relation_type=cmd.relation_type, version=1,
    )
    session.add(row)
    await session.flush()

    new_value = {"source": f"{cmd.source_type}:{cmd.source_id}", "target": f"{cmd.target_type}:{cmd.target_id}"}
    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="trace_link", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value=new_value, event_type="TraceabilityMatrixGenerated", expected_version=None,
        command_type="CreateTraceLink", site_id=site_id,
    )


async def _find_gaps(session: AsyncSession, requirement_refs: list[dict]) -> list[dict]:
    """REQ-FR-014: a BINDING requirement with no TEST trace link is an untested critical requirement."""
    gaps = []
    for ref in requirement_refs:
        req = (
            await session.execute(
                select(ValidationRequirement).where(
                    ValidationRequirement.requirement_code == ref["code"], ValidationRequirement.version == ref["version"]
                )
            )
        ).scalar_one_or_none()
        if req is None or req.binding_status != "BINDING":
            continue
        has_test_link = (
            await session.execute(
                select(TraceLink).where(
                    TraceLink.source_type == "validation_requirement", TraceLink.source_id == ref["code"],
                    TraceLink.relation_type == "TEST",
                )
            )
        ).scalar_one_or_none()
        if has_test_link is None:
            gaps.append({"requirement_code": ref["code"], "reason": "no TEST trace link"})
    return gaps


class FreezeRequirementBaselineCommand(CommandEnvelope):
    release_scope: str
    customer_scope: str | None = None
    requirement_refs: list[dict]  # [{"code": ..., "version": ...}]
    exclusions: list[dict] = []  # [{"code": ..., "rationale": ...}]


async def freeze_requirement_baseline(
    session: AsyncSession, cmd: FreezeRequirementBaselineCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if not cmd.requirement_refs:
        raise ValidationFailedError("requirement_refs must not be empty")

    gaps = await _find_gaps(session, cmd.requirement_refs)
    baseline_hash = hashlib.sha256(
        json.dumps({"refs": cmd.requirement_refs, "exclusions": cmd.exclusions}, sort_keys=True).encode()
    ).hexdigest()

    row = RequirementBaseline(
        release_scope=cmd.release_scope, customer_scope=cmd.customer_scope, requirement_refs=cmd.requirement_refs,
        exclusions=cmd.exclusions, baseline_hash=baseline_hash, gaps_detected=gaps, state="FROZEN", version=1,
    )
    session.add(row)
    await session.flush()

    # Document 81's own field list names a "hash/Vault ref" for this entity (REQ-FR-021: "freeze
    # requirement set/version/hash for validation/release") -- a frozen baseline is exactly Document 06's
    # "controlled document snapshot", so it gets a real immutable vault object, not just the bare hash
    # column already computed above. One vault object per baseline row (business_id=row.id) rather than
    # per release_scope, since a later re-freeze for the same release_scope is a distinct baseline, not a
    # correction of this one.
    vault_obj = await vault_service.release_master(
        session, object_type="requirement_baseline", business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={"requirement_refs": cmd.requirement_refs, "exclusions": cmd.exclusions},
    )
    row.vault_object_id = vault_obj.object_id

    if gaps:
        await write_outbox_event(
            session, event_type="TraceabilityGapDetected", aggregate_type="requirement_baseline",
            aggregate_id=row.id, aggregate_version=1, payload={"gaps": gaps}, correlation_id=uuid.uuid4(),
        )

    new_value = {"release_scope": row.release_scope, "baseline_hash": baseline_hash, "gap_count": len(gaps)}
    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="requirement_baseline", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value=new_value, event_type="RequirementBaselineFrozen", expected_version=None,
        command_type="FreezeRequirementBaseline", site_id=site_id,
    )


async def get_traceability(session: AsyncSession, baseline_id: uuid.UUID) -> dict:
    baseline = await session.get(RequirementBaseline, baseline_id)
    if baseline is None:
        raise NotFoundError("Requirement baseline not found")
    return {
        "release_scope": baseline.release_scope, "requirement_count": len(baseline.requirement_refs),
        "exclusion_count": len(baseline.exclusions), "gap_count": len(baseline.gaps_detected),
        "baseline_hash": baseline.baseline_hash,
    }


async def get_traceability_gaps(session: AsyncSession, baseline_id: uuid.UUID) -> dict:
    """Read-only: recomputes gaps live against current trace links rather than returning the
    possibly-stale snapshot captured at freeze time."""
    baseline = await session.get(RequirementBaseline, baseline_id)
    if baseline is None:
        raise NotFoundError("Requirement baseline not found")
    gaps = await _find_gaps(session, baseline.requirement_refs)
    return {"release_scope": baseline.release_scope, "gaps": gaps}


async def _traceability_rows(session: AsyncSession, baseline_id: uuid.UUID) -> tuple[RequirementBaseline, list[list]]:
    baseline = await session.get(RequirementBaseline, baseline_id)
    if baseline is None:
        raise NotFoundError("Requirement baseline not found")

    excluded_codes = {e.get("code"): e.get("rationale") for e in baseline.exclusions}
    out: list[list] = []
    for ref in baseline.requirement_refs:
        code, version = ref.get("code"), ref.get("version")
        links = (
            await session.execute(
                select(TraceLink).where(TraceLink.source_type == "validation_requirement", TraceLink.source_id == code)
            )
        ).scalars().all()
        has_test_link = any(l.relation_type == "TEST" for l in links)
        rows = links or [None]
        for link in rows:
            out.append([
                baseline.release_scope, code, version, code in excluded_codes, excluded_codes.get(code, ""),
                has_test_link, link.relation_type if link else "", link.target_type if link else "",
                link.target_id if link else "",
            ])
    return baseline, out


async def export_traceability_csv(session: AsyncSession, baseline_id: uuid.UUID) -> str:
    """REQ-FR-022: a real, generated CSV export of the authoritative traceability graph -- one row per
    requirement in the frozen baseline, with every trace link found for it (design/test/defect) and
    whether a TEST link exists at all. Built from the authoritative `requirement_baseline`/`trace_link`
    tables at export time, not from a spreadsheet (REQ-FR-023: the spreadsheet is an export, never the
    source)."""
    import csv
    import io

    baseline, rows = await _traceability_rows(session, baseline_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "release_scope", "requirement_code", "requirement_version", "excluded", "exclusion_rationale",
        "has_test_link", "trace_link_relation", "trace_link_target_type", "trace_link_target_id",
    ])
    writer.writerows(rows)
    return buf.getvalue()


async def export_traceability_pdf(session: AsyncSession, baseline_id: uuid.UUID) -> bytes:
    """REQ-FR-022 (resolved SG-169, 2026-09-01): the same authoritative traceability graph as
    `export_traceability_csv()`, rendered as a paginated PDF via ReportLab for the auditor-/customer-
    facing case CSV doesn't fit. Same source query, same rows -- this is a rendering choice, not a
    second data path."""
    from app.modules.validation.shared import render_pdf_report

    baseline, rows = await _traceability_rows(session, baseline_id)
    header = [
        "Requirement", "Ver", "Excluded", "Rationale", "Has Test", "Link Relation", "Link Target Type", "Link Target",
    ]
    table_rows = [
        [r[1], r[2], "Yes" if r[3] else "No", r[4], "Yes" if r[5] else "No", r[6], r[7], r[8]] for r in rows
    ]
    return render_pdf_report(
        title="Requirement Traceability Export",
        subtitle=f"Release scope: {baseline.release_scope} — {len(rows)} row(s)",
        sections=[("Traceability", header, table_rows)],
    )
