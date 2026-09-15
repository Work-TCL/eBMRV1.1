"""`submitMachineCommand()` -- Document 43 section 4, EDGE-FR-023 ("Inbound machine command channel
disabled by default; enabled only for explicit approved command profiles with allowlist and local safety
interlocks").

This is a stub per the spec's own Implementation Sequence step 11 ("command channel stub disabled by
default") and Prohibitions section 16 ("Do not enable machine write commands as a convenience feature") --
it proves the gate exists and fails closed; it does not implement an actual PLC/SCADA command transport
(no protocol/interlock design is defined anywhere in Document 43-47 to build against, which would be
guessed regulated behavior under AG-15 if invented here).
"""

from __future__ import annotations

from dataclasses import dataclass

from runtime.config.schema import CommandChannelConfig


class CommandChannelDisabledError(Exception):
    pass


class CommandProfileNotAllowlistedError(Exception):
    pass


@dataclass
class CommandExecutionReceipt:
    command_id: str
    status: str


def submit_machine_command(
    config: CommandChannelConfig, *, approved_command_profile_id: str, command_id: str,
) -> CommandExecutionReceipt:
    if not config.enabled:
        raise CommandChannelDisabledError("COMMAND_PROFILE_DISABLED: command channel is disabled by default")
    if approved_command_profile_id not in config.approved_command_profile_ids:
        raise CommandProfileNotAllowlistedError(f"INTERLOCK_DENIED: profile {approved_command_profile_id!r} is not allowlisted")
    # No connector in this reference build implements an actual machine-write transport (see module
    # docstring) -- reaching this point only proves the gate passed; it never dispatches to a real PLC.
    return CommandExecutionReceipt(command_id=command_id, status="accepted_no_transport_configured")