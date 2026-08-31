"""Document 64 (SPEC-SEC-004, APPSEC-FR-001..030): the cross-cutting web/API/runtime security library
(`app/modules/security/appsec.py`) plus the two small Mutation Gateway registry commands
(`outbound_destination`, `webhook_profile`) and the live API-inventory read.

These are command-level / function-level tests, the same style as test_privileged_access.py -- the
router's `evaluate_policy` gate is exercised separately by the module-suite client tests below.
"""

import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.mutation.models import OutboxEvent
from app.modules.security import appsec, appsec_commands as commands
from app.modules.security.appsec_models import OutboundDestination, WebhookProfile
from app.mutation.errors import (
    AccessDeniedError,
    FileTypeBlockedError,
    IdempotencyConflictError,
    MalwareDetectedError,
    RateLimitedError,
    ReplayDetectedError,
    RequestSchemaInvalidError,
    SsrfDestinationBlockedError,
    UnsafeContentRejectedError,
    ValidationFailedError,
    WebhookAuthFailedError,
)
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_user(db, seeded, tag, role_name="Admin"):
    user = User(
        username=f"appsec.user{tag}", email=f"appsec.user{tag}@example.com", full_name="AppSec User",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


async def _get(db, model, obj_id):
    async with db.begin():
        return await db.get(model, obj_id)


@pytest.fixture(autouse=True)
def _reset_process_state():
    appsec.reset_rate_limits()
    appsec.reset_webhook_replay_cache()
    yield
    appsec.reset_rate_limits()
    appsec.reset_webhook_replay_cache()


# =================================================================================================
# outbound_destination / webhook_profile Mutation Gateway commands
# =================================================================================================


@pytest.mark.asyncio
async def test_register_outbound_destination_writes_one_audit_and_one_outbox(db, seeded):
    async with db.begin():
        actor = await _make_user(db, seeded, "1")

    async with db.begin():
        receipt = await commands.register_outbound_destination(
            db, commands.RegisterOutboundDestinationCommand(
                idempotency_key=idem(), service_id="erpnext-sandbox",
                schemes_hosts_ports={"schemes": ["https"], "hosts": ["erp.example.com"], "ports": [443]},
                purpose="ERPNext master-data sync (Document 48)",
            ), actor.id,
        )

    dest = await _get(db, OutboundDestination, receipt.aggregate_id)
    assert dest.state == "ACTIVE" and dest.version == 1
    assert dest.redirect_policy == "BLOCK"

    async with db.begin():
        audit_n = await db.scalar(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.aggregate_id == dest.id)
        )
        outbox_n = await db.scalar(
            select(func.count()).select_from(OutboxEvent).where(OutboxEvent.aggregate_id == dest.id)
        )
        event = await db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == dest.id))
    assert audit_n == 1 and outbox_n == 1
    assert event.event_type == "OutboundDestinationRegistered"


@pytest.mark.asyncio
async def test_register_outbound_destination_rejects_inline_secret_and_bad_redirect(db, seeded):
    async with db.begin():
        actor = await _make_user(db, seeded, "2")

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.register_outbound_destination(
                db, commands.RegisterOutboundDestinationCommand(
                    idempotency_key=idem(), service_id="x",
                    schemes_hosts_ports={"hosts": ["h.example.com"]},
                    purpose="p", auth_secret_ref="https://user:pass@h.example.com/secret",
                ), actor.id,
            )

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.register_outbound_destination(
                db, commands.RegisterOutboundDestinationCommand(
                    idempotency_key=idem(), service_id="x",
                    schemes_hosts_ports={"hosts": ["h.example.com"]},
                    purpose="p", redirect_policy="FOLLOW_ALL",
                ), actor.id,
            )


