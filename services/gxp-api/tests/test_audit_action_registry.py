"""SG-142 partial resolution (2026-09-14, project-owner-directed: "build the registry + warn-only
logging now"). `write_audit_event()` (app/mutation/gateway.py) checks every action against
`app/mutation/audit_actions.py::KNOWN_AUDIT_ACTIONS` and logs a warning for an unregistered value, but
never rejects the write -- closing this to a hard-enforced enum is a separate, later phase (see the
registry module's own docstring for why).
"""

import logging
import uuid

from app.modules.audit.models import AuditEvent
from app.mutation.audit_actions import KNOWN_AUDIT_ACTIONS
from app.mutation.gateway import write_audit_event


async def test_write_audit_event_accepts_known_action_without_warning(db, caplog):
    with caplog.at_level(logging.WARNING, logger="app.mutation.gateway"):
        async with db.begin():
            event = await write_audit_event(
                db, site_id=None, aggregate_type="test_aggregate", aggregate_id=uuid.uuid4(),
                aggregate_version=1, action="Created", actor_id=uuid.uuid4(), correlation_id=uuid.uuid4(),
            )
    assert event.id is not None
    assert not any("audit-action registry" in r.message for r in caplog.records)


async def test_write_audit_event_warns_but_still_commits_for_unregistered_action(db, caplog):
    unregistered = "TotallyMadeUpActionNotInTheRegistry"
    assert unregistered not in KNOWN_AUDIT_ACTIONS
    with caplog.at_level(logging.WARNING, logger="app.mutation.gateway"):
        async with db.begin():
            event = await write_audit_event(
                db, site_id=None, aggregate_type="test_aggregate", aggregate_id=uuid.uuid4(),
                aggregate_version=1, action=unregistered, actor_id=uuid.uuid4(), correlation_id=uuid.uuid4(),
            )
    assert event.id is not None
    assert any("audit-action registry" in r.message and unregistered in r.message for r in caplog.records)

    async with db.begin():
        persisted = await db.get(AuditEvent, event.id, populate_existing=True)
    assert persisted is not None
    assert persisted.action == unregistered