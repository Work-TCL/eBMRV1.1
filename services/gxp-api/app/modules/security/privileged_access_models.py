"""Document 63 (SPEC-SEC-003) — Privileged Access, Support Access, Break-Glass & Administrative
Security. Same `security` schema Documents 61/62 created; adds the 3 owned entities Document 63 itself
lists: `privileged_access_request`, `privileged_grant`, `privileged_session`.

**PAM-FR-002/012 (admin authority never implies GxP/signature authority)** is structural here, not just
documented: nothing in this file's commands ever calls `signature_service.sign()` / `_resolve_signature()`
against a GxP record, and `activate_break_glass()` never creates an `iam` role grant or touches
`signature.signature_policies` -- a break-glass grant is scoped entirely to this module's own admin-command
allowlist (see `identity_commands.py`... no, `privileged_access_commands.py`'s `CONTROLLED_ADMIN_COMMANDS`).

**No `identity_mapping`-style "not enough owned entities" problem this time** -- Document 63's 8 functions
map cleanly onto its 3 owned tables: `requestPrivilegedAccess`/`approvePrivilegedAccess` ->
`privileged_access_request`/`privileged_grant`; `evaluatePrivilegedGrant` is a read-only check against
`privileged_grant`; `openSupportSession`/`activateBreakGlass`/`closePrivilegedSession`/
`reviewPrivilegedSession` all operate on `privileged_session`; `executeControlledAdminCommand` appends to
`privileged_session.actions` (JSONB, same "history lives on the parent aggregate" precedent as Documents
61/62) rather than a dedicated per-command table.

**Document 106 rows 134-136 resolve for real this time** (unlike Document 61's SG-161): row 135
(`requests/{id}/approve`) and row 136 (`privileged-sessions/{id}/close`) both use the platform-floor
"Module approver role (QA Manager / Head of Quality per record class)" / "QA Approver for the record
class" family defaults, which this codebase has *already* established a consistent non-QMS mapping for --
`scripts/seed.py`'s own `inventory_adjustment_request.approve` and `oos_record.close` rows both resolve
that exact family to **QA Releaser**, "same mapping precedent as supplier_qualification.approve" per its
own comment. This module follows that established precedent rather than inventing a new "security
approver" role. Independence ("MUST be independent of the author"/"...of the investigator/owner") is
enforced in code for real this time (checked against `subject_id`/`opened_by`), unlike SG-160's
acknowledged gap -- this module's request/approve and open/close steps are genuinely separate calls by
(potentially) separate actors, not a single same-transaction ceremony.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

REQUEST_STATES = ("PENDING_APPROVAL", "APPROVED", "DENIED")
GRANT_TYPES = ("JIT", "BREAK_GLASS")
GRANT_STATES = ("ACTIVE", "EXPIRED", "REVOKED")
SESSION_TYPES = ("ADMIN", "SUPPORT", "BREAK_GLASS")
SESSION_STATES = ("ACTIVE", "CLOSED")
REVIEW_STATUSES = ("NOT_REQUIRED", "PENDING", "REVIEWED")


class PrivilegedAccessRequest(Base):
    """`requestPrivilegedAccess()` -- PAM-FR-005/016/017."""

    __tablename__ = "privileged_access_request"
    __table_args__ = {"schema": "security"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    requested_role: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    ticket_ref: Mapped[str | None] = mapped_column(String(120))
    requested_start: Mapped[datetime] = mapped_column(nullable=False)
    requested_end: Mapped[datetime] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING_APPROVAL")
    approver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PrivilegedGrant(Base):
    """`approvePrivilegedAccess()` (JIT) / `activateBreakGlass()` (BREAK_GLASS, `request_id` NULL --
    PAM-FR-011: the emergency path bypasses the request/approval gate by design) -- PAM-FR-004/011/012/017."""

    __tablename__ = "privileged_grant"
    __table_args__ = {"schema": "security"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("security.privileged_access_request.id"))
    grant_type: Mapped[str] = mapped_column(String(20), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(nullable=False)
    expiry: Mapped[datetime] = mapped_column(nullable=False)
    auth_strength: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    # PAM-FR-011/026: break-glass incident/reason linkage; NULL for ordinary JIT grants.
    incident_ref: Mapped[str | None] = mapped_column(String(120))
    granted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PrivilegedSession(Base):
    """`openSupportSession()` / `activateBreakGlass()` / `closePrivilegedSession()` /
    `reviewPrivilegedSession()` -- PAM-FR-006/007/008/009/013/014/015/020/023/026.
    `executeControlledAdminCommand()` appends to `actions` (no dedicated table -- see module docstring)."""

    __tablename__ = "privileged_session"
    __table_args__ = {"schema": "security"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("security.privileged_grant.id"), nullable=False)
    session_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # PAM-FR-020: vendor staff tenant/customer scope + support case reference.
    customer_scope_ref: Mapped[str | None] = mapped_column(String(120))
    support_case_ref: Mapped[str | None] = mapped_column(String(120))
    opened_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column()
    connection_source: Mapped[dict | None] = mapped_column(JSONB)
    # PAM-FR-013/018: append-only executed-command log (command_code, parameters, result, actor, at).
    actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recording_evidence_ref: Mapped[str | None] = mapped_column(String(300))
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_REQUIRED")
    review: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    close_outcome: Mapped[str | None] = mapped_column(String(200))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
