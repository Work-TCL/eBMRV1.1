import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (UniqueConstraint("code"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.organizations.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("name"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))


class UserSiteRole(Base):
    __tablename__ = "user_site_roles"
    __table_args__ = (UniqueConstraint("user_id", "site_id", "role_id"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.roles.id"), nullable=False)

    role: Mapped["Role"] = relationship()


class Qualification(Base):
    __tablename__ = "qualifications"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    qualification_code: Mapped[str] = mapped_column(String(100), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column()
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id")
    )


class SodRule(Base):
    __tablename__ = "sod_rules"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.roles.id"), nullable=False)
    role_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.roles.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
