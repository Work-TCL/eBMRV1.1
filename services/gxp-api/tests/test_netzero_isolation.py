"""Document 66 (SPEC-SEC-006, NET-FR-001..030): the zero-trust library — approved-flow validation
(default deny), site-scoped Edge outbound profiles, tenant/site scope propagation, forbidden-path
segmentation tests, workload-hardening admission — plus the two read-only catalogue endpoints.
"""

import uuid

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.mutation.models import OutboxEvent
from app.modules.security import netzero
from app.modules.security.netzero_models import DeploymentSecurityProfile, NetworkFlowDefinition
from app.mutation.errors import (
    NetworkFlowNotAllowedError,
    SegmentationControlFailedError,
    TenantScopeMismatchError,
    WorkloadHardeningFailedError,
)
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _user(db, seeded, tag, role="Admin"):
    u = User(username=f"nz.u{tag}", email=f"nz.u{tag}@x.com", full_name="NZ U",
             password_hash=hash_password(DEMO_PASSWORD), status="active")
    db.add(u)
    await db.flush()
    db.add(UserSiteRole(user_id=u.id, site_id=seeded["site_id"], role_id=seeded["roles"][role].id))
    return u


async def _seed_flows(db):
    rows = [
        NetworkFlowDefinition(deployment_profile="CLOUD", source_zone="APP", source_service="frappe",
                              destination_zone="GXP_SERVICE", destination_service="gxp-api", protocol="TCP",
                              port=8010, purpose="Frappe -> GxP API", auth_mechanism="MTLS", owner="platform"),
        NetworkFlowDefinition(deployment_profile="CLOUD", source_zone="GXP_SERVICE", source_service="gxp-api",
                              destination_zone="DB", destination_service="postgres", protocol="TCP",
                              port=5432, purpose="GxP API -> Postgres", auth_mechanism="MTLS", owner="platform"),
        NetworkFlowDefinition(deployment_profile="CLOUD", source_zone="EDGE_OT", source_service="*",
                              destination_zone="INTEGRATION", destination_service="edge-ingest", protocol="TCP",
                              port=443, purpose="Edge -> integration ingest (outbound only)", auth_mechanism="MTLS",
                              owner="platform"),
    ]
    for r in rows:
        db.add(r)
    await db.flush()


# =================================================================================================
# validateServiceFlow / generateNetworkPolicySet — NET-FR-002/004
# =================================================================================================


@pytest.mark.asyncio
async def test_validate_service_flow_default_deny(db, seeded):
    async with db.begin():
        await _seed_flows(db)

    async with db.begin():
        ok = await netzero.validate_service_flow(
            db, deployment_profile="CLOUD", source_zone="APP", source_service="frappe",
            destination_zone="GXP_SERVICE", destination_service="gxp-api", protocol="TCP", port=8010)
        assert ok["allow"] is True and ok["auth_mechanism"] == "MTLS"

    async with db.begin():
        # Frappe -> DB directly is not in the catalogue -> denied (Document 66 # 14).
        with pytest.raises(NetworkFlowNotAllowedError):
            await netzero.validate_service_flow(
                db, deployment_profile="CLOUD", source_zone="FRAPPE", source_service="frappe",
                destination_zone="DB", destination_service="postgres", protocol="TCP", port=5432)
        # right zones, wrong port -> denied
        with pytest.raises(NetworkFlowNotAllowedError):
            await netzero.validate_service_flow(
                db, deployment_profile="CLOUD", source_zone="APP", source_service="frappe",
                destination_zone="GXP_SERVICE", destination_service="gxp-api", protocol="TCP", port=9999)


@pytest.mark.asyncio
async def test_generate_network_policy_set_is_default_deny(db, seeded):
    async with db.begin():
        await _seed_flows(db)
    async with db.begin():
        bundle = await netzero.generate_network_policy_set(db, deployment_profile="CLOUD")
    assert bundle["default_action"] == "DENY"
    assert bundle["allow_rule_count"] == 3


@pytest.mark.asyncio
async def test_issue_site_scoped_edge_profile_never_includes_db(db, seeded):
    async with db.begin():
        await _seed_flows(db)
        # add a (wrong) EDGE_OT -> DB flow to prove the structural guard drops it
        db.add(NetworkFlowDefinition(deployment_profile="CLOUD", source_zone="EDGE_OT", source_service="*",
                                     destination_zone="DB", destination_service="postgres", protocol="TCP",
                                     port=5432, purpose="(should be filtered)", auth_mechanism="MTLS", owner="x"))
        await db.flush()
    async with db.begin():
        prof = await netzero.issue_site_scoped_edge_network_profile(
            db, site_id=seeded["site_id"], gateway_id=uuid.uuid4(), deployment_profile="CLOUD")
    assert prof["direction"] == "OUTBOUND_ONLY"
    assert all(e["to_zone"] != "DB" for e in prof["allowed_endpoints"])
    assert any(e["to_zone"] == "INTEGRATION" for e in prof["allowed_endpoints"])


