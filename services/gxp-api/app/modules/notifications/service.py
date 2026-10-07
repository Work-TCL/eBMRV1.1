"""Read/write logic for the workflow-notification projection. Two writers converge on the same
`sync_notification()`: the NATS consumer (`consumer.py`, event-driven) and `rebuild_all()` (a full rescan,
the AG-11 recovery path if the projection is ever lost or believed stale -- same role as
`readmodels/search.py::rebuild_search_index()`). Both are idempotent and order-independent because
`sync_notification()` always re-derives the *current* state from the aggregate's own authoritative table
(via `registry.py`'s loader) rather than trusting anything about the specific event/call that triggered it
-- so processing the same aggregate twice, out of order, or from a full rescan always converges on the same
row (AG-11's rebuildability, and "duplicate events cannot create duplicate notifications" satisfied by the
`uq_workflow_notification_identity` constraint on (aggregate_type, aggregate_id, category) that every write
here upserts against).

`list_visible_notifications()` is also where the UI-side self-healing safety net lives (per the task's own
requirement): every open notification it returns is re-checked against the aggregate's *current* state in
the same request, and lazily resolved if the aggregate has already moved on -- so even a fully stopped
consumer cannot leave a stale notification visible to anyone who reads through this function.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.iam.models import Permission, Role, RolePermission, UserSiteRole
from app.modules.notifications.models import WorkflowNotification, WorkflowNotificationRead
from app.modules.notifications.registry import (
    RULE_BY_CATEGORY,
    WORKFLOW_SPECS,
    EntitySnapshot,
    WorkflowNotificationSpec,
)
from app.modules.policy.service import effective_role_names
from app.modules.signature.models import SignaturePolicy


async def _get_open(
    session: AsyncSession, *, aggregate_type: str, aggregate_id: uuid.UUID, category: str
) -> WorkflowNotification | None:
    return await session.scalar(
        select(WorkflowNotification).where(
            WorkflowNotification.aggregate_type == aggregate_type,
            WorkflowNotification.aggregate_id == aggregate_id,
            WorkflowNotification.category == category,
        )
    )


async def _upsert_or_resolve(
    session: AsyncSession, *, aggregate_type: str, aggregate_id: uuid.UUID, category: str,
    required_permission_code: str, pending: bool, snapshot: EntitySnapshot, source_event_id: uuid.UUID | None,
) -> None:
    existing = await _get_open(session, aggregate_type=aggregate_type, aggregate_id=aggregate_id, category=category)
    now = datetime.now(timezone.utc)

    if not pending:
        if existing is not None and existing.resolved_at is None:
            existing.resolved_at = now
            existing.version += 1
        return

    if existing is None:
        session.add(
            WorkflowNotification(
                aggregate_type=aggregate_type, aggregate_id=aggregate_id, category=category,
                required_permission_code=required_permission_code, site_id=snapshot.site_id,
                excluded_actor_id=snapshot.last_actor_id, entity_label=snapshot.entity_label,
                link_path=snapshot.link_path, source_event_id=source_event_id,
            )
        )
        return

    # Reopen (was previously resolved -- e.g. a REOPENED deviation walking back through the same state)
    # or simply refresh denormalized display fields that may have changed since it was opened.
    if existing.resolved_at is not None:
        existing.opened_at = now
        existing.resolved_at = None
    existing.site_id = snapshot.site_id
    existing.excluded_actor_id = snapshot.last_actor_id
    existing.entity_label = snapshot.entity_label
    existing.link_path = snapshot.link_path
    existing.source_event_id = source_event_id
    existing.version += 1


async def sync_notification(
    session: AsyncSession, *, spec: WorkflowNotificationSpec, aggregate_id: uuid.UUID,
    source_event_id: uuid.UUID | None,
) -> dict:
    """Re-derives every category this aggregate type can raise against the aggregate's *current* state
    and upserts/resolves each accordingly. Returns a small summary dict (consumer/test-friendly), never
    raises for "entity not found yet" -- a redelivered event for an aggregate not yet visible in this
    transaction is a no-op, not a poison message."""
    snapshot = await spec.loader(session, aggregate_id)
    if snapshot is None:
        return {"aggregate_id": str(aggregate_id), "skipped": "entity not found"}

    active_rule = spec.pending_states.get(snapshot.state)
    # Compared by category, not object identity: registry.py builds some multi-state groups (e.g. NCR's
    # REWORK/REPAIR/RETURN/SCRAP/USE_AS_IS, all sharing "ncr_verification_pending") with a fresh
    # PendingStateRule instance per state key, even when several states share one category -- `is` would
    # wrongly read those as different rules and never mark the category pending.
    active_category = active_rule.category if active_rule is not None else None
    for category, rule in spec.categories.items():
        await _upsert_or_resolve(
            session, aggregate_type=spec.aggregate_type, aggregate_id=aggregate_id, category=category,
            required_permission_code=rule.required_permission_code, pending=(category == active_category),
            snapshot=snapshot, source_event_id=source_event_id,
        )
    return {"aggregate_id": str(aggregate_id), "state": snapshot.state, "active_category": active_rule.category if active_rule else None}


async def rebuild_all(session: AsyncSession) -> dict:
    """AG-11 recovery path: rescans every row of every registered aggregate type's own authoritative
    table (not the audit ledger -- `EntitySnapshot` always wants *current* state, not a historical
    version) and re-syncs its notifications. Safe to run at any time, including against an empty
    notifications table (rebuilds it from scratch) or a fully populated one (idempotent no-op for
    anything unchanged)."""
    counts: dict[str, int] = {}
    for aggregate_type, spec in WORKFLOW_SPECS.items():
        ids = await spec.list_all_ids(session)
        for entity_id in ids:
            await sync_notification(session, spec=spec, aggregate_id=entity_id, source_event_id=None)
        counts[aggregate_type] = len(ids)
    return {"rescanned": counts}


async def _actor_site_permission_pairs(session: AsyncSession, actor_user_id: uuid.UUID) -> set[tuple[uuid.UUID, str]]:
    now = datetime.now(timezone.utc)
    rows = await session.execute(
        select(UserSiteRole.site_id, Permission.code)
        .join(Role, Role.id == UserSiteRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            UserSiteRole.user_id == actor_user_id, UserSiteRole.status == "active",
            UserSiteRole.effective_from <= now,
            or_(UserSiteRole.expires_at.is_(None), UserSiteRole.expires_at > now),
        )
    )
    return set(rows.all())


async def _signer_role_name_for_category(
    session: AsyncSession, category: str, cache: dict[str, str | None],
) -> str | None:
    """SG-214 fix: reads the *current* `signature.signature_policy.required_role_id` for this category's
    (signature_record_type, signature_action) -- the same policy data `signature_service
    .resolve_signature_requirement()` reads for the real write -- and resolves it to a role name. Returns
    `None` when the category has no signature pointer (`registry.py`'s `PendingStateRule` default) or no
    policy row names a required role, meaning "nothing to narrow beyond the RBAC permission check."
    `cache` is per-call (one `list_visible_notifications()` invocation, potentially many notifications
    sharing one category) so a repeated category costs one query, not one per row."""
    if category in cache:
        return cache[category]
    rule = RULE_BY_CATEGORY.get(category)
    role_name: str | None = None
    if rule is not None and rule.signature_record_type is not None:
        policy = await session.scalar(
            select(SignaturePolicy).where(
                SignaturePolicy.record_type == rule.signature_record_type,
                SignaturePolicy.action == rule.signature_action,
            )
        )
        if policy is not None and policy.required_role_id is not None:
            role_name = await session.scalar(select(Role.name).where(Role.id == policy.required_role_id))
    cache[category] = role_name
    return role_name


async def list_visible_notifications(session: AsyncSession, actor_user_id: uuid.UUID) -> list[WorkflowNotification]:
    permission_pairs = await _actor_site_permission_pairs(session, actor_user_id)
    if not permission_pairs:
        return []
    # "Any site" holders of each code -- for the notifications whose own site_id is None (oot_record,
    # supplier_qualification, an unset-site oos_record), matching policy.service.effective_role_names's
    # own "site_id=None means any site" semantics, not a separate invented rule.
    permission_codes_any_site = {code for (_, code) in permission_pairs}

    candidates = (
        (await session.execute(select(WorkflowNotification).where(WorkflowNotification.resolved_at.is_(None))))
        .scalars()
        .all()
    )

    visible: list[WorkflowNotification] = []
    signer_role_cache: dict[str, str | None] = {}
    actor_role_names_cache: dict[uuid.UUID | None, set[str]] = {}
    for notification in candidates:
        if notification.excluded_actor_id == actor_user_id:
            continue
        if notification.site_id is None:
            if notification.required_permission_code not in permission_codes_any_site:
                continue
        elif (notification.site_id, notification.required_permission_code) not in permission_pairs:
            continue

        required_signer_role = await _signer_role_name_for_category(session, notification.category, signer_role_cache)
        if required_signer_role is not None:
            if notification.site_id not in actor_role_names_cache:
                actor_role_names_cache[notification.site_id] = await effective_role_names(
                    session, actor_user_id, notification.site_id
                )
            if required_signer_role not in actor_role_names_cache[notification.site_id]:
                continue  # holds the RBAC permission but not the narrower signature-policy signer role

        # Self-healing safety net: re-check current entity state before showing it, even if the
        # consumer already resolved (or never processed) this exact row.
        spec = WORKFLOW_SPECS[notification.aggregate_type]
        snapshot = await spec.loader(session, notification.aggregate_id)
        active_rule = spec.pending_states.get(snapshot.state) if snapshot is not None else None
        still_pending = active_rule is not None and active_rule.category == notification.category
        if not still_pending:
            notification.resolved_at = datetime.now(timezone.utc)
            notification.version += 1
            continue

        visible.append(notification)

    visible.sort(key=lambda n: n.opened_at)
    return visible


async def mark_read(session: AsyncSession, *, notification_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
    existing = await session.scalar(
        select(WorkflowNotificationRead).where(
            WorkflowNotificationRead.notification_id == notification_id,
            WorkflowNotificationRead.user_id == actor_user_id,
        )
    )
    if existing is not None:
        return
    session.add(WorkflowNotificationRead(notification_id=notification_id, user_id=actor_user_id))


async def read_notification_ids(session: AsyncSession, *, actor_user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = await session.execute(
        select(WorkflowNotificationRead.notification_id).where(WorkflowNotificationRead.user_id == actor_user_id)
    )
    return set(rows.scalars().all())
