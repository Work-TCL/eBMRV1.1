"""Shared unique-code generation (client requirement #1). One counter per (entity_type, site_id,
prefix) -- `site_id` is the real per-site scope for entities whose own uniqueness constraint is
site-scoped (currently only `Material.code`, `UniqueConstraint(site_id, code)`); entities whose real
constraint is table-wide (equipment asset/area, supplier, product, recipe codes) key on the nil UUID
sentinel (`NIL_SITE_ID`) instead, so two sites never legitimately mint the same global code. This
table is not itself a regulated/audited entity -- it is purely a monotonic counter consumed inside the
same transaction as the create command that needs a code, never pre-reserved outside it.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

NIL_SITE_ID = uuid.UUID(int=0)


class CodeSequenceCounter(Base):
    __tablename__ = "code_sequence_counter"
    __table_args__ = (UniqueConstraint("entity_type", "site_id", "prefix"), {"schema": "codegen"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    last_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
