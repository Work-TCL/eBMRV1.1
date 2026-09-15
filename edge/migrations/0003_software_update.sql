-- Document 43 (SPEC-EDGE-001) EDGE-FR-019 ("Software/plugin update is signed/versioned, change-
-- controlled and supports rollback; no auto-update of validated production gateways by default").
-- Purely additive (MIG-FR-004 expand pattern) -- no existing table touched.

CREATE TABLE IF NOT EXISTS edge_software_version (
    version TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'staged',  -- staged | active | superseded | rolled_back
    change_id TEXT NOT NULL,                -- mandatory change-control reference (EDGE-FR-019 "change-controlled")
    artifact_ref TEXT NOT NULL,             -- staged local path/URL this update was installed from
    manifest_checksum TEXT NOT NULL,        -- SHA-256 over the canonical manifest (integrity check, not a
                                             -- cryptographic signature -- see runtime/security/software_update.py)
    installed_at TEXT NOT NULL,
    activated_at TEXT,
    rolled_back_at TEXT,
    rollback_reason TEXT
);
