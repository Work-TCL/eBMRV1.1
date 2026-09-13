"""Document 74 (SPEC-DATA-006) real Temporal client -- ADR-0011 (SG-183) Stage 2, replacing the "no
Temporal client exists in this deployment yet" state every other `workflowops/*.py` module docstring
declared.

Owns the one process-wide Temporal client. `app/main.py`'s lifespan connects at startup and closes
(no explicit close needed -- the client holds no persistent connection of its own to tear down, see
`close()`'s docstring) at shutdown.

`connect()` is bounded (`asyncio.wait_for(..., timeout=CONNECT_TIMEOUT_SECONDS)`), the same lesson WP-11
Stage 1's NATS integration learned the hard way: `Client.connect()` has no built-in timeout parameter,
and an unreachable server would otherwise hang the caller (and therefore `app/main.py`'s startup)
indefinitely. Applied here from the start rather than discovered by a second hung CI run.
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client

from app.core.config import settings

logger = logging.getLogger("gxp_api.workflowops.client")

CONNECT_TIMEOUT_SECONDS = 5

TASK_QUEUE = "gxp-workflowops"

_client: Client | None = None


async def connect() -> None:
    """Idempotent: a second call while already connected is a no-op. Raises `ConnectionError` (never
    hangs) if no Temporal server is reachable within `CONNECT_TIMEOUT_SECONDS`."""
    global _client
    if _client is not None:
        return
    try:
        _client = await asyncio.wait_for(
            Client.connect(settings.temporal_target, namespace=settings.temporal_namespace),
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 - any connect failure (timeout, refused, DNS, ...) uniformly
        raise ConnectionError(
            f"No Temporal server reachable at {settings.temporal_target} within {CONNECT_TIMEOUT_SECONDS}s"
        ) from exc
    logger.info("connected to Temporal at %s, namespace=%s", settings.temporal_target, settings.temporal_namespace)


async def close() -> None:
    """Temporal's `Client` has no persistent connection to drain (unlike the NATS client) -- gRPC
    channels are managed internally and released on garbage collection. This just clears the reference
    so a subsequent `connect()` establishes a fresh client rather than reusing a stale one."""
    global _client
    _client = None


def is_connected() -> bool:
    return _client is not None


def get_client() -> Client:
    if _client is None:
        raise ConnectionError("Temporal client is not connected")
    return _client
