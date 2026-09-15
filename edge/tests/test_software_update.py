"""EDGE-FR-019 tests -- Document 43 section 4 `installSignedUpdate()` ("signed/versioned, change-
controlled and supports rollback"). Uses a real local staged directory with a real manifest.json and real
files whose SHA-256 checksums are actually computed and actually verified -- no mocked filesystem.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from runtime.security.software_update import UpdateRejectedError, install_signed_update, verify_artifact_manifest


def _stage_artifact(tmp_path: Path, version: str, files: dict[str, bytes]) -> Path:
    staged_dir = tmp_path / f"artifact-{version}"
    staged_dir.mkdir()
    manifest = {"version": version, "files": {}}
    for relative_name, content in files.items():
        (staged_dir / relative_name).write_bytes(content)
        manifest["files"][relative_name] = hashlib.sha256(content).hexdigest()
    (staged_dir / "manifest.json").write_text(json.dumps(manifest))
    return staged_dir


def test_verify_artifact_manifest_accepts_matching_checksums(tmp_path):
    staged_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"print('hello')\n"})
    manifest = verify_artifact_manifest(staged_dir)
    assert manifest["version"] == "2.0.0"


def test_verify_artifact_manifest_rejects_tampered_file(tmp_path):
    staged_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"print('hello')\n"})
    (staged_dir / "plugin.py").write_bytes(b"print('tampered!')\n")  # content changed after manifest was written
    with pytest.raises(UpdateRejectedError) as exc_info:
        verify_artifact_manifest(staged_dir)
    assert exc_info.value.code == "UPDATE_SIGNATURE_INVALID"


def test_verify_artifact_manifest_rejects_missing_manifest(tmp_path):
    staged_dir = tmp_path / "no-manifest"
    staged_dir.mkdir()
    with pytest.raises(UpdateRejectedError) as exc_info:
        verify_artifact_manifest(staged_dir)
    assert exc_info.value.code == "UPDATE_SIGNATURE_INVALID"


def test_verify_artifact_manifest_rejects_missing_declared_file(tmp_path):
    staged_dir = tmp_path / "missing-file"
    staged_dir.mkdir()
    (staged_dir / "manifest.json").write_text(json.dumps({"version": "2.0.0", "files": {"gone.py": "deadbeef"}}))
    with pytest.raises(UpdateRejectedError) as exc_info:
        verify_artifact_manifest(staged_dir)
    assert exc_info.value.code == "UPDATE_SIGNATURE_INVALID"


def test_install_requires_change_id(conn, tmp_path):
    staged_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"x = 1\n"})
    with pytest.raises(UpdateRejectedError) as exc_info:
        install_signed_update(conn, staged_dir, expected_version="2.0.0", change_id="", health_check=lambda: True)
    assert exc_info.value.code == "UPDATE_CHANGE_ID_REQUIRED"


def test_install_rejects_version_mismatch(conn, tmp_path):
    staged_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"x = 1\n"})
    with pytest.raises(UpdateRejectedError) as exc_info:
        install_signed_update(conn, staged_dir, expected_version="9.9.9", change_id="CHG-001", health_check=lambda: True)
    assert exc_info.value.code == "UPDATE_SIGNATURE_INVALID"


def test_install_activates_on_healthy_check(conn, tmp_path):
    staged_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"x = 1\n"})
    result = install_signed_update(conn, staged_dir, expected_version="2.0.0", change_id="CHG-001", health_check=lambda: True)
    assert result.status == "activated"
    assert result.new_version == "2.0.0"
    assert result.old_version is None

    row = conn.execute("SELECT status, change_id FROM edge_software_version WHERE version = '2.0.0'").fetchone()
    assert row["status"] == "active"
    assert row["change_id"] == "CHG-001"


def test_install_rolls_back_on_unhealthy_check(conn, tmp_path):
    staged_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"x = 1\n"})
    result = install_signed_update(conn, staged_dir, expected_version="2.0.0", change_id="CHG-001", health_check=lambda: False)
    assert result.status == "rolled_back"
    assert result.detail is not None

    row = conn.execute("SELECT status, rollback_reason FROM edge_software_version WHERE version = '2.0.0'").fetchone()
    assert row["status"] == "rolled_back"
    assert row["rollback_reason"] is not None


def test_install_rolls_back_when_health_check_raises(conn, tmp_path):
    staged_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"x = 1\n"})

    def failing_health_check():
        raise RuntimeError("connector crashed after restart")

    result = install_signed_update(conn, staged_dir, expected_version="2.0.0", change_id="CHG-001", health_check=failing_health_check)
    assert result.status == "rolled_back"
    assert "connector crashed after restart" in result.detail


def test_install_keeps_prior_active_version_on_rollback(conn, tmp_path):
    """Document 43 section 4's "activates or rolls back" -- a failed update must not disturb whatever
    version was already running (same principle as `runtime/config/activation.py`'s "prior configuration
    retained" on activation failure)."""
    v1_dir = _stage_artifact(tmp_path, "1.0.0", {"plugin.py": b"x = 1\n"})
    first = install_signed_update(conn, v1_dir, expected_version="1.0.0", change_id="CHG-001", health_check=lambda: True)
    assert first.status == "activated"

    v2_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"x = 2\n"})
    second = install_signed_update(conn, v2_dir, expected_version="2.0.0", change_id="CHG-002", health_check=lambda: False)
    assert second.status == "rolled_back"
    assert second.old_version == "1.0.0"

    active_row = conn.execute("SELECT version FROM edge_software_version WHERE status = 'active'").fetchone()
    assert active_row["version"] == "1.0.0"  # v1 is still active -- v2's rollback did not disturb it

    v2_row = conn.execute("SELECT status FROM edge_software_version WHERE version = '2.0.0'").fetchone()
    assert v2_row["status"] == "rolled_back"


def test_install_supersedes_prior_version_on_successful_activation(conn, tmp_path):
    v1_dir = _stage_artifact(tmp_path, "1.0.0", {"plugin.py": b"x = 1\n"})
    install_signed_update(conn, v1_dir, expected_version="1.0.0", change_id="CHG-001", health_check=lambda: True)

    v2_dir = _stage_artifact(tmp_path, "2.0.0", {"plugin.py": b"x = 2\n"})
    result = install_signed_update(conn, v2_dir, expected_version="2.0.0", change_id="CHG-002", health_check=lambda: True)
    assert result.status == "activated"
    assert result.old_version == "1.0.0"

    v1_row = conn.execute("SELECT status FROM edge_software_version WHERE version = '1.0.0'").fetchone()
    assert v1_row["status"] == "superseded"
    v2_row = conn.execute("SELECT status FROM edge_software_version WHERE version = '2.0.0'").fetchone()
    assert v2_row["status"] == "active"
