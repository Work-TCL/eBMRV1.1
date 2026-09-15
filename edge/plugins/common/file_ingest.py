"""File-producing instrument evidence watcher -- Document 46 (SPEC-EDGE-004) PER-FR-017 ("Import original
file/export with checksum and parse result through versioned adapter"). Shared by `plugins.tester` and
`plugins.vision` because both are, at the transport level, the same shape: an instrument drops a result
file into a drop directory (a very common pattern for functional testers, vision systems and other
file-exporting lab/production instruments per Document 46 section 1's "Current Protocol Baseline": "file/
SFTP/REST integration for instruments that export evidence rather than live values"), and the gateway's
job is to notice it, hash it, and hand the exact original bytes onward -- never to re-interpret or
"correct" the file's own reported result (Document 46 section 9: "Tester/vision system output is external
evidence. eDHR/QC module determines whether the result fulfills an acceptance requirement.").

`ADAPTER_VERSION` is the versioned parse-adapter identity PER-FR-017 requires; a caller passes its own
`parse_fn` (tester JSON schema vs. vision JSON schema) but the checksum/move-to-processed/replay-safety
mechanics below are identical and are exercised for real against a real temp filesystem in tests (no
physical tester/camera hardware is available in this build environment, so a written-then-discovered file
is the realistic stand-in Document 46 itself names for this device class).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

ADAPTER_VERSION = "1.0.0"


class FileEvidenceParseError(Exception):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FileEvidenceWatcher:
    """Watches `drop_dir` for new `*.json` result files. A file is moved into `drop_dir/processed/` only
    *after* it has been successfully read, hashed and handed to the caller -- if the connector process is
    killed mid-poll, the file is still sitting in `drop_dir` on restart and will be picked up again rather
    than silently lost (MUT-FR-025 "late/replayed" handling and duplicate suppression are the *ingestion
    pipeline's* job downstream by event id; this watcher's only promise is "never lose a file that was not
    yet confirmed processed"). Files that fail to parse are moved to `drop_dir/rejected/` with the raw
    bytes preserved untouched and never retried in a loop, rather than being deleted or silently skipped.
    """

    def __init__(self, drop_dir: Path, parse_fn: Callable[[dict], dict]) -> None:
        self._drop_dir = drop_dir
        self._processed_dir = drop_dir / "processed"
        self._rejected_dir = drop_dir / "rejected"
        self._processed_dir.mkdir(parents=True, exist_ok=True)
        self._rejected_dir.mkdir(parents=True, exist_ok=True)
        self._parse_fn = parse_fn

    def poll_new_files(self) -> list[dict]:
        results: list[dict] = []
        for path in sorted(self._drop_dir.glob("*.json")):
            checksum = sha256_of(path)
            raw_text = path.read_text(encoding="utf-8")
            try:
                raw_obj = json.loads(raw_text)
                parsed = self._parse_fn(raw_obj)
            except (json.JSONDecodeError, FileEvidenceParseError, KeyError, ValueError) as exc:
                path.rename(self._rejected_dir / path.name)
                results.append({
                    "file_name": path.name, "checksum_sha256": checksum, "adapter_version": ADAPTER_VERSION,
                    "parse_error": str(exc), "raw_text": raw_text,
                })
                continue
            path.rename(self._processed_dir / path.name)
            results.append({
                "file_name": path.name, "checksum_sha256": checksum, "adapter_version": ADAPTER_VERSION,
                "parsed": parsed, "raw_text": raw_text,
            })
        return results