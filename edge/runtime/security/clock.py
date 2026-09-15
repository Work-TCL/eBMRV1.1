"""`evaluateClockHealth()` -- Document 43 EDGE-FR-026 ("Gateway monitors NTP/PTP/system clock offset;
degraded clock marks data quality rather than rewriting source time silently").

No new third-party dependency (no `ntplib`) -- this shells out to whatever OS clock-sync tool is already
present (`chronyc`/`timedatectl`) and degrades to `UNCERTAIN` rather than guessing when neither is
available, which keeps EDGE-FR-026's own rule intact: an unknown clock state is marked UNCERTAIN, it is
never presented as a synchronized GOOD reading it cannot actually verify.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from runtime.contracts import ClockQuality

UNCERTAIN_OFFSET_MS = 1_000.0
BAD_OFFSET_MS = 5_000.0


@dataclass
class ClockProbe:
    offset_ms: float | None
    source: str


def _probe_chronyc() -> ClockProbe | None:
    if shutil.which("chronyc") is None:
        return None
    try:
        out = subprocess.run(["chronyc", "tracking"], capture_output=True, text=True, timeout=5).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    match = re.search(r"System time\s*:\s*([\d.]+)\s*seconds", out)
    if not match:
        return None
    return ClockProbe(offset_ms=float(match.group(1)) * 1000.0, source="chronyc")


def _probe_timedatectl() -> ClockProbe | None:
    if shutil.which("timedatectl") is None:
        return None
    try:
        out = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized"], capture_output=True, text=True, timeout=5).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    if "NTPSynchronized=yes" in out:
        return ClockProbe(offset_ms=0.0, source="timedatectl")  # synchronized, no numeric offset exposed
    if "NTPSynchronized=no" in out:
        return ClockProbe(offset_ms=None, source="timedatectl")
    return None


def evaluate_clock_health(probe: ClockProbe | None = None) -> ClockQuality:
    """`probe` is injectable for deterministic tests; production callers omit it and let this function
    query the OS itself."""
    if probe is None:
        probe = _probe_chronyc() or _probe_timedatectl()

    if probe is None or probe.offset_ms is None:
        return ClockQuality(status="UNCERTAIN", offset_ms=None, source=probe.source if probe else "unavailable")

    offset = abs(probe.offset_ms)
    if offset >= BAD_OFFSET_MS:
        status = "BAD"
    elif offset >= UNCERTAIN_OFFSET_MS:
        status = "UNCERTAIN"
    else:
        status = "GOOD"
    return ClockQuality(status=status, offset_ms=probe.offset_ms, source=probe.source)