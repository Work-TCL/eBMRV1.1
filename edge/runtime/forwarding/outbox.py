"""Local durable outbox -- Document 43 EDGE-FR-014 (local buffering before network transmission),
EDGE-FR-016 (idempotency via event_id + gateway_sequence), section 7's `edge_outbox` table, and section
4's `appendDeliveryEnvelope()`.

Document 45 (SPEC-EDGE-003) extends this same module with the rest of the store-and-forward lifecycle
that 0001_initial.sql's reduced (pending|sent|acked) state set left open: rejection retention
(BUF-FR-006/020), conflict detection (BUF-FR-011), retention-governed purge that never touches an unacked
row (BUF-FR-014/025), a periodic integrity/gap scan (BUF-FR-019/026), controlled manual replay
(BUF-FR-021), backfill tagging (BUF-FR-022) and the remaining outbox-side metrics (BUF-FR-028). All of it
lives in this file rather than a new module -- it is the same table, the same state machine, and the same
durability guarantees `append_delivery_envelope()` already established.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from runtime.contracts import EdgeObservationEnvelope


class BufferedEnvelopeRef:
    def __init__(self, event_id: str, sequence: int) -> None:
        self.event_id = event_id
        self.sequence = sequence


class ReplayNotEligibleError(Exception):
    """Raised when replay is attempted on an event_id that is not in REJECTED_REVIEW (BUF-FR-021: replay
    is a controlled recovery path for rejected evidence, not a generic resend button)."""


def next_gateway_sequence(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(gateway_sequence), 0) + 1 AS next_seq FROM edge_outbox").fetchone()
    return int(row["next_seq"])


def _payload_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode()).hexdigest()


def append_delivery_envelope(
    conn: sqlite3.Connection, envelope: EdgeObservationEnvelope, *, source_kind: str = "live"
) -> BufferedEnvelopeRef:
    """Transactional append with a unique, gateway-assigned sequence and a payload hash (section 7's
    `edge_outbox.payload_hash`) -- `event_id` is the primary key, so a duplicate append (e.g. a plugin
    replaying the same reading) is a no-op via `INSERT OR IGNORE`, not a duplicate row.

    `source_kind` defaults to 'live' -- the ordinary acquisition path. BUF-FR-022 (Backfill): a bulk
    historical import calls this with `source_kind='backfill'` so the row is forwarded/idempotency-checked
    through the exact same path but remains distinguishable for reconciliation/reporting, never silently
    mixed into live-acquisition counts.

    BUF-FR-011 (Conflict handling): if `event_id` already exists with a *different* payload hash, the
    `INSERT OR IGNORE` leaves the original row untouched (never last-write-wins) and this function records
    a `PAYLOAD_CONFLICT` row in `edge_security_event` -- Document 45 section 8 calls this "a security/
    data-integrity incident, not last-write-wins", so it is surfaced through the same security-event table
    `runtime/security/command_channel.py`'s denial path already uses, not silently absorbed."""
    payload_json = envelope.model_dump_json()
    payload_hash = _payload_hash(payload_json)
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO edge_outbox
            (event_id, gateway_sequence, schema_version, payload_json, payload_hash, state, created_at, source_kind)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            str(envelope.event_id), envelope.gateway_sequence, envelope.schema_version,
            payload_json, payload_hash, datetime.now(timezone.utc).isoformat(), source_kind,
        ),
    )
    if cursor.rowcount == 0:
        existing = conn.execute(
            "SELECT payload_hash FROM edge_outbox WHERE event_id = ?", (str(envelope.event_id),)
        ).fetchone()
        if existing is not None and existing["payload_hash"] != payload_hash:
            conn.execute(
                "INSERT INTO edge_security_event (occurred_at, event_type, severity, evidence_json) VALUES (?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(), "PAYLOAD_CONFLICT", "HIGH",
                    f'{{"event_id": "{envelope.event_id}", "existing_hash": "{existing["payload_hash"]}", "incoming_hash": "{payload_hash}"}}',
                ),
            )
    return BufferedEnvelopeRef(event_id=str(envelope.event_id), sequence=envelope.gateway_sequence)


