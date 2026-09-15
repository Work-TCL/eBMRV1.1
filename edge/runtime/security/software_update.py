"""`installSignedUpdate()` -- Document 43 (SPEC-EDGE-001) section 4, EDGE-FR-019 ("Software/plugin update
is signed/versioned, change-controlled and supports rollback; no auto-update of validated production
gateways by default").

Integrity check, not a cryptographic signature: exactly like `runtime/config/loader.py::
validate_config_payload()`'s SHA-256 config checksum, this verifies every staged artifact file against a
SHA-256 digest declared in its own manifest -- it does not verify a detached signature against a trusted
signing key, because (same as SG-118/SG-120/SG-187's precedent) no signing-key distribution/rotation
mechanism is defined anywhere in Document 43 or Document 106 to verify one against. Inventing a PKI here
would be exactly the kind of guessed security-trust-boundary decision AG-15 and this project's SPEC_GAP
rule forbid; see `docs/generated/18_SPEC_GAPS.md` SG-187 (extended, not contradicted, by this module).

Change-controlled: `change_id` is a mandatory, non-empty caller-supplied change-management reference (the
same "reason/change reference required" discipline `runtime/security/command_channel.py` and the server
side's own admin/privileged-action pattern use) -- an update cannot be installed anonymously.

No auto-update by default: this module exposes only a function a caller must explicitly invoke with a
staged artifact path, an expected version and a change_id. Nothing under `runtime/` schedules or calls it
on a timer -- the absence of such a caller is what satisfies "no auto-update... by default", the same way
`runtime/security/command_channel.py` satisfies "disabled by default" by never being wired to anything
that fires without an explicit allowlisted request. `cli/main.py`'s `install-update` subcommand is the one
real (human-invoked) caller in this codebase.

Rollback: `health_check` is a caller-supplied callable representing the post-install health probe Document
43 section 4's function catalogue calls out ("health-checks; activates or rolls back"). This reference
build does not implement a real process-restart-and-observe health check itself (that is a deployment/
process-supervision concern -- systemd/container restart policy territory, not a library function can
honestly fake) -- the caller (a real deployment's install script) supplies what "healthy" means for its
own environment; this function's job is only the atomic activate-or-rollback bookkeeping around whatever
that check reports, which is exactly the regulated-adjacent state transition Document 43 asks for.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


class UpdateRejectedError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass
class UpdateResult:
    old_version: str | None
    new_version: str
    status: str  # "activated" | "rolled_back"
    detail: str | None = None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact_manifest(staged_dir: Path) -> dict:
    """Recomputes SHA-256 for every file `manifest.json` declares and compares -- raises
    `UpdateRejectedError("UPDATE_SIGNATURE_INVALID", ...)` (Document 43 section 4's own error code name
    for this function, even though what is actually verified is a checksum, not a signature -- see module
    docstring) for a missing manifest, a malformed one, a missing file or any checksum mismatch."""
    manifest_path = staged_dir / "manifest.json"
    if not manifest_path.exists():
        raise UpdateRejectedError("UPDATE_SIGNATURE_INVALID", f"staged artifact {staged_dir} has no manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise UpdateRejectedError("UPDATE_SIGNATURE_INVALID", f"manifest.json is not valid JSON: {exc}") from exc

    for key in ("version", "files"):
        if key not in manifest:
            raise UpdateRejectedError("UPDATE_SIGNATURE_INVALID", f"manifest.json missing required field: {key!r}")

    for relative_path, expected_checksum in manifest["files"].items():
        file_path = staged_dir / relative_path
        if not file_path.exists():
            raise UpdateRejectedError("UPDATE_SIGNATURE_INVALID", f"manifest references missing file: {relative_path}")
        actual_checksum = _sha256_file(file_path)
        if actual_checksum != expected_checksum:
            raise UpdateRejectedError(
                "UPDATE_SIGNATURE_INVALID",
                f"checksum mismatch for {relative_path}: manifest declares {expected_checksum}, computed {actual_checksum}",
            )

    return manifest


def install_signed_update(
    conn: sqlite3.Connection,
    staged_dir: Path,
    *,
    expected_version: str,
    change_id: str,
    health_check: Callable[[], bool],
) -> UpdateResult:
    """`staged_dir` is already-staged local content (Document 43 section 4: "Pulls staged image/plugin" is
    the deployment tooling's job, not this function's -- it operates on what is already on disk, matching
    the config loader's split between `load_runtime_config()`'s HTTP fetch and `validate_config_payload()`
    's pure validation)."""
    if not change_id:
        raise UpdateRejectedError(
            "UPDATE_CHANGE_ID_REQUIRED",
            "installSignedUpdate requires a non-empty change-control reference (EDGE-FR-019 'change-controlled')",
        )

    manifest = verify_artifact_manifest(staged_dir)
    if manifest["version"] != expected_version:
        raise UpdateRejectedError(
            "UPDATE_SIGNATURE_INVALID",
            f"manifest version {manifest['version']!r} does not match expected_version {expected_version!r}",
        )

    manifest_checksum = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    existing_active = conn.execute("SELECT version FROM edge_software_version WHERE status = 'active'").fetchone()
    old_version = existing_active["version"] if existing_active else None

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO edge_software_version (version, status, change_id, artifact_ref, manifest_checksum, installed_at)
        VALUES (?, 'staged', ?, ?, ?, ?)
        ON CONFLICT(version) DO UPDATE SET
            status='staged', change_id=excluded.change_id, artifact_ref=excluded.artifact_ref,
            manifest_checksum=excluded.manifest_checksum, installed_at=excluded.installed_at,
            activated_at=NULL, rolled_back_at=NULL, rollback_reason=NULL
        """,
        (expected_version, change_id, str(staged_dir), manifest_checksum, now),
    )

    try:
        healthy = bool(health_check())
        failure_detail = None if healthy else "health_check() returned a falsy result"
    except Exception as exc:  # noqa: BLE001 -- a health check that raises is exactly as unhealthy as one returning False
        healthy = False
        failure_detail = f"health_check() raised: {exc}"

    if healthy:
        conn.execute("UPDATE edge_software_version SET status='superseded' WHERE status='active' AND version != ?", (expected_version,))
        conn.execute("UPDATE edge_software_version SET status='active', activated_at=? WHERE version=?", (now, expected_version))
        return UpdateResult(old_version=old_version, new_version=expected_version, status="activated")

    # Rollback: the new version never reaches 'active' and the prior 'active' row (if any) is untouched --
    # the gateway keeps running whatever it already had, matching every other atomic-activation function
    # in this codebase (runtime/config/activation.py's "prior configuration retained" on failure).
    conn.execute(
        "UPDATE edge_software_version SET status='rolled_back', rolled_back_at=?, rollback_reason=? WHERE version=?",
        (now, failure_detail, expected_version),
    )
    return UpdateResult(old_version=old_version, new_version=expected_version, status="rolled_back", detail=failure_detail)
