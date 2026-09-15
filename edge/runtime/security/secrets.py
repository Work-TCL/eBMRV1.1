"""Secret storage -- Document 43 EDGE-FR-021 ("Secrets stored via OS/key store/secret file with
restrictive permissions; never committed in config repo or logs"). This is the "secret file" arm of that
requirement (no `keyring`/OS-vault dependency added -- the spec names a secret file with restrictive
permissions as an accepted option, and this project's own Document 104 discipline is to not add a
dependency where the spec already names a no-new-dependency-required option).

Nothing in this module ever logs a secret value -- callers must not either (EDGE-FR-028's "redact
credentials/raw secrets" applies at every layer, not just the structured-logging formatter).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path


class SecretStore:
    def __init__(self, secrets_dir: str | Path) -> None:
        self._dir = Path(secrets_dir)
        self._dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._dir, 0o700)

    def put(self, name: str, value: str) -> None:
        path = self._path_for(name)
        path.write_text(value)
        os.chmod(path, 0o600)

    def get(self, name: str) -> str | None:
        path = self._path_for(name)
        if not path.exists():
            return None
        return path.read_text()

    def delete(self, name: str) -> None:
        path = self._path_for(name)
        if path.exists():
            path.unlink()

    def _path_for(self, name: str) -> Path:
        if "/" in name or ".." in name:
            raise ValueError("secret name must not contain path separators")
        return self._dir / name

    def verify_permissions(self, name: str) -> bool:
        """Returns False if the secret file's mode is more permissive than 0600 -- used by a startup
        self-check, not silently auto-fixed, so an operator-caused permission drift is surfaced rather
        than papered over."""
        path = self._path_for(name)
        if not path.exists():
            return False
        mode = stat.S_IMODE(path.stat().st_mode)
        return mode == 0o600