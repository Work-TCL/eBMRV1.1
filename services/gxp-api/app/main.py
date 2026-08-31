import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal, assert_single_organization
from app.modules.audit.router import router as audit_router
from app.modules.batch.router import router as batch_router
from app.modules.batch_execution.router import router as batch_execution_router
from app.modules.ddcp.router import router as ddcp_router
from app.modules.ddcp.injector_router import router as injector_router
from app.modules.ddcp.inhalation_router import router as inhalation_router
from app.modules.ddcp.coated_device_router import router as coated_device_router
from app.modules.device.router import router as device_router
from app.modules.genealogy.router import router as genealogy_router
from app.modules.qa_review.router import router as qa_review_router
from app.modules.qc.router import router as qc_router
from app.modules.qc.router import oos_router
from app.modules.lims_integration.router import router as lims_integration_router
from app.modules.packaging.router import router as packaging_router
from app.modules.qms.router import router as qms_router
from app.modules.qms.capa_router import capa_action_router, capa_router
from app.modules.qms.ncr_router import ncr_router
from app.modules.qms.scar_router import scar_router, supplier_case_router
from app.modules.qms.change_router import change_router
from app.modules.qms.document_router import document_router
from app.modules.qms.training_router import training_router
from app.modules.qms.risk_router import risk_router
from app.modules.qms.internal_audit_router import audit_finding_router, internal_audit_router
from app.modules.qms.complaint_router import complaint_router
from app.modules.qms.field_action_router import field_action_router
from app.modules.qms.quality_metrics_router import effectiveness_router, quality_metrics_router
from app.modules.release.router import router as release_router
from app.modules.iam.router import organization_router, permissions_router, policy_router, roles_router, users_router
from app.modules.iam.router import router as iam_router
from app.modules.iam.router import sites_router
from app.modules.material.router import dispensing_v1_router as material_dispensing_v1_router
from app.modules.material.router import inventory_v1_router as material_inventory_v1_router
from app.modules.material.router import lots_router as material_lots_router
from app.modules.material.router import reconciliation_v1_router as material_reconciliation_v1_router
from app.modules.material.router import router as material_router
from app.modules.material.router import sampling_orders_router as material_sampling_orders_router
from app.modules.material.router import v1_router as material_v1_router
from app.modules.equipment.router import router as equipment_router
from app.modules.equipment.cleaning_router import router as cleaning_router
from app.modules.equipment.cleaning_router import line_clearance_router
from app.modules.equipment.em_router import router as em_router
from app.modules.equipment.sterilization_router import router as sterilization_router
from app.modules.equipment.sterilization_router import cip_sip_router, filtration_router
from app.modules.equipment.aseptic_router import router as aseptic_router
from app.modules.edge.router import router as edge_router
from app.modules.erp.router import router as erp_router
from app.modules.machine_integration.router import router as machine_integration_router
from app.modules.postmarket.router import router as postmarket_router
from app.modules.postmarket.reportability_router import router as postmarket_reportability_router
from app.modules.postmarket.obligation_router import router as postmarket_obligation_router
from app.modules.product.router import router as product_router
from app.modules.product_master.router import router as product_master_router
from app.modules.recipe.router import router as recipe_router
from app.modules.recipe_master.router import router as recipe_master_router
from app.modules.rules.router import router as rules_router
from app.modules.security.router import router as security_router
from app.modules.security.identity_router import router as security_identity_router
from app.modules.security.privileged_access_router import router as security_privileged_access_router
from app.modules.security.appsec_router import router as security_appsec_router
from app.modules.security.crypto_router import router as security_crypto_router
from app.modules.security.netzero_router import router as security_netzero_router
from app.modules.security.incident_router import router as security_incident_router
from app.modules.security.supplychain_router import router as security_supplychain_router
from app.modules.dataops.router import router as dataops_router
from app.modules.evidence.router import router as evidence_router
from app.modules.eventbus import outbox as eventbus_outbox
from app.modules.disaster_recovery.router import router as disaster_recovery_router
from app.modules.readmodels.router import search_router, reports_router, platform_router as readmodels_platform_router
from app.modules.supplier_quality.router import router as supplier_quality_router
from app.modules.vault.router import router as vault_router
from app.modules.yield_reconciliation.router import router as yield_reconciliation_router
from app.mutation.errors import DependencyUnavailableError, GxPError

logger = logging.getLogger("gxp_api.outbox")


async def outbox_publisher_loop() -> None:
    """Document 73 (SPEC-DATA-005) EVT-FR-002/003/004: the transactional-outbox publisher. Reads
    committed, unpublished outbox rows under `SKIP LOCKED` (`claim_outbox_batch`), publishes each
    (`publish_outbox_event` -- Phase 1 stand-in for NATS/JetStream, transport is swappable), and marks
    published only after a broker acknowledgement (`mark_outbox_published`). The transactional-outbox
    *pattern* (write in the same DB transaction as the domain change, publish only after commit) is
    what matters for the regulated guarantee.
    """
    while True:
        try:
            async with SessionLocal() as session:
                async with session.begin():
                    pending = await eventbus_outbox.claim_outbox_batch(session, batch_size=50)
                    for event in pending:
                        receipt = await eventbus_outbox.publish_outbox_event(event)
                        await eventbus_outbox.mark_outbox_published(session, event=event, publish_receipt=receipt)
        except Exception:  # noqa: BLE001 - never let the poller die the process
            logger.exception("outbox publisher iteration failed")
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as session:
        await assert_single_organization(session)
    task = asyncio.create_task(outbox_publisher_loop())
    yield
    task.cancel()


