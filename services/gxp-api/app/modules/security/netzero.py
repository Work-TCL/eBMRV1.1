"""Document 66 (SPEC-SEC-006) -- the 6 network / zero-trust library functions Document 66 # 4 names.
CI / deploy-admission / security-test tooling, not request handlers. Pure functions over the
`network_flow_definition` catalogue and `deployment_security_profile` rows; no state-changing writes.

`emit_security_event()` (thin outbox wrapper) is provided for the 4 telemetry events Document 66 # 9
declares (`ForbiddenNetworkPathDetected`, `TenantScopeMismatchDetected`, `WorkloadHardeningFailed`,
`UnexpectedPublicExposureDetected`); callers with a live session use it, the CI-only call sites log.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.security.netzero_models import DeploymentSecurityProfile, NetworkFlowDefinition
from app.mutation.errors import (
    NetworkFlowNotAllowedError,
    SegmentationControlFailedError,
    TenantScopeMismatchError,
    WorkloadHardeningFailedError,
)

# NET-FR-003: these must never appear as a *destination* of a flow whose source is a public/ingress
# zone, and never be publicly exposed.
_NEVER_PUBLIC_ZONES = {"DB", "GXP_SERVICE", "BACKUP"}


# --------------------------------------------------------------------------------------------------
# generateNetworkPolicySet() -- NET-FR-001/002/016
# --------------------------------------------------------------------------------------------------


async def generate_network_policy_set(session: AsyncSession, *, deployment_profile: str) -> dict:
    """Compile the EFFECTIVE flow catalogue for a deployment profile into a default-deny policy bundle
    (one allow rule per approved flow, an explicit deny-all baseline). No DB writes -- the output is a
    manifest the IaC layer renders."""
    flows = (
        await session.execute(
            select(NetworkFlowDefinition).where(
                NetworkFlowDefinition.deployment_profile == deployment_profile,
                NetworkFlowDefinition.state == "EFFECTIVE",
            )
        )
    ).scalars().all()
    allow_rules = [
        {
            "from": {"zone": f.source_zone, "service": f.source_service},
            "to": {"zone": f.destination_zone, "service": f.destination_service},
            "protocol": f.protocol, "port": f.port, "auth": f.auth_mechanism, "purpose": f.purpose,
        }
        for f in flows
    ]
    return {
        "deployment_profile": deployment_profile,
        "default_action": "DENY",
        "allow_rule_count": len(allow_rules),
        "allow_rules": allow_rules,
    }


# --------------------------------------------------------------------------------------------------
# validateServiceFlow() -- NET-FR-002/004/006
# --------------------------------------------------------------------------------------------------


async def validate_service_flow(
    session: AsyncSession, *, deployment_profile: str, source_zone: str, source_service: str,
    destination_zone: str, destination_service: str, protocol: str, port: int,
) -> dict:
    """Compare an intended connection against the approved flow catalogue. Deny by default: no
    matching EFFECTIVE row -> `NetworkFlowNotAllowedError` (NETWORK_FLOW_NOT_ALLOWED). A `*` service on
    a catalogue row matches any service name."""
    rows = (
        await session.execute(
            select(NetworkFlowDefinition).where(
                NetworkFlowDefinition.deployment_profile == deployment_profile,
                NetworkFlowDefinition.state == "EFFECTIVE",
                NetworkFlowDefinition.source_zone == source_zone,
                NetworkFlowDefinition.destination_zone == destination_zone,
                NetworkFlowDefinition.protocol == protocol,
                NetworkFlowDefinition.port == port,
            )
        )
    ).scalars().all()
    for r in rows:
        if r.source_service in ("*", source_service) and r.destination_service in ("*", destination_service):
            return {"allow": True, "flow_id": str(r.id), "auth_mechanism": r.auth_mechanism}
    raise NetworkFlowNotAllowedError(
        "No approved network flow matches this connection",
        source=f"{source_zone}/{source_service}", destination=f"{destination_zone}/{destination_service}",
        protocol=protocol, port=port,
    )


# --------------------------------------------------------------------------------------------------
# issueSiteScopedEdgeNetworkProfile() -- NET-FR-007/008/011
# --------------------------------------------------------------------------------------------------


async def issue_site_scoped_edge_network_profile(
    session: AsyncSession, *, site_id: uuid.UUID | str, gateway_id: uuid.UUID | str,
    deployment_profile: str,
) -> dict:
    """Derive the minimum outbound endpoint/port profile an Edge gateway at one site needs -- exactly
    the EFFECTIVE flows whose source is EDGE_OT. Never grants an Edge gateway a DB destination
    (NET-FR-007 / Document 66 # 14)."""
    flows = (
        await session.execute(
            select(NetworkFlowDefinition).where(
                NetworkFlowDefinition.deployment_profile == deployment_profile,
                NetworkFlowDefinition.state == "EFFECTIVE",
                NetworkFlowDefinition.source_zone == "EDGE_OT",
            )
        )
    ).scalars().all()
    outbound = []
    for f in flows:
        if f.destination_zone == "DB":  # structural guard -- an Edge gateway is never given a DB path
            continue
        outbound.append({"to_zone": f.destination_zone, "to_service": f.destination_service,
                         "protocol": f.protocol, "port": f.port, "auth": f.auth_mechanism})
    return {
        "site_id": str(site_id), "gateway_id": str(gateway_id), "deployment_profile": deployment_profile,
        "direction": "OUTBOUND_ONLY", "allowed_endpoints": outbound,
    }


# --------------------------------------------------------------------------------------------------
# verifyTenantScopePropagation() -- NET-FR-010/011
# --------------------------------------------------------------------------------------------------


def verify_tenant_scope_propagation(*, auth_context: dict, downstream: dict) -> dict:
    """Assert a downstream job/event/context carries a tenant/site scope compatible with the
    originating AuthContext. Raises `TenantScopeMismatchError` (TENANT_SCOPE_MISMATCH). A downstream
    with no scope at all is a mismatch (fail closed), unless the caller marked it enterprise-scoped."""
    a_tenant, a_site = auth_context.get("tenant_id"), auth_context.get("site_id")
    d_tenant, d_site = downstream.get("tenant_id"), downstream.get("site_id")
    enterprise = bool(downstream.get("enterprise_scope"))

    if a_tenant is not None and d_tenant is not None and str(a_tenant) != str(d_tenant):
        raise TenantScopeMismatchError("Downstream tenant scope differs from the originating context")
    if not enterprise and a_site is not None and d_site is not None and str(a_site) != str(d_site):
        raise TenantScopeMismatchError("Downstream site scope differs and the job is not enterprise-scoped")
    if a_tenant is not None and d_tenant is None and not enterprise:
        raise TenantScopeMismatchError("Downstream context dropped the tenant scope")
    return {"compatible": True, "enterprise_scope": enterprise}


# --------------------------------------------------------------------------------------------------
# testForbiddenNetworkPath() -- NET-FR-029
# --------------------------------------------------------------------------------------------------


async def test_forbidden_network_path(
    session: AsyncSession, *, deployment_profile: str, source_zone: str, source_service: str,
    destination_zone: str, destination_service: str, protocol: str, port: int, reachable: bool,
) -> dict:
    """A path that is NOT in the approved catalogue must be unreachable. `reachable` is the observed
    result of a simulation/probe. If a non-approved path is reachable -> `SegmentationControlFailedError`
    (SEGMENTATION_CONTROL_FAILED). If an approved path is unreachable that is a connectivity finding,
    not a control failure -- returned, not raised."""
    approved = True
    try:
        await validate_service_flow(
            session, deployment_profile=deployment_profile, source_zone=source_zone,
            source_service=source_service, destination_zone=destination_zone,
            destination_service=destination_service, protocol=protocol, port=port,
        )
    except NetworkFlowNotAllowedError:
        approved = False

    if not approved and reachable:
        from app.modules.security.telemetry import record_security_event
        await record_security_event("ForbiddenNetworkPathDetected", {
            "source": f"{source_zone}/{source_service}", "destination": f"{destination_zone}/{destination_service}",
            "protocol": protocol, "port": port, "reachable": True,
        })
        raise SegmentationControlFailedError(
            "A network path that must be blocked was reachable",
            source=f"{source_zone}/{source_service}", destination=f"{destination_zone}/{destination_service}",
        )
    if not approved and not reachable:
        result = "BLOCKED_OK"       # a forbidden path is correctly unreachable -- the happy path
    elif approved and reachable:
        result = "PASS"             # an approved path is reachable
    else:                          # approved and not reachable
        result = "APPROVED_UNREACHABLE"   # a connectivity finding, not a segmentation-control failure
    return {"approved": approved, "reachable": reachable, "result": result}


# --------------------------------------------------------------------------------------------------
# validateDeploymentHardening() -- NET-FR-017
# --------------------------------------------------------------------------------------------------

_HARDENING_CHECKS = (
    ("run_as_non_root", True, "container runs as root"),
    ("read_only_root_fs", True, "root filesystem is writable"),
    ("allow_privilege_escalation", False, "privilege escalation is allowed"),
    ("host_network", False, "workload uses the host network"),
    ("host_path_mounts", False, "workload mounts host paths"),
)


def validate_deployment_hardening(*, workload_manifest: dict, baseline: dict | None = None) -> dict:
    """Check a workload security context against the hardening baseline. Any violation ->
    `WorkloadHardeningFailedError` (WORKLOAD_HARDENING_FAILED). `baseline` overrides the built-in
    expected values where a deployment profile documents an exception."""
    sec = workload_manifest.get("security_context", workload_manifest)
    expected = dict({k: v for k, v, _ in _HARDENING_CHECKS}, **(baseline or {}))
    violations = []
    for key, _default, message in _HARDENING_CHECKS:
        want = expected.get(key)
        got = sec.get(key)
        if got is None:
            violations.append(f"{key} not set")
        elif bool(got) != bool(want):
            violations.append(message)
    caps_added = sec.get("capabilities_added") or []
    if caps_added:
        violations.append(f"added capabilities: {sorted(caps_added)}")
    if violations:
        raise WorkloadHardeningFailedError("Workload violates the hardening baseline", violations=violations)
    return {"hardened": True}


async def emit_security_event(
    session: AsyncSession, *, event_type: str, payload: dict, aggregate_id: uuid.UUID | None = None
) -> None:
    """MUT-FR-031 / Document 66 # 9 -- security-monitoring event to the outbox, separate from GxP audit."""
    from app.mutation.gateway import write_outbox_event

    await write_outbox_event(
        session, event_type=event_type, aggregate_type="security_event",
        aggregate_id=aggregate_id or uuid.uuid4(), aggregate_version=1, payload=payload,
        correlation_id=uuid.uuid4(),
    )