@pytest.mark.asyncio
async def test_register_outbound_destination_idempotent_and_conflict(db, seeded):
    async with db.begin():
        actor = await _make_user(db, seeded, "3")
    key = idem()
    body = dict(
        service_id="lims-1",
        schemes_hosts_ports={"schemes": ["https"], "hosts": ["lims.example.com"]},
        purpose="LIMS result pull",
    )
    async with db.begin():
        r1 = await commands.register_outbound_destination(
            db, commands.RegisterOutboundDestinationCommand(idempotency_key=key, **body), actor.id
        )
    async with db.begin():
        r2 = await commands.register_outbound_destination(
            db, commands.RegisterOutboundDestinationCommand(idempotency_key=key, **body), actor.id
        )
    assert r1.command_id == r2.command_id  # same receipt, no second write

    async with db.begin():
        with pytest.raises(IdempotencyConflictError):
            await commands.register_outbound_destination(
                db, commands.RegisterOutboundDestinationCommand(
                    idempotency_key=key, **{**body, "purpose": "changed purpose"}
                ), actor.id,
            )

    async with db.begin():
        n = await db.scalar(
            select(func.count()).select_from(OutboundDestination).where(OutboundDestination.service_id == "lims-1")
        )
    assert n == 1


@pytest.mark.asyncio
async def test_register_webhook_profile_positive_and_numeric_bounds(db, seeded):
    async with db.begin():
        actor = await _make_user(db, seeded, "4")

    async with db.begin():
        receipt = await commands.register_webhook_profile(
            db, commands.RegisterWebhookProfileCommand(
                idempotency_key=idem(), provider="erpnext", auth_mechanism="HMAC_SHA256",
                replay_window_seconds=300, max_body_bytes=1048576, signing_secret_ref="vault:webhook/erpnext",
            ), actor.id,
        )
    profile = await _get(db, WebhookProfile, receipt.aggregate_id)
    assert profile.provider == "erpnext" and profile.replay_window_seconds == 300

    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.register_webhook_profile(
                db, commands.RegisterWebhookProfileCommand(
                    idempotency_key=idem(), provider="bad", replay_window_seconds=0,
                ), actor.id,
            )
    async with db.begin():
        with pytest.raises(ValidationFailedError):
            await commands.register_webhook_profile(
                db, commands.RegisterWebhookProfileCommand(
                    idempotency_key=idem(), provider="bad2", auth_mechanism="NOT_A_MECHANISM",
                ), actor.id,
            )


# =================================================================================================
# authorizeObjectAccess() -- APPSEC-FR-001/002/003/005/028/029
# =================================================================================================


def test_authorize_object_access_bfla_and_bola_and_mass_assignment():
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()

    # positive
    decision = appsec.authorize_object_access(
        actor_roles={"Security Admin"}, action="outbound_destination.register",
        resource_tenant_id=tenant_a, resource_site_id=None,
        context_tenant_id=tenant_a, context_site_id=None,
        allowed_roles=["Security Admin"], requested_fields=["purpose"], writable_fields=["purpose", "state"],
    )
    assert decision["allow"] is True

    # BFLA: role not permitted for the function
    with pytest.raises(AccessDeniedError):
        appsec.authorize_object_access(
            actor_roles={"Operator"}, action="outbound_destination.register",
            resource_tenant_id=tenant_a, resource_site_id=None,
            context_tenant_id=tenant_a, context_site_id=None, allowed_roles=["Security Admin"],
        )

    # BOLA/IDOR: knows another tenant's object id but is not scoped to it
    with pytest.raises(AccessDeniedError):
        appsec.authorize_object_access(
            actor_roles={"Security Admin"}, action="read",
            resource_tenant_id=tenant_b, resource_site_id=None,
            context_tenant_id=tenant_a, context_site_id=None,
        )

    # property-level: writing a protected field
    with pytest.raises(AccessDeniedError):
        appsec.authorize_object_access(
            actor_roles={"Security Admin"}, action="update",
            resource_tenant_id=tenant_a, resource_site_id=None,
            context_tenant_id=tenant_a, context_site_id=None,
            requested_fields=["state", "version"], writable_fields=["state"],
        )


# =================================================================================================
# validateRequestSchema() -- APPSEC-FR-004/023
# =================================================================================================


