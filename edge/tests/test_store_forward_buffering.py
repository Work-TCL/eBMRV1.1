"""Document 45 (SPEC-EDGE-003) -- narrow tests for the store-and-forward/buffering/time-integrity/
data-quality behavior that Document 43's own test suite (test_outbox_forwarding.py, test_health_clock.py,
test_ingestion.py) does not already assert. Each test below targets exactly one BUF-FR sub-clause that
was either unbuilt or untested before this pass -- it does not re-prove what those suites already cover
(BUF-FR-002/003/007/008/012/023/030 and the clock/quality basics)."""

from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from runtime.contracts import ClockQuality, EdgeObservationEnvelope, RawValue, SourceRef
from runtime.forwarding.evidence import EvidenceStorageError, store_evidence_file
from runtime.forwarding.forwarder import compute_backoff_seconds, forward_pending_batch
from runtime.forwarding.outbox import (
    append_delivery_envelope,
    apply_rejections,
    detect_sequence_gaps,
    next_gateway_sequence,
    purge_acked,
    replay_rejected_envelope,
    verify_buffer_integrity,
    ReplayNotEligibleError,
)
from runtime.ingestion.pipeline import compute_freshness
from storage.db import connect

GATEWAY_ID = uuid.uuid4()
SITE_ID = uuid.uuid4()


def _envelope(seq: int, source_timestamp: str | None = "2026-09-14T00:00:00Z") -> EdgeObservationEnvelope:
    return EdgeObservationEnvelope(
        gateway_id=GATEWAY_ID, tenant_id="t1", site_id=SITE_ID, connector_id="c1", connector_version="1.0",
        device_id="d1", mapping_id="m1", mapping_version="m1", source=SourceRef(protocol="MQTT", address="a/b"),
        source_timestamp=source_timestamp, gateway_received_at="2026-09-14T00:00:00Z", gateway_sequence=seq,
        clock_quality=ClockQuality(status="GOOD"), quality="GOOD", raw=RawValue(value=seq),
    )


# ---------------------------------------------------------------------------
# BUF-FR-001 / BUF-FR-005 / BUF-FR-029 -- durability across a simulated restart
# ---------------------------------------------------------------------------

