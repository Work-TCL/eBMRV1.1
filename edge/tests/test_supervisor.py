import asyncio
import os
import sys
from pathlib import Path

import pytest

from runtime.supervisor.supervisor import ConnectorSupervisor

EDGE_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = EDGE_ROOT / "tests" / "fixtures"


@pytest.fixture(autouse=True)
def _plugin_pythonpath(monkeypatch):
    # The subprocess only inherits PATH/LANG/LC_ALL/PYTHONPATH (runtime/supervisor/supervisor.py's
    # _ALLOWED_ENV_KEYS) -- the plugin needs PYTHONPATH set so `import runtime.contracts`/`plugins.base`
    # resolve inside its own restricted process, same as a real deployment's installed package would.
    monkeypatch.setenv("PYTHONPATH", str(EDGE_ROOT))


@pytest.mark.asyncio
async def test_crashing_connector_does_not_affect_sibling(conn):
    received: list[tuple[str, object]] = []

    async def sink(connector_id, observation):
        received.append((connector_id, observation))

    supervisor = ConnectorSupervisor(conn, sink, quarantine_after_restarts=10)

    await supervisor.start_connector("ok", "v1", [sys.executable, str(FIXTURES / "plugin_ok.py")], {"connector_id": "ok"})
    await supervisor.start_connector("crashy", "v1", [sys.executable, str(FIXTURES / "plugin_crash.py")], {"connector_id": "crashy"})

    await asyncio.sleep(2.0)  # allow the crash + at least one restart cycle to occur

    ok_connector_ids = {c for c, _ in received if c == "ok"}
    crashy_events = [o for c, o in received if c == "crashy"]

    assert "ok" in ok_connector_ids, "healthy connector must keep emitting despite sibling crash"
    assert len(crashy_events) >= 1, "crashing connector's pre-crash observation must still have been ingested"
    assert supervisor.status_of("ok") == "running"

    row = conn.execute("SELECT restart_count FROM edge_connector_state WHERE connector_id = 'crashy'").fetchone()
    assert row["restart_count"] >= 1

    await supervisor.stop_connector("ok", reason="test_teardown")
    await supervisor.stop_connector("crashy", reason="test_teardown")


@pytest.mark.asyncio
async def test_connector_quarantined_after_repeated_crashes(conn):
    async def sink(connector_id, observation):
        pass

    supervisor = ConnectorSupervisor(conn, sink, quarantine_after_restarts=2)
    await supervisor.start_connector("crashy", "v1", [sys.executable, str(FIXTURES / "plugin_crash.py")], {})

    await asyncio.sleep(3.0)  # 2 restarts at 1s/2s backoff should exceed the quarantine threshold

    assert supervisor.status_of("crashy") == "quarantined"
    row = conn.execute("SELECT status FROM edge_connector_state WHERE connector_id = 'crashy'").fetchone()
    assert row["status"] == "quarantined"


@pytest.mark.asyncio
async def test_stop_connector_is_graceful_and_marks_stopped(conn):
    async def sink(connector_id, observation):
        pass

    supervisor = ConnectorSupervisor(conn, sink)
    await supervisor.start_connector("ok", "v1", [sys.executable, str(FIXTURES / "plugin_ok.py")], {"connector_id": "ok"})
    await asyncio.sleep(0.2)
    await supervisor.stop_connector("ok", reason="test")

    row = conn.execute("SELECT status FROM edge_connector_state WHERE connector_id = 'ok'").fetchone()
    assert row["status"] == "stopped"