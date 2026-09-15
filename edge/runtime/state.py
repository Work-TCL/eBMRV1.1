"""Edge Runtime State Model -- Document 43 section 6, transcribed verbatim as the allowed transition
table. UI/log state is never authoritative over this (same MUT-FR-008 discipline the server side applies
to batch/step state) -- every caller goes through `transition()` rather than assigning `.state` directly.
"""

from __future__ import annotations

from enum import Enum


class GatewayState(str, Enum):
    UNENROLLED = "UNENROLLED"
    ENROLLED = "ENROLLED"
    CONFIGURED = "CONFIGURED"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    OFFLINE_UPSTREAM = "OFFLINE_UPSTREAM"
    DISK_PRESSURE = "DISK_PRESSURE"
    SECURITY_HOLD = "SECURITY_HOLD"
    UPDATE_PENDING = "UPDATE_PENDING"
    STOPPED = "STOPPED"


_ALLOWED_TRANSITIONS: dict[GatewayState, frozenset[GatewayState]] = {
    GatewayState.UNENROLLED: frozenset({GatewayState.ENROLLED}),
    GatewayState.ENROLLED: frozenset({GatewayState.CONFIGURED}),
    GatewayState.CONFIGURED: frozenset({GatewayState.RUNNING}),
    GatewayState.RUNNING: frozenset(
        {
            GatewayState.DEGRADED,
            GatewayState.OFFLINE_UPSTREAM,
            GatewayState.DISK_PRESSURE,
            GatewayState.SECURITY_HOLD,
            GatewayState.UPDATE_PENDING,
            GatewayState.STOPPED,
        }
    ),
    GatewayState.DEGRADED: frozenset(
        {
            GatewayState.RUNNING,
            GatewayState.OFFLINE_UPSTREAM,
            GatewayState.DISK_PRESSURE,
            GatewayState.SECURITY_HOLD,
            GatewayState.STOPPED,
        }
    ),
    GatewayState.OFFLINE_UPSTREAM: frozenset({GatewayState.RUNNING, GatewayState.DEGRADED, GatewayState.STOPPED}),
    GatewayState.DISK_PRESSURE: frozenset({GatewayState.RUNNING, GatewayState.DEGRADED, GatewayState.STOPPED}),
    GatewayState.SECURITY_HOLD: frozenset({GatewayState.STOPPED}),
    GatewayState.UPDATE_PENDING: frozenset({GatewayState.RUNNING, GatewayState.DEGRADED, GatewayState.STOPPED}),
    GatewayState.STOPPED: frozenset(),
}


class InvalidStateTransitionError(Exception):
    def __init__(self, current: GatewayState, target: GatewayState) -> None:
        super().__init__(f"Cannot transition edge gateway runtime from {current.value} to {target.value}")
        self.current = current
        self.target = target


def transition(current: GatewayState, target: GatewayState) -> GatewayState:
    if target not in _ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidStateTransitionError(current, target)
    return target