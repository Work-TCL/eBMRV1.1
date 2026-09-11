from app.modules.eventbus import outbox as eventbus_outbox
from app.mutation.gateway import write_outbox_event


async def bad_direct_publish(event):
    # violation: publishes directly instead of going through the transactional outbox.
    await eventbus_outbox.publish_outbox_event(event)


async def ok_via_gateway(session, **kwargs):
    # allowed: writes the outbox row in the same transaction via the sanctioned gateway helper.
    await write_outbox_event(session, **kwargs)