# =================================================================================================
# verifyTenantScopePropagation — NET-FR-010/011
# =================================================================================================


def test_verify_tenant_scope_propagation():
    ctx = {"tenant_id": "T1", "site_id": "S1"}
    assert netzero.verify_tenant_scope_propagation(auth_context=ctx, downstream={"tenant_id": "T1", "site_id": "S1"})["compatible"]
    # enterprise-scoped job may cross site
    assert netzero.verify_tenant_scope_propagation(auth_context=ctx, downstream={"tenant_id": "T1", "site_id": "S2", "enterprise_scope": True})["compatible"]
    with pytest.raises(TenantScopeMismatchError):
        netzero.verify_tenant_scope_propagation(auth_context=ctx, downstream={"tenant_id": "T2", "site_id": "S1"})
    with pytest.raises(TenantScopeMismatchError):
        netzero.verify_tenant_scope_propagation(auth_context=ctx, downstream={"tenant_id": "T1", "site_id": "S2"})
    with pytest.raises(TenantScopeMismatchError):
        netzero.verify_tenant_scope_propagation(auth_context=ctx, downstream={"site_id": "S1"})  # dropped tenant


# =================================================================================================
# testForbiddenNetworkPath — NET-FR-029
# =================================================================================================


@pytest.mark.asyncio
async def test_forbidden_network_path_control(db, seeded):
    async with db.begin():
        await _seed_flows(db)
    async with db.begin():
        # a non-approved path that is NOT reachable -> control OK
        res = await netzero.test_forbidden_network_path(
            db, deployment_profile="CLOUD", source_zone="INGRESS", source_service="proxy",
            destination_zone="DB", destination_service="postgres", protocol="TCP", port=5432, reachable=False)
        assert res["result"] == "BLOCKED_OK"
    async with db.begin():
        # a non-approved path that IS reachable -> segmentation control failed
        with pytest.raises(SegmentationControlFailedError):
            await netzero.test_forbidden_network_path(
                db, deployment_profile="CLOUD", source_zone="INGRESS", source_service="proxy",
                destination_zone="DB", destination_service="postgres", protocol="TCP", port=5432, reachable=True)

    # the segmentation-control failure emitted a ForbiddenNetworkPathDetected event (NET-FR-029 / MUT-FR-031);
    # a correctly-blocked path (the BLOCKED_OK case above) does NOT emit -- only a reachable forbidden path.
    async with db.begin():
        rows = (await db.execute(select(OutboxEvent).where(
            OutboxEvent.event_type == "ForbiddenNetworkPathDetected",
            OutboxEvent.aggregate_type == "security_event"))).scalars().all()
    assert len(rows) == 1 and rows[0].payload["reachable"] is True


# =================================================================================================
# validateDeploymentHardening — NET-FR-017
# =================================================================================================


def test_validate_deployment_hardening():
    good = {"security_context": {"run_as_non_root": True, "read_only_root_fs": True,
                                 "allow_privilege_escalation": False, "host_network": False,
                                 "host_path_mounts": False}}
    assert netzero.validate_deployment_hardening(workload_manifest=good)["hardened"] is True
    for bad in (
        {"security_context": {**good["security_context"], "run_as_non_root": False}},
        {"security_context": {**good["security_context"], "host_network": True}},
        {"security_context": {**good["security_context"], "capabilities_added": ["NET_ADMIN"]}},
        {"security_context": {"run_as_non_root": True}},  # missing keys
    ):
        with pytest.raises(WorkloadHardeningFailedError):
            netzero.validate_deployment_hardening(workload_manifest=bad)


# =================================================================================================
# read-only catalogue endpoints + module suite
# =================================================================================================


@pytest.mark.asyncio
async def test_network_flow_and_profile_endpoints(db, seeded, client):
    async with db.begin():
        await _user(db, seeded, "adm")
        await _seed_flows(db)
        db.add(DeploymentSecurityProfile(profile_name="cloud-default", deployment_profile="CLOUD",
                                         container_hardening={"run_as_non_root": True}, admin_access_pattern="ZTNA"))
        await db.flush()
    token = await login(client, "nz.uadm")

    r = await client.get("/security/v1/network-flows?deployment_profile=CLOUD", headers=auth_headers(token))
    assert r.status_code == 200 and r.json()["count"] == 3

    r = await client.get("/security/v1/deployment-security-profile?profile_name=cloud-default", headers=auth_headers(token))
    assert r.status_code == 200 and r.json()["profiles"][0]["admin_access_pattern"] == "ZTNA"

    r = await client.get("/security/v1/deployment-security-profile?profile_name=missing", headers=auth_headers(token))
    assert r.status_code == 404

    r = await client.get("/security/v1/network-flows")  # unauthenticated
    assert r.status_code == 401

    async with db.begin():
        await _user(db, seeded, "op", role="Operator")
    optoken = await login(client, "nz.uop")
    r = await client.get("/security/v1/network-flows", headers=auth_headers(optoken))
    assert r.status_code == 403
