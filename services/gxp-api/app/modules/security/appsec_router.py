"""Document 64 (SPEC-SEC-004) REST surface, prefix `/security/v1`. Exactly the 3 operations Document
64 # 7 lists: register an outbound destination, register a webhook profile, read the API inventory.
All other APPSEC-FR controls are middleware / library helpers (see `appsec.py`, `app/main.py`), not
endpoints -- an APPSEC document hardens what exists rather than adding surface.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.security import appsec
from app.modules.security import appsec_commands as commands
from app.modules.security.appsec_models import ApiSecurityPolicy
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/security/v1", tags=["security-appsec"])


@router.post("/outbound-destinations", response_model=MutationReceipt)
async def post_register_outbound_destination(
    cmd: commands.RegisterOutboundDestinationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="outbound_destination.register", site_id=None)
        return await commands.register_outbound_destination(session, cmd, actor.user_id)


@router.post("/webhook-profiles", response_model=MutationReceipt)
async def post_register_webhook_profile(
    cmd: commands.RegisterWebhookProfileCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="webhook_profile.register", site_id=None)
        return await commands.register_webhook_profile(session, cmd, actor.user_id)


@router.get("/api-inventory")
async def get_api_inventory(
    request: Request,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """APPSEC-FR-016/027: the live, complete endpoint inventory -- method, path, operationId, declared
    security scheme, deprecation flag -- built from the running app's generated OpenAPI document (the
    literal "documented in OpenAPI/inventory" of APPSEC-FR-016) so it can never drift from what is
    actually deployed. Any `api_security_policy` row for an operationId layers on its auth_mode and
    explicit deprecation/sunset metadata (APPSEC-FR-027)."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="api_inventory.view", site_id=None)
        policy_rows = (await session.execute(select(ApiSecurityPolicy))).scalars().all()

    policy_by_op = {p.operation_id: p for p in policy_rows}
    spec = request.app.openapi()
    endpoints = []
    for path, path_item in sorted(spec.get("paths", {}).items()):
        for method, op in path_item.items():
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                continue
            op_id = op.get("operationId")
            policy = policy_by_op.get(op_id)
            endpoints.append({
                "method": method.upper(),
                "path": path,
                "operation_id": op_id,
                "authenticated": bool(op.get("security")),
                "security_schemes": sorted({k for s in op.get("security", []) for k in s}),
                "deprecated": bool(op.get("deprecated")) or bool(policy and policy.deprecation),
                "auth_mode": policy.auth_mode if policy else None,
                "deprecation": policy.deprecation if policy else None,
            })
    deprecated = [e for e in endpoints if e["deprecated"]]
    if deprecated:
        # APPSEC-FR-027: a deprecated version that is still reachable is attack surface -- surface it
        # as security telemetry so it "cannot linger undocumented".
        async with session.begin():
            await appsec.emit_security_event(
                session, event_type="DeprecatedAPIUsed",
                payload={"deprecated_operations": [e["operation_id"] for e in deprecated],
                         "count": len(deprecated), "detected_via": "api_inventory"},
            )
    return {
        "generated_from": "openapi_document",
        "openapi_version": spec.get("openapi"),
        "endpoint_count": len(endpoints),
        "deprecated_count": len(deprecated),
        "endpoints": endpoints,
    }
