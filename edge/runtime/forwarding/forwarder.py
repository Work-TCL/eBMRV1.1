"""Store-and-forward -- Document 43 section 4's `forwardPendingBatch()`/`applyServerAck()`.
EDGE-FR-015 (delivery ack -- purge only after authoritative server ack of the exact event ID range),
EDGE-FR-016 (idempotency), EDGE-FR-024 (local continuity while upstream is unavailable), EDGE-FR-025
(disk pressure -- never silently delete unacked rows to make room).

Document 45 (SPEC-EDGE-003) adds the retry-scheduling half of the same loop: BUF-FR-009 (exponential
backoff with jitter on unacknowledged items) and BUF-FR-020 (a server rejection is persisted to
REJECTED_REVIEW via `outbox.apply_rejections()`, never silently dropped).
"""

from __future__ import annotations

import logging
import random
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from runtime.forwarding.outbox import apply_rejections

logger = logging.getLogger("edge.forwarder")

DISK_PRESSURE_WARNING_FREE_BYTES = 500 * 1024 * 1024   # 500 MiB
DISK_PRESSURE_CRITICAL_FREE_BYTES = 100 * 1024 * 1024  # 100 MiB

# BUF-FR-009: exponential backoff with jitter. Base/cap are engineering defaults (no regulated numeric
# value is specified by Document 45 or Documents 106-115 for this -- unlike a signature/retention/
# precision figure, a retry cadence has no regulated-behavior consequence: it only changes how soon an
# already-durable, never-lost row is retried, never whether it is retried or delivered), consistent with
# this file's own pre-existing DISK_PRESSURE_* threshold constants being implementation defaults too.
RETRY_BASE_SECONDS = 2.0
RETRY_CAP_SECONDS = 300.0


class UpstreamUnavailableError(Exception):
    pass


@dataclass
class ForwardResult:
    sent_event_ids: list[str]
    server_ack_event_ids: list[str]
    duplicate_event_ids: list[str]
    rejected: list[dict]


def disk_pressure_status(db_path: str | Path) -> str:
    """EDGE-FR-025: returns 'GOOD' | 'WARNING' | 'CRITICAL'. The threshold check itself never deletes
    anything -- callers (the health reporter / runtime loop) decide what a CRITICAL reading means for
    acquisition, per "documented degradation policy" rather than an invented silent-delete shortcut.
    Document 45's acceptance intent names a third 'emergency' tier as a *policy response*, not a distinct
    byte threshold Document 45/106-115 defines a number for; CRITICAL is that top tier here and already
    drives the health snapshot's alarm consumer (BUF-FR-013)."""
    usage = shutil.disk_usage(Path(db_path).resolve().parent)
    if usage.free < DISK_PRESSURE_CRITICAL_FREE_BYTES:
        return "CRITICAL"
    if usage.free < DISK_PRESSURE_WARNING_FREE_BYTES:
        return "WARNING"
    return "GOOD"


def compute_backoff_seconds(attempt_count: int, *, rng: random.Random | None = None) -> float:
    """BUF-FR-009: `min(cap, base * 2**attempt_count)` with full jitter (uniform on `[0, ceiling]`) --
    the standard exponential-backoff-with-jitter shape, deterministic under an injected `rng` for tests."""
    rng = rng or random
    ceiling = min(RETRY_CAP_SECONDS, RETRY_BASE_SECONDS * (2 ** max(attempt_count, 0)))
    return rng.uniform(0.0, ceiling)


