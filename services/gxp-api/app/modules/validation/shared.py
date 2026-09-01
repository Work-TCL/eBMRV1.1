"""Shared Mutation Gateway plumbing for every WP-12 (Documents 79-96) submodule -- the same `_finalize`
(audit event + outbox event + command receipt, one PostgreSQL transaction) and signature-challenge
consumption shape every other module in this codebase repeats per module (see
`app/modules/disaster_recovery/commands.py::_finalize` / `app/modules/batch/commands.py::
_verify_reauth_and_consume`), collected once here since all fifteen WP-12 submodules need the identical
shape rather than fifteen near-identical private copies.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.evidence.models import EvidenceObject
from app.modules.iam.models import User
from app.modules.signature import service as signature_service
from app.mutation.errors import MissingSignatureError, ValidationFailedError
from app.mutation.gateway import record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id, correlation_id=existing.id,
    )


def record_hash(record_id: uuid.UUID, version: int) -> str:
    """Identical binding surface as every other module's `_record_hash()`/`record_hash()` helper (id,
    version) -- see `app/modules/qms/signature_support.py::record_hash`."""
    return sha256_hex({"id": str(record_id), "version": version})


async def finalize(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_type: str,
    aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID, reason: str | None,
    old_value: dict | None, new_value: dict, event_type: str, expected_version: int | None, command_type: str,
    site_id: uuid.UUID | None = None, signature_id: uuid.UUID | None = None,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value=old_value, new_value=new_value, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, payload=new_value, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=site_id, command_type=command_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, correlation_id=correlation_id, signature_id=signature_id,
    )


async def resolve_signature(session: AsyncSession, *, record_type: str, action: str):
    """Thin re-export so every WP-12 commands.py imports one name from one place. Resolution itself is
    Document 106 policy data, never a code conditional (AG-07/SIG-FR-004) -- see
    `app/modules/signature/service.py::resolve_signature_requirement`. Fails closed
    (SIGNATURE_POLICY_UNRESOLVED) when no policy row exists."""
    return await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)


async def verify_reauth_and_consume(
    session: AsyncSession, *, actor_user_id: uuid.UUID, challenge_id: uuid.UUID, reauth_password: str,
    record_id: uuid.UUID, record_version: int,
) -> uuid.UUID:
    """Fresh step-up (Document 04 SIG-FR-006/Document 106 P8) + single-use challenge consumption +
    signature creation. Identical shape to `app/modules/batch/commands.py::_verify_reauth_and_consume`,
    generalized off one hardcoded aggregate type."""
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id,
        record_version=record_version, record_hash=record_hash(record_id, record_version),
    )
    signature = await signature_service.sign(
        session, challenge=challenge, auth_context={"method": "password_reauth"}
    )
    return signature.id


def render_pdf_report(*, title: str, subtitle: str, sections: list[tuple[str, list[str], list[list]]]) -> bytes:
    """SG-169 (resolved): shared ReportLab renderer for the WP-12 CSV-equivalent PDF exports
    (`export_package_pdf()` / `export_traceability_pdf()`) -- one title/subtitle page followed by one
    Platypus `Table` per `(section_heading, header_row, data_rows)` tuple. Kept in one place so both
    export functions render identically rather than hand-rolling ReportLab layout twice. Pure in-memory
    render (`io.BytesIO`), no filesystem write -- the caller streams the returned bytes directly."""
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER, topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch, title=title,
    )
    story = [Paragraph(title, styles["Title"]), Paragraph(subtitle, styles["Normal"]), Spacer(1, 0.25 * inch)]
    for heading, header_row, data_rows in sections:
        story.append(Paragraph(heading, styles["Heading2"]))
        table_data = [header_row] + [[str(c) for c in row] for row in data_rows]
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbe4ee")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))
    doc.build(story)
    return buf.getvalue()


async def verify_evidence_refs(session: AsyncSession, evidence_manifest: list[dict]) -> None:
    """AG-12/OBJ-FR-004: any `evidence_manifest` entry that names a real Evidence Store object (via an
    `evidence_id` key) must point at a `FINALIZED`/`ARCHIVED` object -- a validation record cannot cite
    evidence the store itself doesn't yet consider real. This is a plain DB existence/state check, not
    the full `evidence.commands.verify_evidence_integrity()` object-store `head()` scan (that is a
    scheduled integrity job, not something every completion command should pay object-store I/O for).
    Entries with no `evidence_id` key (e.g. a raw file path from an installed-inventory dump, or a
    third-party report reference) are plain provenance strings and pass through unchanged -- not every
    piece of evidence this module records is Evidence-Store-backed."""
    for item in evidence_manifest:
        evidence_id = item.get("evidence_id") if isinstance(item, dict) else None
        if evidence_id is None:
            continue
        try:
            obj = await session.get(EvidenceObject, uuid.UUID(str(evidence_id)))
        except ValueError:
            raise ValidationFailedError("evidence_manifest entry has a malformed evidence_id", evidence_id=str(evidence_id))
        if obj is None or obj.state not in ("FINALIZED", "ARCHIVED"):
            raise ValidationFailedError(
                "evidence_manifest references an evidence object that is not finalized", evidence_id=str(evidence_id)
            )