app = FastAPI(title="eBMR GxP Core", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Dev-only: the frontend can be reached via localhost, a LAN IP, or a public IP/hostname
    # depending on how this box is accessed, so match any origin on its port rather than one
    # fixed hostname. Tighten this to an explicit allowlist before any non-dev deployment.
    allow_origin_regex=r"^https?://[^/]+:4101$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Document 64 (SPEC-SEC-004) APPSEC-FR-026: browser-hardening response headers on every response.
# CSP is deliberately strict (no inline script, no framing) -- the SPA is served separately and the API
# returns JSON only. HSTS is emitted but only meaningful over TLS; harmless otherwise.
_SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


@app.exception_handler(GxPError)
async def gxp_error_handler(request: Request, exc: GxPError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Document 64 (SPEC-SEC-004) APPSEC-FR-018: a client never sees a stack trace, file path, SQL
    fragment or secret. Any exception that is not a GxPError / OperationalError collapses to a stable
    SYSTEM_FAULT body with a correlation id; the real detail is logged server-side only.
    """
    correlation_id = uuid.uuid4()
    logger.exception("unhandled request error correlation_id=%s path=%s", correlation_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "code": "SYSTEM_FAULT",
            "message": "An internal error occurred. Contact support with the correlation id.",
            "details": {"correlation_id": str(correlation_id)},
        },
    )


@app.exception_handler(OperationalError)
async def dependency_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """MUT-FR-022 / REMEDIATION_R1 FIX 3b: a compliance-critical dependency outage (DB connection loss
    reaching the signature service, the authorization service, etc.) must fail closed with a stable
    machine-readable code, never a bare 500 — and never a degraded-mode commit.
    """
    mapped = DependencyUnavailableError("A compliance-critical dependency is unavailable")
    return JSONResponse(
        status_code=mapped.status_code,
        content={"code": mapped.code, "message": mapped.message, "details": mapped.details},
    )


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


app.include_router(iam_router)
app.include_router(organization_router)
app.include_router(sites_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(permissions_router)
app.include_router(policy_router)
app.include_router(product_router)
app.include_router(recipe_router)
# batch_execution_router (prefix /batches/v1) must be registered before batch_router (prefix /batches) --
# Starlette matches routes in registration order across the whole app, and legacy's GET /batches/{batch_id}
# would otherwise shadow this module's exact GET /batches/v1 (batch_id="v1" fails UUID parsing instead of
# falling through to the next route).
app.include_router(batch_execution_router)
app.include_router(batch_router)
app.include_router(material_router)
app.include_router(material_lots_router)
app.include_router(material_v1_router)
app.include_router(material_sampling_orders_router)
app.include_router(material_inventory_v1_router)
app.include_router(material_dispensing_v1_router)
app.include_router(material_reconciliation_v1_router)
app.include_router(audit_router)
app.include_router(vault_router)
app.include_router(rules_router)
app.include_router(product_master_router)
app.include_router(recipe_master_router)
app.include_router(device_router)
app.include_router(genealogy_router)
app.include_router(qa_review_router)
app.include_router(release_router)
app.include_router(packaging_router)
app.include_router(supplier_quality_router)
app.include_router(qms_router)
app.include_router(capa_router)
app.include_router(capa_action_router)
app.include_router(ncr_router)
app.include_router(supplier_case_router)
app.include_router(scar_router)
app.include_router(change_router)
app.include_router(document_router)
app.include_router(training_router)
app.include_router(risk_router)
app.include_router(internal_audit_router)
app.include_router(audit_finding_router)
app.include_router(complaint_router)
app.include_router(field_action_router)
app.include_router(quality_metrics_router)
app.include_router(effectiveness_router)
app.include_router(qc_router)
app.include_router(oos_router)
app.include_router(lims_integration_router)
app.include_router(equipment_router)
app.include_router(cleaning_router)
app.include_router(line_clearance_router)
app.include_router(em_router)
app.include_router(sterilization_router)
app.include_router(cip_sip_router)
app.include_router(filtration_router)
app.include_router(aseptic_router)
app.include_router(edge_router)
app.include_router(erp_router)
app.include_router(ddcp_router)
app.include_router(injector_router)
app.include_router(inhalation_router)
app.include_router(coated_device_router)
app.include_router(machine_integration_router)
app.include_router(yield_reconciliation_router)
app.include_router(postmarket_router)
app.include_router(postmarket_reportability_router)
app.include_router(postmarket_obligation_router)
app.include_router(security_router)
app.include_router(security_identity_router)
app.include_router(security_privileged_access_router)
app.include_router(security_appsec_router)
app.include_router(security_crypto_router)
app.include_router(security_netzero_router)
app.include_router(security_incident_router)
app.include_router(security_supplychain_router)
app.include_router(dataops_router)
app.include_router(evidence_router)
app.include_router(search_router)
app.include_router(reports_router)
app.include_router(readmodels_platform_router)
app.include_router(disaster_recovery_router)
