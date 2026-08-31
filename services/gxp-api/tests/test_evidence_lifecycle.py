"""Document 72 (SPEC-DATA-004) -- Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle.

Executable evidence for the evidence lifecycle: stage -> finalize (hash verified) -> manifest ->
legal hold (signed, Document 106 row 142) -> integrity check -> purge, plus the negatives from the
spec test catalogue (hash mismatch quarantine, missing object, legal hold blocks purge, generic
delete denied, MIME/size upload denial, presigned/authorized download gating).
"""

import base64
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.main import app
from app.modules.evidence import commands as ev
from app.modules.evidence.commands import evidence_record_hash
from app.modules.evidence.models import EvidenceManifest, EvidenceObject
from app.modules.evidence.store import LocalEvidenceStore, content_key, set_store, sha256_bytes
from app.modules.mutation.models import OutboxEvent
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    EvidenceHashMismatchError,
    EvidenceMissingError,
    EvidenceNotFinalizedError,
    EvidencePurgeBlockedError,
    EvidenceUploadDeniedError,
    MissingSignatureError,
)
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    set_store(LocalEvidenceStore(base_dir=str(tmp_path / "evstore")))
    yield
    set_store(LocalEvidenceStore())


@pytest.fixture
async def api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _stage(s, actor_id, *, mime="application/pdf", expected_hash=None, size=None):
    return await ev.stage_evidence_upload(
        s,
        ev.StageEvidenceUploadCommand(
            idempotency_key=idem(), owner_type="gxp_batch", owner_id=uuid.uuid4(),
            filename="report.pdf", mime_type=mime, declared_size_bytes=size,
            expected_hash=expected_hash, reason="attach batch evidence",
        ),
        actor_id,
    )


# --------------------------------------------------------------------------------------------------
# OBJ-FR-002/003/004/016 -- stage + finalize
# --------------------------------------------------------------------------------------------------


async def test_stage_then_finalize_happy_path(db, seeded):
    """TC-072-*-01: a staged upload finalizes to FINALIZED after whole-object hash verification; the
    store holds the content-addressed object; one audit event + EvidenceFinalized outbox row."""
    actor = seeded["users"]["qa.reviewer"].id
    data = b"%PDF-1.4 fake batch record\n"
    digest = sha256_bytes(data)

    async with SessionLocal() as s:
        async with s.begin():
            r1 = await _stage(s, actor, expected_hash=digest)
        eid = r1.aggregate_id
        async with s.begin():
            r2 = await ev.finalize_evidence_upload(
                s,
                ev.FinalizeEvidenceUploadCommand(
                    idempotency_key=idem(), evidence_id=eid, expected_version=1,
                    content_base64=base64.b64encode(data).decode(), reason="upload complete",
                ),
                actor,
            )
    assert r2.resulting_version == 2
    async with SessionLocal() as s:
        obj = await s.get(EvidenceObject, eid)
        assert obj.state == "FINALIZED"
        assert obj.content_hash == digest
        assert obj.object_key == content_key(digest)
        assert obj.size_bytes == len(data)
        events = (await s.execute(
            select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id == eid)
        )).scalars().all()
        assert "EvidenceUploadStaged" in events and "EvidenceFinalized" in events


async def test_finalize_hash_mismatch_quarantines(db, seeded):
    """TC-072 negative / OBJ-FR-016: bytes that don't match the declared hash quarantine the object
    and raise EVIDENCE_HASH_MISMATCH; the object never reaches FINALIZED."""
    actor = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            r = await _stage(s, actor, expected_hash="0" * 64)
        eid = r.aggregate_id
        async with s.begin():
            with pytest.raises(EvidenceHashMismatchError) as exc:
                await ev.finalize_evidence_upload(
                    s,
                    ev.FinalizeEvidenceUploadCommand(
                        idempotency_key=idem(), evidence_id=eid, expected_version=1,
                        content_base64=base64.b64encode(b"actual bytes").decode(), reason="x",
                    ),
                    actor,
                )
            assert exc.value.code == "EVIDENCE_HASH_MISMATCH"
    async with SessionLocal() as s:
        obj = await s.get(EvidenceObject, eid)
        assert obj.state == "QUARANTINE"
        ev_types = (await s.execute(
            select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id == eid)
        )).scalars().all()
        assert "EvidenceHashMismatch" in ev_types


