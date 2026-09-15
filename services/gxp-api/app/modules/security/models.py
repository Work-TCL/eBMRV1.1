"""Document 61 (SPEC-SEC-001) — Security Architecture, Threat Model & Control Framework. New module,
new `security` schema. 4 owned entities exactly per `04_DATA_MODEL_CATALOGUE.md`:
`security_threat_model_version`, `security_threat`, `security_control`, `security_exception`.

**No `site_id`.** Document 61 never lists a site field on any of its 4 tables (unlike every WP-02..09
module), and its own actors (Security Architect, Security Engineer, System Architect, ...) and lifecycle
(architecture baseline -> threat model -> control matrix) operate at the platform/deployment level, not a
manufacturing site -- `deployment_profile` (SEC-THR-025: cloud/private cloud/on-prem) is the module's own
scoping concept, not site_id. Same precedent as `app/modules/rules/models.py` (platform-wide rule
definitions, no site_id column). `tenant_id` is dropped throughout per ADR-0006, same as every module
since WP-05.

**Only 4 owned entities for 8 functions** (same shape as postmarket's Vault-backed metrics -- see
`app/modules/postmarket/models.py` module docstring): Document 61's contract catalogue (`# 4`) names 8
functions but its data model (`# 6`) owns exactly 4 tables. The other 4 functions' outputs are modelled as
fields/append-only JSONB history on the 4 owned tables rather than invented tables:

- `mapSecurityControl()` -> `ThreatControlMapping` has no table of its own; `security_control` is the
  *control catalogue* (control code/objective/owner/evidence source/test owner/framework mappings -- Doc 61
  `# 6` lists exactly those 6 fields, a master-data shape, not a per-threat mapping row). The mapping
  itself is appended to `security_threat.control_mappings` (JSONB list), and `mapSecurityControl()` does
  get-or-create against `security_control` by `control_code` (no `createSecurityControl()` function exists
  anywhere in Document 61's 8-function catalogue, yet the catalogue table needs entries from somewhere) --
  an ordinary engineering decision to satisfy SEC-THR-013 ("each identified threat maps ... controls"),
  not a guess about regulated behaviour.
- `calculateSecurityRisk()` -> `SecurityRiskAssessment` has no table; `security_threat` already lists
  "inherent/residual risk" as an owned field (Doc 61 `# 6`), so the calculation writes directly onto
  `security_threat.inherent_risk` / `.residual_risk`, appending the prior value onto
  `risk_calculation_history` first (never overwritten silently -- same discipline as
  `qms.RiskAssessmentVersion.residual_score`, Document 33 RSK-FR-012). The risk *rating itself* is
  caller-supplied (`impact_inputs`/`likelihood_inputs`/`methodology` plus an asserted rating) rather than
  computed from a hidden formula -- no baseline anywhere in this codebase defines a risk-scoring matrix
  (checked `app/modules/qms/risk_commands.py`: `CreateRiskCommand.score` is caller-supplied there too, the
  same established precedent, not a fresh gap).
- `acceptResidualSecurityRisk()` -> `SecurityRiskAcceptance` has no table; recorded as
  `security_threat.residual_risk_acceptance` (JSONB) plus `state -> RISK_ACCEPTED`. No Document 106 row
  exists for `POST /security/v1/risks/{id}/accept` at all (checked the full register, rows 133-141) even
  though Document 61's own function-contract table flags "signatures" as an input and a
  "SIGNATURE POLICY LOOKUP REQUIRED" note -- `accept_residual_security_risk()` calls `_resolve_signature()`
  unconditionally and is deliberately left unresolved (fails closed with `SIGNATURE_POLICY_UNRESOLVED`),
  same "record the deliberate resolution, don't guess a role" discipline as SG-157/SG-160. See
  `docs/generated/18_SPEC_GAPS.md` SG-161.
- `triggerThreatModelReview()` -> `ThreatReviewTask` has no table; appended to
  `security_threat_model_version.review_triggers` (JSONB list) -- SEC-THR-002/024.
- `generateSecurityControlMatrix()` -> `SecurityControlMatrix` is a read-only join over `security_threat`
  (+ its `control_mappings`) and the `security_control` catalogue, scoped by threat_model_version_id and
  deployment_profile -- no write, no owned table, same shape as postmarket's
  `get_postmarket_dashboard()`.

**`security_exception`'s Document 106 row 133 (`POST /security/v1/exceptions` -> `Approved`, "Elevated
authority defined by the record class", 1, "MUST be independent of the requester", required=yes) is
RESOLVED_APPROVED 2026-09-14 (project-owner-directed).** "Elevated authority" resolves to the "Security
Risk Approver" role (already seeded anticipating exactly this gap); independence has no meaning in a
single-step create+sign command, so the endpoint was split into an unsigned `requestSecurityException()`
(records the requester) and a signed `approveSecurityException()` (independence-checked against that
requester) -- see `commands.py`'s module docstring. Row 141 (vulnerability exceptions, Document 68) is
the same "elevated authority" shape but remains its own, separately-tracked unresolved gap (SG-165, out
of scope this pass). See SG-161.

**Threat state model** (Doc 61 `# 5` gives a *pipeline*-level diagram -- THREAT_MODEL_DRAFT -> THREATS +
CONTROLS + TESTS -> RISK_REVIEW -> MITIGATE/ACCEPT/EXCEPTION -> APPROVED SECURITY BASELINE -- not a
per-threat enum). Modelled here as `security_threat.state`: `OPEN` (registered, may accumulate control
mappings and risk calculations) -> `RISK_ACCEPTED` (after `acceptResidualSecurityRisk()`, when that
endpoint is eventually resolved). `security_threat_model_version.state` stays `DRAFT` throughout this pass
-- no function in Document 61's 8-function catalogue transitions a version to "APPROVED SECURITY BASELINE"
(same "no reachable further state without a corresponding operation" shape as postmarket's
`CLOSED_FOR_SURVEILLANCE`, noted there rather than guessed into existence).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# SEC-THR-025: cloud / private cloud / on-prem deployment profiles receive profile-specific baselines.
DEPLOYMENT_PROFILES = ("CLOUD", "PRIVATE_CLOUD", "ON_PREM")

# SEC-THR-003: STRIDE (or equivalent controlled methodology) categories; OTHER covers abuse cases that do
# not map cleanly onto classic STRIDE (e.g. supply-chain compromise, insider misuse -- SEC-THR-006).
THREAT_TYPES = (
    "SPOOFING", "TAMPERING", "REPUDIATION", "INFORMATION_DISCLOSURE",
    "DENIAL_OF_SERVICE", "ELEVATION_OF_PRIVILEGE", "OTHER",
)

THREAT_MODEL_VERSION_STATES = ("DRAFT",)
THREAT_STATES = ("OPEN", "RISK_ACCEPTED")
SECURITY_EXCEPTION_STATES = ("OPEN",)


class SecurityThreatModelVersion(Base):
    """`createThreatModelVersion()` -- SEC-THR-001/002/003/004/005/019/025."""

    __tablename__ = "security_threat_model_version"
    __table_args__ = {"schema": "security"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_version: Mapped[str] = mapped_column(String(60), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(60), nullable=False)
    deployment_profile: Mapped[str] = mapped_column(String(30), nullable=False)
    # SEC-THR-001/004/005/019: architecture register -- assets, trust boundaries, attack-surface scope.
    scope: Mapped[dict | None] = mapped_column(JSONB)
    assets: Mapped[dict | None] = mapped_column(JSONB)
    boundaries: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    # SEC-THR-002/024: triggerThreatModelReview() appends here -- no dedicated table (see module docstring).
    review_triggers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Doc 61 `# 6` data-model field; no vault-release function is defined in this module's 8-function
    # catalogue, so this stays unpopulated (nullable) this pass -- not guessed into a fabricated release.
    vault_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SecurityThreat(Base):
    """`registerThreat()` -- SEC-THR-003/004/005/006/007/008/009/010/011/012. Also carries the
    `mapSecurityControl()`, `calculateSecurityRisk()` and `acceptResidualSecurityRisk()` outputs (see
    module docstring for why those three have no table of their own)."""

    __tablename__ = "security_threat"
    __table_args__ = (
        Index("ix_security_threat_model_version", "threat_model_version_id"),
        {"schema": "security"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    threat_model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security.security_threat_model_version.id"), nullable=False
    )
    asset_or_boundary: Mapped[str] = mapped_column(String(200), nullable=False)
    threat_type: Mapped[str] = mapped_column(String(40), nullable=False)
    abuse_case: Mapped[str] = mapped_column(Text, nullable=False)
    attack_preconditions: Mapped[dict | None] = mapped_column(JSONB)
    # SEC-THR-007/008/009/010/011/012: which CIA/GxP-integrity/availability/privacy/OT/integration/tenant
    # attributes this threat impacts, e.g. ["CONFIDENTIALITY", "GXP_INTEGRITY"].
    impacted_attributes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    # SEC-THR-013: append-only preventive/detective/recovery control mappings (see module docstring).
    control_mappings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # SEC-THR-014: current inherent/residual rating plus history (never silently overwritten).
    inherent_risk: Mapped[dict | None] = mapped_column(JSONB)
    residual_risk: Mapped[dict | None] = mapped_column(JSONB)
    risk_calculation_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # SEC-THR-015: set by acceptResidualSecurityRisk() once Document 106 resolves its signature point.
    residual_risk_acceptance: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SecurityControl(Base):
    """Control catalogue -- Doc 61 `# 6` `security_control` (control code / objective / implementation
    owner / evidence source / test owner / framework mappings). Populated by `mapSecurityControl()`'s
    get-or-create (see module docstring) since no `createSecurityControl()` function exists."""

    __tablename__ = "security_control"
    __table_args__ = (UniqueConstraint("control_code"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_code: Mapped[str] = mapped_column(String(100), nullable=False)
    objective: Mapped[str | None] = mapped_column(Text)
    implementation_owner: Mapped[str | None] = mapped_column(String(200))
    evidence_source: Mapped[str | None] = mapped_column(String(200))
    test_owner: Mapped[str | None] = mapped_column(String(200))
    # SEC-THR-028: NIST/OWASP/etc framework mappings supplement, never replace, the system-specific
    # threat model itself.
    framework_mappings: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SecurityException(Base):
    """`requestSecurityException()` / `approveSecurityException()` -- SEC-THR-023.

    SG-161 RESOLVED_APPROVED 2026-09-14: split into an unsigned request (`state=PENDING_APPROVAL`,
    `opened_by` records the requester) and a signed approval by the "Security Risk Approver" role,
    independent of `opened_by`, that moves the record to `state=OPEN`. `signature_id` and `approvers`
    are populated only at approval, never at request.
    """

    __tablename__ = "security_exception"
    __table_args__ = (
        Index("ix_security_exception_state", "state", "expiry"),
        {"schema": "security"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_or_requirement: Mapped[str] = mapped_column(String(200), nullable=False)
    # "risk assessment exists" precondition (Doc 61 `# 4`) -- reference/snapshot of the threat this
    # exception compensates for; nullable because a policy-level exception may not trace to one threat.
    risk_assessment_ref: Mapped[dict | None] = mapped_column(JSONB)
    compensating_controls: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(server_default=func.now())
    expiry: Mapped[datetime] = mapped_column(nullable=False)
    # SEC-THR-023: approvers + remediation target.
    approvers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    remediation_target: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING_APPROVAL")
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    opened_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
