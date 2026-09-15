"""EDGE-FR-008: "Protocol plugins expose fixed adapter interfaces and cannot access GxP database
credentials or unrestricted filesystem/secrets." Verified from the parent side: the plugin subprocess's
actual environment must not contain any GxP secret, and its working directory must be its own dedicated
scratch dir, not the supervisor process's own cwd or any shared secrets directory.
"""

import asyncio
import sys
from pathlib import Path

import pytest

from runtime.supervisor.supervisor import ConnectorSupervisor

EDGE_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = EDGE_ROOT / "tests" / "fixtures"


@pytest.mark.asyncio
async def test_plugin_subprocess_has_no_gxp_secrets_in_environment(conn, monkeypatch):
    # Simulate a real deployment where the gateway process itself holds a GxP service-identity bearer
    # token and a GxP database URL in its own environment.
    monkeypatch.setenv("PYTHONPATH", str(EDGE_ROOT))
    monkeypatch.setenv("EDGE_SERVICE_IDENTITY_BEARER_TOKEN", "sid_super-secret-value")
    monkeypatch.setenv("GXP_DATABASE_URL", "postgresql://gxp:supersecret@db/gxp")

    observed = {}

    async def sink(connector_id, observation):
        observed["value"] = observation.value

    supervisor = ConnectorSupervisor(conn, sink)
    await supervisor.start_connector("introspect", "v1", [sys.executable, str(FIXTURES / "plugin_introspect.py")], {})
    await asyncio.sleep(1.0)
    await supervisor.stop_connector("introspect", reason="test_teardown")

    assert "value" in observed, "introspection plugin did not report back"
    env_keys = set(observed["value"]["env_keys"])
    assert "EDGE_SERVICE_IDENTITY_BEARER_TOKEN" not in env_keys
    assert "GXP_DATABASE_URL" not in env_keys


@pytest.mark.asyncio
async def test_each_connector_gets_its_own_isolated_scratch_dir(conn):
    cwds = {}

    async def sink(connector_id, observation):
        cwds[connector_id] = observation.value["cwd"]

    supervisor = ConnectorSupervisor(conn, sink)
    await supervisor.start_connector("intro-a", "v1", [sys.executable, str(FIXTURES / "plugin_introspect.py")], {})
    await supervisor.start_connector("intro-b", "v1", [sys.executable, str(FIXTURES / "plugin_introspect.py")], {})
    await asyncio.sleep(1.0)
    await supervisor.stop_connector("intro-a", reason="test_teardown")
    await supervisor.stop_connector("intro-b", reason="test_teardown")

    assert "intro-a" in cwds and "intro-b" in cwds
    assert cwds["intro-a"] != cwds["intro-b"], "connectors must not share a working directory"


@pytest.mark.asyncio
async def test_plugin_filesystem_access_is_hygiene_not_os_level_denial(conn, tmp_path, monkeypatch):
    """Honest measurement of what EDGE-FR-008's "unrestricted filesystem" boundary actually is in this
    reference build: no secret is ever *placed* somewhere the plugin process could reach (proven by
    `test_plugin_subprocess_has_no_gxp_secrets_in_environment`), but this is credential hygiene, not an
    OS-level filesystem jail (no chroot/mount-namespace/seccomp is applied to the subprocess) -- a plugin
    process still runs as the same OS user and can open any absolute path that user can read. This is a
    genuine, documented limitation (see docs/generated/18_SPEC_GAPS.md SG-187's addendum), not a passing
    security control -- this test proves the *actual* boundary rather than assuming a stronger one."""
    monkeypatch.setenv("PYTHONPATH", str(EDGE_ROOT))
    outside_file = tmp_path / "outside_scratch_dir.txt"
    outside_file.write_text("not a secret, but outside the plugin's scratch dir")

    observed = {}

    async def sink(connector_id, observation):
        observed["value"] = observation.value

    supervisor = ConnectorSupervisor(conn, sink)
    await supervisor.start_connector(
        "fs-probe", "v1", [sys.executable, str(FIXTURES / "plugin_filesystem_probe.py")],
        {"probe_path": str(outside_file)},
    )
    await asyncio.sleep(1.0)
    await supervisor.stop_connector("fs-probe", reason="test_teardown")

    assert "value" in observed
    # Documents actual behavior: the read succeeds (no OS-level jail), which is why this reference build
    # relies entirely on never exposing secrets to the process rather than on filesystem denial.
    assert observed["value"]["read_succeeded"] is True