async def test_stage_upload_denied_mime_and_size(db, seeded):
    """OBJ-FR-015/003: a MIME outside the allowlist and an oversize declared size are EVIDENCE_UPLOAD_DENIED."""
    actor = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(EvidenceUploadDeniedError):
                await _stage(s, actor, mime="application/x-msdownload")
        async with s.begin():
            with pytest.raises(EvidenceUploadDeniedError):
                await _stage(s, actor, size=999 * 1024 * 1024)


# --------------------------------------------------------------------------------------------------
# OBJ-FR-008 -- manifest
# --------------------------------------------------------------------------------------------------


async def _finalized(s, actor, data: bytes):
    r = await _stage(s, actor, expected_hash=sha256_bytes(data))
    await s.flush()
    r2 = await ev.finalize_evidence_upload(
        s,
        ev.FinalizeEvidenceUploadCommand(
            idempotency_key=idem(), evidence_id=r.aggregate_id, expected_version=1,
            content_base64=base64.b64encode(data).decode(), reason="done",
        ),
        actor,
    )
    return r.aggregate_id


async def test_manifest_create_and_supersede(db, seeded):
    """TC-072-*-01 / OBJ-FR-008: a manifest over finalized objects gets a canonical hash; a re-create
    supersedes the prior ACTIVE manifest and bumps manifest_version. A STAGED object cannot be
    manifested."""
    actor = seeded["users"]["qa.reviewer"].id
    owner_id = uuid.uuid4()
    async with SessionLocal() as s:
        async with s.begin():
            e1 = await _finalized(s, actor, b"one")
            e2 = await _finalized(s, actor, b"two")
        async with s.begin():
            m1 = await ev.create_evidence_manifest(
                s,
                ev.CreateEvidenceManifestCommand(
                    idempotency_key=idem(), owner_type="gxp_batch", owner_id=owner_id,
                    manifest_type="RELEASE", evidence_ids=[e1, e2], reason="release package",
                ),
                actor,
            )
        async with s.begin():
            staged = await _stage(s, actor)
            with pytest.raises(EvidenceNotFinalizedError):
                await ev.create_evidence_manifest(
                    s,
                    ev.CreateEvidenceManifestCommand(
                        idempotency_key=idem(), owner_type="gxp_batch", owner_id=owner_id,
                        manifest_type="RELEASE", evidence_ids=[staged.aggregate_id], reason="bad",
                    ),
                    actor,
                )
        async with s.begin():
            m2 = await ev.create_evidence_manifest(
                s,
                ev.CreateEvidenceManifestCommand(
                    idempotency_key=idem(), owner_type="gxp_batch", owner_id=owner_id,
                    manifest_type="RELEASE", evidence_ids=[e1], reason="corrected package",
                ),
                actor,
            )
    async with SessionLocal() as s:
        rows = (await s.execute(
            select(EvidenceManifest).where(EvidenceManifest.owner_id == owner_id).order_by(EvidenceManifest.manifest_version)
        )).scalars().all()
        assert [r.state for r in rows] == ["SUPERSEDED", "ACTIVE"]
        assert rows[0].manifest_version == 1 and rows[1].manifest_version == 2
        assert rows[0].canonical_hash != rows[1].canonical_hash


# --------------------------------------------------------------------------------------------------
# OBJ-FR-018 -- legal hold (signed, Document 106 row 142)
# --------------------------------------------------------------------------------------------------


