"""`reportHealth()` -- Document 43 EDGE-FR-017 ("Gateway reports host, storage, buffer age/depth,
connector status, clock health, certificate expiry, CPU/memory and version") and section 11's declared
metrics.

Document 45 (SPEC-EDGE-003) BUF-FR-028 adds `rejected_count` (`edge_outbox_rejected`),
`delivery_attempts_total` (`edge_delivery_attempts_total`) and `sequence_gap_count`
(`edge_sequence_gap_total`) to the same snapshot. `edge_duplicate_acks_total` and
`edge_integrity_failures_total` are not yet emitted here -- recorded as a known limitation, not
fabricated: the former needs `apply_server_ack()` to distinguish a fresh ack from a duplicate one, and the
latter needs a scheduled `verify_buffer_integrity()` scan wired into the runtime loop, neither of which
this pass adds beyond the underlying functions themselves.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from runtime.contracts import ClockQuality
from runtime.forwarding.forwarder import disk_pressure_status
from runtime.forwarding.outbox import (
    delivery_attempts_total,
    oldest_unacked_age_seconds,
    pending_depth,
    rejected_count,
    sequence_gap_count,
)
from runtime.supervisor.supervisor import ConnectorSupervisor

GATEWAY_VERSION = "0.1.0"


@dataclass
class HealthSnapshot:
    gateway_version: str
    outbox_depth: int
    oldest_unacked_age_seconds: float | None
    disk_pressure_status: str
    connector_statuses: dict
    clock_quality: dict
    cert_expiry_days: int | None
    restart_count_total: int
    rejected_count: int
    delivery_attempts_total: int
    sequence_gap_total: int

    def to_dict(self) -> dict:
        return asdict(self)


def collect_health_snapshot(
    conn: sqlite3.Connection,
    db_path: str | Path,
    supervisor: ConnectorSupervisor,
    clock_quality: ClockQuality,
    cert_expiry_days: int | None,
) -> HealthSnapshot:
    connector_rows = conn.execute("SELECT connector_id, status, restart_count FROM edge_connector_state").fetchall()
    return HealthSnapshot(
        gateway_version=GATEWAY_VERSION,
        outbox_depth=pending_depth(conn),
        oldest_unacked_age_seconds=oldest_unacked_age_seconds(conn),
        disk_pressure_status=disk_pressure_status(db_path),
        connector_statuses={r["connector_id"]: r["status"] for r in connector_rows},
        clock_quality=clock_quality.model_dump(mode="json"),
        cert_expiry_days=cert_expiry_days,
        restart_count_total=sum(r["restart_count"] for r in connector_rows),
        rejected_count=rejected_count(conn),
        delivery_attempts_total=delivery_attempts_total(conn),
        sequence_gap_total=sequence_gap_count(conn),
    )