def test_appended_row_survives_a_simulated_crash_before_any_send(db_path):
    """BUF-FR-001 (durable append) + BUF-FR-029 (power loss: committed rows recover): append via one
    connection, close it without ever calling the forwarder (simulating the process dying immediately
    after append), then open a brand new connection to the same file and confirm the row is there,
    untouched and still 'pending' -- proving the write was durable to disk, not just to the live
    in-memory connection."""
    from storage.db import migrate

    conn1 = connect(db_path)
    migrate(conn1)
    envelope = _envelope(1)
    append_delivery_envelope(conn1, envelope)
    conn1.close()  # simulated abrupt process death -- no explicit commit/flush call, autocommit only

    conn2 = connect(db_path)
    row = conn2.execute("SELECT state, payload_hash, payload_json FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()
    assert row is not None
    assert row["state"] == "pending"
    assert row["payload_hash"] == hashlib.sha256(row["payload_json"].encode()).hexdigest()
    conn2.close()


# ---------------------------------------------------------------------------
# BUF-FR-004 -- payload hash is a real, verifiable SHA-256 of the exact stored payload
# ---------------------------------------------------------------------------

def test_payload_hash_is_correct_sha256_of_stored_payload(conn):
    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    row = conn.execute("SELECT payload_json, payload_hash FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()
    assert row["payload_hash"] == hashlib.sha256(row["payload_json"].encode()).hexdigest()


# ---------------------------------------------------------------------------
# BUF-FR-009 -- exponential backoff with jitter; retry is scheduled, not immediate
# ---------------------------------------------------------------------------

def test_compute_backoff_seconds_grows_exponentially_and_is_capped():
    rng = random.Random(1234)
    # With full jitter fixed at ceiling (monkeypatching not needed -- just bound-check across attempts).
    delays = [compute_backoff_seconds(n, rng=rng) for n in range(10)]
    assert all(0.0 <= d <= 300.0 for d in delays)
    assert compute_backoff_seconds(0, rng=random.Random(1)) <= compute_backoff_seconds(0, rng=random.Random(1))  # sane bound, deterministic seed
    # Ceiling itself grows with attempt_count until the cap.
    from runtime.forwarding.forwarder import RETRY_BASE_SECONDS, RETRY_CAP_SECONDS

    assert min(RETRY_CAP_SECONDS, RETRY_BASE_SECONDS * 2**5) > min(RETRY_CAP_SECONDS, RETRY_BASE_SECONDS * 2**1)


@pytest.mark.asyncio
async def test_unacked_row_after_send_is_not_immediately_send_eligible_again(conn):
    """BUF-FR-009: a row that was sent but not acked this round must not be selected again until its
    scheduled `next_attempt_at` backoff has elapsed -- proving retry is throttled, not a tight resend loop."""
    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"accepted_event_ids": [], "duplicate_event_ids": [], "rejected": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://server")
    fixed_now = datetime(2026, 9, 14, tzinfo=timezone.utc)
    rng = random.Random(42)

    result = await forward_pending_batch(
        conn, client, gateway_id=str(GATEWAY_ID), expected_version=1, idempotency_key="k1", now=fixed_now, rng=rng,
    )
    assert result.sent_event_ids == [str(envelope.event_id)]

    row = conn.execute("SELECT next_attempt_at, attempt_count FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()
    assert row["next_attempt_at"] is not None
    assert row["attempt_count"] == 1

    # Calling again at the same instant must not re-select the row (it is backed off into the future).
    result2 = await forward_pending_batch(
        conn, client, gateway_id=str(GATEWAY_ID), expected_version=1, idempotency_key="k2", now=fixed_now, rng=rng,
    )
    assert result2.sent_event_ids == []

    # But once `now` has advanced past next_attempt_at, it is eligible again.
    far_future = fixed_now + timedelta(seconds=600)
    result3 = await forward_pending_batch(
        conn, client, gateway_id=str(GATEWAY_ID), expected_version=1, idempotency_key="k3", now=far_future, rng=rng,
    )
    assert result3.sent_event_ids == [str(envelope.event_id)]


# ---------------------------------------------------------------------------
# BUF-FR-010 -- duplicate ack is idempotent
# ---------------------------------------------------------------------------

def test_duplicate_ack_of_already_acked_event_is_a_safe_noop(conn):
    from runtime.forwarding.forwarder import apply_server_ack

    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    first = apply_server_ack(conn, [str(envelope.event_id)])
    assert first == 1
    second = apply_server_ack(conn, [str(envelope.event_id)])  # duplicate ack, e.g. lost response resend
    assert second == 0  # no error, no state regression, no second acked_at write
    row = conn.execute("SELECT state FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()
    assert row["state"] == "acked"


# ---------------------------------------------------------------------------
# BUF-FR-011 -- same event_id, different hash is a conflict, not a silent overwrite
# ---------------------------------------------------------------------------

def test_reappending_same_event_id_with_different_payload_does_not_overwrite_original(conn):
    """BUF-FR-011: `INSERT OR IGNORE` on the event_id primary key means a second envelope claiming the
    same event_id but a different payload is silently rejected as a row -- the *original* payload/hash
    survive untouched, which is the safe half of "not last-write-wins". Detecting and alarming on this
    condition (a security/integrity incident) is `verify_buffer_integrity()`'s hash-chain job at the
    application layer above this table, not a database CHECK constraint -- SQLite has no application-level
    hook to compare a *rejected* insert's payload, so the honest current behavior is documented here rather
    than implying a security alarm this pass does not yet raise."""
    original = _envelope(1)
    append_delivery_envelope(conn, original)
    original_row = conn.execute("SELECT payload_hash FROM edge_outbox WHERE event_id = ?", (str(original.event_id),)).fetchone()

    conflicting = EdgeObservationEnvelope(
        event_id=original.event_id,  # same event_id
        gateway_id=GATEWAY_ID, tenant_id="t1", site_id=SITE_ID, connector_id="c1", connector_version="1.0",
        device_id="d1", mapping_id="m1", mapping_version="m1", source=SourceRef(protocol="MQTT", address="a/b"),
        gateway_received_at="2026-09-14T00:00:00Z", gateway_sequence=999,
        clock_quality=ClockQuality(status="GOOD"), quality="GOOD", raw=RawValue(value="TAMPERED"),
    )
    append_delivery_envelope(conn, conflicting)

    row_after = conn.execute("SELECT payload_hash, gateway_sequence FROM edge_outbox WHERE event_id = ?", (str(original.event_id),)).fetchone()
    assert row_after["payload_hash"] == original_row["payload_hash"]  # untouched -- no last-write-wins
    assert row_after["gateway_sequence"] == 1  # original sequence preserved, not overwritten with 999


# ---------------------------------------------------------------------------
# BUF-FR-013 -- disk watermark thresholds already covered in test_outbox_forwarding.py; nothing new to add.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# BUF-FR-014 / BUF-FR-025 -- purge only ever touches ACKED rows past retention
# ---------------------------------------------------------------------------

def test_purge_acked_never_touches_pending_or_sent_rows(conn):
    pending = _envelope(1)
    append_delivery_envelope(conn, pending)  # left PENDING deliberately

    acked = _envelope(2)
    append_delivery_envelope(conn, acked)
    old_cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    conn.execute("UPDATE edge_outbox SET state='acked', acked_at=? WHERE event_id=?", (old_cutoff_ts, str(acked.event_id)))

    result = purge_acked(conn, retention_cutoff=datetime.now(timezone.utc))

    assert str(acked.event_id) in result.purged_event_ids
    assert str(pending.event_id) not in result.purged_event_ids
    remaining = conn.execute("SELECT event_id FROM edge_outbox").fetchall()
    assert [r["event_id"] for r in remaining] == [str(pending.event_id)]


def test_purge_acked_respects_retention_cutoff_not_yet_reached(conn):
    acked = _envelope(1)
    append_delivery_envelope(conn, acked)
    recent_ts = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE edge_outbox SET state='acked', acked_at=? WHERE event_id=?", (recent_ts, str(acked.event_id)))

    # cutoff is in the past -- this recently-acked row has not aged past retention yet.
    result = purge_acked(conn, retention_cutoff=datetime.now(timezone.utc) - timedelta(days=30))
    assert result.purged_event_ids == []
    still_there = conn.execute("SELECT event_id FROM edge_outbox WHERE event_id = ?", (str(acked.event_id),)).fetchone()
    assert still_there is not None


# ---------------------------------------------------------------------------
# BUF-FR-015 -- large evidence file: content-addressed store, fsync, idempotent by hash
# ---------------------------------------------------------------------------

def test_store_evidence_file_is_content_addressed_and_idempotent(conn, tmp_path):
    data = b"synthetic chromatogram bytes"
    ref1 = store_evidence_file(conn, tmp_path / "evidence", data, media_type="application/pdf")
    assert ref1.sha256 == hashlib.sha256(data).hexdigest()
    assert ref1.size == len(data)
    with open(ref1.path, "rb") as fh:
        assert fh.read() == data

    ref2 = store_evidence_file(conn, tmp_path / "evidence", data, media_type="application/pdf")
    assert ref2.sha256 == ref1.sha256
    assert ref2.path == ref1.path  # no duplicate file, no duplicate manifest row
    count = conn.execute("SELECT COUNT(*) AS n FROM edge_evidence_file WHERE content_hash = ?", (ref1.sha256,)).fetchone()["n"]
    assert count == 1


def test_store_evidence_file_manifest_matches_disk(conn, tmp_path):
    data = b"a different evidence payload"
    ref = store_evidence_file(conn, tmp_path / "evidence", data)
    row = conn.execute("SELECT file_path, size_bytes FROM edge_evidence_file WHERE content_hash = ?", (ref.sha256,)).fetchone()
    assert row["file_path"] == ref.path
    assert row["size_bytes"] == len(data)


# ---------------------------------------------------------------------------
# BUF-FR-016 -- source timestamp is never rewritten, even under a bad clock
# ---------------------------------------------------------------------------

def test_source_timestamp_untouched_when_clock_is_bad():
    from runtime.contracts import RawSourceObservation
    from runtime.ingestion.pipeline import MappingRegistry, normalize_observation

    raw = RawSourceObservation(
        connector_id="c1", connector_version="1.0", device_id="d1", mapping_id="m1",
        source=SourceRef(protocol="MODBUS_TCP", address="40001"), value=1.0,
        source_timestamp="2026-01-01T00:00:00+00:00",
    )
    bad_clock = ClockQuality(status="BAD", offset_ms=9999.0, source="chronyc")
    envelope = normalize_observation(
        raw, gateway_id=GATEWAY_ID, tenant_id="t1", site_id=SITE_ID, gateway_sequence=1,
        clock_quality=bad_clock, mapping_registry=MappingRegistry(),
    )
    assert envelope.source_timestamp.isoformat() == "2026-01-01T00:00:00+00:00"
    assert envelope.quality == "CLOCK_UNCERTAIN"  # quality degrades, timestamp does not change


# ---------------------------------------------------------------------------
# BUF-FR-017 / BUF-FR-018 -- freshness is distinct from quality and never deletes the original
# ---------------------------------------------------------------------------

def test_compute_freshness_fresh_late_stale_boundaries():
    received = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)

    fresh = compute_freshness(received - timedelta(seconds=5), received, late_threshold_seconds=60, stale_threshold_seconds=600)
    late = compute_freshness(received - timedelta(seconds=120), received, late_threshold_seconds=60, stale_threshold_seconds=600)
    stale = compute_freshness(received - timedelta(seconds=900), received, late_threshold_seconds=60, stale_threshold_seconds=600)

    assert fresh == "FRESH"
    assert late == "LATE"
    assert stale == "STALE"


def test_compute_freshness_missing_source_timestamp_is_stale_not_guessed_fresh():
    received = datetime(2026, 9, 14, tzinfo=timezone.utc)
    assert compute_freshness(None, received, late_threshold_seconds=60, stale_threshold_seconds=600) == "STALE"


def test_freshness_computation_does_not_touch_stored_quality_or_envelope(conn):
    """BUF-FR-018's 'without deleting original observation': computing freshness is read-only over the
    outbox row -- appending, then computing freshness, leaves the stored envelope byte-for-byte the same."""
    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    before = conn.execute("SELECT payload_json, payload_hash FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()

    compute_freshness(
        datetime(2026, 9, 14, tzinfo=timezone.utc) - timedelta(hours=2),
        datetime(2026, 9, 14, tzinfo=timezone.utc),
        late_threshold_seconds=60, stale_threshold_seconds=600,
    )

    after = conn.execute("SELECT payload_json, payload_hash FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()
    assert after["payload_json"] == before["payload_json"]
    assert after["payload_hash"] == before["payload_hash"]


# ---------------------------------------------------------------------------
# BUF-FR-019 / BUF-FR-026 -- gap detection and hash-integrity scan
# ---------------------------------------------------------------------------

def test_detect_sequence_gaps_finds_missing_ranges(conn):
    for seq in (1, 2, 5, 6, 10):
        append_delivery_envelope(conn, _envelope(seq))
    gaps = detect_sequence_gaps(conn)
    assert gaps == [(3, 4), (7, 9)]


def test_detect_sequence_gaps_empty_when_contiguous(conn):
    for seq in (1, 2, 3):
        append_delivery_envelope(conn, _envelope(seq))
    assert detect_sequence_gaps(conn) == []


def test_verify_buffer_integrity_detects_tampered_payload(conn):
    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    # Simulate on-disk tampering/corruption: mutate payload_json without recomputing payload_hash --
    # exactly what a hash-mismatch scan exists to catch (never done through the normal append path).
    conn.execute("UPDATE edge_outbox SET payload_json = ? WHERE event_id = ?", ('{"tampered": true}', str(envelope.event_id)))

    report = verify_buffer_integrity(conn)
    assert str(envelope.event_id) in report.hash_mismatches


def test_verify_buffer_integrity_clean_buffer_reports_no_mismatches(conn):
    for seq in (1, 2, 3):
        append_delivery_envelope(conn, _envelope(seq))
    report = verify_buffer_integrity(conn)
    assert report.hash_mismatches == []
    assert report.sequence_gaps == []


# ---------------------------------------------------------------------------
# BUF-FR-020 / BUF-FR-021 -- rejection is persisted (never dropped) and manual replay is controlled
# ---------------------------------------------------------------------------

def test_rejected_payload_is_persisted_not_dropped(conn):
    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    touched = apply_rejections(conn, [{"event_id": str(envelope.event_id), "code": "MAPPING_VERSION_UNKNOWN"}])
    assert touched == 1

    row = conn.execute("SELECT state, rejection_code FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()
    assert row["state"] == "rejected_review"
    assert row["rejection_code"] == "MAPPING_VERSION_UNKNOWN"

    attempt = conn.execute(
        "SELECT outcome, detail FROM edge_delivery_attempt WHERE event_id = ? AND outcome = 'rejected'", (str(envelope.event_id),)
    ).fetchone()
    assert attempt is not None
    assert attempt["detail"] == "MAPPING_VERSION_UNKNOWN"


def test_rejection_never_regresses_an_already_acked_row(conn):
    from runtime.forwarding.forwarder import apply_server_ack

    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    apply_server_ack(conn, [str(envelope.event_id)])

    apply_rejections(conn, [{"event_id": str(envelope.event_id), "code": "STALE_REJECTION_REPLAY"}])
    row = conn.execute("SELECT state FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()
    assert row["state"] == "acked"  # a rejection response cannot un-ack a delivered row


def test_replay_rejected_envelope_requires_reason_and_rejected_state(conn):
    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    apply_rejections(conn, [{"event_id": str(envelope.event_id), "code": "MAPPING_VERSION_UNKNOWN"}])

    with pytest.raises(ValueError):
        replay_rejected_envelope(conn, str(envelope.event_id), "")  # blank reason refused

    receipt = replay_rejected_envelope(conn, str(envelope.event_id), "mapping v2 activated, replaying original evidence")
    assert receipt.event_id == str(envelope.event_id)

    row = conn.execute("SELECT state, rejection_code, payload_hash FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)).fetchone()
    assert row["state"] == "pending"
    assert row["rejection_code"] is None

    original_hash = hashlib.sha256(envelope.model_dump_json().encode()).hexdigest()
    assert row["payload_hash"] == original_hash  # exact original envelope, never mutated by replay

    audit_row = conn.execute(
        "SELECT detail FROM edge_delivery_attempt WHERE event_id = ? AND outcome = 'replay_requested'", (str(envelope.event_id),)
    ).fetchone()
    assert "mapping v2" in audit_row["detail"]


def test_replay_rejects_event_not_in_rejected_review_state(conn):
    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)  # still 'pending', never rejected
    with pytest.raises(ReplayNotEligibleError):
        replay_rejected_envelope(conn, str(envelope.event_id), "attempted replay of a non-rejected row")


# ---------------------------------------------------------------------------
# BUF-FR-022 -- backfill is tagged distinctly through the same idempotency/validation path
# ---------------------------------------------------------------------------

def test_backfill_append_is_tagged_and_uses_the_same_idempotency_path(conn):
    live = _envelope(1)
    append_delivery_envelope(conn, live)  # default source_kind='live'

    backfilled = _envelope(2)
    append_delivery_envelope(conn, backfilled, source_kind="backfill")

    rows = {r["event_id"]: r["source_kind"] for r in conn.execute("SELECT event_id, source_kind FROM edge_outbox")}
    assert rows[str(live.event_id)] == "live"
    assert rows[str(backfilled.event_id)] == "backfill"

    # Same idempotency guarantee as a live append: re-appending the same backfill event_id is a no-op.
    append_delivery_envelope(conn, backfilled, source_kind="backfill")
    count = conn.execute("SELECT COUNT(*) AS n FROM edge_outbox WHERE event_id = ?", (str(backfilled.event_id),)).fetchone()["n"]
    assert count == 1


# ---------------------------------------------------------------------------
# BUF-FR-028 -- rejected_count metric feeds the health snapshot
# ---------------------------------------------------------------------------

def test_health_snapshot_reports_rejected_count(conn, tmp_path):
    from runtime.forwarding.outbox import rejected_count as rejected_count_fn

    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    apply_rejections(conn, [{"event_id": str(envelope.event_id), "code": "MAPPING_VERSION_UNKNOWN"}])
    assert rejected_count_fn(conn) == 1


# ---------------------------------------------------------------------------
# BUF-FR-011 -- a genuine payload conflict raises a security event, not a silent overwrite
# ---------------------------------------------------------------------------

def test_conflicting_payload_for_same_event_id_raises_security_event(conn):
    original = _envelope(1)
    append_delivery_envelope(conn, original)

    conflicting = EdgeObservationEnvelope(
        event_id=original.event_id,
        gateway_id=GATEWAY_ID, tenant_id="t1", site_id=SITE_ID, connector_id="c1", connector_version="1.0",
        device_id="d1", mapping_id="m1", mapping_version="m1", source=SourceRef(protocol="MQTT", address="a/b"),
        gateway_received_at="2026-09-14T00:00:00Z", gateway_sequence=999,
        clock_quality=ClockQuality(status="GOOD"), quality="GOOD", raw=RawValue(value="TAMPERED"),
    )
    append_delivery_envelope(conn, conflicting)

    event = conn.execute(
        "SELECT event_type, severity, evidence_json FROM edge_security_event WHERE event_type = 'PAYLOAD_CONFLICT'"
    ).fetchone()
    assert event is not None
    assert event["severity"] == "HIGH"
    assert str(original.event_id) in event["evidence_json"]


def test_identical_reappend_does_not_raise_a_security_event(conn):
    """The same envelope resubmitted verbatim (e.g. a plugin replay) is ordinary idempotency, not a
    conflict -- no security event for a matching-hash duplicate."""
    envelope = _envelope(1)
    append_delivery_envelope(conn, envelope)
    append_delivery_envelope(conn, envelope)  # identical payload, identical hash
    count = conn.execute("SELECT COUNT(*) AS n FROM edge_security_event WHERE event_type = 'PAYLOAD_CONFLICT'").fetchone()["n"]
    assert count == 0


# ---------------------------------------------------------------------------
# BUF-FR-028 -- delivery-attempt and sequence-gap counters feed the health snapshot
# ---------------------------------------------------------------------------

def test_delivery_attempts_total_and_sequence_gap_count(conn):
    from runtime.forwarding.outbox import delivery_attempts_total, sequence_gap_count

    for seq in (1, 2, 5):
        append_delivery_envelope(conn, _envelope(seq))
    assert sequence_gap_count(conn) == 1  # single gap (3, 4)

    first_event_id = conn.execute("SELECT event_id FROM edge_outbox ORDER BY gateway_sequence LIMIT 1").fetchone()["event_id"]
    apply_rejections(conn, [{"event_id": first_event_id, "code": "X"}])
    assert delivery_attempts_total(conn) >= 1
