"""Document 66 (SPEC-SEC-006) -- Network, Tenant, Deployment Isolation & Zero-Trust Architecture. Same
`security` PostgreSQL schema Documents 61-65 created; adds the 2 owned entities the approved
`04_DATA_MODEL_CATALOGUE.md` lists: `network_flow_definition`, `deployment_security_profile`.

**Read-only catalogue module.** Document 66 # 7 lists exactly two HTTP endpoints, both `GET`
(`/security/v1/network-flows`, `/security/v1/deployment-security-profile`), plus "infrastructure-as-code
generated policies" which are not an HTTP API. There is **no state-changing endpoint and no Mutation
Gateway command** -- the flow catalogue and deployment profile are approved-baseline configuration data,
seeded (`scripts/seed.py`) and superseded, never edited through a generic CRUD API (AG-06 /
Document 113 §6). The 6 functions Document 66 # 4 names (`generateNetworkPolicySet`,
`validateServiceFlow`, `issueSiteScopedEdgeNetworkProfile`, `verifyTenantScopePropagation`,
`testForbiddenNetworkPath`, `validateDeploymentHardening`) are a pure library in
`app/modules/security/netzero.py` -- CI/deploy-admission/security-test tooling, not request handlers.

**No signature** -- Document 106 has zero rows for any SPEC-SEC-006 action (checked rows 133-141).

**No `site_id`.** Site scoping in this module is a *value* on a flow/profile row
(`deployment_profile`, and `issueSiteScopedEdgeNetworkProfile()` takes a `site_id` argument), not a
column -- same platform-level treatment as every other `security.*` table. `tenant_id` dropped
(ADR-0006). Ports are integers.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

ZONES = (
    "INGRESS", "APP", "FRAPPE", "GXP_SERVICE", "DB", "INTEGRATION",
    "OBSERVABILITY", "ADMIN", "EDGE_OT", "BACKUP",
)
FLOW_STATES = ("EFFECTIVE", "SUPERSEDED")
PROFILE_STATES = ("EFFECTIVE", "SUPERSEDED")
AUTH_MECHANISMS = ("MTLS", "BEARER_JWT", "SERVICE_BEARER", "NETWORK_POLICY_ONLY", "NONE")


class NetworkFlowDefinition(Base):
    """Document 66 # 6 `network_flow_definition` -- one approved source->destination flow for a
    deployment profile. `validateServiceFlow()` compares an intended connection against the EFFECTIVE
    rows here; anything not matched is `NETWORK_FLOW_NOT_ALLOWED` (default deny, NET-FR-002)."""

    __tablename__ = "network_flow_definition"
    __table_args__ = (
        UniqueConstraint("deployment_profile", "source_zone", "source_service", "destination_zone",
                         "destination_service", "protocol", "port", "version",
                         name="uq_network_flow_definition_identity"),
        Index("ix_network_flow_definition_lookup", "deployment_profile", "source_zone", "destination_zone", "state"),
        {"schema": "security"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_profile: Mapped[str] = mapped_column(String(40), nullable=False)  # CLOUD / PRIVATE_CLOUD / ON_PREM
    source_zone: Mapped[str] = mapped_column(String(30), nullable=False)
    source_service: Mapped[str] = mapped_column(String(80), nullable=False, default="*")
    destination_zone: Mapped[str] = mapped_column(String(30), nullable=False)
    destination_service: Mapped[str] = mapped_column(String(80), nullable=False, default="*")
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)  # TCP / UDP
    port: Mapped[int] = mapped_column(BigInteger, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    auth_mechanism: Mapped[str] = mapped_column(String(30), nullable=False, default="MTLS")
    effective_from: Mapped[datetime] = mapped_column(server_default=func.now())
    effective_to: Mapped[datetime | None] = mapped_column()
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DeploymentSecurityProfile(Base):
    """Document 66 # 6 `deployment_security_profile` -- the per-deployment zero-trust posture record
    (ingress/egress policy, private endpoints, K8s namespaces/service accounts, container hardening
    baseline, admin access pattern, backup/network isolation). `validateDeploymentHardening()` checks a
    workload manifest against `container_hardening`."""

    __tablename__ = "deployment_security_profile"
    __table_args__ = (UniqueConstraint("profile_name"), {"schema": "security"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_name: Mapped[str] = mapped_column(String(60), nullable=False)
    deployment_profile: Mapped[str] = mapped_column(String(40), nullable=False)
    ingress_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    egress_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    private_endpoints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    namespaces: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    service_accounts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # NET-FR-017: {run_as_non_root: true, read_only_root_fs: true, drop_capabilities: ["ALL"],
    #              allow_privilege_escalation: false, host_network: false, host_path_mounts: false}
    container_hardening: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    admin_access_pattern: Mapped[str] = mapped_column(String(40), nullable=False, default="ZTNA")
    backup_isolation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    network_isolation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