def test_validate_request_schema_rejects_unknown_and_typed_violations():
    good = appsec.validate_request_schema(
        commands.RegisterWebhookProfileCommand,
        {"idempotency_key": "k", "provider": "p"},
    )
    assert good.provider == "p"

    with pytest.raises(RequestSchemaInvalidError):
        appsec.validate_request_schema(
            commands.RegisterWebhookProfileCommand,
            {"idempotency_key": "k", "provider": "p", "evil_extra": "drop table"},
        )
    with pytest.raises(RequestSchemaInvalidError):
        appsec.validate_request_schema(
            commands.RegisterWebhookProfileCommand,
            {"idempotency_key": "k", "provider": "p", "replay_window_seconds": "not-an-int"},
        )


# =================================================================================================
# sanitizeRichText() -- APPSEC-FR-008/022
# =================================================================================================


def test_sanitize_rich_text_blocks_xss_and_template_tokens_keeps_safe_markup():
    out = appsec.sanitize_rich_text("<p>hello <strong>world</strong></p><table>x</table>")
    assert "<strong>" in out["content"]
    assert "&lt;table" in out["content"]  # unknown tag escaped, not executed
    assert out["sanitizer_policy_version"]

    for payload in (
        "<script>steal()</script>",
        '<img src=x onerror="steal()">',
        '<a href="javascript:evil()">x</a>',
        "Hello {{ 7*7 }}",
        "<%= system('rm -rf /') %>",
    ):
        with pytest.raises(UnsafeContentRejectedError):
            appsec.sanitize_rich_text(payload)


# =================================================================================================
# validateOutboundDestination() -- APPSEC-FR-011  (SSRF)
# =================================================================================================


@pytest.mark.asyncio
async def test_validate_outbound_destination_allowlist_and_metadata_block(db, seeded):
    async with db.begin():
        actor = await _make_user(db, seeded, "5")
        await commands.register_outbound_destination(
            db, commands.RegisterOutboundDestinationCommand(
                idempotency_key=idem(), service_id="erp",
                schemes_hosts_ports={"schemes": ["https"], "hosts": ["erp.example.com"], "ports": [443]},
                purpose="erp",
            ), actor.id,
        )

    async with db.begin():
        ok = await appsec.validate_outbound_destination(
            db, url="https://erp.example.com/api/v2/items", purpose="sync"
        )
    assert ok["allow"] is True

    async with db.begin():
        # SSRF metadata IP -- blocked before the allowlist is even consulted
        with pytest.raises(SsrfDestinationBlockedError):
            await appsec.validate_outbound_destination(
                db, url="http://169.254.169.254/latest/meta-data/", purpose="sync"
            )
        # private range
        with pytest.raises(SsrfDestinationBlockedError):
            await appsec.validate_outbound_destination(
                db, url="http://10.1.2.3:8080/internal", purpose="sync"
            )
        # not on the allowlist
        with pytest.raises(SsrfDestinationBlockedError):
            await appsec.validate_outbound_destination(
                db, url="https://evil.example.net/x", purpose="sync"
            )
        # non-absolute
        with pytest.raises(SsrfDestinationBlockedError):
            await appsec.validate_outbound_destination(db, url="/relative/path", purpose="sync")

    # every block emitted an SSRFBlocked security-telemetry event to the outbox (MUT-FR-031),
    # written in its own committed transaction so it survives the caller's rollback.
    async with db.begin():
        n = await db.scalar(
            select(func.count()).select_from(OutboxEvent)
            .where(OutboxEvent.event_type == "SSRFBlocked", OutboxEvent.aggregate_type == "security_event")
        )
    assert n == 4


# =================================================================================================
# validateFileUpload() -- APPSEC-FR-012
# =================================================================================================


