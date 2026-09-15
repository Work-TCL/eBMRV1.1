-- Document 43 (SPEC-EDGE-001) section 7 -- Local Persistence. SQLite in WAL mode (set by
-- storage/db.py::connect(), not here). No credentials in any of these tables (section 7: "No credentials
-- in SQLite rows") -- secrets live via runtime/security/secrets.py's OS-keystore/secret-file path only.

CREATE TABLE IF NOT EXISTS edge_gateway_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton: one gateway identity per local store
    gateway_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    host_identity TEXT NOT NULL,
    gateway_fingerprint TEXT NOT NULL,
    runtime_state TEXT NOT NULL,
    config_endpoint TEXT NOT NULL,
    enrolled_at TEXT NOT NULL,
    cert_rotated_at TEXT
);

CREATE TABLE IF NOT EXISTS edge_config_snapshot (
    config_version TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    checksum TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | active | superseded | rejected
    received_at TEXT NOT NULL,
    activated_at TEXT,
    rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS edge_connector_state (
    connector_id TEXT PRIMARY KEY,
    connector_config_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'stopped',  -- stopped | starting | running | crashed | quarantined
    pid INTEGER,
    restart_count INTEGER NOT NULL DEFAULT 0,
    last_started_at TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS edge_outbox (
    event_id TEXT PRIMARY KEY,
    gateway_sequence INTEGER NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',  -- pending | sent | acked
    created_at TEXT NOT NULL,
    first_sent_at TEXT,
    acked_at TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT
);

CREATE TABLE IF NOT EXISTS edge_delivery_attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES edge_outbox (event_id),
    attempted_at TEXT NOT NULL,
    outcome TEXT NOT NULL,  -- sent | upstream_unavailable | rejected
    detail TEXT
);

CREATE TABLE IF NOT EXISTS edge_health_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reported_at TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    posted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS edge_security_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    evidence_json TEXT,
    posted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS edge_evidence_file (
    content_hash TEXT PRIMARY KEY,  -- SHA-256, content-addressed (section 7)
    file_path TEXT NOT NULL,
    media_type TEXT,
    size_bytes INTEGER NOT NULL,
    recorded_at TEXT NOT NULL
);