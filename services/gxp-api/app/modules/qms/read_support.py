"""Shared shaping helpers for the WP-05 QMS read side.

Every QMS aggregate lists the same way -- filter by site, optionally by workflow state, free-text search
on the human-facing record number, then hand off to the standard `paginate()` envelope so the frontend's
DataTable talks to all of them identically. This module holds that one filter builder plus the datetime/
UUID shaping every `_dict()` needs, rather than repeating both in ten routers.

These are non-authoritative reads (AG-11): they exist so a reviewer can find a record. Every regulated
decision still reads the owning aggregate through its command path.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column
from sqlalchemy.sql import Select

from app.core.pagination import PageParams


def iso(value: datetime | None) -> str | None:
    """ISO-8601 or None -- the shape every existing `_dict()` in this codebase emits for a timestamp."""
    return value.isoformat() if value else None


def sid(value: uuid.UUID | None) -> str | None:
    """UUID as a string, preserving None (JSON has no UUID type and `str(None)` would emit "None")."""
    return str(value) if value else None


def filtered(
    model: Any,
    params: PageParams,
    *,
    search_column: Column,
    site_id: uuid.UUID | None = None,
    state: str | None = None,
    state_column: Column | None = None,
) -> Select:
    """Base statement for a QMS list endpoint: site scope, optional workflow state, free-text search.

    Returns a statement carrying filters only -- no order_by/limit/offset -- which is exactly what
    `paginate()` requires of its `base_stmt`.
    """
    from sqlalchemy import select

    stmt = select(model)
    if site_id is not None:
        stmt = stmt.where(model.site_id == site_id)
    if state:
        column = state_column if state_column is not None else model.state
        stmt = stmt.where(column == state)
    if params.q:
        stmt = stmt.where(search_column.ilike(f"%{params.q}%"))
    return stmt
