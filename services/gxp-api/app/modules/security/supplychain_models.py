"""Document 68 (SPEC-SEC-008) -- Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release
Security. Same `security` PostgreSQL schema Documents 61-67 created; adds the 3 owned entities the
approved `04_DATA_MODEL_CATALOGUE.md` lists: `software_component_inventory`, `vulnerability_record`,
`release_security_evidence`.

**Signature: `POST /security/v1/vulnerabilities/{id}/exceptions` is Part 11 signed BUT Document 106
row 141's role is unresolvable.** Row 141 says `Approved` by "Elevated authority defined by the record
class" -- which names no actual role and no dispatch table exists to resolve it, exactly the shape of
Document 61's row 133 (tracked under SG-161). Following that established precedent,
`approve_vulnerability_exception()` calls `_resolve_signature()` unconditionally and **fails closed with
SIGNATURE_POLICY_UNRESOLVED** -- no signature policy row is seeded for `vulnerability`/`exception`. See
`docs/generated/18_SPEC_GAPS.md` SG-165. `register` and `assess` have no Document 106 row -> RBAC-gated
only (Security Admin). `GET /security/v1/releases/{id}/security-evidence` is read-only.

**No `site_id`.** Supply-chain artefacts are platform/product-wide, not per-site. `tenant_id` dropped
(ADR-0006). `kev_status` is a real boolean; there are no float columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

VULN_SOURCES = ("INTERNAL_SCAN", "SCA", "CONTAINER_SCAN", "CUSTOMER_REPORT", "RESEARCHER", "VENDOR_ADVISORY")
VULN_STATES = ("OPEN", "ASSESSED", "EXCEPTION_APPROVED", "REMEDIATED", "CLOSED")
SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
GATE_RESULTS = ("PASS", "WARN", "BLOCK", "NOT_EVALUATED")
COMPONENT_SUPPORT = ("SUPPORTED", "MAINTENANCE", "EOL", "ABANDONED", "UNKNOWN")


class SoftwareComponentInventory(Base):
    """Document 68 # 6 `software_component_inventory` -- one third-party component/package/image with
    version/digest/license/source/owner/support-EOL (SDLC-FR-032). `component_version` is the semver
    string; `version` is the optimistic-concurrency counter."""

    __tablename__ = "software_component_inventory"
    __table_args__ = (UniqueConstraint("component_name", "component_version"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_name: Mapped[str] = mapped_column(String(200), nullable=False)
    component_version: Mapped[str] = mapped_column(String(80), nullable=False)
    digest: Mapped[str | None] = mapped_column(String(160))
    license: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)  # registry / repo
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    support_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    eol_date: Mapped[datetime | None] = mapped_column()
    sbom_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class VulnerabilityRecord(Base):
    """Document 68 # 6 `vulnerability_record` -- fields taken from the catalogue's DDL. State:
    OPEN -> ASSESSED -> (EXCEPTION_APPROVED | REMEDIATED) -> CLOSED. `exception` carries the
    time-bounded risk acceptance (SDLC-FR-021); it is only ever written by
    `approve_vulnerability_exception()`, which is signed (Document 106 row 141 -- unresolved, SG-165)."""

    __tablename__ = "vulnerability_record"
    __table_args__ = (UniqueConstraint("vulnerability_id", "source"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vulnerability_id: Mapped[str] = mapped_column(String(80), nullable=False)  # CVE / GHSA / internal id
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    component: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {name, version, digest}
    affected_releases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    severity: Mapped[str | None] = mapped_column(String(20))
    kev_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gxp_impact: Mapped[dict | None] = mapped_column(JSONB)
    assessment: Mapped[dict | None] = mapped_column(JSONB)
    exception: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    remediation_due: Mapped[datetime | None] = mapped_column()
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ReleaseSecurityEvidence(Base):
    """Document 68 # 6 `release_security_evidence` -- the per-release provenance bundle (SDLC-FR-013):
    commit, build provenance, SBOM, scan reports, pen/security test refs, accepted exceptions, gate
    result, artifact digest + signature. Populated by the CI pipeline functions (generateReleaseSBOM,
    scanReleaseArtifact, evaluateSecurityReleaseGate, signReleaseArtifact -- `supplychain.py`); read via
    `GET /security/v1/releases/{id}/security-evidence`."""

    __tablename__ = "release_security_evidence"
    __table_args__ = (UniqueConstraint("release_id"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id: Mapped[str] = mapped_column(String(120), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    build_provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    sbom_ref: Mapped[str | None] = mapped_column(String(300))
    scan_reports: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    pentest_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    security_test_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    accepted_exceptions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    gate_result: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_EVALUATED")
    artifact_digest: Mapped[str | None] = mapped_column(String(160))
    signature_ref: Mapped[str | None] = mapped_column(String(300))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
