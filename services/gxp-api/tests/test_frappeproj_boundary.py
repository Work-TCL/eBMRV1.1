"""Document 71 (SPEC-DATA-003) -- Frappe / MariaDB Operational Database, Projection & UI Data
Architecture. Executable evidence for the one piece of Document 71 that lives on the
`services/gxp-api` side of the boundary: the structural guarantee (MDB-FR-001/002/010/028) that this
service has no path to MariaDB at all, plus the shared projection-envelope contract (MDB-FR-003).
"""

import pathlib

import pytest

from app.modules.frappeproj.contract import PROJECTION_BASELINE_FIELDS, build_projection_envelope

_SERVICE_ROOT = pathlib.Path(__file__).resolve().parents[1]
_MARIADB_MARKERS = ("pymysql", "mysqlclient", "aiomysql", "mysql-connector", "asyncmy", "frappe")


def test_no_mariadb_driver_dependency():
    """MDB-FR-001/010/028: services/gxp-api declares no MariaDB/MySQL/Frappe Python dependency --
    proof, not just policy, that this service structurally cannot open a direct MariaDB connection or
    do a cross-engine join. Scans the real dependency manifests, not a hand-maintained allowlist."""
    pyproject = (_SERVICE_ROOT / "pyproject.toml").read_text().lower()
    lock = (_SERVICE_ROOT / "uv.lock")
    lock_text = lock.read_text().lower() if lock.exists() else ""
    for marker in _MARIADB_MARKERS:
        assert marker not in pyproject, f"unexpected MariaDB/Frappe dependency marker {marker!r} in pyproject.toml"
        assert marker not in lock_text, f"unexpected MariaDB/Frappe dependency marker {marker!r} in uv.lock"


def test_build_projection_envelope_shape_and_validation():
    """MDB-FR-003: every projected record carries the baseline envelope fields."""
    env = build_projection_envelope(source_type="gxp_batch", source_id="b1", source_version=4, status="LIVE")
    assert set(env) == set(PROJECTION_BASELINE_FIELDS)
    assert env["gxp_source_version"] == 4
    assert env["gxp_projection_status"] == "LIVE"

    with pytest.raises(ValueError):
        build_projection_envelope(source_type="gxp_batch", source_id="b1", source_version=1, status="MADE_UP")