async def test_legal_hold_requires_signature_then_applies(db, seeded):
    """TC-072-*-02 (missing signature) + TC-072-*-01: legal hold without step-up is MISSING_SIGNATURE;
    with a valid challenge + reauth it sets legal_hold=True, records a signature_id and emits
    EvidenceLegalHoldApplied."""
    actor = seeded["users"]["qa.reviewer"].id
    data = b"hold me"
    async with SessionLocal() as s:
        async with s.begin():
            eid = await _finalized(s, actor, data)

        async with s.begin():
            with pytest.raises(MissingSignatureError):
                await ev.apply_evidence_legal_hold(
                    s,
                    ev.ApplyEvidenceLegalHoldCommand(
                        idempotency_key=idem(), evidence_id=eid, expected_version=2,
                        hold_ref="LEGAL-2026-01", reason="litigation hold",
                    ),
                    actor,
                )

        async with s.begin():
            obj = await s.get(EvidenceObject, eid)
            challenge = await signature_service.create_challenge(
                s, user_id=actor, record_type="evidence_object", record_id=obj.id,
                record_version=obj.version, record_hash=evidence_record_hash(obj), meaning="Performed",
            )
            receipt = await ev.apply_evidence_legal_hold(
                s,
                ev.ApplyEvidenceLegalHoldCommand(
                    idempotency_key=idem(), evidence_id=eid, expected_version=obj.version,
                    hold_ref="LEGAL-2026-01", reason="litigation hold",
                    challenge_id=challenge.id, reauth_password=DEMO_PASSWORD,
                ),
                actor,
            )
    assert receipt.signature_id is not None
    async with SessionLocal() as s:
        obj = await s.get(EvidenceObject, eid)
        assert obj.legal_hold is True and obj.legal_hold_ref == "LEGAL-2026-01"
        assert "EvidenceLegalHoldApplied" in (await s.execute(
            select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id == eid)
        )).scalars().all()


# --------------------------------------------------------------------------------------------------
# OBJ-FR-016/023 -- integrity check ; OBJ-FR-018/019 -- purge
# --------------------------------------------------------------------------------------------------


async def test_integrity_check_flags_missing_object(db, seeded):
    """TC-072 'missing object' / OBJ-FR-023: when the backing object is gone, the check flips the row
    to MISSING, emits EvidenceMissing and raises."""
    actor = seeded["users"]["qa.reviewer"].id
    data = b"will vanish"
    async with SessionLocal() as s:
        async with s.begin():
            eid = await _finalized(s, actor, data)
        async with s.begin():
            rep = await ev.verify_evidence_integrity(
                s, ev.VerifyEvidenceIntegrityCommand(idempotency_key=idem(), evidence_ids=[eid], reason="scheduled"),
                actor,
            )
            assert rep["healthy"] is True

    # remove the backing file
    from app.modules.evidence.store import get_store
    st = get_store()
    obj_key = content_key(sha256_bytes(data))
    (st.base / "gxp-evidence" / obj_key).unlink()

    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(EvidenceMissingError):
                await ev.verify_evidence_integrity(
                    s, ev.VerifyEvidenceIntegrityCommand(idempotency_key=idem(), evidence_ids=[eid], reason="rescan"),
                    actor,
                )
    async with SessionLocal() as s:
        assert (await s.get(EvidenceObject, eid)).state == "MISSING"


