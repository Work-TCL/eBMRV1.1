"""Fixed protocol-plugin adapter interface -- Document 43 EDGE-FR-008 ("Protocol plugins expose fixed
adapter interfaces and cannot access GxP database credentials or unrestricted filesystem/secrets").

The sandbox boundary is enforced at the OS-process level, not by trusting plugin code: `runtime/
supervisor/supervisor.py` launches every connector as its own subprocess with a restricted environment
(no GxP DB URL, no service-identity bearer token, no secrets directory) and a dedicated per-connector
working directory. A plugin can only ever see what its own `--config` file names, and its only channel out
is a line-delimited JSON stream on stdout -- it cannot import supervisor internals, open the local SQLite
outbox, or reach the GxP API credential store, because those objects/paths never exist in its process.

A plugin author subclasses `ConnectorPlugin` and calls `run_plugin_main(MyPlugin())` from `__main__`.
"""

from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from typing import Iterable

from runtime.contracts import RawSourceObservation


class PeripheralCommandNotSupportedError(NotImplementedError):
    """Raised by the default `send_command()` -- this connector only supports poll()-based acquisition."""


class ConnectorPlugin(ABC):
    """`connector_config` is exactly the JSON object the supervisor read from the plugin's own config
    file -- never the full gateway configuration, and never anything containing another connector's
    settings or gateway-level secrets (EDGE-FR-008's "unrestricted filesystem/secrets" boundary)."""

    def __init__(self, connector_config: dict) -> None:
        self.connector_config = connector_config

    @abstractmethod
    def poll(self) -> Iterable[RawSourceObservation]:
        """Called repeatedly by the plugin runloop. Returns zero or more raw observations acquired since
        the previous call. Must not raise for a single bad reading -- report it as a BAD/COMM_ERROR
        quality_hint observation instead, so one bad tag does not kill the connector process (that
        distinction belongs to the supervisor's crash-isolation, not the plugin's own read loop)."""

    def poll_interval_seconds(self) -> float:
        return float(self.connector_config.get("poll_interval_seconds", 1.0))

    def send_command(self, command: dict) -> RawSourceObservation:
        """OPTIONAL outbound extension point -- added for Document 46 (SPEC-EDGE-004) peripherals whose
        contract genuinely needs the gateway to *send* something to the device rather than only read from
        it: PER-FR-011/013 (send an already-approved, already-rendered print payload to a label printer)
        and PER-FR-009 (send a tare instruction to a balance the connector already has an open connection
        to). `poll()` alone cannot express this -- Document 43's `ConnectorPlugin` was deliberately
        inbound-only (see this module's docstring), and Document 46 needs a small, explicitly-scoped
        extension rather than being forced into that shape.

        This is deliberately NOT Document 43's EDGE-FR-023 command channel
        (`runtime/security/command_channel.py`), which gates *remote, network-issued* writes to
        OT/PLC/SCADA process outputs behind an interlock allowlist because such a write can change a
        physical process the gateway does not own end-to-end. `send_command()` dispatches an
        already-authorized, already-rendered payload (an approved print job's exact bytes; a tare
        instruction) to a peripheral this connector process already exclusively owns the connection to --
        it makes no new regulated decision and drives no PLC/SCADA output. Overriding plugins must not
        decide label content, template choice or test acceptance themselves (Document 46 section 8/9,
        Prohibitions section 13); they only relay what the caller already approved.

        No supervisor-side transport delivers a command into a *running, sandboxed* connector subprocess
        in this reference build -- `runtime/supervisor/supervisor.py` opens the child's stdin as
        `DEVNULL` (see `_spawn()`), matching `run_plugin_main()`'s "stdout only" contract above. Wiring a
        real duplex channel (stdin protocol, or otherwise) would touch that shared supervisor code, which
        Document 44's protocol-driver work may also need to change -- deliberately left unresolved this
        pass rather than guessed (AG-15); see docs/generated/18_SPEC_GAPS.md for the open item. Plugins
        that override this method today are exercised directly (constructed and called in-process) by
        their own tests; there is no production dispatch path into a supervised subprocess yet."""
        raise PeripheralCommandNotSupportedError(
            f"{type(self).__name__} does not support outbound peripheral commands (poll()-only connector)"
        )


def run_plugin_main(plugin: ConnectorPlugin, *, max_iterations: int | None = None) -> None:
    """The plugin's entire contract with the outside world: emit each observation as one JSON line on
    stdout, flush immediately (the supervisor reads the pipe line-by-line), and never touch any other
    file descriptor or path. `max_iterations` exists only so tests can run this deterministically instead
    of forever."""
    import time

    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        for observation in plugin.poll():
            sys.stdout.write(json.dumps(observation.model_dump(mode="json")) + "\n")
            sys.stdout.flush()
        iterations += 1
        if max_iterations is None or iterations < max_iterations:
            time.sleep(plugin.poll_interval_seconds())