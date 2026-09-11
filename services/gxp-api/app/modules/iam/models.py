import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    """Also the platform's `iam_subject` (Document 07) — one authoritative human-identity record,
    not a separate parallel table (AG-05)."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # iam_subject fields (Document 07 / docs/generated/04_DATA_MODEL_CATALOGUE.md)
    external_issuer: Mapped[str | None] = mapped_column(String(500))
    external_subject: Mapped[str | None] = mapped_column(String(255))
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False, default="human")
    identity_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signing_entitled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    disabled_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("name"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))


class UserSiteRole(Base):
    """Also the platform's `iam_role_assignment` (Document 07)."""

    __tablename__ = "user_site_roles"
    __table_args__ = (UniqueConstraint("user_id", "site_id", "role_id"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.roles.id"), nullable=False)
    # iam_role_assignment fields (Document 07): time-bounded, approvable assignment.
    effective_from: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.users.id")
    )

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


class Permission(Base):
    """Action/resource-based permission catalog (IAM-FR-006) — what a role can be granted, replacing
    hardcoded role-name checks scattered through the codebase."""

    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("code"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))


class RolePermission(Base):
    """Assigns a Permission to a Role — this is the table "assign permissions to a role" means."""

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"), {"schema": "iam"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.roles.id"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.permissions.id"), nullable=False
    )


class SodRule(Base):
    """Document 107 §3 schema exactly (approved SoD baseline). `role_a`/`role_b` are plain role-name
    strings, not FKs — a rule naming a role nobody currently holds is simply inert, not invalid, so the
    full platform-default matrix seeds safely regardless of which roles a deployment actually has."""

    __tablename__ = "sod_rules"
    __table_args__ = (
        UniqueConstraint("code", "effective_from"),
        CheckConstraint(
            "rule_type <> 'STANDING_ROLE_PAIR' OR (role_a IS NOT NULL AND role_b IS NOT NULL)",
            name="ck_sod_rules_standing_pair_roles",
        ),
        {"schema": "iam"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)  # STANDING_ROLE_PAIR | ACTION_INDEPENDENCE
    role_a: Mapped[str | None] = mapped_column(String(120))
    role_b: Mapped[str | None] = mapped_column(String(120))
    record_class: Mapped[str | None] = mapped_column(String(80))
    action: Mapped[str | None] = mapped_column(String(120))
    independent_of: Mapped[list | None] = mapped_column(JSONB)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # PROHIBITED | REQUIRES_APPROVAL | REPORT_ONLY
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(server_default=func.now())
    effective_to: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    policy_source: Mapped[str] = mapped_column(String(30), nullable=False, default="PLATFORM_FLOOR")


class SodException(Base):
    """Document 107 §3 schema exactly. Not wired to any enforcement/granting workflow this pass — the
    table exists per the specified data model; exception-granting is future work (see SPEC_GAP)."""

    __tablename__ = "sod_exceptions"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    sod_rule_code: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approval_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    valid_from: Mapped[datetime | None] = mapped_column()
    valid_to: Mapped[datetime] = mapped_column(nullable=False)
    review_due: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class ServiceIdentity(Base):
    """Document 43 (SPEC-EDGE-001) SG-120 — minimal non-human identity primitive. No general Document 62
    (Identity Federation/SSO/Service Identities) implementation exists in this codebase; `User.subject_type`
    hints one was anticipated but nothing ever populates it with a working credential path. This table is
    the interim, edge-gateway-scoped mechanism only (MUT-FR-023/AUD-FR-004: non-human actors are a distinct
    identity class from `iam.users`) so EDGE-FR-001/002 and the machine-driven Document 43 APIs are
    callable. `subject_ref` points at the owning `edge.edge_gateways.id` — a plain UUID, not an FK, since
    this table lives in `iam` and must not reach into another module's schema (AG-05). Per Document 106 P7
    (service/device identity can never satisfy a signature requirement), a `ServiceIdentity` is never
    passed to `signature.service.sign()` — see `app/core/security.py::get_service_identity`.
    """

    __tablename__ = "service_identities"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_type: Mapped[str] = mapped_column(String(40), nullable=False, default="edge_gateway")
    subject_ref: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    credential_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column()