def test_validate_file_upload_size_type_malware_and_filename():
    pdf = b"%PDF-1.7\n" + b"0" * 100
    receipt = appsec.validate_file_upload(
        content=pdf, filename="../../etc/pa ss wd.pdf", declared_type="application/pdf",
        max_bytes=10_000, allowed_types=["application/pdf"],
    )
    assert receipt["safe_filename"] == "pa_ss_wd.pdf"  # path stripped, spaces neutralised
    assert receipt["content_type"] == "application/pdf"
    assert receipt["sha256"] == hashlib.sha256(pdf).hexdigest()

    with pytest.raises(FileTypeBlockedError):  # oversized
        appsec.validate_file_upload(
            content=b"0" * 20_000, filename="a.pdf", declared_type="application/pdf",
            max_bytes=10_000, allowed_types=["application/pdf"],
        )
    with pytest.raises(FileTypeBlockedError):  # declared != sniffed
        appsec.validate_file_upload(
            content=pdf, filename="a.png", declared_type="image/png",
            max_bytes=10_000, allowed_types=["image/png", "application/pdf"],
        )
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    with pytest.raises(MalwareDetectedError):
        appsec.validate_file_upload(
            content=eicar, filename="a.txt", declared_type="text/plain",
            max_bytes=10_000, allowed_types=[],
        )


# =================================================================================================
# protectSpreadsheetExport() -- APPSEC-FR-021
# =================================================================================================


def test_protect_spreadsheet_export_neutralises_formula_injection_and_drops_columns():
    rows = [["=cmd|' /C calc'!A0", "safe", "secret-value"], ["+1234", "ok", "another-secret"]]
    out = appsec.protect_spreadsheet_export(
        rows, columns=["formula", "note", "secret"], allowed_columns=["formula", "note"]
    )
    assert out[0] == ["'=cmd|' /C calc'!A0", "safe"]
    assert out[1] == ["'+1234", "ok"]
    assert all(len(r) == 2 for r in out)  # secret column dropped


# =================================================================================================
# enforceRateLimit() -- APPSEC-FR-014/015
# =================================================================================================


def test_enforce_rate_limit_token_bucket_and_boundary():
    key = f"test:{uuid.uuid4()}"
    base = time.monotonic()
    for i in range(3):
        appsec.enforce_rate_limit(bucket_key=key, limit=3, window_seconds=60, now=base)
    with pytest.raises(RateLimitedError):  # 4th call in the window
        appsec.enforce_rate_limit(bucket_key=key, limit=3, window_seconds=60, now=base)
    # after a full window the bucket has refilled
    appsec.enforce_rate_limit(bucket_key=key, limit=3, window_seconds=60, now=base + 61)
    # a disabled policy fails closed
    with pytest.raises(RateLimitedError):
        appsec.enforce_rate_limit(bucket_key=key, limit=0, window_seconds=60)


# =================================================================================================
# verifyWebhook() -- APPSEC-FR-020
# =================================================================================================


@pytest.mark.asyncio
async def test_verify_webhook_hmac_replay_window_and_delivery_dedupe(db, seeded):
    secret = "s3cr3t-signing-key"
    async with db.begin():
        actor = await _make_user(db, seeded, "6")
        await commands.register_webhook_profile(
            db, commands.RegisterWebhookProfileCommand(
                idempotency_key=idem(), provider="erpnext", auth_mechanism="HMAC_SHA256",
                replay_window_seconds=300, max_body_bytes=1024,
            ), actor.id,
        )

    body = b'{"event":"po.updated","id":"PO-1"}'
    now = datetime.now(timezone.utc)
    ts = str(int(now.timestamp()))
    sig = hmac.new(secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()

    async with db.begin():
        ok = await appsec.verify_webhook(
            db, provider="erpnext", body=body, signature_header=sig, timestamp_header=ts,
            delivery_id="d-1", signing_secret=secret, now=now,
        )
    assert ok["verified"] is True

    async with db.begin():
        # replayed delivery id
        with pytest.raises(ReplayDetectedError):
            await appsec.verify_webhook(
                db, provider="erpnext", body=body, signature_header=sig, timestamp_header=ts,
                delivery_id="d-1", signing_secret=secret, now=now,
            )
        # bad signature
        with pytest.raises(WebhookAuthFailedError):
            await appsec.verify_webhook(
                db, provider="erpnext", body=body, signature_header="deadbeef", timestamp_header=ts,
                delivery_id="d-2", signing_secret=secret, now=now,
            )
        # stale timestamp -> outside replay window
        old_ts = str(int((now - timedelta(seconds=3600)).timestamp()))
        old_sig = hmac.new(secret.encode(), old_ts.encode() + b"." + body, hashlib.sha256).hexdigest()
        with pytest.raises(ReplayDetectedError):
            await appsec.verify_webhook(
                db, provider="erpnext", body=body, signature_header=old_sig, timestamp_header=old_ts,
                delivery_id="d-3", signing_secret=secret, now=now,
            )
        # oversized body
        with pytest.raises(WebhookAuthFailedError):
            await appsec.verify_webhook(
                db, provider="erpnext", body=b"0" * 5000, signature_header=sig, timestamp_header=ts,
                delivery_id="d-4", signing_secret=secret, now=now,
            )

    # the two replay rejections (duplicate delivery id + stale timestamp) each emitted a
    # WebhookReplayDetected security-telemetry event (MUT-FR-031).
    async with db.begin():
        rows = (await db.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "WebhookReplayDetected",
                                      OutboxEvent.aggregate_type == "security_event")
        )).scalars().all()
    assert len(rows) == 2
    assert {r.payload["reason"] for r in rows} == {"DUPLICATE_DELIVERY", "OUTSIDE_REPLAY_WINDOW"}


