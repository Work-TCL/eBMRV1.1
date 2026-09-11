from sqlalchemy import text


async def bad_frappe_style(record_id, new_status):
    # violation: literal frappe.db.set_value() equivalent.
    frappe.db.set_value("Regulated Doc", record_id, "status", new_status)


async def bad_raw_sql(session, record_id, new_status):
    # violation: raw SQL UPDATE via text() bypasses the ORM version/audit discipline.
    await session.execute(text("UPDATE regulated.records SET status = :s WHERE id = :id"), {"s": new_status, "id": record_id})


async def bad_generic_patch(record, payload):
    # violation: copies every externally-provided field onto the record with no per-field validation.
    for field, value in payload.items():
        setattr(record, field, value)


async def ok_bounded_setattr(record, which):
    # allowed: field name comes from a fixed, closed vocabulary chosen by internal control flow, not
    # from an externally-provided payload dict.
    field = "approved_at" if which == "approve" else "rejected_at"
    setattr(record, field, "now")
