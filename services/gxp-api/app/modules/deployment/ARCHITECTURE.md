# `deployment` — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade (Document 77 / SPEC-DATA-009)

Document 77 declares **1 owned entity, 0 HTTP APIs, 7 events, no signatures**. This deployment
currently runs as a single Docker/VM host, not a live Kubernetes cluster — most K8s-specific
requirements (namespaces, probes, PDBs, HPA, node scheduling) are deployment-profile configuration
that does not exist to check yet, same "mechanism present, infra feed deferred" shape used throughout
WP-11's declaration modules.

| DEP-FR | Requirement | Where enforced / evidenced |
|---|---|---|
| DEP-FR-001..003 | Deployment profiles / dedicated customer / environment separation | `deployment_profile` (`environment`, `cloud_provider`, `region`), `register_deployment_profile()`. |
| DEP-FR-004 | IaC | `deployment_profile.iac_state_ref` is the pointer to the version-controlled IaC state; this codebase does not itself run Terraform/Helm. |
| DEP-FR-005 | Immutable images | `deployment_profile.image_digest` records the currently-applied digest; `record_platform_upgrade()` requires an explicit `to_image_digest`, never a floating tag. |
| DEP-FR-006 | Configuration separated from code | Already true: `app/core/config.py::Settings` reads every value from environment/`.env`, never hardcoded. |
| DEP-FR-007..010 | Namespaces / stateless / stateful / PVCs | Kubernetes-topology concern; no live cluster to check against yet. |
| DEP-FR-011..015 | Ingress / service discovery / secrets / PKI / DB endpoints | Deployment concern; `checks.py::validate_deployment_prerequisites()` verifies the one secret this codebase itself holds (`GXP_JWT_SECRET`) is not a known dev placeholder. |
| DEP-FR-016 | Object store provider abstraction | Already built: `evidence/store.py::EvidenceStore` (Document 72) is exactly this abstraction. |
| DEP-FR-017/018/019 | NATS / Temporal / Redis-search profiles | Documents 73/74/75's own "no live broker/orchestrator/cache in Phase 1" known limitations carry forward here; nothing new to check. |
| DEP-FR-020..026 | Resource limits / probes / graceful shutdown / PDB / autoscaling / rolling deploy / rollback | Kubernetes-topology concern; `/healthz` (`app/main.py`) is the one liveness probe that exists today. |
| DEP-FR-027..029 | On-prem install / prerequisites / post-install validation | `checks.py::validate_deployment_prerequisites()` — DB reachable, JWT secret not a dev placeholder, clock sane (a real cross-check against the database's own `now()`). |
| DEP-FR-030 | Upgrade evidence | `commands.py::record_platform_upgrade()` — requires explicit before/after image digest AND before/after Alembic migration revision (DEP-FR-026: never a blind rollback of an incompatible migration). |
| DEP-FR-031 | Infrastructure drift | `checks.py::detect_infrastructure_drift()` — compares a declared digest against a caller-observed one. |
| DEP-FR-032 | Feature flags | No feature-flag system exists in this codebase; SPEC_GAP not raised (no GxP-affecting flag exists to guess a value for) -- recorded as a known limitation. |
| DEP-FR-033 | Time sync | `validate_deployment_prerequisites()`'s `clock_sane` check (app-server clock vs. database clock, 30 s engineering-default floor, SG-166 family). |
| DEP-FR-034 | Certificate/DNS expiry | `checks.py::check_certificate_expiry()` reuses `security.certificate_metadata.expires_at` (Document 65) rather than reinventing certificate tracking. |
| DEP-FR-035 | No single-node assumption | Policy; `deployment_profile.ha_profile` (`COMPACT`/`HA`) records which posture a given profile declares. |

## Known limitation

No live Kubernetes API, cloud-provider SDK or IaC runner is queried by this codebase. Every DEP-FR
requiring observation of real infrastructure (namespaces, probes, autoscaling, PDBs, rolling
deployment mechanics) is recorded as configuration policy for when that deployment exists, not
fabricated as a passing check today.
