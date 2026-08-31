"""Document 76 (SPEC-DATA-008) recovery-objective seed -- DR-FR-001/002. Transcribed verbatim from
Document 109 (SPEC-DATA-012, APPROVED) `# 1. Component recovery tiers`. One representative `component`
per tier, mapped to what actually exists in this codebase; a deployment overrides any row via
`register_recovery_objective()` with its own `approved_by` reference (DR-FR-009).
"""

DOCUMENT_109_TIER_SEED: list[dict] = [
    {
        "component": "postgres_gxp", "tier": "T0", "rpo_seconds": 0, "rto_seconds": 4 * 3600,
        "approved_by": "Document 109 platform default (T0, closes SG-006/008/016)",
    },
    {
        "component": "evidence_object_store", "tier": "T1", "rpo_seconds": 0, "rto_seconds": 8 * 3600,
        "approved_by": "Document 109 platform default (T1)",
    },
    {
        "component": "mariadb_frappe", "tier": "T2", "rpo_seconds": 15 * 60, "rto_seconds": 8 * 3600,
        "approved_by": "Document 109 platform default (T2)",
    },
    {
        "component": "temporal_orchestration", "tier": "T3", "rpo_seconds": 15 * 60, "rto_seconds": 8 * 3600,
        "approved_by": "Document 109 platform default (T3)",
    },
    {
        # T4: "Rebuildable (no RPO commitment)" per Document 109 -- rpo_seconds is None by design, not omitted.
        "component": "readmodels_search_cache", "tier": "T4", "rpo_seconds": None, "rto_seconds": 24 * 3600,
        "approved_by": "Document 109 platform default (T4)",
    },
    {
        # T5: RPO is expressed as edge-local durability (>=72h offline), not a platform RPO seconds
        # value -- Document 76's own field shape only has rpo_seconds, so this stays None with the
        # durability requirement recorded in approved_by rather than a fabricated seconds figure.
        "component": "edge_gateway_buffer", "tier": "T5", "rpo_seconds": None, "rto_seconds": 4 * 3600,
        "approved_by": "Document 109 platform default (T5, local durability >=72h offline per site)",
    },
]
