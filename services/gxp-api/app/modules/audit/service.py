"""Document 05 (SPEC-GXP-003) — the query/review/export layer over `audit.audit_events`. This module
owns zero data entities of its own (confirmed against the source spec and
docs/generated/04_DATA_MODEL_CATALOGUE.md — no `gxp_audit_event` entity is declared anywhere): every other
module already writes correctly into the shared, hash-chained, append-only ledger via
`app.mutation.gateway.write_audit_event`. This file is purely read-side.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.iam.models import UserSiteRole
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import ForbiddenError, GxPError
from app.mutation.hashing import sha256_hex


def changed_fields(old_value: dict | None, new_value: dict | None) -> list[str]:
    """AUD-FR-007: a normalized changed-field set, derived at read time rather than stored — no schema
    change needed (see SG-029 for the fields that genuinely do need one: causation_id, source, rule/
    software version)."""
    if old_value is None or new_value is None:
        return sorted((old_value or new_value or {}).keys())
    keys = set(old_value.keys()) | set(new_value.keys())
    return sorted(k for k in keys if old_value.get(k) != new_value.get(k))


def _recomputed_event_hash(event: AuditEvent) -> str:
    """Exactly the same canonicalization `write_audit_event` used at write time — recomputing it here
    is what makes tampering with a stored row detectable (AUD-FR-016's acceptance intent)."""
    return sha256_hex(
        {
            "prev_event_hash": event.prev_event_hash,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": str(event.aggregate_id),
            "aggregate_version": event.aggregate_version,
            "action": event.action,
            "actor_id": str(event.actor_id),
            "occurred_at": event.occurred_at.isoformat(),
            "old_value": event.old_value,
            "new_value": event.new_value,
        }
    )


async def verify_chain(session: AsyncSession, aggregate_type: str, aggregate_id: uuid.UUID) -> dict[uuid.UUID, dict]:
    """Recomputes each event's hash from its own stored fields (detects row-content tampering) and
    confirms each row's `prev_event_hash` matches the previous row's real `event_hash` (detects deletion/
    reordering/relinking). Returns {event_id: {"hash_valid": bool, "link_valid": bool}}.
    """
    events = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.aggregate_type == aggregate_type, AuditEvent.aggregate_id == aggregate_id)
            .order_by(AuditEvent.aggregate_version)
        )
    ).scalars().all()
    result: dict[uuid.UUID, dict] = {}
    prior_hash: str | None = None
    for event in events:
        result[event.id] = {
            "hash_valid": _recomputed_event_hash(event) == event.event_hash,
            "link_valid": event.prev_event_hash == prior_hash,
        }
        prior_hash = event.event_hash
    return result


async def actor_accessible_sites(session: AsyncSession, actor_user_id: uuid.UUID) -> set[uuid.UUID] | None:
    """None means unrestricted (the actor holds `platform.administer` somewhere — reuses the exact same
    check `evaluate_policy` already performs elsewhere, not reinvented). Otherwise, the set of site_ids
    the actor holds any active, currently-effective role at — audit review for a non-admin actor is
    scoped to what they could otherwise see anyway (REMEDIATION_R1 Fix 2's tenancy reasoning, applied here
    for the first time to a cross-cutting read endpoint).
    """
    try:
        await evaluate_policy(session, actor_user_id, action="platform.administer", site_id=None)
        return None
    except GxPError:
        pass

    now = datetime.now(timezone.utc)
    stmt = select(UserSiteRole.site_id).where(
        UserSiteRole.user_id == actor_user_id,
        UserSiteRole.status == "active",
        UserSiteRole.effective_from <= now,
        (UserSiteRole.expires_at.is_(None)) | (UserSiteRole.expires_at > now),
    )
    return set((await session.execute(stmt)).scalars().all())


def apply_site_scope(stmt: Select, accessible_sites: set[uuid.UUID] | None) -> Select:
    """Platform-level events (site_id IS NULL — user/role/organization aggregates) are visible to
    everyone with audit-review access; site-scoped events are restricted to sites the actor can see.
    `accessible_sites=None` means unrestricted (admin)."""
    if accessible_sites is None:
        return stmt
    return stmt.where((AuditEvent.site_id.is_(None)) | (AuditEvent.site_id.in_(accessible_sites)))


async def assert_site_visible(
    session: AsyncSession, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> None:
    """For an explicit single-site filter/lookup: reject up front rather than silently returning an
    empty result, so a caller can tell "not authorized for that site" apart from "no matching events"."""
    if site_id is None:
        return
    accessible = await actor_accessible_sites(session, actor_user_id)
    if accessible is not None and site_id not in accessible:
        raise ForbiddenError("Actor is not authorized to review audit events for this site", site_id=str(site_id))


async def event_to_dict(session: AsyncSession, event: AuditEvent, actor_usernames: dict[uuid.UUID, str]) -> dict:
    return {
        "id": str(event.id),
        "site_id": str(event.site_id) if event.site_id else None,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id),
        "aggregate_version": event.aggregate_version,
        "action": event.action,
        "actor_type": event.actor_type,
        "actor_id": str(event.actor_id),
        "actor_username": actor_usernames.get(event.actor_id),
        "occurred_at": event.occurred_at.isoformat(),
        "reason": event.reason,
        "old_value": event.old_value,
        "new_value": event.new_value,
        "changed_fields": changed_fields(event.old_value, event.new_value),
        "signature_id": str(event.signature_id) if event.signature_id else None,
        "correlation_id": str(event.correlation_id),
        "prev_event_hash": event.prev_event_hash,
        "event_hash": event.event_hash,
    }


async def actor_usernames_for(session: AsyncSession, events: list[AuditEvent]) -> dict[uuid.UUID, str]:
    """Batched actor_id -> username lookup (same pattern as iam/router.py's list_users roles-by-user
    lookup) — there is no DB-level FK from audit_events.actor_id to iam.users.id (actor_type can be
    "service", with no matching user row), so this is an application-level best-effort join."""
    from app.modules.iam.models import User

    actor_ids = {e.actor_id for e in events}
    if not actor_ids:
        return {}
    rows = await session.execute(select(User.id, User.username).where(User.id.in_(actor_ids)))
    return dict(rows.all())
