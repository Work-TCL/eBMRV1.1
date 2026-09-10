"""Document 15 (SPEC-EBMR-006) — Release / Disposition Engine. New module. See migration
<pending>_0016_release_schema for the schema deviations from docs/generated/04_DATA_MODEL_CATALOGUE.md.

`release_scope` is DDL-ready. `release_evaluation` and `release_decision` are prose-only field-name lists
in the catalogue, but -- like 5 of Document 10's 9 entities (SG-045's reasoning) -- both lists are
genuinely unambiguous: no polymorphic value typing, no missing referenced entity, no signature-policy
content to invent. Document 15 §6 even gives a concrete JSON shape for the one semi-structured field
(blockers). Typed here directly as an ordinary engineering decision, not a guess at regulated content --
the same latitude already used for Document 10's unambiguous entities.

Eligibility (REL-FR-003) is supposed to evaluate manufacturing completeness, QA review, QC, QMS,
materials, equipment, environment, packaging, genealogy and yield/reconciliation. Only two of those have
anything real to check against in this codebase: QA review currency/completeness (Document 14, just
built) and Vault execution-snapshot integrity (Document 06, reused the same way Document 14 did). Every
other category has no real data source yet -- see SG-056.

State model (real Document 15 §3/REL-FR-010 names a fuller list: Draft Evaluation, Eligible, Blocked,
Pending Signature, Released, Rejected, Hold, Rework, Reprocess, Destruction, Return/Other). REWORK/
REPROCESS/DESTRUCTION need an approved route entity that doesn't exist anywhere in this codebase (same
gap BAT-FR-024/DHR-FR-012 already hit -- SG-048/050) and have no way to reach closure without one, so
they're not modelled as reachable states this pass. PENDING_SIGNATURE isn't a separate persisted phase --
the signature ceremony is synchronous within release()/reject()/hold(), matching every other signed
action in this codebase. RELEASE_STATES below is the honestly-reachable subset.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

SCOPE_TYPES = ("batch",)  # device_lot/serial/combination scope types need Document 12/13 deeper
                          # integration this pass doesn't build -- see SG-056.

RELEASE_STATES = ("draft_evaluation", "eligible", "blocked", "released", "rejected", "hold")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft_evaluation": {"eligible", "blocked", "hold"},
    "eligible": {"eligible", "blocked", "released", "rejected", "hold"},
    "blocked": {"eligible", "blocked", "rejected", "hold"},
    # REL-FR-031: post-release hold/recall is a new controlled status -- the original RELEASED
    # release_decision row is never edited or removed, so moving scope.state away from "released" here
    # doesn't rewrite history, it only reflects current availability. Reuses the same hold_scope command.
    "released": {"hold"},
    "rejected": set(),
    "hold": set(),
}

DECISION_CODES = ("RELEASED", "REJECTED", "HOLD")


class ReleaseScope(Base):
    __tablename__ = "release_scope"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="draft_evaluation")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    # No FK constraint: avoids a circular dependency with release_evaluation.release_scope_id, which
    # already enforces the real relationship from the other side. A plain pointer/cache column, same
    # latitude as other logical-reference columns elsewhere in this codebase (e.g. recipe_master's
    # qualification_policy_id).
    current_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    released_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    decision_at: Mapped[datetime | None] = mapped_column()


class ReleaseEvaluation(Base):
    __tablename__ = "release_evaluation"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.release_scope.id"), nullable=False)
    scope_version: Mapped[int] = mapped_column(nullable=False)
    rule_set_version: Mapped[str | None] = mapped_column(String(40))
    evaluated_batch_version: Mapped[int] = mapped_column(nullable=False)
    blockers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    eligible: Mapped[bool] = mapped_column(nullable=False)
    evaluation_time: Mapped[datetime] = mapped_column(server_default=func.now())


class ReleaseDecision(Base):
    __tablename__ = "release_decision"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.release_scope.id"), nullable=False)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.release_evaluation.id"), nullable=False)
    decision_code: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(2000))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decision_time: Mapped[datetime] = mapped_column(server_default=func.now())
    release_package_hash: Mapped[str | None] = mapped_column(String(64))
