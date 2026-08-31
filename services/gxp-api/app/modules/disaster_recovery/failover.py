"""Document 76 (SPEC-DATA-008) `promoteStandby()` -- DR-FR-021/022/024.

Phase 1 runs a single PostgreSQL primary with no configured standby/replica (Document 70 PG-FR-002's
"managed PostgreSQL or self-hosted HA profile" is a deployment-profile choice not yet made) -- there is
nothing to promote. `record_database_failover()` is the governance record a real failover tool would
call: it requires an incident/change reference, previous/new primary identity and a reason before
recording anything (DR-FR-024: "DR activation has incident/change record, owner, time"), and emits
`DatabaseFailoverCompleted`. Split-brain prevention (DR-FR-022) is a deployment-topology guarantee (a
fencing/consensus mechanism such as Patroni or a cloud-managed failover controller) this single-primary
Phase 1 does not need and does not fabricate -- recorded as a known limitation, not guessed.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.mutation.errors import ValidationFailedError
from app.mutation.gateway import write_audit_event, write_outbox_event


async def record_database_failover(
    session: AsyncSession, *, incident_ref: str, previous_primary: str, new_primary: str,
    reason: str, actor_user_id: uuid.UUID,
) -> dict:
    if not incident_ref or not reason:
        raise ValidationFailedError("incident_ref and reason are required to record a database failover (DR-FR-024)")
    if previous_primary == new_primary:
        raise ValidationFailedError("new_primary must differ from previous_primary")

    aggregate_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    await write_audit_event(
        session, site_id=None, aggregate_type="disaster_recovery", aggregate_id=aggregate_id,
        aggregate_version=1, action="StatusChanged", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason,
        new_value={"incident_ref": incident_ref, "previous_primary": previous_primary, "new_primary": new_primary},
    )
    await write_outbox_event(
        session, event_type="DatabaseFailoverCompleted", aggregate_type="disaster_recovery",
        aggregate_id=aggregate_id, aggregate_version=1,
        payload={"incident_ref": incident_ref, "previous_primary": previous_primary, "new_primary": new_primary},
        correlation_id=correlation_id,
    )
    return {"failover_id": str(aggregate_id), "incident_ref": incident_ref, "new_primary": new_primary}
