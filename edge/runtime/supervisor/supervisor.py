"""Connector Supervisor -- Document 43 EDGE-FR-007 ("Gateway starts/stops/restarts drivers under
supervisor and isolates crashing connector from other connectors") and the `startConnector`/
`stopConnector`/`quarantineConnector` operations from section 4.

Isolation is real OS-process isolation (asyncio subprocess), not an in-process try/except around plugin
code sharing the supervisor's memory space -- a plugin segfaulting, deadlocking or leaking memory cannot
take any other connector, or the supervisor itself, down with it. The restricted environment passed to
`asyncio.create_subprocess_exec` is also EDGE-FR-008's enforcement point (see plugins/base.py).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from runtime.contracts import RawSourceObservation

logger = logging.getLogger("edge.supervisor")

_ALLOWED_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "PYTHONPATH")
_MAX_RESTART_BACKOFF_SECONDS = 60.0
_BASE_RESTART_BACKOFF_SECONDS = 1.0


@dataclass
class ConnectorHandle:
    connector_id: str
    connector_config_version: str
    plugin_command: list[str]
    status: str = "stopped"  # stopped | starting | running | crashed | quarantined
    restart_count: int = 0
    last_error: str | None = None
    process: asyncio.subprocess.Process | None = field(default=None, repr=False)
    _reader_task: asyncio.Task | None = field(default=None, repr=False)
    _scratch_dir: str | None = field(default=None, repr=False)


class ConnectorSupervisor:
    """`observation_sink` is called once per parsed `RawSourceObservation` -- normally
    `runtime.ingestion.pipeline.ingest_source_observation`, injected rather than imported directly so
    supervisor tests do not need a real ingestion pipeline/outbox."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        observation_sink: Callable[[str, RawSourceObservation], Awaitable[None]],
        *,
        quarantine_after_restarts: int = 5,
    ) -> None:
        self._conn = conn
        self._observation_sink = observation_sink
        self._quarantine_after_restarts = quarantine_after_restarts
        self._handles: dict[str, ConnectorHandle] = {}

    def _persist_state(self, handle: ConnectorHandle) -> None:
        self._conn.execute(
            """
            INSERT INTO edge_connector_state (connector_id, connector_config_version, status, pid, restart_count, last_started_at, last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(connector_id) DO UPDATE SET
                connector_config_version=excluded.connector_config_version, status=excluded.status,
                pid=excluded.pid, restart_count=excluded.restart_count,
                last_started_at=excluded.last_started_at, last_error=excluded.last_error
            """,
            (
                handle.connector_id, handle.connector_config_version, handle.status,
                handle.process.pid if handle.process else None, handle.restart_count,
                datetime.now(timezone.utc).isoformat(), handle.last_error,
            ),
        )

    async def start_connector(self, connector_id: str, connector_config_version: str, plugin_command: list[str], connector_config: dict) -> ConnectorHandle:
        """`connector_config` is written to a scratch dir visible to *only* this connector's process --
        the fixed-adapter-interface sandbox boundary (EDGE-FR-008)."""
        if connector_id in self._handles and self._handles[connector_id].status in ("starting", "running"):
            return self._handles[connector_id]

        scratch_dir = tempfile.mkdtemp(prefix=f"edge-connector-{connector_id}-")
        config_path = Path(scratch_dir) / "config.json"
        config_path.write_text(json.dumps(connector_config))
        os.chmod(config_path, 0o600)

        handle = self._handles.get(connector_id) or ConnectorHandle(
            connector_id=connector_id, connector_config_version=connector_config_version, plugin_command=plugin_command,
        )
        handle.connector_config_version = connector_config_version
        handle.plugin_command = plugin_command
        handle.status = "starting"
        handle._scratch_dir = scratch_dir
        self._handles[connector_id] = handle
        self._persist_state(handle)

        await self._spawn(handle, config_path)
        return handle

    async def _spawn(self, handle: ConnectorHandle, config_path: Path) -> None:
        restricted_env = {k: os.environ[k] for k in _ALLOWED_ENV_KEYS if k in os.environ}
        handle.process = await asyncio.create_subprocess_exec(
            *handle.plugin_command, "--config", str(config_path),
            cwd=handle._scratch_dir, env=restricted_env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, stdin=asyncio.subprocess.DEVNULL,
        )
        handle.status = "running"
        self._persist_state(handle)
        handle._reader_task = asyncio.create_task(self._read_and_supervise(handle))

    async def _read_and_supervise(self, handle: ConnectorHandle) -> None:
        assert handle.process is not None and handle.process.stdout is not None
        try:
            async for raw_line in handle.process.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    observation = RawSourceObservation.model_validate_json(line)
                except Exception as exc:  # malformed plugin output never propagates to other connectors
                    logger.warning("supervisor: connector=%s emitted unparseable output: %s", handle.connector_id, exc)
                    continue
                await self._observation_sink(handle.connector_id, observation)
        finally:
            return_code = await handle.process.wait()
            if handle.status == "quarantined":
                return
            if handle.status != "stopping":
                await self._handle_unexpected_exit(handle, return_code)
            else:
                handle.status = "stopped"
                self._persist_state(handle)

    async def _handle_unexpected_exit(self, handle: ConnectorHandle, return_code: int) -> None:
        stderr_tail = b""
        if handle.process and handle.process.stderr:
            stderr_tail = await handle.process.stderr.read()
        handle.status = "crashed"
        handle.restart_count += 1
        handle.last_error = f"exit_code={return_code} stderr={stderr_tail.decode(errors='replace')[-500:]}"
        self._persist_state(handle)
        logger.error("supervisor: connector=%s crashed (restart #%d): %s", handle.connector_id, handle.restart_count, handle.last_error)

        if handle.restart_count >= self._quarantine_after_restarts:
            await self.quarantine_connector(handle.connector_id, reason="restart_count_exceeded", evidence={"last_error": handle.last_error})
            return

        backoff = min(_BASE_RESTART_BACKOFF_SECONDS * (2 ** (handle.restart_count - 1)), _MAX_RESTART_BACKOFF_SECONDS)
        await asyncio.sleep(backoff)
        if handle.status in ("stopping", "quarantined"):
            # A stop/quarantine request arrived during the backoff window -- honor it instead of
            # respawning a connector the caller just asked to stop.
            if handle.status == "stopping":
                handle.status = "stopped"
            self._persist_state(handle)
            return
        config_path = Path(handle._scratch_dir or tempfile.mkdtemp()) / "config.json"
        handle.status = "starting"
        self._persist_state(handle)
        await self._spawn(handle, config_path)

    async def _terminate_and_wait(self, process: asyncio.subprocess.Process) -> None:
        """Guards against the process having already exited (e.g. it crashed and was reaped by
        `_read_and_supervise` a moment before a caller decided to stop/quarantine it) -- `returncode`
        being set means `wait()` already completed, so there is nothing left to signal."""
        if process.returncode is not None:
            return
        try:
            process.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                return
            await process.wait()

    async def stop_connector(self, connector_id: str, reason: str) -> None:
        handle = self._handles.get(connector_id)
        if handle is None or handle.process is None:
            return
        handle.status = "stopping"
        handle.last_error = f"stopped: {reason}"
        self._persist_state(handle)
        await self._terminate_and_wait(handle.process)
        if handle._reader_task:
            await handle._reader_task

    async def quarantine_connector(self, connector_id: str, reason: str, evidence: dict | None = None) -> dict:
        """Stops the connector and blocks restart until a human reviews it (EDGE-FR-007's isolation
        combined with the security/health-rule caller class in section 4's `quarantineConnector()`)."""
        handle = self._handles.get(connector_id)
        if handle is not None and handle.process is not None and handle.status not in ("stopped", "quarantined"):
            handle.status = "quarantined"
            self._persist_state(handle)
            await self._terminate_and_wait(handle.process)
        elif handle is not None:
            handle.status = "quarantined"
            self._persist_state(handle)
        logger.critical("supervisor: connector=%s QUARANTINED reason=%s evidence=%s", connector_id, reason, evidence)
        return {"connector_id": connector_id, "status": "quarantined", "reason": reason}

    def status_of(self, connector_id: str) -> str | None:
        handle = self._handles.get(connector_id)
        return handle.status if handle else None