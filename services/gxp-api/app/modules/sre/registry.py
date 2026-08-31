"""Document 78 (SPEC-DATA-010) seed data -- transcribed verbatim from Document 109 (SPEC-DATA-012,
APPROVED v1.0, closes SG-006/008/016). Not invented; a deployment overrides any row via
`register_slo()` / `register_capacity_forecast()` with its own reference (SRE-FR-001 "not one generic
uptime number", per-capability).
"""

# Document 109 # 3 "Performance SLOs by operation class" -- measured server-side at the GxP API
# boundary, steady-state load, excluding client network.
DOCUMENT_109_SLO_SEED: list[dict] = [
    {"operation_class": "OC-1", "sli_name": "Interactive read (batch execution view, step list, material lookup)", "p95_target_ms": 300, "p99_target_ms": 800},
    {"operation_class": "OC-2", "sli_name": "Regulated mutation, no signature (record step result, start step, place hold)", "p95_target_ms": 500, "p99_target_ms": 1200},
    {"operation_class": "OC-3", "sli_name": "Regulated mutation, with signature (approve, verify, release) -- excludes human step-up time", "p95_target_ms": 1500, "p99_target_ms": 3000},
    {"operation_class": "OC-4", "sli_name": "Policy/authorization decision (internal policy call)", "p95_target_ms": 50, "p99_target_ms": 150},
    {"operation_class": "OC-5", "sli_name": "Rules/calculation evaluation (yield, tolerance, eligibility)", "p95_target_ms": 200, "p99_target_ms": 600},
    {"operation_class": "OC-6", "sli_name": "Event publish lag, commit to bus (outbox publisher)", "p95_target_ms": 2000, "p99_target_ms": 10000},
    {"operation_class": "OC-7", "sli_name": "Projection lag, commit to Frappe read model (projection updater)", "p95_target_ms": 5000, "p99_target_ms": 30000},
    {"operation_class": "OC-8", "sli_name": "Search/report query (audit search, trending) -- never on a regulated decision path", "p95_target_ms": 2000, "p99_target_ms": 8000},
    {"operation_class": "OC-9", "sli_name": "Evidence write (file/evidence put + digest) -- size-dependent, measured per MB tier", "p95_target_ms": 3000, "p99_target_ms": 10000},
    {"operation_class": "OC-10", "sli_name": "Edge upload acceptance (buffered batch upload) -- per upload window, not per sample", "p95_target_ms": 5000, "p99_target_ms": 20000},
]

# Document 109 # 4 "Capacity baseline (PROPOSED reference profile)". growth_rate_pct/headroom_pct left
# unset (None) at the platform-default layer -- Document 109 does not supply a growth rate or headroom
# percentage, only reference values; a deployment/capacity-review sets those (SRE-FR-005/006/033).
DOCUMENT_109_CAPACITY_SEED: list[dict] = [
    {"dimension": "concurrent_execution_users_per_site", "reference_value": 150, "horizon_days": 90},
    {"dimension": "regulated_mutations_per_hour_peak", "reference_value": 20_000, "horizon_days": 90},
    {"dimension": "audit_events_per_year_minimum", "reference_value": 200_000_000, "horizon_days": 365},
    {"dimension": "edge_samples_per_second_per_gateway", "reference_value": 500, "horizon_days": 90},
    {"dimension": "evidence_objects_per_batch_avg", "reference_value": 200, "horizon_days": 90},
    {"dimension": "evidence_objects_per_batch_max", "reference_value": 2_000, "horizon_days": 90},
]
