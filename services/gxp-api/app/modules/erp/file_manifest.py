"""SG-151 RESOLVED_APPROVED 2026-09-14 (project-owner-directed, "build the rule shape now, defer the
dependency"): MULTI-FR-015's manifest/checksum/file-identity/acknowledgement/replay rule shape for the
future SFTP/CSV/XML/EDI batch file adapter, as pure Python logic with no transport dependency.

This module intentionally has zero I/O -- no SFTP client, no filesystem access, no database table. SG-153
(no Document 104/DEP-FR-018 approval yet for a parser-touching SFTP/SOAP dependency, and no registered ERP
instance requires either transport today) remains open and unresolved on its own terms; this module is the
extensibility point a real transport adapter plugs into once that dependency is approved, exactly like
`generic.py`'s own `endpoint_map`/`transport_mode` is for MULTI-FR-014. Persistence for the replay-dedup
set (a real `inbound_file_manifest` table) is deferred alongside the transport itself -- `is_replay()`
below takes the "already seen" set as a parameter rather than owning storage, so the caller decides that
once a real consumer exists.

Checksum algorithm: SHA-256, matching `app.mutation.hashing.sha256_hex` -- this project's existing
standard hash used for every other integrity check in the codebase (command payload hashes, audit event
hashes, edge gateway config checksums), not a new algorithm choice.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone


class ManifestChecksumMismatchError(Exception):
    """The file's actual content does not match its declared manifest checksum -- MULTI-FR-015's
    "checksum" control catching a corrupted or tampered file before it is accepted as genuine."""


@dataclass(frozen=True)
class FileManifest:
    """MULTI-FR-015's "manifest" + "file identity" controls. `file_identity` is (filename, checksum,
    record_count) taken together -- two files with the same name but different content are different
    identities; the same content resent under the same name is the same identity (replay-detectable)."""

    filename: str
    record_count: int
    sequence_number: int
    checksum: str
    generated_at: str

    @property
    def file_identity(self) -> tuple[str, str, int]:
        return (self.filename, self.checksum, self.record_count)


def compute_checksum(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def build_manifest(*, file_bytes: bytes, filename: str, record_count: int, sequence_number: int) -> FileManifest:
    """MULTI-FR-015 "manifest" control -- built once, at the moment a batch file is produced/received, and
    never recomputed from a mutated file (the checksum is the file's identity, not a live property of it)."""
    if record_count < 0:
        raise ValueError("record_count must not be negative")
    if sequence_number < 1:
        raise ValueError("sequence_number must be a positive, monotonically assigned integer")
    return FileManifest(
        filename=filename, record_count=record_count, sequence_number=sequence_number,
        checksum=compute_checksum(file_bytes), generated_at=datetime.now(timezone.utc).isoformat(),
    )


def verify_manifest(*, file_bytes: bytes, manifest: FileManifest) -> None:
    """MULTI-FR-015 "checksum" control. Raises rather than returning a bool -- a checksum mismatch is
    exactly the "silently accepting a corrupted or duplicated regulated file as genuine" risk SG-151's own
    description names; a caller must not be able to accidentally ignore a False return value."""
    actual = compute_checksum(file_bytes)
    if actual != manifest.checksum:
        raise ManifestChecksumMismatchError(
            f"File {manifest.filename!r} checksum mismatch: manifest declares {manifest.checksum}, actual content hashes to {actual}"
        )


def is_replay(seen_identities: set[tuple[str, str, int]], manifest: FileManifest) -> bool:
    """MULTI-FR-015 "replay" control. `seen_identities` is caller-owned storage (see module docstring --
    no persistence layer is committed here); this function is a pure membership check so the eventual
    real consumer can back it with whatever store SG-153's approved transport dependency ships with."""
    return manifest.file_identity in seen_identities


def acknowledgement_receipt(manifest: FileManifest, *, accepted: bool, reason: str | None = None) -> dict:
    """MULTI-FR-015 "acknowledgement" control -- the structured receipt a real transport adapter would
    return to the sending system once one exists. Pure data construction, no network call."""
    return {
        "filename": manifest.filename,
        "checksum": manifest.checksum,
        "sequence_number": manifest.sequence_number,
        "record_count": manifest.record_count,
        "accepted": accepted,
        "reason": reason,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
    }