async def test_purge_blocked_by_legal_hold_and_manifest(db, seeded):
    """TC-072 'legal hold blocks lifecycle deletion' / OBJ-FR-018/019: purge is blocked by an active
    legal hold and by an ACTIVE manifest still referencing the object; a clean object purges to
    PURGED (state change, never a delete)."""
    actor = seeded["users"]["qa.reviewer"].id
    async with SessionLocal() as s:
        async with s.begin():
            held = await _finalized(s, actor, b"held")
            manifested = await _finalized(s, actor, b"manifested")
            clean = await _finalized(s, actor, b"clean")
        async with s.begin():
            obj = await s.get(EvidenceObject, held)
            challenge = await signature_service.create_challenge(
                s, user_id=actor, record_type="evidence_object", record_id=obj.id,
                record_version=obj.version, record_hash=evidence_record_hash(obj), meaning="Performed",
            )
            await ev.apply_evidence_legal_hold(
                s,
                ev.ApplyEvidenceLegalHoldCommand(
                    idempotency_key=idem(), evidence_id=held, expected_version=obj.version,
                    hold_ref="H1", reason="hold", challenge_id=challenge.id, reauth_password=DEMO_PASSWORD,
                ),
                actor,
            )
            await ev.create_evidence_manifest(
                s,
                ev.CreateEvidenceManifestCommand(
                    idempotency_key=idem(), owner_type="gxp_batch", owner_id=uuid.uuid4(),
                    manifest_type="EXPORT", evidence_ids=[manifested], reason="export",
                ),
                actor,
            )
        async with s.begin():
            out = await ev.purge_expired_evidence(
                s,
                ev.PurgeExpiredEvidenceCommand(
                    idempotency_key=idem(), evidence_ids=[held, manifested, clean],
                    policy_version="RET-v1", reason="retention run",
                ),
                actor,
            )
    assert out["purged"] == [str(clean)]
    reasons = {b["evidence_id"]: b["reason"] for b in out["blocked"]}
    assert reasons[str(held)] == "legal_hold"
    assert reasons[str(manifested)] == "referenced_by_active_manifest"
    async with SessionLocal() as s:
        assert (await s.get(EvidenceObject, clean)).state == "PURGED"


# --------------------------------------------------------------------------------------------------
# API surface: RBAC + authorized download
# --------------------------------------------------------------------------------------------------


async def test_api_rbac_and_download(api, seeded):
    """TC-072-M01/M02 + OBJ-FR-011/012: unauthenticated -> 401; a user without the permission -> 403;
    an authorized user completes stage->finalize->download and a STAGED object is not downloadable."""
    body = {"idempotency_key": idem(), "owner_type": "gxp_batch", "owner_id": str(uuid.uuid4()),
            "filename": "r.pdf", "mime_type": "application/pdf", "reason": "x"}
    assert (await api.post("/evidence/v1/uploads", json=body)).status_code == 401

    op_tok = await login(api, "operator1")
    assert (await api.post("/evidence/v1/uploads", json=body, headers=auth_headers(op_tok))).status_code == 403

    tok = await login(api, "qa.reviewer")
    data = b"%PDF api roundtrip"
    body["expected_hash"] = sha256_bytes(data)
    staged = await api.post("/evidence/v1/uploads", json=body, headers=auth_headers(tok))
    assert staged.status_code == 200
    eid = staged.json()["aggregate_id"]

    dl_staged = await api.get(f"/evidence/v1/{eid}/download", headers=auth_headers(tok))
    assert dl_staged.status_code == 403  # not finalized

    fin = await api.post(
        f"/evidence/v1/{eid}:finalize",
        json={"idempotency_key": idem(), "evidence_id": eid, "expected_version": 1,
              "content_base64": base64.b64encode(data).decode(), "reason": "done"},
        headers=auth_headers(tok),
    )
    assert fin.status_code == 200

    dl = await api.get(f"/evidence/v1/{eid}/download", headers=auth_headers(tok))
    assert dl.status_code == 200
    assert dl.content == data
    assert dl.headers["x-evidence-content-hash"] == sha256_bytes(data)


async def test_generic_delete_denied_at_db_privilege_level(db, seeded):
    """OBJ-FR-019: the runtime app role has no DELETE on evidence.evidence_object -- refused by
    PostgreSQL, not just application code."""
    with pytest.raises(Exception) as exc:
        await db.execute(text("DELETE FROM evidence.evidence_object"))
        await db.commit()
    assert "permission denied" in str(exc.value).lower() or "InsufficientPrivilege" in type(exc.value).__name__
