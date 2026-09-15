import pytest

from runtime.config.schema import CommandChannelConfig
from runtime.security.command_channel import (
    CommandChannelDisabledError,
    CommandProfileNotAllowlistedError,
    submit_machine_command,
)


def test_command_channel_disabled_by_default():
    config = CommandChannelConfig()  # default: enabled=False
    assert config.enabled is False
    with pytest.raises(CommandChannelDisabledError):
        submit_machine_command(config, approved_command_profile_id="any", command_id="cmd-1")


def test_command_rejected_when_profile_not_allowlisted():
    config = CommandChannelConfig(enabled=True, approved_command_profile_ids=["profile-a"])
    with pytest.raises(CommandProfileNotAllowlistedError):
        submit_machine_command(config, approved_command_profile_id="profile-z", command_id="cmd-1")


def test_command_accepted_when_enabled_and_allowlisted():
    config = CommandChannelConfig(enabled=True, approved_command_profile_ids=["profile-a"])
    receipt = submit_machine_command(config, approved_command_profile_id="profile-a", command_id="cmd-1")
    assert receipt.status == "accepted_no_transport_configured"