"""Document 31 (SPEC-QMS-006) -- Training & Personnel Qualification. Same owner service as Documents
26-30 (`services/gxp-api/app/modules/qms`), so these entities live in the same `qms` schema
(migration 0029_training_qualification_schema). This module's own API prefix is `/training/v1`.

`training_requirement`'s 5-field list and `qualification_record`'s 6-field list in
docs/generated/04_DATA_MODEL_CATALOGUE.md are both prose, not DDL-ready -- like ncr_disposition and
controlled_copy before them (SG-045's precedent), they are genuinely unambiguous and typed directly.
`training_assignment`'s 10-field list is DDL-ready as given.

`training_waiver` is a fourth table beyond the catalogue's declared 3-entity count: TRN-FR-015 requires
"reason/scope/approver/expiry" as first-class data, and `POST /training/v1/waivers` is its own declared
API operation (not a sub-action of qualification or assignment), so it needs its own backing store --
ordinary engineering to persist a declared operation, not an invented requirement (same latitude used for
Document 30's controlled_copy, which was also a table beyond the catalogue's headline description).

A genuine architecture finding: `iam.qualifications` (WP-01, Document 07 SPEC-IAM-001) already exists as
an authoritative store for what looks like the same real-world concept -- a subject's qualification for a
task. Document 07 lists "Training/Qualification specification" as a dependency and defines its own
`iam_qualification` model, its own execution-time gate ("Execution checks qualification at action time,
not only at login") and its own error codes QUALIFICATION_MISSING/QUALIFICATION_EXPIRED -- but that gate
is not wired into the Mutation Gateway anywhere in this codebase (grep confirms zero call sites), and
`iam.qualifications` has no `version`/`state` column, so it was never built through the full Mutation
Gateway pattern. `docs/generated/04_DATA_MODEL_CATALOGUE.md` declares `qualification_record`'s migration
owner as this module (`services/gxp-api/src/modules/qms`), so this module builds its own entity as
specified rather than writing into `iam.qualifications` (a different service's authoritative schema,
AG-05/AG-06). The dual-authority question -- which one the platform-wide execution gate should ultimately
read, and whether `qms.qualification_record` should write through to `iam.qualifications` on issuance --
is filed as SG-086 rather than guessed.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# TRN-FR-002: "Training can originate from document, role, qualification, change, CAPA or manager
# assignment" -- the source_type enumeration Document 31 itself gives.
SOURCE_TYPES = ("document", "role", "qualification", "change", "capa", "manager_assignment")

# TRN-FR-004: the training types Document 31 itself enumerates.
TRAINING_TYPES = (
    "read_and_understand", "instructor_led", "practical_ojt", "exam", "demonstration", "qualification",
    "recurring",
)

ASSIGNMENT_STATES = ("ASSIGNED", "ASSESSMENT_PENDING", "COMPLETED", "FAILED")

# IN_PROGRESS (named in Document 31 section 4's diagram) has no dedicated "start" operation in this
# module's own 6-op mutating API list, so it is folded into ASSIGNED -- the same fold-in pattern this
# module family has used since SG-055 (no operation to drive a named diagram state independently).
ASSIGNMENT_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "ASSIGNED": {"ASSESSMENT_PENDING", "COMPLETED"},
    "ASSESSMENT_PENDING": {"COMPLETED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": set(),  # terminal -- TRN-FR-024 "failed attempts retained"; retraining creates a NEW
    # linked assignment (retrain_of_assignment_id) rather than reopening this one (TRN-FR-022 "history...
    # does not rewrite old training").
}

QUALIFICATION_STATES = ("QUALIFIED", "EXPIRING", "EXPIRED", "RENEWED")


class TrainingRequirement(Base):
    __tablename__ = "training_requirement"
    __table_args__ = {"schema": "qms"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    # TRN-FR-001: "role/site/department/product/process/equipment/area" -- a flexible multi-dimensional
    # curriculum scope, typed as structured JSON (same latitude as controlled_document's site_scope).
    scope: Mapped[dict | None] = mapped_column(JSONB)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # Unenforced logical reference (uuid, no FK): source_type is polymorphic across document/change/capa/
    # qualification/role -- a real FK would need a per-type check constraint or a join table this
    # module's own scope does not call for; every other cross-module reference in this codebase uses the
    # same unenforced-logical-id pattern until the referencing module explicitly builds the join.
    source_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    training_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # TRN-FR-005: "Document training references exact released version" -- a real enforced FK, since
    # Document 30 (built in this same WP-05 pass) makes controlled_document_version available.
    content_document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("qms.controlled_document_version.id")
    )
    recurrence_interval_days: Mapped[int | None] = mapped_column()
    requires_assessment: Mapped[bool] = mapped_column(nullable=False, default=False)
    pass_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2))
    # TRN-FR-017: "Trainer/evaluator qualification where required" -- an explicit, curriculum-author-
    # supplied qualification code (never a code this module invents; Document 31 gives no qualification
    # taxonomy, so the taxonomy is caller-configured per requirement, matching TRN-FR-011's "explicit
    # controlled policy only" principle).
    required_trainer_qualification_code: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class TrainingAssignment(Base):
    __tablename__ = "training_assignment"
    __table_args__ = (
        Index("ix_training_assignment_requirement", "requirement_id"),
        Index("ix_training_assignment_subject", "subject_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    requirement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.training_requirement.id"), nullable=False)
    # TRN-FR-005: the exact content version snapshotted at assignment time (may differ from the
    # requirement's current content_document_version_id if the requirement is later re-pointed).
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.controlled_document_version.id"))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="ASSIGNED")
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())
    due_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    result: Mapped[str | None] = mapped_column(String(40))
    # TRN-FR-006: "trainee/trainer/date/score/result/evidence/signature".
    trainer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2))
    # TRN-FR-007/008: "attempt rules" (no numeric attempt cap given anywhere in the baseline -- SG-087)
    # and "observed checklist" for practical qualification.
    attempt_number: Mapped[int] = mapped_column(nullable=False, default=1)
    practical_checklist: Mapped[dict | None] = mapped_column(JSONB)
    evidence_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id"))
    # TRN-FR-014: equivalency credit for prior training/experience, requires evidence and approval.
    equivalency_credit: Mapped[bool] = mapped_column(nullable=False, default=False)
    equivalency_evidence: Mapped[str | None] = mapped_column(Text)
    equivalency_approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    waiver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.training_waiver.id"))
    # TRN-FR-012: retraining triggers; TRN-FR-022/024: history preserved, a new linked record instead of
    # rewriting the failed one.
    retrain_of_assignment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.training_assignment.id"))
    retraining_trigger: Mapped[str | None] = mapped_column(String(40))
    # TRN-FR-021: external course/certificate, folded into this same assignment rather than a new
    # endpoint (source_type="external" on the requirement signals the assignment is for an external item).
    external_source: Mapped[str | None] = mapped_column(String(200))
    external_reference: Mapped[str | None] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QualificationRecord(Base):
    __tablename__ = "qualification_record"
    __table_args__ = (
        Index("ix_qualification_record_subject", "subject_id", "qualification_code"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    qualification_code: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[dict | None] = mapped_column(JSONB)
    effective_from: Mapped[datetime] = mapped_column(nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="QUALIFIED")
    evaluator_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    # TRN-FR-009: "Completion may issue qualification" -- the completed assignment that earned it.
    source_assignment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.training_assignment.id"))
    # TRN-FR-010: renewal supersedes the prior qualification_record rather than editing it in place
    # (the same superseding-history discipline as controlled_document_version).
    renewed_from_qualification_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.qualification_record.id"))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class TrainingWaiver(Base):
    __tablename__ = "training_waiver"
    __table_args__ = {"schema": "qms"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    requirement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.training_requirement.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[dict | None] = mapped_column(JSONB)
    approved_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
