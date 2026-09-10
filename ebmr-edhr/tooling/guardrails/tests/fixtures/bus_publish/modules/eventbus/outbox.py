async def publish_outbox_event(event):
    # allowed: this *is* the outbox publisher.
    return {"published": True}


async def republish_all(session, events):
    for event in events:
        await publish_outbox_event(event)