def pending_depth(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM edge_outbox WHERE state != 'acked'").fetchone()
    return int(row["n"])


def oldest_unacked_age_seconds(conn: sqlite3.Connection) -> float | None:
    row = conn.execute(
        "SELECT created_at FROM edge_outbox WHERE state != 'acked' ORDER BY gateway_sequence ASC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    created = datetime.fromisoformat(row["created_at"])
    return (datetime.now(timezone.utc) - created).total_seconds()


def rejected_count(conn: sqlite3.Connection) -> int:
    """BUF-FR-028 (Metrics: `edge_outbox_rejected`)."""
    row = conn.execute("SELECT COUNT(*) AS n FROM edge_outbox WHERE state = 'rejected_review'").fetchone()
    return int(row["n"])


def delivery_attempts_total(conn: sqlite3.Connection) -> int:
    """BUF-FR-028 (Metrics: `edge_delivery_attempts_total`)."""
    row = conn.execute("SELECT COUNT(*) AS n FROM edge_delivery_attempt").fetchone()
    return int(row["n"])


def sequence_gap_count(conn: sqlite3.Connection) -> int:
    """BUF-FR-028 (Metrics: `edge_sequence_gap_total`) -- count of gap *ranges*, not missing sequence
    numbers, matching `detect_sequence_gaps()`'s own unit."""
    return len(detect_sequence_gaps(conn))


def apply_rejections(conn: sqlite3.Connection, rejected: list[dict]) -> int:
    """`applyAck()`'s rejection half. BUF-FR-020: a server-side schema/mapping rejection moves the row to
    REJECTED_REVIEW with its code recorded -- it is never left as if still in flight, and never deleted.
    Only rows the server actually named are touched; an already-ACKED row cannot be rejected retroactively
    (a stale/duplicate rejection response can never regress a delivered row)."""
    if not rejected:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    touched = 0
    for item in rejected:
        cursor = conn.execute(
            """
            UPDATE edge_outbox SET state = 'rejected_review', rejection_code = ?
            WHERE event_id = ? AND state != 'acked'
            """,
            (item.get("code"), str(item["event_id"])),
        )
        conn.execute(
            "INSERT INTO edge_delivery_attempt (event_id, attempted_at, outcome, detail) VALUES (?, ?, 'rejected', ?)",
            (str(item["event_id"]), now, item.get("code")),
        )
        touched += cursor.rowcount
    return touched


@dataclass
class ReplayReceipt:
    event_id: str
    reason: str
    replayed_at: str


def replay_rejected_envelope(conn: sqlite3.Connection, event_id: str, reason: str) -> ReplayReceipt:
    """`replayRejected()`. BUF-FR-021: an authorized admin can replay the *exact original* envelope after
    resolving the config/mapping problem that caused the rejection. This function does not mutate
    `payload_json`/`payload_hash` -- the original evidence is untouched -- it only resets delivery state
    so the unmodified envelope is picked up by the next `forward_pending_batch()` call, and it requires
    and records a non-empty reason exactly like every other controlled correction in this codebase
    (AUD-FR-008). Caller authorization (who may invoke this) is enforced by whichever privileged interface
    calls it -- same boundary as `command_channel.py`'s allowlist gate -- this function is the audited
    mechanism, not the authorization decision itself."""
    if not reason or not reason.strip():
        raise ValueError("replay reason is required and cannot be blank (AUD-FR-008)")

    row = conn.execute("SELECT state FROM edge_outbox WHERE event_id = ?", (event_id,)).fetchone()
    if row is None:
        raise ReplayNotEligibleError(f"no such event_id={event_id!r}")
    if row["state"] != "rejected_review":
        raise ReplayNotEligibleError(f"event_id={event_id!r} is state={row['state']!r}, not rejected_review")

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE edge_outbox
        SET state = 'pending', rejection_code = NULL, next_attempt_at = NULL
        WHERE event_id = ?
        """,
        (event_id,),
    )
    conn.execute(
        "INSERT INTO edge_delivery_attempt (event_id, attempted_at, outcome, detail) VALUES (?, ?, 'replay_requested', ?)",
        (event_id, now, reason),
    )
    return ReplayReceipt(event_id=event_id, reason=reason, replayed_at=now)


@dataclass
class PurgeResult:
    purged_event_ids: list[str]


def purge_acked(conn: sqlite3.Connection, retention_cutoff: datetime, max_rows: int = 1000) -> PurgeResult:
    """`purgeAcked()`. BUF-FR-014/BUF-FR-025: only rows already ACKED *and* past the configured retention
    cutoff are ever eligible -- the WHERE clause makes it structurally impossible for this function to
    delete a pending/sent/rejected_review row, so there is no separate "PURGE_BLOCKED_UNACKED" error path
    to invent: an unacked row is simply never selected, by construction, not by a runtime check that could
    be bypassed."""
    rows = conn.execute(
        "SELECT event_id FROM edge_outbox WHERE state = 'acked' AND acked_at < ? ORDER BY gateway_sequence ASC LIMIT ?",
        (retention_cutoff.isoformat(), max_rows),
    ).fetchall()
    event_ids = [r["event_id"] for r in rows]
    if event_ids:
        placeholders = ",".join("?" for _ in event_ids)
        conn.execute(f"DELETE FROM edge_outbox WHERE event_id IN ({placeholders})", event_ids)
    return PurgeResult(purged_event_ids=event_ids)


@dataclass
class IntegrityReport:
    hash_mismatches: list[str]
    sequence_gaps: list[tuple[int, int]]


def detect_sequence_gaps(conn: sqlite3.Connection) -> list[tuple[int, int]]:
    """BUF-FR-019: reports missing `gateway_sequence` ranges as (gap_start, gap_end) inclusive pairs --
    e.g. sequences 1,2,5,6 report a single gap (3, 4). Never renumbers/backfills a placeholder row; this
    is read-only detection for an admin/health consumer to act on."""
    rows = conn.execute("SELECT gateway_sequence FROM edge_outbox ORDER BY gateway_sequence ASC").fetchall()
    sequences = [r["gateway_sequence"] for r in rows]
    gaps: list[tuple[int, int]] = []
    for prev, curr in zip(sequences, sequences[1:]):
        if curr - prev > 1:
            gaps.append((prev + 1, curr - 1))
    return gaps


def verify_buffer_integrity(conn: sqlite3.Connection) -> IntegrityReport:
    """`verifyBufferIntegrity()`. BUF-FR-026: recomputes SHA-256 over each stored `payload_json` and
    compares it to the `payload_hash` recorded at append time -- any row where the two now disagree (e.g.
    on-disk tampering or corruption) is reported, never silently trusted or auto-repaired. Combines with
    `detect_sequence_gaps()` for BUF-FR-019's completeness half of the same scheduled scan."""
    rows = conn.execute("SELECT event_id, payload_json, payload_hash FROM edge_outbox").fetchall()
    mismatches = [r["event_id"] for r in rows if _payload_hash(r["payload_json"]) != r["payload_hash"]]
    return IntegrityReport(hash_mismatches=mismatches, sequence_gaps=detect_sequence_gaps(conn))