# =================================================================================================
# mapSafeErrorResponse() -- APPSEC-FR-018
# =================================================================================================


def test_map_safe_error_response_hides_internal_detail():
    known = appsec.map_safe_error_response(RateLimitedError("too many"), correlation_id="corr-1")
    assert known == {"code": "RATE_LIMITED", "message": "too many", "correlation_id": "corr-1"}

    unknown = appsec.map_safe_error_response(RuntimeError("psycopg: password=hunter2 at /app/secret.py:42"))
    assert unknown["code"] == "SYSTEM_FAULT"
    assert "hunter2" not in unknown["message"] and "secret.py" not in unknown["message"]
    assert uuid.UUID(unknown["correlation_id"])  # a real correlation id was minted


# =================================================================================================
# Module suite (client-level) -- unauth / RBAC / security headers / api-inventory
# =================================================================================================


@pytest.mark.asyncio
async def test_module_suite_unauth_rbac_headers_and_inventory(db, seeded, client):
    # M01 -- unauthenticated state-changing call is rejected, no row written
    resp = await client.post("/security/v1/outbound-destinations", json={
        "idempotency_key": idem(), "service_id": "x",
        "schemes_hosts_ports": {"hosts": ["h.example.com"]}, "purpose": "p",
    })
    assert resp.status_code == 401
    async with db.begin():
        n = await db.scalar(select(func.count()).select_from(OutboundDestination))
    assert n == 0

    # APPSEC-FR-026 -- security headers present on every response
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "frame-ancestors 'none'" in resp.headers.get("Content-Security-Policy", "")

    # M02 -- authenticated but unprivileged actor is denied by the policy service
    async with db.begin():
        await _make_user(db, seeded, "op", role_name="Operator")
    token = await login(client, "appsec.userop")
    resp = await client.post("/security/v1/outbound-destinations", headers=auth_headers(token), json={
        "idempotency_key": idem(), "service_id": "x",
        "schemes_hosts_ports": {"hosts": ["h.example.com"]}, "purpose": "p",
    })
    assert resp.status_code == 403

    # positive -- Admin (carries the SPEC-SEC-004 codes in conftest) can register + read inventory
    async with db.begin():
        await _make_user(db, seeded, "adm", role_name="Admin")
    token = await login(client, "appsec.useradm")
    resp = await client.post("/security/v1/outbound-destinations", headers=auth_headers(token), json={
        "idempotency_key": idem(), "service_id": "erp",
        "schemes_hosts_ports": {"schemes": ["https"], "hosts": ["erp.example.com"]},
        "purpose": "erp sync",
    })
    assert resp.status_code == 200, resp.text

    inv = await client.get("/security/v1/api-inventory", headers=auth_headers(token))
    assert inv.status_code == 200
    body = inv.json()
    assert body["endpoint_count"] > 0
    paths = {e["path"] for e in body["endpoints"]}
    assert "/security/v1/outbound-destinations" in paths
    assert "/security/v1/api-inventory" in paths
