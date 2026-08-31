# `sre` — Performance, Capacity, Observability, SLOs & SRE Operations (Document 78 / SPEC-DATA-010)

Document 78 declares **2 owned entities, 0 HTTP APIs, 9 named events (5 new + 2 reused + 2 the function
catalogue names that the events table omits, both added here for consistency)**. Numbers are
transcribed from Document 109 (SPEC-DATA-012, APPROVED, closes SG-006/008/016) — never invented.

| SRE-FR | Requirement | Where enforced / evidenced |
|---|---|---|
| SRE-FR-001 | Service objectives per capability | `slo_definition`, seeded from Document 109 # 3's OC-1..OC-10 (`registry.py::DOCUMENT_109_SLO_SEED`); `record_service_level_objective()`. |
| SRE-FR-002 | SLI coverage | The seeded OC-1..OC-10 rows cover API latency (OC-1..4), rules (OC-5), event/projection lag (OC-6/7, cross-referenced to Documents 70/73/75's own lag signals), search (OC-8), evidence (OC-9), Edge (OC-10). |
| SRE-FR-003/004 | Scale baseline / load model | `capacity_forecast`, seeded from Document 109 # 4 (`DOCUMENT_109_CAPACITY_SEED`); a real load-test harness is deployment/ops tooling, not application code. |
| SRE-FR-005/006 | Capacity unit / headroom | `capacity_forecast.headroom_pct` (integer basis points); `record_capacity_forecast()` computes `forecasted_value` from `current_value` + `growth_rate_pct_bp` over `horizon_days`, integer-only. |
| SRE-FR-007 | API budgets | `monitor.py::evaluate_operational_alert()` compares a measured value against the matching `slo_definition` row. |
| SRE-FR-008 | Signature latency | Covered by OC-3 (regulated mutation with signature) in the seeded SLO table; a dedicated signature-only SLI is a future refinement, not a missing mechanism. |
| SRE-FR-009/010 | Mutation / audit throughput | Load-test/ops concern; `capacity_forecast`'s `regulated_mutations_per_hour_peak` / `audit_events_per_year_minimum` rows are the sizing inputs Document 70's partitioning (PG-FR-016) is measured against. |
| SRE-FR-011/012 | Event / projection lag | **Reused, not reinvented**: `OutboxLagExceeded` (Document 70/`dbops`) and `ProjectionLagExceeded` (Document 75/`readmodels`) are the real signals; see `event-data-010.json`'s description. |
| SRE-FR-013 | DB capacity | `monitor.py::check_database_saturation()` reads real `pg_stat_activity`/`max_connections`, not a synthetic metric. |
| SRE-FR-014/015/016 | Object / Temporal / Edge capacity | Deployment/ops monitoring concern; not application-code testable without a live object-store/Temporal/Edge-fleet deployment (none exist in Phase 1 -- Documents 72/74's own known limitations). |
| SRE-FR-017 | Report isolation | Already true: Document 75's read models / async exports are the only report path; there is no synchronous heavy-report code on the regulated execution path. |
| SRE-FR-018 | Resource limits | Deployment concern (container/pool sizing); `check_database_saturation()`'s threshold is the one application-observable proxy. |
| SRE-FR-019/020/021 | Autoscaling / backpressure / rate limits | Deployment/ops concern; Document 64's `appsec.py` rate-limit mechanism (WP-10) is the one already-built piece of this. |
| SRE-FR-022 | Graceful degradation | `monitor.py::verify_graceful_degradation()` -- a real check against a caller-supplied critical-capability matrix and observed results. |
| SRE-FR-023 | Health semantics | `GET /healthz` (app/main.py) is liveness only today; readiness/startup/dependency-health differentiation is a known limitation. |
| SRE-FR-024/025/026 | Metrics / tracing / logs | No Prometheus/OpenTelemetry exporter or tracing SDK is wired in this codebase (no dependency); `emitPlatformMetric()`/`startTraceSpan()` are therefore not implemented as no-op stubs (a stub proves nothing) -- recorded as a known limitation rather than fabricated. Structured logging with `logger.exception` + correlation IDs on every audit/outbox row is the current evidence trail. |
| SRE-FR-027/029 | Dashboards / runbooks | Operational artefacts, not application code. |
| SRE-FR-028 | Alert policy | `evaluate_operational_alert()` / `check_database_saturation()` / `evaluate_release_performance_gate()` each emit a real event only on breach, never on every check (avoids noisy metric-only alerts by construction). |
| SRE-FR-030 | Error budget | Governance practice; `slo_definition` is the input an error-budget calculation would consume. |
| SRE-FR-031/032 | Soak / failure-injection testing | Ops/QA practice; `verify_graceful_degradation()` is the assertion layer such a drill's results are checked against. |
| SRE-FR-033/034 | Capacity review / storage forecast | `capacity_forecast` rows, one per dimension (relational counts, object counts, etc. per Document 109 # 4), reviewed/regenerated on a cadence outside application code. |
| SRE-FR-035 | Performance regression gate | `monitor.py::evaluate_release_performance_gate()` -- integer basis-points comparison, never float. |
| SRE-FR-036 | No hidden optimization | Policy; enforced by code review, not a runtime check. |

## Known limitation

No metrics/tracing exporter (Prometheus/OpenTelemetry) is wired into this codebase (SRE-FR-024/025).
Object-store, Temporal and Edge-fleet capacity monitoring (SRE-FR-014/015/016) require those
deployments to exist first — none do in Phase 1 (Documents 72/74's own known limitations carry
forward here).
