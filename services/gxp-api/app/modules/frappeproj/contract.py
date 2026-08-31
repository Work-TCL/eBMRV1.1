"""Document 71 (SPEC-DATA-003) -- Frappe / MariaDB Operational Database, Projection & UI Data
Architecture. **0 owned entities, 1 read-only API** (`04_DATA_MODEL_CATALOGUE.md` / Document 71 # 7)
-- every DocType-level enforcement point Document 71 specifies (MDB-FR-003/004/005/011/013/019/020) is
*Frappe-side* code inside `apps/ebmr_frappe`, which does not exist yet: `ADR-0008-frappe-role-and-ui-
layer.md` decided the operator UI of record IS Frappe (affirming Document 02/71 as written, no
SPEC_GAP), and its own point 4 records that `apps/ebmr_frappe` is scaffolded module-by-module starting
with WP-01 Document 04 -- not in bulk here. As of this pass every module built so far (WP-01..WP-10,
WP-11 Documents 69/70/72/73/75) delivered `services/gxp-api` only; `apps/ebmr_frappe` remains
unscaffolded project-wide. This is recorded as a known limitation (see `ARCHITECTURE.md`), not guessed
around.

What Document 71 DOES own on the `services/gxp-api` side of the boundary:

- **`PROJECTION_BASELINE_FIELDS` / `build_projection_envelope()`** -- the exact field set (Document 71
  # 6) any Frappe DocType projection (once scaffolded) or any other read-model consumer must carry so
  the source is traceable and never mistaken for authoritative (MDB-FR-003). Already fully exercised by
  this codebase's own read-model tables: `dataops.data_ownership_registry` / `projection_checkpoint`,
  `readmodels.projection_document_metadata` / `read_model_checkpoint` all carry the equivalent fields
  (source id/version/type/projected_at/status) -- this module makes the shared shape a named, reusable
  contract rather than four independent re-derivations.
- **The structural boundary guarantee** (MDB-FR-002/010/028): `services/gxp-api` has no MariaDB/MySQL
  driver dependency at all -- proven in `tests/test_frappeproj_boundary.py::test_no_mariadb_driver_dependency`,
  not just documented. Frappe (whenever scaffolded) can only reach GxP state over the same REST API
  every other caller uses; there is no shared-connection path for it to bypass.
- **`getProjectionStatus()`'s contract** is already implemented -- `GET /platform/v1/read-models/{name}/status`
  (Document 75/`readmodels`) and `GET /platform/v1/data-ownership/{entityType}` (Document 69/`dataops`)
  are the same "source version / projected_at / staleness" read Document 71 # 7 asks for; Document 71
  does not need a third copy.
"""

from __future__ import annotations

from datetime import datetime, timezone

PROJECTION_BASELINE_FIELDS = (
    "gxp_source_type",
    "gxp_source_id",
    "gxp_source_version",
    "gxp_projected_at",
    "gxp_projection_status",
)

PROJECTION_STATUSES = ("LIVE", "STALE", "REBUILDING", "ERROR")


def build_projection_envelope(
    *, source_type: str, source_id: str, source_version: int, status: str = "LIVE"
) -> dict:
    """MDB-FR-003: the baseline envelope every projected record (Frappe DocType or otherwise) must
    carry alongside its display/search fields. Raises on an unknown status rather than silently
    accepting a made-up one (AG-15)."""
    if status not in PROJECTION_STATUSES:
        raise ValueError(f"status must be one of {PROJECTION_STATUSES}")
    return {
        "gxp_source_type": source_type,
        "gxp_source_id": source_id,
        "gxp_source_version": source_version,
        "gxp_projected_at": datetime.now(timezone.utc).isoformat(),
        "gxp_projection_status": status,
    }
