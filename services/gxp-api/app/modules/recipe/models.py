import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (UniqueConstraint("product_id", "version"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.products.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RecipeStep(Base):
    __tablename__ = "recipe_steps"
    __table_args__ = (UniqueConstraint("recipe_id", "step_number"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.recipes.id"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    instructions: Mapped[str | None] = mapped_column(String(4000))
    requires_signature: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signature_meaning: Mapped[str | None] = mapped_column(String(50))
