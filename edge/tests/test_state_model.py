import pytest

from runtime.state import GatewayState, InvalidStateTransitionError, transition


def test_full_happy_path_transitions():
    state = GatewayState.UNENROLLED
    for target in (GatewayState.ENROLLED, GatewayState.CONFIGURED, GatewayState.RUNNING):
        state = transition(state, target)
    assert state == GatewayState.RUNNING


def test_running_can_degrade_and_recover():
    state = transition(GatewayState.RUNNING, GatewayState.DEGRADED)
    assert state == GatewayState.DEGRADED
    state = transition(state, GatewayState.RUNNING)
    assert state == GatewayState.RUNNING


def test_stopped_is_terminal():
    state = transition(GatewayState.RUNNING, GatewayState.STOPPED)
    with pytest.raises(InvalidStateTransitionError):
        transition(state, GatewayState.RUNNING)


def test_cannot_skip_enrollment():
    with pytest.raises(InvalidStateTransitionError):
        transition(GatewayState.UNENROLLED, GatewayState.RUNNING)


def test_security_hold_only_leads_to_stopped():
    with pytest.raises(InvalidStateTransitionError):
        transition(GatewayState.SECURITY_HOLD, GatewayState.RUNNING)
    assert transition(GatewayState.SECURITY_HOLD, GatewayState.STOPPED) == GatewayState.STOPPED