"""SQLite local store -- Document 43 section 7 ("SQLite in WAL mode for delivery/outbox metadata and
configuration snapshots"). One connection per process, WAL mode, foreign keys on. Migrations are applied
in order by filename and tracked in `schema_migrations` (MIG-FR-008 idempotency: rerun is a no-op).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), isolation_level=None)  # autocommit; callers open explicit txns
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=FULL")  # durability over speed: this is the loss-resistance layer
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Applies every `.sql` file under migrations/ not yet recorded, in filename order. Returns the list
    of migration filenames applied this call (empty on a fully up-to-date store -- MIG-FR-008)."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    applied = {row["filename"] for row in conn.execute("SELECT filename FROM schema_migrations")}
    newly_applied: list[str] = []
    for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        if path.name in applied:
            continue
        conn.executescript(path.read_text())
        conn.execute("INSERT INTO schema_migrations (filename) VALUES (?)", (path.name,))
        newly_applied.append(path.name)
    return newly_applied