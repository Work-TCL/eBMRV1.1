"""`activateRuntimeConfig()` -- Document 43 section 4. EDGE-FR-006: "New configuration activates
atomically; on failure gateway retains prior valid configuration and reports failure."
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from runtime.config.loader import ValidatedGatewayConfig
from runtime.ingestion.pipeline import MappingRegistry, UnitConversionRule
from runtime.supervisor.supervisor import ConnectorSupervisor

logger = logging.getLogger("edge.config.activation")


class ActivationFailedError(Exception):
    pass


@dataclass
class ActivationResult:
    active_version: str
    restarted_connectors: list[str]


def _snapshot_pending(conn: sqlite3.Connection, validated: ValidatedGatewayConfig) -> None:
    import json

    conn.execute(
        """
        INSERT INTO edge_config_snapshot (config_version, payload_json, checksum, status, received_at)
        VALUES (?, ?, ?, 'pending', ?)
        ON CONFLICT(config_version) DO NOTHING
        """,
        (validated.config_version, json.dumps(validated.raw_payload), validated.checksum, datetime.now(timezone.utc).isoformat()),
    )


def _current_active_connectors(conn: sqlite3.Connection) -> dict:
    """Returns each previously-active connector's *normalized* config (parsed back through
    `ConnectorConfig`, not the raw stored JSON) so the unchanged-connector comparison in
    `activate_runtime_config` compares like-for-like -- a raw payload that omitted an optional field
    (e.g. `poll_interval_seconds`) must not look "different" from the new config's fully-defaulted
    `model_dump()` just because the two dicts don't have identical keys."""
    import json

    from runtime.config.schema import ConnectorConfig

    row = conn.execute("SELECT payload_json FROM edge_config_snapshot WHERE status = 'active'").fetchone()
    if row is None:
        return {}
    payload = json.loads(row["payload_json"])
    return {c["connector_id"]: ConnectorConfig.model_validate(c).model_dump() for c in payload.get("connectors", [])}


async def activate_runtime_config(
    conn: sqlite3.Connection,
    supervisor: ConnectorSupervisor,
    mapping_registry: MappingRegistry,
    validated: ValidatedGatewayConfig,
) -> ActivationResult:
    """Only connectors whose config actually changed are restarted (section 4: "restarts affected
    connectors only") -- an unrelated mapping-only config change does not bounce every running driver.

    Atomicity: the SQLite write (supersede old, insert new as active) happens in one transaction. If any
    connector restart raises, the transaction is rolled back before it commits, so a partially-applied
    config is never left as the recorded active version -- the prior snapshot (still marked 'active' on
    disk because the UPDATE never committed) remains what a restart of the whole gateway process would
    reload.
    """
    _snapshot_pending(conn, validated)

    previous_connectors = _current_active_connectors(conn)
    restarted: list[str] = []

    try:
        conn.execute("BEGIN")
        conn.execute("UPDATE edge_config_snapshot SET status='superseded' WHERE status='active' AND config_version != ?", (validated.config_version,))
        conn.execute(
            "UPDATE edge_config_snapshot SET status='active', activated_at=? WHERE config_version=?",
            (datetime.now(timezone.utc).isoformat(), validated.config_version),
        )

        for mapping in validated.config.mappings:
            mapping_registry.register(
                mapping.mapping_version,
                [UnitConversionRule(c.from_unit, c.to_unit, c.factor, c.offset) for c in mapping.conversions],
            )

        for connector in validated.config.connectors:
            previous = previous_connectors.get(connector.connector_id)
            if previous is not None and previous == connector.model_dump():
                continue  # unchanged: do not bounce a healthy running connector
            if previous is not None:
                await supervisor.stop_connector(connector.connector_id, reason="config_changed")
            await supervisor.start_connector(
                connector.connector_id, connector.plugin_version,
                ["python", "-m", connector.plugin], connector.settings,
            )
            restarted.append(connector.connector_id)

        conn.execute("COMMIT")
    except Exception as exc:
        conn.execute("ROLLBACK")
        conn.execute(
            "UPDATE edge_config_snapshot SET status='rejected', rejection_reason=? WHERE config_version=?",
            (str(exc), validated.config_version),
        )
        logger.error("config activation failed for version=%s: %s -- prior configuration retained", validated.config_version, exc)
        raise ActivationFailedError(str(exc)) from exc

    return ActivationResult(active_version=validated.config_version, restarted_connectors=restarted)