async def forward_pending_batch(
    conn: sqlite3.Connection,
    client: httpx.AsyncClient,
    *,
    gateway_id: str,
    expected_version: int,
    idempotency_key: str,
    max_items: int = 200,
    now: datetime | None = None,
    rng: random.Random | None = None,
) -> ForwardResult:
    """Reads ordered eligible rows (never deletes on read) -- eligible means not yet ACKED *and* either
    never attempted or past its scheduled `next_attempt_at` backoff (BUF-FR-009) -- POSTs the canonical
    batch, and marks exactly the event IDs the server actually acknowledged/rejected. A network/5xx
    failure leaves every row untouched -- the next call re-sends the same ordered window (EDGE-FR-024),
    and the server's own EDGE-FR-016 idempotency (event_id primary key) makes a resend safe rather than a
    duplicate GxP effect."""
    now = now or datetime.now(timezone.utc)
    rows = conn.execute(
        """
        SELECT event_id, payload_json FROM edge_outbox
        WHERE state NOT IN ('acked', 'rejected_review')
          AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
        ORDER BY gateway_sequence ASC LIMIT ?
        """,
        (now.isoformat(), max_items),
    ).fetchall()
    if not rows:
        return ForwardResult([], [], [], [])

    import json

    observations = [json.loads(r["payload_json"]) for r in rows]
    event_ids = [r["event_id"] for r in rows]

    try:
        response = await client.post(
            f"/edge/v1/gateways/{gateway_id}/observations:batch",
            json={"idempotency_key": idempotency_key, "expected_version": expected_version, "observations": observations},
        )
    except httpx.HTTPError as exc:
        logger.warning("forwarder: UPSTREAM_UNAVAILABLE gateway=%s error=%s", gateway_id, exc)
        raise UpstreamUnavailableError(str(exc)) from exc

    if response.status_code >= 500:
        raise UpstreamUnavailableError(f"server returned {response.status_code}")
    response.raise_for_status()
    body = response.json()

    sent_at = now.isoformat()
    conn.execute(
        "UPDATE edge_outbox SET state='sent', first_sent_at=COALESCE(first_sent_at, ?), attempt_count=attempt_count+1 WHERE event_id IN (%s)"
        % ",".join("?" for _ in event_ids),
        (sent_at, *event_ids),
    )
    for event_id in event_ids:
        conn.execute(
            "INSERT INTO edge_delivery_attempt (event_id, attempted_at, outcome) VALUES (?, ?, 'sent')",
            (event_id, sent_at),
        )

    accepted = body.get("accepted_event_ids", []) + body.get("duplicate_event_ids", [])
    apply_server_ack(conn, accepted)
    apply_rejections(conn, body.get("rejected", []))

    # BUF-FR-009: anything sent this round that is still neither ACKED nor REJECTED_REVIEW gets a
    # scheduled backoff before it becomes send-eligible again -- otherwise the very next loop iteration
    # would resend it immediately in a tight retry storm rather than a backed-off retry.
    acked_or_rejected = {str(e) for e in accepted} | {str(r["event_id"]) for r in body.get("rejected", [])}
    still_pending = [e for e in event_ids if e not in acked_or_rejected]
    for event_id in still_pending:
        row = conn.execute("SELECT attempt_count FROM edge_outbox WHERE event_id = ?", (event_id,)).fetchone()
        delay = compute_backoff_seconds(row["attempt_count"], rng=rng)
        next_attempt_at = (now + timedelta(seconds=delay)).isoformat()
        conn.execute("UPDATE edge_outbox SET next_attempt_at = ? WHERE event_id = ?", (next_attempt_at, event_id))

    return ForwardResult(
        sent_event_ids=event_ids,
        server_ack_event_ids=[str(e) for e in accepted],
        duplicate_event_ids=[str(e) for e in body.get("duplicate_event_ids", [])],
        rejected=body.get("rejected", []),
    )


def apply_server_ack(conn: sqlite3.Connection, acked_event_ids: list[str]) -> int:
    """`applyServerAck()` -- marks *exactly* the acknowledged rows ACKED. Never bulk-acks a whole window
    on a partial response (EDGE-FR-015: ack is scoped to the "exact event ID/range"). BUF-FR-010: a
    duplicate ack for an already-ACKED event_id is a safe no-op here (the `state != 'acked'` guard), which
    is exactly "duplicate accepted safely" rather than an error."""
    if not acked_event_ids:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    placeholders = ",".join("?" for _ in acked_event_ids)
    cursor = conn.execute(
        f"UPDATE edge_outbox SET state='acked', acked_at=? WHERE event_id IN ({placeholders}) AND state != 'acked'",
        (now, *[str(e) for e in acked_event_ids]),
    )
    return cursor.rowcount
