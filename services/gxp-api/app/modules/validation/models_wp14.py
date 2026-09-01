"""WP-14 (Documents 85, 87, 95 / SPEC-VAL-007, SPEC-VAL-009, SPEC-VAL-017) -- Customer Deployment /
PQ / Go-Live. Seven tables *added to the existing `validation` PostgreSQL schema* that WP-12 created
(migration 0079). These are the entities `04_DATA_MODEL_CATALOGUE.md` declares for Documents 85/87/95,
which WP-12 deliberately excluded (`app/modules/validation/__init__.py`):

  Document 85 -- `pq_scenario`, `pq_execution`
  Document 87 -- `migration_validation_plan`, `migration_run`, `migration_reconciliation`
  Document 95 -- `validation_summary_report`, `validated_release_authorization`

Same conventions as `models.py`: **no `tenant_id`** (ADR-0006, single-organization platform);
`site_id` nullable (a customer deployment's PQ / migration / release authorization is naturally
site-scoped, but the platform-level VSR is not). Every table carries `id, state, version, created_at,
updated_at`. `version` is the Doc 70 / MUT-FR-009 optimistic-concurrency bigint. Counts/sizes are
`BigInteger`; there are no `float` columns (rates/percentages, where they occur, are integer basis
points inside JSONB). Retention/legal-hold periods are **not** given a numeric value here -- Document
108 supplies retention *classes*, not this table's default period, and no approved baseline gives
WP-14 evidence a concrete number of years (SG-005, already open); `retention_class` is a free-text
label column, same posture as every WP-12 table.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base
from app.modules.validation.models import SCHEMA


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# =====================================================================================================
# Document 85 (SPEC-VAL-007) -- Performance Qualification (PQ), UAT & Business Process Verification
# =====================================================================================================

PQ_SCENARIO_STATES = (
    "DRAFT", "PARTICIPANTS_ASSIGNED", "IN_EXECUTION", "READY_FOR_ACCEPTANCE", "ACCEPTED", "REJECTED",
)
PQ_EXECUTION_STATES = ("IN_PROGRESS", "COMPLETED", "FAILED", "INTERRUPTED")


class PqScenario(Base):
    """PQ-FR-001..006/014/016/017/020: one customer/site/process-specific end-to-end qualification
    scenario. `product_profile` is nullable -- PFS/injector/inhalation/coated content is included
    "only when applicable" (PQ-FR-006). `is_uat`/`vmp_equivalence_ref` cover PQ-FR-017 (a controlled
    customer UAT may stand in for PQ evidence *if* the VMP criteria are recorded). `is_template` marks
    a reusable vendor scenario (PQ-FR-020) -- a template is never itself a customer acceptance record.
    `participants` is populated by `assign_pq_participants()` (each entry carries the training refs and
    a `trained` flag, PQ-FR-005). History is superseding: a rejected scenario is not edited, a new
    DRAFT supersedes it.
    """

    __tablename__ = "pq_scenario"
    __table_args__ = (UniqueConstraint("scenario_number", "version"), {"schema": SCHEMA})

    id: Mapped[uuid.UUID] = _pk()
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    scenario_number: Mapped[str] = mapped_column(String(60), nullable=False)
    product_profile: Mapped[str | None] = mapped_column(String(40))
    process_area: Mapped[str] = mapped_column(String(40), nullable=False)
    intended_workflow: Mapped[str] = mapped_column(Text, nullable=False)
    representative_roles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    training_prerequisites: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    prerequisites: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    interfaces_equipment: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    exception_paths: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    is_uat: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vmp_equivalence_ref: Mapped[str | None] = mapped_column(String(200))
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    participants: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    authored_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    retention_class: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class PqExecution(Base):
    """PQ-FR-003/007..013/015/016/018: one run of a scenario by representative trained users.
    `prior_execution_id` links a re-run to the execution it supersedes (Document 85 §11 -- a failed or
    interrupted execution stays recorded, a re-run is a *new* row). `observations` is the PQ-FR-015
    usability-observation list (each may be flagged a change candidate). `go_live_blocker` is computed
    at completion time (PQ-FR-018): true when any deviation is `critical` and unresolved, or any
    participant identity is not among the scenario's trained participants. `evidence_manifest` entries
    that name a real Evidence Store object are checked FINALIZED/ARCHIVED before a COMPLETED result is
    allowed (AG-12 / Document 85 §11 "evidence-upload or DB failure must not produce PASS").
    """

    __tablename__ = "pq_execution"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.pq_scenario.id"), nullable=False
    )
    scenario_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    prior_execution_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    participant_identities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    environment: Mapped[str] = mapped_column(String(120), nullable=False)
    config_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_ref: Mapped[str | None] = mapped_column(String(200))
    step_results: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    observations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    deviations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_manifest: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    go_live_blocker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 87 (SPEC-VAL-009) -- Data Migration, Conversion, Cutover & Reconciliation Validation
# =====================================================================================================

MIGRATION_PLAN_STATES = ("DRAFT", "PROFILED", "ACCEPTED", "ROLLED_BACK")
MIGRATION_RUN_TYPES = ("DRY_RUN", "CUTOVER")
MIGRATION_RUN_STATES = ("RUNNING", "COMPLETED", "FAILED", "INTERRUPTED", "ACCEPTED")
RECONCILIATION_OUTCOMES = ("PASS", "FAIL")


class MigrationValidationPlan(Base):
    """MIGV-FR-001..006/013/014/015/019/021: the controlled migration plan -- source/target, scope,
    freeze cutoff, the exact frozen source export ref + hash (MIGV-FR-002), versioned+approved
    source->target mappings (MIGV-FR-004), transform script version (MIGV-FR-005) and the
    `reconciliation_rules` the runs are judged against. **`reconciliation_rules` is customer-authored
    per-plan data, not a platform constant** -- no approved baseline gives a numeric reconciliation
    tolerance, so the platform ships none and `reconcile_migration_run()` fails closed when a rule for
    a compared data class is absent (SG-171). `source_profile` is filled in by
    `profile_migration_source()` (MIGV-FR-003).
    """

    __tablename__ = "migration_validation_plan"
    __table_args__ = (UniqueConstraint("plan_number", "version"), {"schema": SCHEMA})

    id: Mapped[uuid.UUID] = _pk()
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    plan_number: Mapped[str] = mapped_column(String(60), nullable=False)
    source_system: Mapped[str] = mapped_column(String(120), nullable=False)
    target_system: Mapped[str] = mapped_column(String(120), nullable=False, default="eBMR/eDHR platform")
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    cutoff_at: Mapped[datetime] = mapped_column(nullable=False)
    source_snapshot_ref: Mapped[str] = mapped_column(String(300), nullable=False)
    source_snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    source_timezone: Mapped[str | None] = mapped_column(String(60))
    mappings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    mapping_version: Mapped[str] = mapped_column(String(40), nullable=False)
    transform_version: Mapped[str] = mapped_column(String(40), nullable=False)
    reconciliation_rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    source_profile: Mapped[dict | None] = mapped_column(JSONB)
    authored_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    regulated_history_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    legacy_access_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    retention_class: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class MigrationRun(Base):
    """MIGV-FR-007..013/016..018: one rehearsal (`DRY_RUN`) or the production `CUTOVER` run.
    `identity_map` retains legacy_id -> new_id (MIGV-FR-007). `rejected_records` retains every
    conversion failure with a reason and disposition (MIGV-FR-018 -- never silently dropped).
    `legacy_signatures.mode` is always `PROVENANCE_MARKED` -- legacy signature evidence is preserved
    as provenance, never recreated as a new platform signing (MIGV-FR-012 / Document 87 §13).
    `is_delta` marks the final cutover delta run (MIGV-FR-017). `prior_run_id` links a re-run
    (Document 87 §11).
    """

    __tablename__ = "migration_run"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.migration_validation_plan.id"), nullable=False
    )
    plan_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    run_type: Mapped[str] = mapped_column(String(20), nullable=False)
    run_number: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    prior_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_delta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sandbox: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scripts_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    control_totals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    identity_map: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rejected_records: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    attachments: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    legacy_signatures: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    legacy_audit: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    target_refs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    retention_class: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class MigrationReconciliation(Base):
    """MIGV-FR-008..011/020: the reconciliation of one run against the plan's `reconciliation_rules`.
    `critical_field_comparison.method` is `FULL_AUTOMATED` where feasible, otherwise `SAMPLING` with a
    recorded `sample_size` (MIGV-FR-010 -- migration is never validated by count alone, Document 87
    §13). `outcome` is `PASS` only when every compared class is within its rule's tolerance AND every
    deviation carries a disposition (MIGV-FR-020).
    """

    __tablename__ = "migration_reconciliation"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.migration_run.id"), nullable=False
    )
    run_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reconciliation_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    count_comparison: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    hash_comparison: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    control_total_comparison: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    critical_field_comparison: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    attachment_comparison: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reference_integrity: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    deviations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    outcome: Mapped[str] = mapped_column(String(10), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="COMPLETED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 95 (SPEC-VAL-017) -- Validation Summary Report, Release-to-Production & Go-Live Authorization
# =====================================================================================================

VSR_STATES = ("DRAFT", "APPROVED", "REJECTED")
VSR_RECOMMENDATIONS = ("RECOMMENDED", "RECOMMENDED_WITH_CONDITIONS", "NOT_RECOMMENDED")
VSR_DECISIONS = ("APPROVED", "CONDITIONAL", "REJECTED")
RELEASE_AUTH_STATES = (
    "AUTHORIZED", "DEPLOYMENT_VERIFIED", "GO_LIVE_VERIFIED", "ROLLED_BACK", "REJECTED",
)


class ValidationSummaryReport(Base):
    """VSR-FR-001..014/018..021: the final validation summary, aggregated from authoritative
    validation artifacts. `recommendation` is the *validation* recommendation (VSR-FR-014) and is
    recorded at generation by the validation service; it is deliberately separate from `decision`
    (APPROVED/CONDITIONAL/REJECTED) which a QA / System Owner records at `approve` under an
    independent `Approved` signature (Document 106 row 169, signer independent of the author).
    `known_limitations` is never optional (Document 95 §13). `decision_conditions` cannot bypass a
    critical GxP control -- `approve_validation_summary()` rejects a CONDITIONAL decision whose
    conditions name a critical control (VSR-FR-019).
    """

    __tablename__ = "validation_summary_report"
    __table_args__ = (UniqueConstraint("report_number", "version"), {"schema": SCHEMA})

    id: Mapped[uuid.UUID] = _pk()
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    report_number: Mapped[str] = mapped_column(String(60), nullable=False)
    release_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    customer: Mapped[str | None] = mapped_column(String(200))
    environment: Mapped[str] = mapped_column(String(120), nullable=False)
    intended_use: Mapped[str] = mapped_column(Text, nullable=False)
    config_scope: Mapped[str] = mapped_column(Text, nullable=False)
    baselines: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    execution_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    traceability_status: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    deviations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    security_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    performance_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    dr_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    migration_summary: Mapped[dict | None] = mapped_column(JSONB)
    part11_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    customer_responsibilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    known_limitations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recommendation: Mapped[str] = mapped_column(String(40), nullable=False)
    recommendation_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    recommendation_at: Mapped[datetime | None] = mapped_column()
    evidence_manifest_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    decision: Mapped[str | None] = mapped_column(String(20))
    decision_conditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    vault_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    retention_class: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ValidatedReleaseAuthorization(Base):
    """VSR-FR-015..024: binds an approved VSR to the *exact* software/configuration/environment
    promoted into regulated production. `release_identity` carries image/code/SBOM/schema/migration/
    config versions (VSR-FR-017); `config_fingerprint` is the approved production configuration hash
    (VSR-FR-016). `go_live_readiness` is the snapshot evaluated at authorization time (VSR-FR-015).
    `deployment_check` records `verify_deployment_against_validation_release()` -- a signed comparison
    of what is actually being deployed against `release_identity`/`config_fingerprint` (VSR-FR-022,
    Document 106 row 167). `post_go_live` records the smoke/monitoring verification and, on failure,
    the rollback/incident/change references (VSR-FR-023/024).
    """

    __tablename__ = "validated_release_authorization"
    __table_args__ = (UniqueConstraint("authorization_number", "version"), {"schema": SCHEMA})

    id: Mapped[uuid.UUID] = _pk()
    vsr_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.validation_summary_report.id"), nullable=False
    )
    vsr_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    authorization_number: Mapped[str] = mapped_column(String(60), nullable=False)
    release_identity: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    artifact_digests: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    config_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    environment: Mapped[str] = mapped_column(String(120), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    go_live_readiness: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    conditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    authorized_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    authorized_at: Mapped[datetime | None] = mapped_column()
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    deployment_check: Mapped[dict | None] = mapped_column(JSONB)
    post_go_live: Mapped[dict | None] = mapped_column(JSONB)
    retention_class: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="AUTHORIZED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
