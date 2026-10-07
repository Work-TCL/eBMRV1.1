"""Shared helper for the "business code -> row" dict every bulk-import validate/commit pair builds
right before resolving a CSV row's reference field (role_name, site_code, equipment_class_code,
product_family_code, ...). Each of iam/equipment/product_master's commands.py used to hand-roll its own
`{row.code: row for row in rows}` dict comprehension inline -- same shape, four separate copies. This
replaces those comprehensions only; it takes the same already-fetched rows each call site already fetches
(via its own model query or service-layer list function), so it changes no query and no matching
semantics (still an exact, case-sensitive match on the code attribute, same as before).
"""

from typing import Iterable, TypeVar

T = TypeVar("T")


def build_code_index(rows: Iterable[T], code_attr: str) -> dict[str, T]:
    """`{getattr(row, code_attr): row for row in rows}` under one name."""
    return {getattr(row, code_attr): row for row in rows}
