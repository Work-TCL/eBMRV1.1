"""Document 77 (SPEC-DATA-009) -- Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade
Architecture. New `deployment` PostgreSQL schema. One owned entity per `04_DATA_MODEL_CATALOGUE.md`:
`deployment_profile` (8 fields). **0 owned HTTP APIs** -- CI/installer-populated, same "no independent
API" shape as Document 68's `release_security_evidence`.

**Not the same entity as `security.deployment_security_profile` (Document 66).** That table is the
zero-trust *posture* (ingress/egress policy, container hardening, admin access pattern) for a
deployment profile name; this one is the *infrastructure/topology* record (cloud provider, region,
Kubernetes namespace, currently-applied image digest, IaC state reference, HA profile) for the same
named profile. Two different concerns of the same `deployment_profile` name -- not a dual master of one
entity (AG-05): Document 66 owns the security posture, Document 77 owns the infrastructure topology,
and a future join is by `profile_name`, not a shared table.

No signature (Document 106 has no SPEC-DATA-009 row). No `tenant_id` (ADR-0006); no `site_id`
(a deployment profile is a whole-environment concept, not per-site).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

CLOUD_PROVIDERS = ("AWS", "AZURE", "PRIVATE_CLOUD", "ON_PREM")
ENVIRONMENTS = ("dev", "test", "validation", "staging", "prod")
HA_PROFILES = ("COMPACT", "HA")


class DeploymentProfile(Base):
    __tablename__ = "deployment_profile"
    __table_args__ = (UniqueConstraint("profile_name"), {"schema": "deployment"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_name: Mapped[str] = mapped_column(String(80), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    cloud_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    region: Mapped[str | None] = mapped_column(String(60))
    k8s_namespace: Mapped[str | None] = mapped_column(String(80))
    image_digest: Mapped[str | None] = mapped_column(String(160))
    iac_state_ref: Mapped[str | None] = mapped_column(String(300))
    ha_profile: Mapped[str] = mapped_column(String(20), nullable=False, default="HA")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
