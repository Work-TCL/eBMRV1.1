"""SG-151 RESOLVED_APPROVED 2026-09-14: MULTI-FR-015 manifest/checksum/replay/acknowledgement rule shape
(app/modules/erp/file_manifest.py). Pure Python, no DB/transport -- no fixtures needed.
"""

import pytest

from app.modules.erp.file_manifest import (
    ManifestChecksumMismatchError,
    acknowledgement_receipt,
    build_manifest,
    is_replay,
    verify_manifest,
)


def test_build_manifest_computes_sha256_checksum():
    content = b"record1,record2,record3"
    manifest = build_manifest(file_bytes=content, filename="batch-001.csv", record_count=3, sequence_number=1)
    import hashlib

    assert manifest.checksum == hashlib.sha256(content).hexdigest()
    assert manifest.filename == "batch-001.csv"
    assert manifest.record_count == 3
    assert manifest.sequence_number == 1


def test_build_manifest_rejects_invalid_record_count_and_sequence():
    with pytest.raises(ValueError):
        build_manifest(file_bytes=b"x", filename="f.csv", record_count=-1, sequence_number=1)
    with pytest.raises(ValueError):
        build_manifest(file_bytes=b"x", filename="f.csv", record_count=1, sequence_number=0)


def test_verify_manifest_passes_for_untampered_file():
    content = b"exact original bytes"
    manifest = build_manifest(file_bytes=content, filename="f.csv", record_count=1, sequence_number=1)
    verify_manifest(file_bytes=content, manifest=manifest)  # must not raise


def test_verify_manifest_rejects_tampered_content():
    original = b"original regulated content"
    manifest = build_manifest(file_bytes=original, filename="f.csv", record_count=1, sequence_number=1)
    tampered = b"original regulated content, quietly altered"
    with pytest.raises(ManifestChecksumMismatchError):
        verify_manifest(file_bytes=tampered, manifest=manifest)


def test_is_replay_detects_identical_resend():
    manifest = build_manifest(file_bytes=b"same content", filename="f.csv", record_count=1, sequence_number=1)
    seen = {manifest.file_identity}
    assert is_replay(seen, manifest) is True


def test_is_replay_allows_new_file_identity():
    manifest = build_manifest(file_bytes=b"content A", filename="f.csv", record_count=1, sequence_number=1)
    other = build_manifest(file_bytes=b"content B", filename="f.csv", record_count=1, sequence_number=2)
    seen = {manifest.file_identity}
    assert is_replay(seen, other) is False


def test_is_replay_treats_same_name_different_content_as_distinct():
    v1 = build_manifest(file_bytes=b"version 1 content", filename="daily-export.csv", record_count=10, sequence_number=1)
    v2 = build_manifest(file_bytes=b"version 2 content, corrected", filename="daily-export.csv", record_count=10, sequence_number=1)
    seen = {v1.file_identity}
    assert is_replay(seen, v2) is False  # a legitimate resend of a corrected file under the same name is not a replay


def test_acknowledgement_receipt_records_outcome():
    manifest = build_manifest(file_bytes=b"data", filename="f.csv", record_count=1, sequence_number=1)
    accepted = acknowledgement_receipt(manifest, accepted=True)
    assert accepted["accepted"] is True
    assert accepted["checksum"] == manifest.checksum

    rejected = acknowledgement_receipt(manifest, accepted=False, reason="duplicate")
    assert rejected["accepted"] is False
    assert rejected["reason"] == "duplicate"