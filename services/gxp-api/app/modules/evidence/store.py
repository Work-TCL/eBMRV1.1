"""Document 72 (SPEC-DATA-004) EvidenceStore provider abstraction -- OBJ-FR-001.

One interface for S3-compatible, Azure Blob and on-prem object storage. Phase 1 ships
`LocalEvidenceStore` (content-addressed files under a configured base directory); an S3/Azure provider
implements the same four methods and is selected by deployment config with no caller change.

Content addressing (OBJ-FR-002): `object_key = <sha256[:2]>/<sha256>`. Overwrite is prohibited
(OBJ-FR-004): `put()` refuses if the key exists with *different* bytes and is a no-op if it exists
with identical bytes (idempotent re-finalize). There is no `delete()` -- lifecycle removal is a
controlled state change on the metadata row, never a store delete from application code (OBJ-FR-019 /
OBJ-FR-030).
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.mutation.errors import EvidenceObjectImmutableError

_DEFAULT_LOCAL_BASE = os.environ.get(
    "GXP_EVIDENCE_LOCAL_BASE",
    str(Path(os.environ.get("TMPDIR", "/tmp")) / "ebmr_evidence_store"),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_key(digest: str) -> str:
    return f"{digest[:2]}/{digest}"


class EvidenceStore(ABC):
    provider: str

    @abstractmethod
    async def put(self, bucket: str, key: str, data: bytes) -> dict: ...

    @abstractmethod
    async def get(self, bucket: str, key: str) -> bytes: ...

    @abstractmethod
    async def exists(self, bucket: str, key: str) -> bool: ...

    @abstractmethod
    async def head(self, bucket: str, key: str) -> dict | None:
        """{'size_bytes': int, 'content_hash': str} or None if the object is missing."""


class LocalEvidenceStore(EvidenceStore):
    provider = "LOCAL"

    def __init__(self, base_dir: str | None = None) -> None:
        self.base = Path(base_dir or _DEFAULT_LOCAL_BASE)

    def _path(self, bucket: str, key: str) -> Path:
        # bucket/key are derived internally (content hash), never raw user input, but keep the join safe
        safe = key.replace("..", "")
        return self.base / bucket / safe

    async def put(self, bucket: str, key: str, data: bytes) -> dict:
        path = self._path(bucket, key)
        digest = sha256_bytes(data)
        if path.exists():
            existing = path.read_bytes()
            if sha256_bytes(existing) != digest:
                raise EvidenceObjectImmutableError(
                    "Refusing to overwrite an existing evidence object with different bytes",
                    bucket=bucket, key=key,
                )
            return {"provider_version_id": None, "size_bytes": len(existing), "content_hash": digest}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        try:
            path.chmod(0o440)  # best-effort local WORM: read-only after write
        except OSError:
            pass
        return {"provider_version_id": None, "size_bytes": len(data), "content_hash": digest}

    async def get(self, bucket: str, key: str) -> bytes:
        return self._path(bucket, key).read_bytes()

    async def exists(self, bucket: str, key: str) -> bool:
        return self._path(bucket, key).exists()

    async def head(self, bucket: str, key: str) -> dict | None:
        path = self._path(bucket, key)
        if not path.exists():
            return None
        data = path.read_bytes()
        return {"size_bytes": len(data), "content_hash": sha256_bytes(data)}


_store: EvidenceStore | None = None


def get_store() -> EvidenceStore:
    """Deployment selects the provider; Phase 1 is LOCAL. Kept as a module singleton so tests can
    monkeypatch it."""
    global _store
    if _store is None:
        _store = LocalEvidenceStore()
    return _store


def set_store(store: EvidenceStore) -> None:
    global _store
    _store = store
