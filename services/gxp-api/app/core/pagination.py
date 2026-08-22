"""Shared server-side pagination/search/sort for list endpoints. Every list endpoint returns the same
envelope shape so the frontend's DataTable component can talk to any of them identically.
"""

from dataclasses import dataclass

from fastapi import Query
from sqlalchemy import Column, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


@dataclass
class PageParams:
    page: int
    page_size: int
    q: str | None
    sort_by: str | None
    sort_dir: str


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="Free-text search"),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> PageParams:
    return PageParams(page=page, page_size=page_size, q=q, sort_by=sort_by, sort_dir=sort_dir)


async def paginate(
    session: AsyncSession,
    base_stmt: Select,
    params: PageParams,
    *,
    sortable: dict[str, Column],
    default_sort: Column,
) -> tuple[list, dict]:
    """`base_stmt` must already have filters (including any `q` search) applied and carry no
    order_by/limit/offset. Returns (rows, envelope) where envelope has total/page/page_size/total_pages.
    """
    total = (await session.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one()

    sort_column = sortable.get(params.sort_by or "", default_sort)
    ordered = sort_column.desc() if params.sort_dir == "desc" else sort_column.asc()
    page_stmt = base_stmt.order_by(ordered).offset((params.page - 1) * params.page_size).limit(
        params.page_size
    )
    rows = (await session.execute(page_stmt)).all()

    total_pages = max(1, (total + params.page_size - 1) // params.page_size)
    envelope = {
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "total_pages": total_pages,
    }
    return rows, envelope
