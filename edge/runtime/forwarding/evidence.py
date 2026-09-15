"""Content-addressed large-evidence store -- Document 45 (SPEC-EDGE-003) BUF-FR-015 (`storeEvidenceFile()`)
and section 4's `EvidenceRef{sha256,path,size}` output. Backs the `edge_evidence_file` table Document 43's
session already declared in `migrations/0001_initial.sql` but never wrote to.

Large binary evidence (instrument PDFs/exports, chromatograms, etc.) does not belong inline in the
`edge_outbox.payload_json` blob -- it is written once to a content-addressed path on local disk, fsynced,
and referenced by hash; the outbox envelope that accompanies it carries only the hash/size/path reference,
never the bytes themselves (same "reference, not embedded base64" rule CTR-FR-019 applies server-side).
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class EvidenceStorageError(Exception):
    pass


@dataclass
class EvidenceRef:
    sha256: str
    path: str
    size: int


def store_evidence_file(
    conn: sqlite3.Connection,
    evidence_dir: str | Path,
    data: bytes,
    *,
    media_type: str | None = None,
) -> EvidenceRef:
    """`storeEvidenceFile()`. Content-addressed by SHA-256: writing the same bytes twice is idempotent --
    the manifest row already exists (`content_hash` is the primary key) and the second call is a cheap
    no-op rather than a duplicate file or a duplicate manifest row. Writes to a temp file in the same
    directory and `os.replace()`s it into place so a crash mid-write can never leave a half-written file
    at the final content-addressed path, then `fsync`s the containing directory so the rename itself is
    durable across an abrupt power loss (BUF-FR-029's guarantee extended to evidence files, not just the
    SQLite outbox)."""
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    content_hash = hashlib.sha256(data).hexdigest()
    final_path = evidence_dir / content_hash

    existing = conn.execute(
        "SELECT file_path, size_bytes FROM edge_evidence_file WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    if existing is not None:
        return EvidenceRef(sha256=content_hash, path=existing["file_path"], size=existing["size_bytes"])

    tmp_path = evidence_dir / f".{content_hash}.tmp"
    try:
        with open(tmp_path, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, final_path)
        dir_fd = os.open(str(evidence_dir), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError as exc:
        raise EvidenceStorageError(str(exc)) from exc

    conn.execute(
        "INSERT OR IGNORE INTO edge_evidence_file (content_hash, file_path, media_type, size_bytes, recorded_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (content_hash, str(final_path), media_type, len(data), datetime.now(timezone.utc).isoformat()),
    )
    return EvidenceRef(sha256=content_hash, path=str(final_path), size=len(data))
