import os
import uuid
from datetime import datetime, timedelta, timezone

# Point the app at the dedicated test database *before* anything imports app.core.config
# (Settings is instantiated once at import time).
os.environ.setdefault(
    "GXP_DATABASE_URL",
    "postgresql+asyncpg://ebmr_new_gxp_app:" + os.environ.get("GXP_TEST_DB_APP_PW", "")
    + "@localhost:5432/ebmr_new_gxp_test",
)
# The migration role's connection, pointed at the test database — needed by tests that must bypass the
# runtime app role's restricted privileges (e.g. simulating a missing signature policy row, which the
# app role can never DELETE — see test_signature_policy_missing_fails_closed).
os.environ.setdefault(
    "GXP_MIGRATION_DATABASE_URL",
    "postgresql+asyncpg://ebmr_new_migrator:" + os.environ.get("GXP_TEST_DB_MIGRATOR_PW", "")
    + "@localhost:5432/ebmr_new_gxp_test",
)

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.modules.dataops.models import DataOwnershipRegistry
from app.modules.dataops.registry import OWNERSHIP_SEED
from app.modules.disaster_recovery.models import RecoveryObjectiveProfile
from app.modules.disaster_recovery.registry import DOCUMENT_109_TIER_SEED
from app.modules.edge.models import EdgeEnrollmentToken
from app.modules.equipment.aseptic_models import AsepticProfileVersion
from app.modules.equipment.cleaning_models import CleaningProcedureVersion, EquipmentArea
from app.modules.equipment.em_models import EmLocation, EmProgramVersion
from app.modules.equipment.sterilization_models import ProcessCycleProfileVersion
from app.modules.erp.models import ErpInstance
from app.modules.iam.models import (
    Organization,
    Permission,
    Qualification,
    Role,
    RolePermission,
    Site,
    User,
    UserSiteRole,
)
from app.modules.material.models import WarehouseLocation
from app.modules.rules.models import RuleDefinition
from app.modules.signature.models import SignaturePolicy
from app.modules.sre.models import CapacityForecast, SloDefinition
from app.modules.sre.registry import DOCUMENT_109_CAPACITY_SEED, DOCUMENT_109_SLO_SEED
from app.mutation.hashing import sha256_hex

DEMO_PASSWORD = "ChangeMe123!"
# Document 43 (SPEC-EDGE-001) -- same literal value scripts/seed.py's DEMO_EDGE_BOOTSTRAP_TOKEN uses.
DEMO_EDGE_BOOTSTRAP_TOKEN = "demo-edge-bootstrap-token-0001"

APP_TABLES = [
    "ebmr.reconciliation_records",
    "ebmr.manufacturing_calculations",
    "machine_integration.machine_replay_jobs",
    "machine_integration.machine_command_requests",
    "machine_integration.machine_command_profiles",
    "machine_integration.cycle_evidence_manifests",
    "machine_integration.machine_alarm_events",
    "machine_integration.machine_evidence_candidates",
    "machine_integration.batch_contexts",
    "machine_integration.signal_mappings",
    "machine_integration.machine_sources",
    "erp.erp_migration_packages",
    "erp.integration_bulk_jobs",
    "erp.integration_security_events",
    "erp.integration_circuit_breakers",
    "erp.integration_reconciliation_differences",
    "erp.integration_reconciliation_runs",
    "erp.integration_inbound_events",
    "erp.integration_command_attempts",
    "erp.integration_commands",
    "erp.erp_sync_checkpoints",
    "erp.erp_mapping_conflicts",
    "erp.erp_external_mappings",
    "erp.erp_instances",
    "edge.edge_certificate_rotations",
    "edge.edge_security_events",
    "edge.edge_health_snapshots",
    "edge.edge_observations",
    "edge.edge_config_snapshots",
    "edge.edge_enrollment_tokens",
    "edge.edge_gateways",
    "equipment.aseptic_event_timeline",
    "equipment.aseptic_interventions",
    "equipment.aseptic_operations",
    "equipment.aseptic_profile_versions",
    "equipment.sterile_filter_uses",
    "equipment.sterilization_load_items",
    "equipment.process_cycles",
    "equipment.process_cycle_profile_versions",
    "equipment.em_excursions",
    "equipment.em_samples_or_readings",
    "equipment.em_locations",
    "equipment.em_program_versions",
    "equipment.line_clearances",
    "equipment.cleaning_executions",
    "equipment.cleaning_procedure_versions",
    "equipment.equipment_use_logs",
    "equipment.maintenance_work_orders",
    "equipment.equipment_calibrations",
    "equipment.equipment_assets",
    "equipment.equipment_areas",
    "ebmr.oot_record",
    "ebmr.oos_resample_plan",
    "ebmr.oos_retest_plan",
    "ebmr.oos_investigation_activity",
    "ebmr.oos_record",
    "ebmr.lims_message",
    "ebmr.lims_mapping",
    "ebmr.lims_instance",
    "ebmr.qc_result_correction",
    "ebmr.qc_result",
    "ebmr.qc_test_run",
    "ebmr.qc_test_order",
    "ebmr.qc_sample",
    "ebmr.qc_test_definition",
    "ebmr.qc_test_specification",
    "qms.effectiveness_check",
    "qms.quality_metric_snapshot",
    "qms.quality_metric_definition",
    "qms.field_action_reconciliation",
    "qms.field_action_communication",
    "qms.field_action_scope_item",
    "qms.field_action",
    "qms.complaint_communication",
    "qms.complaint_reportability_assessment",
    "qms.complaint_record",
    "qms.audit_finding",
    "qms.internal_audit",
    "qms.risk_assessment_version",
    "qms.risk_record",
    "qms.scar_record",
    "qms.supplier_quality_case",
    "qms.qualification_record",
    "qms.training_assignment",
    "qms.training_waiver",
    "qms.training_requirement",
    "qms.controlled_copy",
    "qms.controlled_document_version",
    "qms.controlled_document",
    "qms.change_task",
    "qms.change_affected_object",
    "qms.change_control",
    "qms.ncr_disposition",
    "qms.nonconformance_record",
    "qms.capa_effectiveness_check",
    "qms.capa_action",
    "qms.capa_record",
    "qms.deviation_impact_link",
    "qms.deviation_record",
    "materials.dispensed_containers",
    "materials.weighing_readings",
    "materials.weighing_sessions",
    "materials.dispensing_sources",
    "materials.dispensing_orders",
    "materials.material_issues",
    "materials.material_lot_dispositions",
    "materials.material_quality_dispositions",
    "materials.sampling_orders",
    "materials.inventory_reservations",
    "materials.inventory_balance_projections",
    "materials.inventory_transactions",
    "materials.material_containers",
    "materials.material_lots",
    "materials.material_receipts",
    "materials.materials",
    "materials.warehouse_locations",
    "ebmr.supplier_qualification_evidence",
    "ebmr.supplier_qualification",
    "ebmr.supplier_site",
    "ebmr.supplier",
    "ebmr.package_node",
    "ebmr.label_reconciliation",
    "ebmr.label_issue",
    "ebmr.packaging_run",
    "ebmr.release_decision",
    "ebmr.release_evaluation",
    "ebmr.release_scope",
    "ebmr.qa_review_package",
    "ebmr.genealogy_edge",
    "ebmr.genealogy_node",
    "ebmr.device_unit",
    "ebmr.gxp_batch_step",
    "ebmr.gxp_batch",
    "ebmr.batch_releases",
    "ebmr.batch_reviews",
    "ebmr.batch_steps",
    "ebmr.batches",
    "ebmr.recipe_steps",
    "ebmr.recipes",
    "ebmr.products",
    "ebmr.gxp_recipe_evidence_requirement",
    "ebmr.gxp_recipe_parameter",
    "ebmr.gxp_recipe_step_dependency",
    "ebmr.gxp_recipe_step",
    "ebmr.gxp_recipe_section",
    "ebmr.gxp_recipe_version",
    "ebmr.gxp_recipe_family",
    "ebmr.gxp_constituent_compatibility_version",
    "ebmr.gxp_product_constituent",
    "ebmr.gxp_product_version",
    "ebmr.gxp_product_family",
    "security.webhook_profile",
    "security.outbound_destination",
    "security.api_security_policy",
    "security.release_security_evidence",
    "security.vulnerability_record",
    "security.software_component_inventory",
    "security.forensic_evidence",
    "security.security_incident",
    "security.deployment_security_profile",
    "security.network_flow_definition",
    "security.certificate_metadata",
    "security.secret_metadata",
    "security.crypto_profile",
    "sre.capacity_forecast",
    "sre.slo_definition",
    "disaster_recovery.restore_test",
    "disaster_recovery.backup_inventory",
    "disaster_recovery.recovery_objective_profile",
    "readmodels.projection_document_metadata",
    "readmodels.read_model_checkpoint",
    "eventbus.consumer_inbox",
    "evidence.evidence_manifest",
    "evidence.evidence_object",
    "dataops.migration_batch",
    "dataops.projection_checkpoint",
    "dataops.data_ownership_registry",
    "deployment.deployment_profile",
    "ai_governance.ai_provider_switch",
    "ai_governance.ai_prompt_injection_event",
    "ai_governance.ai_release_gate",
    "ai_governance.ai_evaluation_report",
    "ai_governance.ai_disposition",
    "ai_governance.ai_tool_decision",
    "ai_governance.ai_advisory_log",
    "ai_governance.ai_prompt_version",
    "ai_governance.ai_tool_registry",
    "ai_governance.ai_model_deployment",
    "ai_governance.ai_risk_assessment",
    "ai_governance.ai_use_case",
    "validation.validated_release_authorization",
    "validation.validation_summary_report",
    "validation.migration_reconciliation",
    "validation.migration_run",
    "validation.migration_validation_plan",
    "validation.pq_execution",
    "validation.pq_scenario",
    "validation.periodic_validation_review",
    "validation.validation_change_impact",
    "validation.validated_state_baseline",
    "validation.validation_exception",
    "validation.performance_run",
    "validation.performance_qualification_scenario",
    "validation.security_qualification_finding",
    "validation.security_qualification_suite",
    "validation.dr_qualification_execution",
    "validation.dr_qualification_scenario",
    "validation.interface_test_execution",
    "validation.interface_validation_profile",
    "validation.tamper_test_execution",
    "validation.data_integrity_test_profile",
    "validation.part11_control_evidence",
    "validation.part11_scope_assessment",
    "validation.infrastructure_fingerprint",
    "validation.infrastructure_qualification_profile",
    "validation.oq_execution",
    "validation.oq_suite",
    "validation.iq_execution",
    "validation.iq_protocol",
    "validation.validation_test_execution",
    "validation.validation_test_definition",
    "validation.requirement_baseline",
    "validation.trace_link",
    "validation.validation_requirement",
    "validation.function_risk_assessment",
    "validation.intended_use",
    "validation.validation_release_gate",
    "validation.validation_deliverable_requirement",
    "validation.validation_master_plan",
    "signature.signatures",
    "signature.signature_challenges",
    "signature.signature_policies",
    "rules.gxp_rule_evaluation",
    "rules.gxp_rule_definition",
    "rules.gxp_uom_conversion",
    "rules.gxp_uom",
    "vault.gxp_record_correction",
    "vault.gxp_vault_evidence",
    "vault.gxp_vault_object",
    "mutation.idempotency_keys",
    "mutation.outbox_events",
    "mutation.command_receipts",
    "audit.audit_events",
    "iam.service_identities",
    "iam.user_site_roles",
    "iam.qualifications",
    "iam.sod_exceptions",
    "iam.sod_rules",
    "iam.role_permissions",
    "iam.permissions",
    "iam.users",
    "iam.roles",
    "iam.sites",
    "iam.organizations",
]

# Truncated via the migration role, not the runtime app role: `signature.signatures`/`audit.audit_events`
# are deliberately append-only for the app role (AG-08, migration 0002 revokes UPDATE/DELETE on both, and
# this project correctly does not grant them TRUNCATE either -- see migration 0094). Postgres's `TRUNCATE
# ... CASCADE` semantics force the issue for the *whole* combined statement, not just those two tables:
# `signature.signatures` carries an FK to `iam.users`, so truncating `iam.users` (needed for cleanup, and
# granted to the app role by migration 0094) would itself need to cascade into `signatures` and fail the
# same way. Rather than hand-picking which subset of the 252-table cleanup list happens to chain into an
# append-only table via some FK path (fragile and silently stale the next time a schema changes), the
# whole cleanup truncate runs as the migration role, which owns every table. This is pure test-harness
# reset plumbing, not part of what any test exercises -- the actual command handlers under test still run
# through `SessionLocal`/the app role exactly as in production; only this between-test reset is
# privileged, the same pattern test_audit_review.py/test_vault.py/test_batch_flow.py already use for
# other test-only operations that must bypass the app role's restricted grants.
_migration_engine = create_async_engine(settings.migration_database_url)


@pytest.fixture(autouse=True)
async def clean_database():
    """Full truncate between tests. Simple and correct beats clever for a small test suite."""
    async with _migration_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(APP_TABLES)} CASCADE"))
    yield


@pytest.fixture
async def db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
async def seeded(db: AsyncSession) -> dict:
    """Same reference data as scripts/seed.py, inlined so tests don't depend on a separate run."""
    async with db.begin():
        org = Organization(name="Test Org")
        db.add(org)
        await db.flush()

        site = Site(organization_id=org.id, code="T1", name="Test Site")
        db.add(site)
        await db.flush()

        # Document 20 (SPEC-MAT-002B) INV-FR-001/002: warehouse_location has no CRUD API (SG-081) --
        # seed-only, same rows scripts/seed.py's WAREHOUSE_LOCATION_FLOOR upserts.
        locations = {}
        for warehouse_code, location_code, zone_type in (
            ("WH1", "QUARANTINE-01", "quarantine"),
            ("WH1", "RELEASED-01", "released"),
            ("WH1", "REJECTED-01", "rejected"),
        ):
            location = WarehouseLocation(
                site_id=site.id, warehouse_code=warehouse_code, location_code=location_code,
                zone_type=zone_type, status="active",
            )
            db.add(location)
            locations[location_code] = location
        await db.flush()

        # Document 39 (SPEC-EQP-002) -- same rows scripts/seed.py's EQUIPMENT_AREA_FLOOR/
        # CLEANING_PROCEDURE_FLOOR upsert.
        areas = {}
        for area_code, area_type, classification, criticality in (
            ("AREA-GRADE-A", "cleanroom", "ISO_5", "critical"),
            ("AREA-GRADE-C", "cleanroom", "ISO_7", "non_critical"),
            ("AREA-WAREHOUSE", "warehouse", None, "non_critical"),
        ):
            area = EquipmentArea(
                site_id=site.id, area_code=area_code, area_type=area_type,
                classification=classification, criticality=criticality, status="active",
            )
            db.add(area)
            areas[area_code] = area
        await db.flush()

        cleaning_procedures = {}
        for procedure_number, cleaning_type, dirty_limit, clean_limit in (
            ("CLN-PROC-001", "routine", 240, 4320),
        ):
            procedure = CleaningProcedureVersion(
                site_id=site.id, procedure_number=procedure_number, version_no=1,
                cleaning_type=cleaning_type, dirty_hold_limit_minutes=dirty_limit,
                clean_hold_limit_minutes=clean_limit, state="RELEASED",
            )
            db.add(procedure)
            cleaning_procedures[procedure_number] = procedure
        await db.flush()

        # Document 41 (SPEC-EQP-004) -- same rows scripts/seed.py upserts.
        em_program = EmProgramVersion(
            site_id=site.id, program_number="EM-PROG-001", version_no=1,
            monitoring_types={"types": ["viable_air", "surface_contact"]},
        )
        db.add(em_program)
        em_locations = {}
        for location_code, area_code, criticality in (
            ("EM-LOC-GRADE-A-01", "AREA-GRADE-A", "critical"),
            ("EM-LOC-GRADE-C-01", "AREA-GRADE-C", "non_critical"),
        ):
            location = EmLocation(
                site_id=site.id, area_id=areas[area_code].id, location_code=location_code,
                criticality=criticality, status="active",
            )
            db.add(location)
            em_locations[location_code] = location
        await db.flush()

        # Document 42 (SPEC-EQP-005) -- same row scripts/seed.py upserts.
        sterilization_profile = ProcessCycleProfileVersion(
            site_id=site.id, profile_number="STR-PROC-001", version_no=1, process_type="steam_autoclave",
            sterile_status_validity_hours=72, state="RELEASED",
        )
        db.add(sterilization_profile)
        await db.flush()

        # Document 40 (SPEC-EQP-003) -- same row scripts/seed.py upserts.
        aseptic_profile = AsepticProfileVersion(
            site_id=site.id, profile_number="ASP-PROC-001", version_no=1,
            required_area_classification="ISO_5", state="RELEASED",
        )
        db.add(aseptic_profile)
        await db.flush()

        # Document 43 (SPEC-EDGE-001) -- same row scripts/seed.py upserts (DEMO_EDGE_BOOTSTRAP_TOKEN).
        db.add(
            EdgeEnrollmentToken(
                site_id=site.id, token_hash=sha256_hex(DEMO_EDGE_BOOTSTRAP_TOKEN),
                status="unused", expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
        )
        await db.flush()

        # Document 48 (SPEC-ERP-001) -- same row scripts/seed.py's DEMO_ERP_INSTANCE upserts.
        erp_instance = ErpInstance(
            site_id=site.id, instance_name="demo-erpnext", vendor="ERPNEXT", environment="SANDBOX",
            base_url="https://erpnext.demo.invalid", auth_method="API_KEY", auth_secret_ref="demo-key:demo-secret",
            contract_version="v14-resource-api",
            capabilities={"supported_operations": [
                "SYNC_MATERIAL_ITEM", "SYNC_SUPPLIER", "SYNC_WAREHOUSE_LOCATION", "SYNC_UOM",
                "POST_GOODS_RECEIPT", "POST_CONSUMPTION", "POST_RETURN", "POST_SCRAP_DESTRUCTION",
                "POST_FINISHED_GOODS_RECEIPT", "POST_QUALITY_STATUS", "GET_PRODUCTION_ORDER_REFERENCE",
                "FETCH_MASTER_DATA_CHANGES",
                # ERP-ARC-008/011/016 -- WP-07 completion pass.
                "POST_PURCHASE_ORDER_REF", "POST_RESERVATION", "POST_RELEASE_AVAILABILITY", "GET_PURCHASE_ORDER_REFERENCE",
            ]}, status="ACTIVE",
        )
        db.add(erp_instance)
        await db.flush()

        # Document 17 (SPEC-EBMR-008) -- same released floor rule scripts/seed.py upserts (the literal
        # formula Document 17 §3 gives; Document 110 CC-4 precision/rounding).
        db.add(
            RuleDefinition(
                rule_id="yield_percent", rule_type="CALCULATION", semantic_version="1.0.0",
                status="released", effective_from=datetime.now(timezone.utc) - timedelta(days=1),
                expression_ast={
                    "op": "*",
                    "args": [{"op": "/", "args": [{"var": "actual_yield"}, {"var": "theoretical_yield"}]}, 100],
                },
                input_contract={"actual_yield": {"type": "decimal"}, "theoretical_yield": {"type": "decimal"}},
                output_contract={"type": "decimal"},
                unit_policy={"dimension": "percentage", "conversion": "none"},
                # SG-146: calculation_class is what app/modules/rules/precision.py resolves -- CC-4 fixes
                # storage precision, rounding mode/stage and reported dp (2) by table.
                precision_policy={"calculation_class": "CC-4"},
                rounding_policy={"policy_version": "DOCUMENT-110-v1.0"},
                engine_compatibility="v1",
            )
        )
        await db.flush()

        roles = {}
        for name in (
            "Admin", "Operator", "Supervisor", "QA Reviewer", "QA Releaser", "QC Reviewer",
            # Document 38 (SPEC-EQP-001) — same rows scripts/seed.py's ROLE_NAMES adds.
            "Equipment Administrator", "Engineering Manager", "Calibration Technician", "Maintenance Technician",
            # Document 39 (SPEC-EQP-002) — same row scripts/seed.py's ROLE_NAMES adds.
            "Sanitation Operator",
            # Document 41 (SPEC-EQP-004) — same rows scripts/seed.py's ROLE_NAMES adds.
            "EM Technician", "Microbiology Analyst",
            # Document 42 (SPEC-EQP-005) — same row scripts/seed.py's ROLE_NAMES adds.
            "Sterilization Operator",
            # Document 40 (SPEC-EQP-003) — same rows scripts/seed.py's ROLE_NAMES adds.
            "Aseptic Operator", "Aseptic Supervisor",
            # Document 10 (SPEC-EBMR-002) — dedicated master-recipe author (SG-178 authoring-SoD half).
            "Process Engineer",
            # WP-07 (Documents 48/52/53) — same row scripts/seed.py's ROLE_NAMES adds.
            "Integration Administrator",
            # WP-08 (Document 54, SPEC-DDCP-001) — same rows scripts/seed.py's ROLE_NAMES adds.
            "DDCP Engineer", "DDCP Operator",
            # WP-10 (Document 63, SPEC-SEC-003) — same rows scripts/seed.py's ROLE_NAMES adds.
            "Platform Admin", "Vendor Support Engineer",
            # WP-09 (Documents 58-60) / SG-138 (2026-09-10): Document 106 section 9 rows 102/105's
            # "Regulatory Affairs authorized submitter" signer class for QMS reportability assessments.
            "Postmarket Regulatory Affairs",
        ):
            role = Role(name=name)
            db.add(role)
            roles[name] = role
        await db.flush()

        users = {}
        for username, role_name in (
            ("operator1", "Operator"),
            ("qa.reviewer", "QA Reviewer"),
            ("qa.releaser", "QA Releaser"),
            ("qc.reviewer", "QC Reviewer"),
            ("equipment.admin", "Equipment Administrator"),
            ("engineering.manager", "Engineering Manager"),
            ("calibration.tech", "Calibration Technician"),
            ("maintenance.tech", "Maintenance Technician"),
            ("sanitation.operator", "Sanitation Operator"),
            ("em.technician", "EM Technician"),
            ("microbiology.analyst", "Microbiology Analyst"),
            ("sterilization.operator", "Sterilization Operator"),
            ("aseptic.operator", "Aseptic Operator"),
            ("aseptic.supervisor", "Aseptic Supervisor"),
            ("process.engineer", "Process Engineer"),
            ("integration.admin", "Integration Administrator"),
            ("ddcp.engineer", "DDCP Engineer"),
            ("ddcp.operator", "DDCP Operator"),
        ):
            user = User(
                username=username,
                email=f"{username}@example.com",
                full_name=username,
                password_hash=hash_password(DEMO_PASSWORD),
                status="active",
            )
            db.add(user)
            await db.flush()
            db.add(UserSiteRole(user_id=user.id, site_id=site.id, role_id=roles[role_name].id))
            users[username] = user

        # Document 21 (SPEC-MAT-002C) DSP-FR-005: operator1's current dispensing_operator qualification --
        # `iam.Qualification` exists but was enforced by zero commands until this document's session wired
        # it up for real (see app/modules/material/commands.py::_check_dispensing_qualification).
        db.add(
            Qualification(
                user_id=users["operator1"].id,
                qualification_code="dispensing_operator",
                expires_at=None,
            )
        )

        # Document 106 signature policy floor — same rows scripts/seed.py upserts. All four record_type/
        # action pairs that have a real call site today must be present, or the fail-closed resolver
        # (REMEDIATION_R1 FIX 1) rejects every batch/material command with SIGNATURE_POLICY_UNRESOLVED.
        db.add(
            SignaturePolicy(
                record_type="batch_step",
                action="complete_step",
                meaning="Performed",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        # Document 106 rows 19/21 -- the new batch_execution module's own results/complete endpoints
        # (SG-047 partial resolution, 2026-09-09), distinct from the legacy complete_step row above.
        db.add(
            SignaturePolicy(
                record_type="batch_step",
                action="results",
                meaning="Performed",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="batch_step",
                action="complete",
                meaning="Performed",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        # BAT-FR-020 step-scoped hold/resume + BAT-FR-026 production-complete (SG-047/SG-048 further
        # partial resolution, 2026-09-09).
        db.add(
            SignaturePolicy(
                record_type="batch_step",
                action="hold",
                meaning="Performed",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                reason_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="batch_step",
                action="resume",
                meaning="Approved",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="batch",
                action="production_complete",
                meaning="Performed",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="batch",
                action="review",
                meaning="Reviewed",
                required_role_id=roles["QA Reviewer"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="batch",
                action="release",
                meaning="Released",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="material_lot",
                action="disposition",
                meaning="Approved",
                required_role_id=roles["QC Reviewer"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="material_lot",
                action="release",
                meaning="Released",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="material_lot",
                action="reject",
                meaning="Rejected",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="supplier_qualification",
                action="approve",
                meaning="Approved",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="qc_test_specification",
                action="release",
                meaning="Released",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="qc_test_order",
                action="review",
                meaning="Reviewed",
                required_role_id=roles["QA Reviewer"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="qc_result",
                action="correct",
                meaning="Approved",
                required_role_id=roles["QC Reviewer"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="lims_sample",
                action="cancel",
                meaning="Approved",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="oos_record",
                action="extended_investigation",
                meaning="Approved",
                required_role_id=roles["QA Reviewer"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="oos_record",
                action="disposition",
                meaning="Released",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="oos_record",
                action="close",
                meaning="Approved",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="oot_record",
                action="close",
                meaning="Approved",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="inventory_reservation",
                action="release",
                meaning="Released",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                reason_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        # Document 106 rows 47-54 (SPEC-MAT-002C) -- row 47 (order creation) intentionally has no row
        # here either, matching scripts/seed.py: create_dispensing_order is unsigned/RBAC-gated (SG-087).
        for record_type, action, meaning, role_name, independent, reason_required in (
            ("dispensing_order", "select_source", "Performed", "Operator", False, False),
            ("dispensing_order", "start", "Performed", "Operator", False, False),
            ("dispensing_order", "readings", "Performed", "Operator", False, False),
            ("dispensing_order", "manual_reading", "Performed", "Operator", False, False),
            ("dispensing_order", "verify", "Verified", "QC Reviewer", True, False),
            ("dispensing_order", "complete", "Performed", "Operator", False, False),
            ("dispensing_order", "cancel", "Approved", "QA Releaser", True, True),
        ):
            db.add(
                SignaturePolicy(
                    record_type=record_type,
                    action=action,
                    meaning=meaning,
                    required_role_id=roles[role_name].id,
                    requires_independent_signer=independent,
                    signature_required=True,
                    reason_required=reason_required,
                    policy_source="PLATFORM_FLOOR",
                )
            )

        # Document 106 rows 55/56 (SPEC-MAT-002D, Document 22) -- same rows scripts/seed.py upserts.
        db.add(
            SignaturePolicy(
                record_type="inventory_adjustment_request",
                action="approve",
                meaning="Approved",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                reason_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="destruction_record",
                action="execute",
                meaning="Performed",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                reason_required=False,
                policy_source="PLATFORM_FLOOR",
            )
        )
        # SG-035 pair 4 (record_correction/complete), RESOLVED 2026-09-11, project-owner-directed
        # (PHASE_3_DEFERRED_DECISIONS.md item D). Document 106 section 9 row 1: `Approved`, count 2,
        # "Corrector and approver MUST differ", reason mandatory. Position 1 ("Authorized corrector") ->
        # no fixed role (RBAC `vault.correct` gates who may attempt it); position 2 ("independent
        # approver") -> `QA Releaser`. No test file adds its own local record_correction/complete row
        # (only test_vault.py exercises it, using this global row).
        db.add(
            SignaturePolicy(
                record_type="record_correction",
                action="complete",
                meaning="Approved",
                required_role_id=None,
                requires_independent_signer=True,
                signature_required=True,
                signature_count=2,
                signature_order=[None, "QA Releaser"],
                reason_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        # Document 106 section 9 row 9 (SPEC-EBMR-000) -- SG-035 partial, 2026-09-10, project-owner-
        # directed ("follow the ebmr-edhr docs"): product_version/suspend is `Performed` by an
        # "Authorized holder (Production / QA)" (role pair -> required_role_id=None; RBAC product.suspend
        # gates it), Independence "None", Reason "yes". Same row scripts/seed.py's SIGNATURE_POLICY_FLOOR
        # adds. product_version/reinstate has no Document 106 row and stays unresolved (SG-035, deferred).
        db.add(
            SignaturePolicy(
                record_type="product_version",
                action="suspend",
                meaning="Performed",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                reason_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        # product_version/reinstate -- SG-035 pair 5, RESOLVED 2026-09-11, project-owner-directed
        # (PHASE_3_DEFERRED_DECISIONS.md item B). No test file adds its own local product_version/
        # reinstate row (only test_product_master.py exercises it, and it uses this global row).
        db.add(
            SignaturePolicy(
                record_type="product_version",
                action="reinstate",
                meaning="Approved",
                required_role_id=roles["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
                reason_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        # SG-167 -- all 5 AI-governance pairs, RESOLVED 2026-09-11, project-owner-directed
        # (PHASE_3_DEFERRED_DECISIONS.md item C). No test file adds its own local row for any of the 5
        # ai_governance record types -- test_ai_governance.py's 5 formerly "fails closed, no policy" tests
        # were rewritten to exercise the real ceremony against this global row.
        for record_type, action, meaning, role_name, independent, reason in (
            ("ai_model_deployment", "approve", "Approved", "QA Releaser", True, True),
            ("ai_tool_call", "authorize", "Approved", "QA Releaser", True, True),
            ("ai_disposition", "record", "Performed", None, False, False),
            ("ai_release_gate", "evaluate", "Released", "QA Releaser", True, True),
            ("ai_provider_switch", "switch", "Approved", "QA Releaser", True, True),
        ):
            db.add(
                SignaturePolicy(
                    record_type=record_type,
                    action=action,
                    meaning=meaning,
                    required_role_id=roles[role_name].id if role_name else None,
                    requires_independent_signer=independent,
                    signature_required=True,
                    reason_required=reason,
                    policy_source="PLATFORM_FLOOR",
                )
            )
        # Document 106 row 108 (SPEC-EQP-001) -- same row scripts/seed.py upserts.
        db.add(
            SignaturePolicy(
                record_type="equipment_asset",
                action="hold",
                meaning="Performed",
                required_role_id=None,
                requires_independent_signer=False,
                signature_required=True,
                reason_required=True,
                policy_source="PLATFORM_FLOOR",
            )
        )
        # Document 106 rows 109-111 (SPEC-EQP-002) -- same rows scripts/seed.py upserts.
        for record_type, action, meaning, independent in (
            ("cleaning_execution", "complete", "Performed", False),
            ("cleaning_execution", "verify", "Verified", True),
            ("line_clearance", "complete", "Performed", False),
            ("em_sample_or_reading", "record_result", "Performed", False),
            ("em_sample_or_reading", "review", "Reviewed", True),
            ("sterile_filter_use", "complete", "Performed", False),
            ("process_cycle", "review", "Reviewed", True),
            ("process_cycle", "start", "Performed", False),
            ("aseptic_operation", "complete", "Performed", False),
            ("aseptic_operation", "start", "Performed", False),
        ):
            db.add(
                SignaturePolicy(
                    record_type=record_type,
                    action=action,
                    meaning=meaning,
                    required_role_id=None,
                    requires_independent_signer=independent,
                    signature_required=True,
                    reason_required=False,
                    policy_source="PLATFORM_FLOOR",
                )
            )

        # Document 43 (SPEC-EDGE-001) -- same rows scripts/seed.py upserts. "enroll" is SG-118's interim
        # baseline (Admin, independent=False); "certificate_rotation" is Document 106 row 119 (QA
        # Releaser, independent=True). Both reason_required=True.
        db.add(
            SignaturePolicy(
                record_type="edge_gateway", action="enroll", meaning="Approved",
                required_role_id=roles["Admin"].id, requires_independent_signer=False,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="edge_gateway", action="certificate_rotation", meaning="Released",
                required_role_id=roles["QA Releaser"].id, requires_independent_signer=True,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )
        # SG-119: pure gateway-to-server machine calls -- Document 106 P7 makes a human signature
        # structurally impossible, so signature_required=False is the recorded resolution.
        for record_type, action in (
            ("edge_gateway", "observation_batch"),
            ("edge_gateway", "health_report"),
            ("edge_gateway", "security_event"),
        ):
            db.add(
                SignaturePolicy(
                    record_type=record_type, action=action, meaning="Performed", required_role_id=None,
                    requires_independent_signer=False, signature_required=False, reason_required=False,
                    policy_source="PLATFORM_FLOOR",
                )
            )

        # WP-07 (Documents 48/52/53) -- SG-122: Document 106 has zero rows for any SPEC-ERP-00x action.
        # Same "record the deliberate resolution" discipline as the edge_gateway machine-call rows above.
        for record_type, action, meaning in (
            ("erp_instance", "register", "Performed"),
            ("erp_external_mapping", "approve", "Approved"),
            ("erp_mapping_conflict", "resolve", "Approved"),
        ):
            db.add(
                SignaturePolicy(
                    record_type=record_type, action=action, meaning=meaning, required_role_id=None,
                    requires_independent_signer=False, signature_required=False, reason_required=False,
                    policy_source="PLATFORM_FLOOR",
                )
            )

        # WP-08 (Document 54, SPEC-DDCP-001) -- SG-148: Document 106 has zero rows for any SPEC-DDCP-00x
        # action. Same "record the deliberate resolution" discipline as the erp_instance rows above.
        for record_type, action, meaning in (
            ("ddcp_profile_version", "release", "Released"),
            ("constituent_handoff", "decide", "Approved"),
            ("fill_operation", "start", "Performed"),
            ("fill_operation", "complete", "Performed"),
        ):
            db.add(
                SignaturePolicy(
                    record_type=record_type, action=action, meaning=meaning, required_role_id=None,
                    requires_independent_signer=False, signature_required=False, reason_required=False,
                    policy_source="PLATFORM_FLOOR",
                )
            )

        # Document 47 (SPEC-EDGE-005) -- Document 106 has zero rows for any SPEC-EDGE-005 action, same
        # rows scripts/seed.py upserts. SG-127 (signal_mapping.release, QA Releaser, independent of the
        # drafting actor), SG-128 (machine_command_profile.submit, Equipment Administrator, independent=
        # False), SG-131 (machine_replay_job.replay, Integration Administrator, independent=False) are
        # human-signed; SG-129's 3 machine-to-machine ops are signature_required=False (Doc 106 P7).
        db.add(
            SignaturePolicy(
                record_type="signal_mapping", action="release", meaning="Released",
                required_role_id=roles["QA Releaser"].id, requires_independent_signer=True,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="machine_command_profile", action="submit", meaning="Approved",
                required_role_id=roles["Equipment Administrator"].id, requires_independent_signer=False,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="machine_replay_job", action="replay", meaning="Approved",
                required_role_id=roles["Integration Administrator"].id, requires_independent_signer=False,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )
        for record_type, action in (
            ("machine_source", "evidence_ingest"),
            ("machine_source", "cycle_evidence_manifest"),
            ("machine_command_request", "finalize"),
        ):
            db.add(
                SignaturePolicy(
                    record_type=record_type, action=action, meaning="Performed", required_role_id=None,
                    requires_independent_signer=False, signature_required=False, reason_required=False,
                    policy_source="PLATFORM_FLOOR",
                )
            )

        # Document 17 (SPEC-EBMR-008) -- Document 106 row 40: `verify` requires a "Qualified independent
        # verifier", independent of the performer (checked in code), no dedicated role named. Same rows
        # scripts/seed.py upserts.
        for record_type in ("manufacturing_calculation", "reconciliation_record"):
            db.add(
                SignaturePolicy(
                    record_type=record_type, action="verify", meaning="Verified", required_role_id=None,
                    requires_independent_signer=True, signature_required=True, reason_required=False,
                    policy_source="PLATFORM_FLOOR",
                )
            )

        # WP-10 (Document 63, SPEC-SEC-003) -- Document 106 rows 134-136, same rows scripts/seed.py upserts.
        db.add(
            SignaturePolicy(
                record_type="admin_command", action="execute", meaning="Performed", required_role_id=None,
                requires_independent_signer=False, signature_required=True, reason_required=False,
                policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="privileged_access_request", action="approve", meaning="Approved",
                required_role_id=roles["QA Releaser"].id, requires_independent_signer=True,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )
        db.add(
            SignaturePolicy(
                record_type="privileged_session", action="close", meaning="Approved",
                required_role_id=roles["QA Releaser"].id, requires_independent_signer=True,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )

        # WP-10 (Document 65, SPEC-SEC-005) -- Document 106 rows 137-139: certificate issue/rotate/revoke
        # each require a `Released` signature by an independent QA Releaser. Same rows scripts/seed.py upserts.
        for _cert_action in ("issue", "rotate", "revoke"):
            db.add(
                SignaturePolicy(
                    record_type="certificate", action=_cert_action, meaning="Released",
                    required_role_id=roles["QA Releaser"].id, requires_independent_signer=True,
                    signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
                )
            )

        # WP-10 (Document 67, SPEC-SEC-007) -- Document 106 row 140: security-incident close requires an
        # `Approved` signature by an independent QA Releaser. Same row scripts/seed.py upserts.
        db.add(
            SignaturePolicy(
                record_type="security_incident", action="close", meaning="Approved",
                required_role_id=roles["QA Releaser"].id, requires_independent_signer=True,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )

        # WP-11 (Document 72, SPEC-DATA-004) -- Document 106 row 142: evidence legal hold is
        # `Performed` by an "Authorized holder (Production / QA)" -- a role pair, so required_role_id
        # is None and RBAC `evidence.legal_hold` defines the holder; independence None; reason
        # required. Exact precedent = Document 106 row 108 (equipment_asset/hold). Same row
        # scripts/seed.py upserts.
        db.add(
            SignaturePolicy(
                record_type="evidence_object", action="legal_hold", meaning="Performed",
                required_role_id=None, requires_independent_signer=False,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )

        # WP-12/WP-14 (Documents 79-96, SPEC-VAL-001..018) -- Document 106 rows 144-171, the complete
        # 28-row validation-platform signature-policy block (SG-172's "policy-data half"). Confirmed
        # 2026-09-10 (SG-184/SG-172 gap-fixing pass): all 28 rows are approved in Document 106 and were
        # simply never transcribed anywhere -- not a regulated decision left to make here, a transcription
        # gap. "Module approver role (QA Manager / Head of Quality per record class)" and "Elevated
        # authority defined by the record class" both map to this codebase's "QA Releaser" -- same
        # established precedent as every other "Module approver role" row above (e.g. row 55/56's
        # inventory_adjustment_request.approve), and QA Releaser already holds every validation.*.approve/
        # release/authorize/deployment_check/disposition/triage/retest_plan/create permission code
        # (scripts/seed.py ROLE_PERMISSIONS) -- the permission layer already assumed this exact mapping.
        # Same 28 rows scripts/seed.py's SIGNATURE_POLICY_FLOOR upserts.
        for _rt, _act in (
            ("function_risk_assessment", "approve"),          # row 145
            ("validation_test_definition", "approve"),        # row 147
            ("iq_execution", "approve"),                      # row 148
            ("oq_execution", "approve"),                      # row 150
            ("pq_scenario", "approve"),                       # row 151
            ("infrastructure_fingerprint", "approve"),        # row 152
            ("migration_run", "approve"),                     # row 153
            ("part11_scope_assessment", "approve"),           # row 154
            ("data_integrity_test_profile", "approve"),       # row 155
            ("interface_validation_profile", "approve"),      # row 156
            ("dr_qualification_execution", "approve"),        # row 157
            ("security_qualification_suite", "approve"),      # row 158
            ("validation_exception", "create"),               # row 162
            ("validation_exception", "retest_plan"),          # row 164
            ("validation_exception", "triage"),               # row 165
            ("validation_summary_report", "approve"),         # row 169
        ):
            db.add(
                SignaturePolicy(
                    record_type=_rt, action=_act, meaning="Approved",
                    required_role_id=roles["QA Releaser"].id, requires_independent_signer=True,
                    signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
                )
            )
        for _rt, _act in (
            ("validation_master_plan", "release"),            # row 144
            ("validation_exception", "disposition"),          # row 163
            ("validated_release_authorization", "authorize"),        # row 166
            ("validated_release_authorization", "deployment_check"),  # row 167
        ):
            db.add(
                SignaturePolicy(
                    record_type=_rt, action=_act, meaning="Released",
                    required_role_id=roles["QA Releaser"].id, requires_independent_signer=True,
                    signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
                )
            )
        # "Qualified performer for the task", independence "None required unless the step is flagged
        # critical" -- same no-fixed-role treatment as every other "qualified performer" row (e.g.
        # dispensing_order.start above); the per-record critical-flag conditional isn't built this pass
        # (no commands_*.py in app/modules/validation/ checks a `critical` flag for these actions today),
        # so independent=False/reason_required=False at the floor level, same documented limitation as
        # cleaning_execution.complete/equipment_asset.hold's own critical-flag callouts above.
        for _rt, _act in (
            ("validation_test_execution", "complete"),  # row 146
            ("iq_execution", "complete"),                # row 149
            ("performance_run", "create"),               # row 159
            ("performance_qualification_scenario", "create"),  # row 160
            ("performance_run", "evaluate"),             # row 161
        ):
            db.add(
                SignaturePolicy(
                    record_type=_rt, action=_act, meaning="Performed",
                    required_role_id=None, requires_independent_signer=False,
                    signature_required=True, reason_required=False, policy_source="PLATFORM_FLOOR",
                )
            )
        for _act in ("create", "decision"):  # rows 170/171
            db.add(
                SignaturePolicy(
                    record_type="periodic_validation_review", action=_act, meaning="Reviewed",
                    required_role_id=roles["QA Reviewer"].id, requires_independent_signer=True,
                    signature_required=True, reason_required=False, policy_source="PLATFORM_FLOOR",
                )
            )
        # Row 168 (POST /validation/v1/summary-reports, VSR authoring/create): "Regulatory Affairs
        # authorized submitter" -- the identical phrase Document 106 rows 123/125-128 (Document 59) use,
        # already mapped in this codebase to the "Postmarket Regulatory Affairs" role (see the WP-09/
        # SG-138 certificate/incident rows above); reused verbatim here as the literal, least-inventive
        # reading rather than guessing a validation-specific role no spec names. Independence column says
        # "MUST be a human; service identity prohibited (SIG-FR-023)" -- an identity-type restriction, not
        # an independence-from-another-actor requirement, so requires_independent_signer=False (no
        # commands_vsr.py call site resolves this action today -- create_validation_summary_report is
        # unsigned/RBAC-gated per SG-172's own affected_functions list -- this row is inert until that
        # changes, kept only so the floor is complete rather than partially transcribed).
        db.add(
            SignaturePolicy(
                record_type="validation_summary_report", action="create", meaning="Approved",
                required_role_id=roles["Postmarket Regulatory Affairs"].id, requires_independent_signer=False,
                signature_required=True, reason_required=True, policy_source="PLATFORM_FLOOR",
            )
        )

        # NOTE: no global product_version/release row here, deliberately -- SG-035 PARTIALLY RESOLVED
        # 2026-09-07 (project-owner-directed: self-signed by Admin) added this row to the *live-DB* floor
        # (scripts/seed.py SIGNATURE_POLICY_FLOOR, applied via scripts/sync_signature_policies.py), but at
        # least 6 other test files (test_release.py, test_device.py, test_qa_review.py,
        # test_batch_execution.py, test_packaging.py, test_yield_reconciliation.py) already add their own
        # *local*, per-test product_version/release row (with signature_required=False, for cheap
        # unsigned-release test setup unrelated to what they're actually testing) -- adding it here too
        # would collide with every one of them on UniqueConstraint(record_type, action). Product Master's
        # own tests (test_product_master.py) that need the real, signed version add their own local row
        # instead, same pattern as everyone else, just with the real values.

        # WP-01 Document 07 permission catalog + role grants — same rows scripts/seed.py upserts. Every
        # rewired evaluate_policy() call site needs these or it fail-closes with ROLE_MISSING for all
        # six roles, same fail-closed discipline as the signature floor above.
        permissions = {}
        for code, action, resource_type in (
            ("batch_step.start", "execute", "batch_step"),
            ("batch_step.role_override", "role_override", "batch_step"),
            ("batch.review", "review", "batch"),
            ("batch.release", "release", "batch"),
            ("material_lot.disposition", "approve", "material_lot"),
            ("platform.administer", "administer", "platform"),
            ("audit.review", "review", "audit_event"),
            ("audit.export", "export", "audit_event"),
            ("vault.review", "review", "vault_object"),
            ("vault.correct", "correct", "vault_object"),
            ("rules.author", "author", "rule"),
            ("rules.release", "release", "rule"),
            ("rules.evaluate", "evaluate", "rule"),
            ("product.author", "author", "product_version"),
            ("product.release", "release", "product_version"),
            ("product.suspend", "suspend", "product_version"),
            ("product.view", "view", "product_version"),
            ("recipe.author", "author", "recipe_version"),
            ("recipe.release", "release", "recipe_version"),
            ("recipe.view", "view", "recipe_version"),
            ("batch_execution.create", "create", "batch"),
            ("batch_execution.issue", "issue", "batch"),
            ("batch_execution.execute", "execute", "batch"),
            ("batch_execution.view", "view", "batch"),
            ("device.create", "create", "device_unit"),
            ("device.execute", "execute", "device_unit"),
            ("device.view", "view", "device_unit"),
            ("genealogy.view", "view", "genealogy_node"),
            ("qa_review.create", "create", "qa_review_package"),
            ("qa_review.execute", "execute", "qa_review_package"),
            ("qa_review.view", "view", "qa_review_package"),
            ("release.evaluate", "evaluate", "release_scope"),
            ("release.release", "release", "release_scope"),
            ("release.hold", "hold", "release_scope"),
            ("release.reject", "reject", "release_scope"),
            ("release.view", "view", "release_scope"),
            ("packaging.execute", "execute", "packaging_run"),
            ("supplier_qualification.approve", "approve", "supplier_qualification"),
            ("qms_deviation.create", "create", "deviation_record"),
            ("qms_deviation.triage", "triage", "deviation_record"),
            ("qms_deviation.contain", "contain", "deviation_record"),
            ("qms_deviation.investigate", "investigate", "deviation_record"),
            ("qms_deviation.impact", "impact", "deviation_record"),
            ("qms_deviation.disposition", "disposition", "deviation_record"),
            ("qms_deviation.extend", "extend", "deviation_record"),
            ("qms_deviation.close", "close", "deviation_record"),
            ("qms_deviation.reopen", "reopen", "deviation_record"),
            ("capa.create", "create", "capa_record"),
            ("capa.plan", "plan", "capa_record"),
            ("capa.action.add", "add", "capa_action"),
            ("capa.action.complete", "complete", "capa_action"),
            ("capa.effectiveness", "effectiveness", "capa_record"),
            ("capa.extend", "extend", "capa_record"),
            ("capa.close", "close", "capa_record"),
            ("capa.reopen", "reopen", "capa_record"),
            ("ncr.create", "create", "nonconformance_record"),
            ("ncr.segregate", "segregate", "nonconformance_record"),
            ("ncr.evaluate", "evaluate", "nonconformance_record"),
            ("ncr.disposition", "disposition", "nonconformance_record"),
            ("ncr.verify", "verify", "nonconformance_record"),
            ("ncr.close", "close", "nonconformance_record"),
            ("change.create", "create", "change_control"),
            ("change.impact", "impact", "change_control"),
            ("change.approve", "approve", "change_control"),
            ("change.task.add", "add", "change_task"),
            ("change.implement", "implement", "change_control"),
            ("change.verify", "verify", "change_control"),
            ("change.make_effective", "make_effective", "change_control"),
            ("change.close", "close", "change_control"),
            ("document.create", "create", "controlled_document"),
            ("document.submit", "submit", "controlled_document_version"),
            ("document.release", "release", "controlled_document_version"),
            ("document.make_effective", "make_effective", "controlled_document_version"),
            ("document.obsolete", "obsolete", "controlled_document_version"),
            ("document.controlled_copy.issue", "issue", "controlled_copy"),
            ("document.view", "view", "controlled_document"),
            ("training.requirement.create", "create", "training_requirement"),
            ("training.assignment.create", "create", "training_assignment"),
            ("training.assignment.complete", "complete", "training_assignment"),
            ("training.assignment.assess", "assess", "training_assignment"),
            ("training.qualification.create", "create", "qualification_record"),
            ("training.waiver.create", "create", "training_waiver"),
            ("training.subject.view", "view", "training_assignment"),
            ("training.matrix.view", "view", "training_requirement"),
            ("qc_test_specification.release", "release", "qc_test_specification"),
            ("qc_test_order.review", "review", "qc_test_order"),
            ("qc_result.correct", "correct", "qc_result"),
            ("lims_sample.cancel", "cancel", "lims_mapping"),
            ("oos_record.extended_investigation", "extended_investigation", "oos_record"),
            ("oos_record.disposition", "disposition", "oos_record"),
            ("oos_record.close", "close", "oos_record"),
            ("oot_record.close", "close", "oot_record"),
            ("material_receipt.create", "create", "material_receipt"),
            ("material_receipt.examine", "examine", "material_receipt"),
            ("material_lot.sampling_order", "create", "material_lot"),
            ("material_lot.collect_sample", "execute", "material_lot"),
            ("material_lot.release", "release", "material_lot"),
            ("material_lot.reject", "reject", "material_lot"),
            ("material_lot.retest", "retest", "material_lot"),
            ("inventory_reservation.create", "create", "inventory_reservation"),
            ("inventory_reservation.release", "release", "inventory_reservation"),
            ("inventory_transaction.transfer", "transfer", "inventory_transaction"),
            ("material_container.split", "split", "material_container"),
            ("material_container.merge", "merge", "material_container"),
            ("inventory_cycle_count.execute", "execute", "inventory_cycle_count"),
            ("dispensing_order.create", "create", "dispensing_order"),
            ("dispensing_order.select_source", "select_source", "dispensing_order"),
            ("dispensing_order.start", "start", "dispensing_order"),
            ("dispensing_order.readings", "readings", "dispensing_order"),
            ("dispensing_order.manual_reading", "manual_reading", "dispensing_order"),
            ("dispensing_order.verify", "verify", "dispensing_order"),
            ("dispensing_order.complete", "complete", "dispensing_order"),
            ("dispensing_order.cancel", "cancel", "dispensing_order"),
            ("material_consumption.create", "create", "material_consumption"),
            ("material_return.create", "create", "material_return"),
            ("material_loss.create", "create", "inventory_transaction"),
            ("inventory_adjustment_request.create", "create", "inventory_adjustment_request"),
            ("inventory_adjustment_request.approve", "approve", "inventory_adjustment_request"),
            ("destruction_record.create", "create", "destruction_record"),
            ("destruction_record.execute", "execute", "destruction_record"),
            ("material_reconciliation.evaluate", "evaluate", "material_reconciliation"),
            ("scar.case.create", "create", "supplier_quality_case"),
            ("scar.issue", "issue", "scar_record"),
            ("scar.response", "response", "scar_record"),
            ("scar.review", "review", "scar_record"),
            ("scar.effectiveness", "effectiveness", "scar_record"),
            ("scar.close", "close", "scar_record"),
            ("risk.create", "create", "risk_record"),
            ("risk.assessment.add", "add", "risk_assessment_version"),
            ("risk.controls.add", "add", "risk_assessment_version"),
            ("risk.accept", "accept", "risk_record"),
            ("risk.review", "review", "risk_record"),
            ("risk.dashboard.view", "view", "risk_record"),
            ("internal_audit.create", "create", "internal_audit"),
            ("internal_audit.start", "start", "internal_audit"),
            ("internal_audit.finding.add", "add", "audit_finding"),
            ("internal_audit.finding.response", "response", "audit_finding"),
            ("internal_audit.finding.verify", "verify", "audit_finding"),
            ("internal_audit.close", "close", "internal_audit"),
            ("complaint.create", "create", "complaint_record"),
            ("complaint.triage", "triage", "complaint_record"),
            ("complaint.investigation_decision", "investigation_decision", "complaint_record"),
            ("complaint.investigate", "investigate", "complaint_record"),
            ("complaint.reportability", "reportability", "complaint_record"),
            ("complaint.response", "response", "complaint_record"),
            ("complaint.close", "close", "complaint_record"),
            ("field_action.create", "create", "field_action"),
            ("field_action.scope", "scope", "field_action"),
            ("field_action.reportability", "reportability", "field_action"),
            ("field_action.approve", "approve", "field_action"),
            ("field_action.communications", "communications", "field_action"),
            ("field_action.reconcile", "reconcile", "field_action"),
            ("field_action.effectiveness", "effectiveness", "field_action"),
            ("field_action.close", "close", "field_action"),
            ("quality_metric.definition.create", "create", "quality_metric_definition"),
            ("quality_metric.definition.release", "release", "quality_metric_definition"),
            ("quality_metric.calculate", "calculate", "quality_metric_snapshot"),
            ("quality_metric.dashboard.view", "view", "quality_metric_snapshot"),
            ("quality_metric.management_review", "management_review", "quality_metric_snapshot"),
            ("effectiveness_check.create", "create", "effectiveness_check"),
            ("effectiveness_check.evaluate", "evaluate", "effectiveness_check"),
            ("equipment_asset.create", "create", "equipment_asset"),
            ("equipment_area.create", "create", "equipment_area"),
            ("equipment_asset.qualify", "qualify", "equipment_asset"),
            ("equipment_asset.calibrate", "calibrate", "equipment_asset"),
            ("equipment_asset.maintain", "maintain", "equipment_asset"),
            ("equipment_asset.hold", "hold", "equipment_asset"),
            ("equipment_asset.return_to_service", "return_to_service", "equipment_asset"),
            ("cleaning_execution.create", "create", "cleaning_execution"),
            ("cleaning_execution.complete", "complete", "cleaning_execution"),
            ("cleaning_execution.verify", "verify", "cleaning_execution"),
            ("line_clearance.create", "create", "line_clearance"),
            ("line_clearance.complete", "complete", "line_clearance"),
            ("em_program.create", "create", "em_program_version"),
            ("em_sample.create", "create", "em_sample_or_reading"),
            ("em_sample.record_result", "record_result", "em_sample_or_reading"),
            ("em_sample.review", "review", "em_sample_or_reading"),
            ("em_excursion.impact", "impact", "em_excursion"),
            ("process_cycle.create", "create", "process_cycle"),
            ("process_cycle.start", "start", "process_cycle"),
            ("process_cycle.review", "review", "process_cycle"),
            ("sterile_filter_use.create", "create", "sterile_filter_use"),
            ("sterile_filter_use.complete", "complete", "sterile_filter_use"),
            ("aseptic_operation.create", "create", "aseptic_operation"),
            ("aseptic_operation.start", "start", "aseptic_operation"),
            ("aseptic_operation.intervention", "intervention", "aseptic_operation"),
            ("aseptic_operation.event", "event", "aseptic_operation"),
            ("aseptic_operation.complete", "complete", "aseptic_operation"),
            ("aseptic_profile_version.create", "create", "aseptic_profile_version"),
            ("edge_gateway.enroll", "enroll", "edge_gateway"),
            ("edge_gateway.certificate_rotation", "certificate_rotation", "edge_gateway"),
            ("erp_instance.administer", "administer", "erp_instance"),
            ("erp_mapping.propose", "propose", "erp_external_mapping"),
            ("erp_mapping.approve", "approve", "erp_external_mapping"),
            ("erp_mapping.resolve_conflict", "resolve_conflict", "erp_mapping_conflict"),
            ("erp_sync.checkpoint", "checkpoint", "erp_sync_checkpoint"),
            ("integration_command.queue", "queue", "integration_command"),
            ("integration_command.dispatch", "dispatch", "integration_command"),
            ("integration_command.retry", "retry", "integration_command"),
            ("integration_command.cancel", "cancel", "integration_command"),
            ("integration_event.ingest", "ingest", "integration_inbound_event"),
            ("integration_reconciliation.manage", "manage", "integration_reconciliation_run"),
            ("signal_mapping.release", "release", "signal_mapping"),
            ("batch_context.open", "open", "batch_context"),
            ("batch_context.close", "close", "batch_context"),
            ("machine_command.submit", "submit", "machine_command_request"),
            ("machine_replay.create", "create", "machine_replay_job"),
            ("machine_evidence.review_view", "view", "machine_evidence_candidate"),
            ("yield_calculation.evaluate", "evaluate", "manufacturing_calculation"),
            ("reconciliation.evaluate", "evaluate", "reconciliation_record"),
            ("reconciliation.verify", "verify", "reconciliation_record"),
            # WP-08 (Document 54, SPEC-DDCP-001) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("ddcp_profile.author", "author", "ddcp_profile_version"),
            ("ddcp_profile.release", "release", "ddcp_profile_version"),
            ("ddcp_constituent.handoff", "handoff", "constituent_handoff"),
            ("ddcp_constituent.decide", "decide", "constituent_handoff"),
            ("ddcp_fill.start", "start", "fill_operation"),
            ("ddcp_fill.record_ipc", "record_ipc", "fill_operation"),
            ("ddcp_fill.record_count", "record_count", "production_count_ledger"),
            ("ddcp_fill.record_intervention", "record_intervention", "fill_operation"),
            ("ddcp_fill.complete", "complete", "fill_operation"),
            ("ddcp_device.assemble", "assemble", "device_assembly_record"),
            ("ddcp_device.verify", "verify", "device_assembly_record"),
            ("ddcp_device.record_test", "record_test", "device_functional_test_link"),
            ("ddcp_release.evaluate", "evaluate", "ddcp_release_checkpoint"),
            ("ddcp_release.export", "export", "batch_evidence_manifest"),
            # WP-09 (Document 58, SPEC-PM-001) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("postmarket_source.register", "register", "postmarket_source"),
            ("safety_case.create", "create", "safety_case"),
            ("safety_case.resolve_product", "resolve_product", "safety_case"),
            ("safety_case.classify", "classify", "safety_case"),
            ("safety_case.followup", "followup", "safety_case"),
            ("safety_case.link_duplicates", "link_duplicates", "safety_case"),
            ("safety_case.view", "view", "safety_case"),
            ("safety_signal.open", "open", "safety_signal"),
            ("safety_signal.assess", "assess", "safety_signal"),
            ("safety_signal.escalate", "escalate", "safety_signal"),
            ("safety_signal.view", "view", "safety_signal"),
            ("postmarket_dataset.freeze", "freeze", "postmarket_periodic_safety_dataset"),
            # WP-09 (Document 59, SPEC-PM-002) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("reportability_track.create", "create", "reportability_track"),
            ("reportability_track.calculate_deadline", "calculate_deadline", "reportability_track"),
            ("reportability_track.decide", "decide", "reportability_track"),
            ("reportability_track.view", "view", "reportability_track"),
            ("regulatory_report.create", "create", "regulatory_report"),
            ("regulatory_report.approve", "approve", "regulatory_report"),
            ("regulatory_report.generate_payload", "generate_payload", "regulatory_report"),
            ("regulatory_report.submit", "submit", "regulatory_report"),
            ("regulatory_report.followup", "followup", "regulatory_report"),
            ("regulatory_submission.acknowledge", "acknowledge", "regulatory_submission_ack"),
            # WP-09 (Document 60, SPEC-PM-003) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("applicant_relationship.configure", "configure", "applicant_relationship"),
            ("constituent_information_share.evaluate", "evaluate", "constituent_information_share"),
            ("constituent_information_share.package", "package", "constituent_information_share"),
            ("constituent_information_share.record_sent", "record_sent", "constituent_information_share"),
            ("correction_removal.create", "create", "correction_removal_regulatory_record"),
            ("correction_removal.decide", "decide", "correction_removal_regulatory_record"),
            ("regulatory_obligation.create", "create", "regulatory_obligation"),
            ("regulatory_obligation.decide", "decide", "regulatory_obligation"),
            ("regulatory_obligation.override_deadline", "override_deadline", "regulatory_obligation"),
            ("regulatory_obligation.calculate_retention", "calculate_retention", "regulatory_obligation"),
            ("regulatory_obligation.legal_hold", "legal_hold", "regulatory_obligation"),
            ("regulatory_obligation.view", "view", "regulatory_obligation"),
            ("periodic_reporting_cycle.generate", "generate", "periodic_reporting_cycle"),
            ("periodic_reporting_cycle.freeze", "freeze", "periodic_reporting_cycle"),
            # WP-10 (Document 61, SPEC-SEC-001) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("security_threat_model.create", "create", "security_threat_model_version"),
            ("security_threat_model.trigger_review", "trigger_review", "security_threat_model_version"),
            ("security_control_matrix.view", "view", "security_threat_model_version"),
            ("security_threat.register", "register", "security_threat"),
            ("security_threat.map_control", "map_control", "security_threat"),
            ("security_threat.calculate_risk", "calculate_risk", "security_threat"),
            ("security_threat.accept_risk", "accept_risk", "security_threat"),
            ("security_exception.open", "open", "security_exception"),
            ("security_exception.view", "view", "security_exception"),
            # WP-10 (Document 62, SPEC-SEC-002) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("identity_provider.create", "create", "identity_provider_config"),
            ("identity_provider.map_identity", "map_identity", "identity_provider_config"),
            ("identity_provider.validate_token", "validate_token", "identity_provider_config"),
            ("application_session.view", "view", "application_session"),
            ("application_session.revoke", "revoke", "application_session"),
            ("service_identity.provision", "provision", "service_identity"),
            ("service_identity.revoke", "revoke", "service_identity"),
            # WP-10 (Document 63, SPEC-SEC-003) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("privileged_access.request", "request", "privileged_access_request"),
            ("privileged_access.approve", "approve", "privileged_access_request"),
            ("privileged_access.view", "view", "privileged_grant"),
            ("privileged_session.open_support", "open_support", "privileged_session"),
            ("privileged_session.break_glass", "break_glass", "privileged_session"),
            ("privileged_session.execute_command", "execute_command", "privileged_session"),
            ("privileged_session.close", "close", "privileged_session"),
            ("privileged_session.review", "review", "privileged_session"),
            # WP-10 (Document 64, SPEC-SEC-004) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            # No new role: reuses the existing Security Admin actor (granted below via Admin here since
            # conftest's grant loop has no Security Admin row). No Document 106 signature row exists.
            ("outbound_destination.register", "register", "outbound_destination"),
            ("webhook_profile.register", "register", "webhook_profile"),
            ("api_inventory.view", "view", "api_security_policy"),
            # WP-10 (Document 65, SPEC-SEC-005) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("secret.rotate", "rotate", "secret_metadata"),
            ("certificate.issue", "issue", "certificate_metadata"),
            ("certificate.rotate", "rotate", "certificate_metadata"),
            ("certificate.revoke", "revoke", "certificate_metadata"),
            ("crypto_health.view", "view", "crypto_profile"),
            # WP-10 (Document 66, SPEC-SEC-006) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("network_flow.view", "view", "network_flow_definition"),
            ("deployment_security_profile.view", "view", "deployment_security_profile"),
            # WP-10 (Document 67, SPEC-SEC-007) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("security_incident.open", "open", "security_incident"),
            ("security_incident.contain", "contain", "security_incident"),
            ("security_incident.evidence", "evidence", "security_incident"),
            ("security_incident.gxp_impact", "gxp_impact", "security_incident"),
            ("security_incident.close", "close", "security_incident"),
            # WP-10 (Document 68, SPEC-SEC-008) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            ("vulnerability.register", "register", "vulnerability_record"),
            ("vulnerability.assess", "assess", "vulnerability_record"),
            ("vulnerability.exception", "exception", "vulnerability_record"),
            ("release_security_evidence.view", "view", "release_security_evidence"),
            # WP-11 (Document 69, SPEC-DATA-001) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            # No new role: reuses the existing Admin actor (Data Engineer / DBA / System Architect map
            # to it in this deployment). No Document 106 signature row (Document 106 # 10 exempts
            # projection rebuilds and reads).
            ("data_ownership.view", "view", "data_ownership_registry"),
            ("projection.rebuild", "rebuild", "projection_checkpoint"),
            ("data_dictionary.view", "view", "data_ownership_registry"),
            # WP-11 (Document 72, SPEC-DATA-004) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            # legal_hold is signed (Document 106 row 142); the rest RBAC-only.
            ("evidence.upload", "upload", "evidence_object"),
            ("evidence.download", "download", "evidence_object"),
            ("evidence.manifest", "create", "evidence_manifest"),
            ("evidence.legal_hold", "legal_hold", "evidence_object"),
            ("evidence.integrity_check", "verify", "evidence_object"),
            # WP-11 (Document 75, SPEC-DATA-007) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            # RBAC-only: Document 106 has no SPEC-DATA-007 row (Document 106 # 10 exempts rebuilds/reads).
            ("search.query", "query", "projection_document_metadata"),
            ("search.rebuild", "rebuild", "read_model_checkpoint"),
            ("report.export", "export", "read_model_checkpoint"),
            # WP-11 (Document 76, SPEC-DATA-008) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            # RBAC-only: Document 106 has no SPEC-DATA-008 row.
            ("dr.recovery_objective.manage", "manage", "recovery_objective_profile"),
            ("dr.backup.view", "view", "backup_inventory"),
            ("dr.restore_test.execute", "execute", "restore_test"),
            # WP-13 (Document 105, SPEC-AI-001) — same rows scripts/seed.py's PERMISSION_CATALOG adds.
            # model.approve/tool.authorize/disposition.record/release_gate.evaluate/provider.switch are
            # signature-gated per Document 106 rows added for SG-167/168.
            ("ai_governance.use_case.register", "register", "ai_use_case"),
            ("ai_governance.use_case.assess_risk", "assess_risk", "ai_use_case"),
            ("ai_governance.model.approve", "approve", "ai_model_deployment"),
            ("ai_governance.context.build", "build", "ai_context_package"),
            ("ai_governance.advisory.execute", "execute", "ai_advisory_log"),
            ("ai_governance.tool.authorize", "authorize", "ai_tool_decision"),
            ("ai_governance.disposition.record", "record", "ai_disposition"),
            ("ai_governance.evaluation.run", "run", "ai_evaluation_report"),
            ("ai_governance.release_gate.evaluate", "evaluate", "ai_release_gate"),
            ("ai_governance.injection.detect", "detect", "ai_prompt_injection_event"),
            ("ai_governance.provider.switch", "switch", "ai_provider_switch"),
            ("ai_governance.use_case.retire", "retire", "ai_use_case"),
            ("ai_governance.package.generate", "generate", "ai_use_case"),
            # WP-12/WP-14 (Documents 79-96, SPEC-VAL-001..018) — same rows scripts/seed.py's
            # PERMISSION_CATALOG adds; role split explained there.
            ("validation.plan.manage", "manage", "validation_master_plan"),
            ("validation.plan.release", "release", "validation_master_plan"),
            ("validation.gate.view", "view", "validation_release_gate"),
            ("validation.package.view", "view", "validation_master_plan"),
            ("validation.intended_use.manage", "manage", "intended_use"),
            ("validation.function_risk.manage", "manage", "function_risk_assessment"),
            ("validation.function_risk.approve", "approve", "function_risk_assessment"),
            ("validation.function_risk.view", "view", "function_risk_assessment"),
            ("validation.requirement.manage", "manage", "validation_requirement"),
            ("validation.trace_link.manage", "manage", "trace_link"),
            ("validation.baseline.manage", "manage", "requirement_baseline"),
            ("validation.traceability.view", "view", "trace_link"),
            ("validation.test_definition.manage", "manage", "validation_test_definition"),
            ("validation.test_definition.approve", "approve", "validation_test_definition"),
            ("validation.test_execution.manage", "manage", "validation_test_execution"),
            ("validation.test_execution.complete", "complete", "validation_test_execution"),
            ("validation.iq.manage", "manage", "iq_protocol"),
            ("validation.iq.complete", "complete", "iq_execution"),
            ("validation.iq.approve", "approve", "iq_execution"),
            ("validation.oq.manage", "manage", "oq_suite"),
            ("validation.oq.view", "view", "oq_execution"),
            ("validation.oq.approve", "approve", "oq_execution"),
            ("validation.infrastructure.manage", "manage", "infrastructure_qualification_profile"),
            ("validation.infrastructure.approve", "approve", "infrastructure_fingerprint"),
            ("validation.part11.manage", "manage", "part11_scope_assessment"),
            ("validation.part11.approve", "approve", "part11_scope_assessment"),
            ("validation.data_integrity.manage", "manage", "data_integrity_test_profile"),
            ("validation.data_integrity.approve", "approve", "data_integrity_test_profile"),
            ("validation.interface.manage", "manage", "interface_validation_profile"),
            ("validation.interface.approve", "approve", "interface_validation_profile"),
            ("validation.dr.manage", "manage", "dr_qualification_scenario"),
            ("validation.dr.approve", "approve", "dr_qualification_execution"),
            ("validation.security.manage", "manage", "security_qualification_suite"),
            ("validation.security.view", "view", "security_qualification_suite"),
            ("validation.security.approve", "approve", "security_qualification_suite"),
            ("validation.performance.manage", "manage", "performance_qualification_scenario"),
            ("validation.performance.view", "view", "performance_run"),
            ("validation.exception.create", "create", "validation_exception"),
            ("validation.exception.triage", "triage", "validation_exception"),
            ("validation.exception.retest_plan", "retest_plan", "validation_exception"),
            ("validation.exception.disposition", "disposition", "validation_exception"),
            ("validation.exception.view", "view", "validation_exception"),
            ("validation.change_impact.manage", "manage", "validation_change_impact"),
            ("validation.periodic_review.manage", "manage", "periodic_validation_review"),
            ("validation.periodic_review.decide", "decide", "periodic_validation_review"),
            ("validation.state_baseline.decommission", "decommission", "validated_state_baseline"),
            ("validation.pq.manage", "manage", "pq_scenario"),
            ("validation.pq.execute", "execute", "pq_execution"),
            ("validation.pq.approve", "approve", "pq_scenario"),
            ("validation.migration.manage", "manage", "migration_validation_plan"),
            ("validation.migration.approve", "approve", "migration_run"),
            ("validation.migration.trace_view", "trace_view", "migration_validation_plan"),
            ("validation.vsr.manage", "manage", "validation_summary_report"),
            ("validation.vsr.approve", "approve", "validation_summary_report"),
            ("validation.release_auth.view", "view", "validated_release_authorization"),
            ("validation.release_auth.authorize", "authorize", "validated_release_authorization"),
            ("validation.release_auth.deployment_check", "deployment_check", "validated_release_authorization"),
            ("validation.post_go_live.record", "record", "validated_release_authorization"),
        ):
            permission = Permission(code=code, action=action, resource_type=resource_type)
            db.add(permission)
            permissions[code] = permission
        await db.flush()

        for role_name, codes in (
            (
                "Admin",
                [
                    "platform.administer", "audit.review", "audit.export", "vault.review", "vault.correct",
                    "rules.author", "rules.release", "rules.evaluate",
                    "product.author", "product.release", "product.suspend", "product.view",
                    "recipe.author", "recipe.release", "recipe.view",
                    "batch_execution.create", "batch_execution.issue", "batch_execution.execute", "batch_execution.view",
                    "batch_step.role_override",
                    "device.create", "device.execute", "device.view", "genealogy.view",
                    "qa_review.create", "qa_review.execute", "qa_review.view",
                    "release.evaluate", "release.release", "release.hold", "release.reject", "release.view",
                    "packaging.execute", "supplier_qualification.approve",
                    "qms_deviation.create", "qms_deviation.triage", "qms_deviation.contain", "qms_deviation.investigate",
                    "qms_deviation.impact", "qms_deviation.disposition", "qms_deviation.extend", "qms_deviation.close",
                    "qms_deviation.reopen",
                    "capa.create", "capa.plan", "capa.action.add", "capa.action.complete", "capa.effectiveness",
                    "capa.extend", "capa.close", "capa.reopen",
                    "ncr.create", "ncr.segregate", "ncr.evaluate", "ncr.disposition", "ncr.verify", "ncr.close",
                    "change.create", "change.impact", "change.approve", "change.task.add", "change.implement",
                    "change.verify", "change.make_effective", "change.close",
                    "document.create", "document.submit", "document.release", "document.make_effective",
                    "document.obsolete", "document.controlled_copy.issue", "document.view",
                    "training.requirement.create", "training.assignment.create", "training.assignment.complete",
                    "training.assignment.assess", "training.qualification.create", "training.waiver.create",
                    "training.subject.view", "training.matrix.view",
                    "qc_test_specification.release", "qc_test_order.review", "qc_result.correct", "lims_sample.cancel",
                    "oos_record.extended_investigation", "oos_record.disposition", "oos_record.close", "oot_record.close",
                    "material_receipt.create", "material_receipt.examine", "material_lot.sampling_order",
                    "material_lot.collect_sample", "material_lot.release", "material_lot.reject", "material_lot.retest",
                    "inventory_reservation.create", "inventory_reservation.release", "inventory_transaction.transfer",
                    "material_container.split", "material_container.merge", "inventory_cycle_count.execute",
                    "dispensing_order.create", "dispensing_order.select_source", "dispensing_order.start",
                    "dispensing_order.readings", "dispensing_order.manual_reading", "dispensing_order.verify",
                    "dispensing_order.complete", "dispensing_order.cancel",
                    "material_consumption.create", "material_return.create", "material_loss.create",
                    "inventory_adjustment_request.create", "inventory_adjustment_request.approve",
                    "destruction_record.create", "destruction_record.execute", "material_reconciliation.evaluate",
                    "scar.case.create", "scar.issue", "scar.response", "scar.review", "scar.effectiveness", "scar.close",
                    "risk.create", "risk.assessment.add", "risk.controls.add", "risk.accept", "risk.review",
                    "risk.dashboard.view",
                    "internal_audit.create", "internal_audit.start", "internal_audit.finding.add",
                    "internal_audit.finding.response", "internal_audit.finding.verify", "internal_audit.close",
                    "complaint.create", "complaint.triage", "complaint.investigation_decision",
                    "complaint.investigate", "complaint.reportability", "complaint.response", "complaint.close",
                    "field_action.create", "field_action.scope", "field_action.reportability",
                    "field_action.approve", "field_action.communications", "field_action.reconcile",
                    "field_action.effectiveness", "field_action.close",
                    "quality_metric.definition.create", "quality_metric.definition.release",
                    "quality_metric.calculate", "quality_metric.dashboard.view", "quality_metric.management_review",
                    "effectiveness_check.create", "effectiveness_check.evaluate",
                    "equipment_asset.create", "equipment_asset.qualify", "equipment_asset.calibrate",
                    "equipment_asset.maintain", "equipment_asset.hold", "equipment_asset.return_to_service",
                    "equipment_area.create",
                    "cleaning_execution.create", "cleaning_execution.complete", "cleaning_execution.verify",
                    "line_clearance.create", "line_clearance.complete",
                    "em_program.create", "em_sample.create", "em_sample.record_result", "em_sample.review",
                    "em_excursion.impact",
                    "process_cycle.create", "process_cycle.start", "process_cycle.review",
                    "sterile_filter_use.create", "sterile_filter_use.complete",
                    "aseptic_operation.create", "aseptic_operation.start", "aseptic_operation.intervention",
                    "aseptic_operation.event", "aseptic_operation.complete", "aseptic_profile_version.create",
                    "edge_gateway.enroll",
                    "erp_instance.administer", "erp_mapping.propose", "erp_mapping.approve", "erp_mapping.resolve_conflict",
                    "erp_sync.checkpoint", "integration_command.queue", "integration_command.dispatch",
                    "integration_command.retry", "integration_command.cancel", "integration_event.ingest",
                    "integration_reconciliation.manage",
                    "signal_mapping.release", "batch_context.open", "batch_context.close",
                    "machine_command.submit", "machine_replay.create", "machine_evidence.review_view",
                    "yield_calculation.evaluate", "reconciliation.evaluate", "reconciliation.verify",
                    "ddcp_profile.author", "ddcp_profile.release", "ddcp_constituent.handoff", "ddcp_constituent.decide",
                    "ddcp_fill.start", "ddcp_fill.record_ipc", "ddcp_fill.record_count", "ddcp_fill.record_intervention",
                    "ddcp_fill.complete", "ddcp_device.assemble", "ddcp_device.verify", "ddcp_device.record_test",
                    "ddcp_release.evaluate", "ddcp_release.export",
                    "postmarket_source.register", "safety_case.create", "safety_case.resolve_product",
                    "safety_case.classify", "safety_case.followup", "safety_case.link_duplicates", "safety_case.view",
                    "safety_signal.open", "safety_signal.assess", "safety_signal.escalate", "safety_signal.view",
                    "postmarket_dataset.freeze",
                    "reportability_track.create", "reportability_track.calculate_deadline", "reportability_track.decide",
                    "reportability_track.view", "regulatory_report.create", "regulatory_report.approve",
                    "regulatory_report.generate_payload", "regulatory_report.submit", "regulatory_report.followup",
                    "regulatory_submission.acknowledge",
                    "applicant_relationship.configure", "constituent_information_share.evaluate",
                    "constituent_information_share.package", "constituent_information_share.record_sent",
                    "correction_removal.create", "correction_removal.decide", "regulatory_obligation.create",
                    "regulatory_obligation.decide", "regulatory_obligation.override_deadline",
                    "regulatory_obligation.calculate_retention", "regulatory_obligation.legal_hold",
                    "regulatory_obligation.view", "periodic_reporting_cycle.generate", "periodic_reporting_cycle.freeze",
                    "security_threat_model.create", "security_threat_model.trigger_review", "security_control_matrix.view",
                    "security_threat.register", "security_threat.map_control", "security_threat.calculate_risk",
                    "security_threat.accept_risk", "security_exception.open", "security_exception.view",
                    "identity_provider.create", "identity_provider.map_identity", "identity_provider.validate_token",
                    "application_session.view", "application_session.revoke",
                    "service_identity.provision", "service_identity.revoke",
                    "privileged_access.request", "privileged_access.approve", "privileged_access.view",
                    "privileged_session.open_support", "privileged_session.break_glass", "privileged_session.execute_command",
                    "privileged_session.close", "privileged_session.review",
                    "outbound_destination.register", "webhook_profile.register", "api_inventory.view",
                    "secret.rotate", "certificate.issue", "certificate.rotate", "certificate.revoke",
                    "crypto_health.view", "network_flow.view", "deployment_security_profile.view",
                    "security_incident.open", "security_incident.contain", "security_incident.evidence",
                    "security_incident.gxp_impact", "security_incident.close",
                    "vulnerability.register", "vulnerability.assess", "vulnerability.exception",
                    "release_security_evidence.view",
                    "data_ownership.view", "projection.rebuild", "data_dictionary.view",
                    "evidence.upload", "evidence.download", "evidence.manifest",
                    "evidence.legal_hold", "evidence.integrity_check",
                    "search.query", "search.rebuild", "report.export",
                    "dr.recovery_objective.manage", "dr.backup.view", "dr.restore_test.execute",
                    "ai_governance.use_case.register", "ai_governance.use_case.assess_risk",
                    "ai_governance.model.approve", "ai_governance.context.build",
                    "ai_governance.advisory.execute", "ai_governance.tool.authorize",
                    "ai_governance.disposition.record", "ai_governance.evaluation.run",
                    "ai_governance.release_gate.evaluate", "ai_governance.injection.detect",
                    "ai_governance.provider.switch", "ai_governance.use_case.retire",
                    "ai_governance.package.generate",
                    "validation.plan.manage", "validation.plan.release", "validation.gate.view",
                    "validation.package.view", "validation.intended_use.manage", "validation.function_risk.manage",
                    "validation.function_risk.approve", "validation.function_risk.view", "validation.requirement.manage",
                    "validation.trace_link.manage", "validation.baseline.manage", "validation.traceability.view",
                    "validation.test_definition.manage", "validation.test_definition.approve", "validation.test_execution.manage",
                    "validation.test_execution.complete", "validation.iq.manage", "validation.iq.complete",
                    "validation.iq.approve", "validation.oq.manage", "validation.oq.view",
                    "validation.oq.approve", "validation.infrastructure.manage", "validation.infrastructure.approve",
                    "validation.part11.manage", "validation.part11.approve", "validation.data_integrity.manage",
                    "validation.data_integrity.approve", "validation.interface.manage", "validation.interface.approve",
                    "validation.dr.manage", "validation.dr.approve", "validation.security.manage",
                    "validation.security.view", "validation.security.approve", "validation.performance.manage",
                    "validation.performance.view", "validation.exception.create", "validation.exception.triage",
                    "validation.exception.retest_plan", "validation.exception.disposition", "validation.exception.view",
                    "validation.change_impact.manage", "validation.periodic_review.manage", "validation.periodic_review.decide",
                    "validation.state_baseline.decommission", "validation.pq.manage", "validation.pq.execute",
                    "validation.pq.approve", "validation.migration.manage", "validation.migration.approve",
                    "validation.migration.trace_view", "validation.vsr.manage", "validation.vsr.approve",
                    "validation.release_auth.view", "validation.release_auth.authorize", "validation.release_auth.deployment_check",
                    "validation.post_go_live.record",
                ],
            ),
            ("Operator", ["batch_step.start", "rules.evaluate", "product.view", "recipe.view", "batch_execution.execute", "batch_execution.view", "device.execute", "device.view", "genealogy.view", "qa_review.view", "release.view", "packaging.execute", "material_receipt.create", "material_receipt.examine", "material_lot.sampling_order", "inventory_reservation.create", "inventory_transaction.transfer", "material_container.split", "material_container.merge", "inventory_cycle_count.execute", "dispensing_order.create", "dispensing_order.select_source", "dispensing_order.start", "dispensing_order.readings", "dispensing_order.manual_reading", "dispensing_order.complete", "material_consumption.create", "material_return.create", "material_loss.create", "inventory_adjustment_request.create", "destruction_record.create", "destruction_record.execute", "equipment_asset.hold", "cleaning_execution.create", "cleaning_execution.complete", "line_clearance.create", "line_clearance.complete", "batch_context.open", "batch_context.close", "yield_calculation.evaluate", "reconciliation.evaluate", "validation.plan.manage", "validation.gate.view", "validation.package.view", "validation.intended_use.manage", "validation.function_risk.manage", "validation.function_risk.view", "validation.requirement.manage", "validation.trace_link.manage", "validation.baseline.manage", "validation.traceability.view", "validation.test_definition.manage", "validation.test_execution.manage", "validation.test_execution.complete", "validation.iq.manage", "validation.iq.complete", "validation.oq.manage", "validation.oq.view", "validation.infrastructure.manage", "validation.part11.manage", "validation.data_integrity.manage", "validation.interface.manage", "validation.dr.manage", "validation.security.manage", "validation.security.view", "validation.performance.manage", "validation.performance.view", "validation.exception.view", "validation.change_impact.manage", "validation.periodic_review.manage", "validation.periodic_review.decide", "validation.state_baseline.decommission", "validation.pq.execute", "validation.migration.manage", "validation.migration.trace_view", "validation.vsr.manage", "validation.release_auth.view"]),
            ("Supervisor", ["batch_step.start", "batch_step.role_override", "rules.evaluate", "product.view", "recipe.view", "batch_execution.create", "batch_execution.issue", "batch_execution.execute", "batch_execution.view", "device.create", "device.execute", "device.view", "genealogy.view", "qa_review.view", "release.view", "packaging.execute", "material_receipt.create", "material_receipt.examine", "material_lot.sampling_order", "inventory_reservation.create", "inventory_transaction.transfer", "material_container.split", "material_container.merge", "inventory_cycle_count.execute", "dispensing_order.create", "dispensing_order.select_source", "dispensing_order.start", "dispensing_order.readings", "dispensing_order.manual_reading", "dispensing_order.complete", "material_consumption.create", "material_return.create", "material_loss.create", "inventory_adjustment_request.create", "destruction_record.create", "destruction_record.execute", "material_reconciliation.evaluate", "line_clearance.create", "line_clearance.complete", "batch_context.open", "batch_context.close", "yield_calculation.evaluate", "reconciliation.evaluate"]),
            ("Process Engineer", ["product.author", "product.view", "recipe.author", "recipe.view", "rules.evaluate"]),
            ("QA Reviewer", ["batch.review", "audit.review", "vault.review", "rules.evaluate", "product.view", "recipe.view", "batch_execution.view", "device.view", "genealogy.view", "qa_review.create", "qa_review.execute", "qa_review.view", "release.evaluate", "release.hold", "release.view", "qc_test_order.review", "oos_record.extended_investigation", "equipment_asset.hold", "equipment_asset.return_to_service", "cleaning_execution.create", "cleaning_execution.complete", "cleaning_execution.verify", "em_sample.review", "em_excursion.impact", "process_cycle.create", "process_cycle.start", "process_cycle.review", "reconciliation.verify", "machine_evidence.review_view", "evidence.upload", "evidence.download", "evidence.manifest", "evidence.legal_hold", "evidence.integrity_check", "ai_governance.use_case.register", "ai_governance.use_case.assess_risk", "ai_governance.context.build", "ai_governance.advisory.execute", "ai_governance.disposition.record", "ai_governance.evaluation.run", "ai_governance.release_gate.evaluate", "ai_governance.injection.detect", "validation.gate.view", "validation.package.view", "validation.function_risk.approve", "validation.function_risk.view", "validation.traceability.view", "validation.oq.view", "validation.security.view", "validation.performance.view", "validation.exception.view", "validation.periodic_review.decide", "validation.migration.manage", "validation.migration.trace_view", "validation.vsr.manage", "validation.release_auth.view",
                # SG-138 policy-data half (2026-09-10) -- QMS review codes the "QA Reviewer" signer class
                # (Document 106 section 9 rows 96/97/107) needs; aligned with scripts/seed.py's own
                # QA Reviewer grant.
                "scar.review", "risk.review", "quality_metric.management_review"]),
            ("QA Releaser", ["batch.release", "audit.review", "vault.review", "vault.correct", "rules.evaluate", "rules.release", "product.view", "product.release", "recipe.view", "recipe.release", "batch_execution.view", "device.view", "genealogy.view", "qa_review.view", "release.evaluate", "release.release", "release.hold", "release.reject", "release.view", "supplier_qualification.approve", "qc_test_specification.release", "lims_sample.cancel", "oos_record.disposition", "oos_record.close", "oot_record.close", "material_lot.release", "material_lot.reject", "material_lot.retest", "inventory_reservation.release", "dispensing_order.cancel", "inventory_adjustment_request.create", "inventory_adjustment_request.approve", "material_reconciliation.evaluate", "equipment_asset.hold", "edge_gateway.certificate_rotation", "signal_mapping.release", "security_incident.close",
                # SG-138 policy-data half (2026-09-10) -- QMS signing codes, aligned with scripts/seed.py's
                # own QA Releaser grant so an independent QA Releaser can actually reach the signed QMS
                # transitions Document 106 section 9 rows 80-107 now require.
                "qms_deviation.disposition", "qms_deviation.close", "qms_deviation.reopen",
                "capa.effectiveness", "capa.close", "capa.reopen",
                "ncr.disposition", "ncr.close",
                "change.approve", "change.make_effective", "change.close",
                "document.release", "document.make_effective", "document.obsolete", "document.controlled_copy.issue",
                "training.assignment.assess", "training.qualification.create", "training.waiver.create",
                "risk.accept", "scar.effectiveness", "scar.close",
                "internal_audit.finding.verify", "internal_audit.close",
                "complaint.reportability", "complaint.response", "complaint.close",
                "field_action.reportability", "field_action.approve", "field_action.effectiveness", "field_action.close",
                "quality_metric.definition.create", "quality_metric.definition.release", "quality_metric.management_review",
                "validation.exception.create", "validation.exception.triage", "validation.exception.retest_plan", "validation.exception.disposition", "validation.plan.release", "validation.function_risk.approve", "validation.test_definition.approve", "validation.iq.approve", "validation.oq.approve", "validation.infrastructure.approve", "validation.part11.approve", "validation.data_integrity.approve", "validation.interface.approve", "validation.dr.approve", "validation.security.approve", "validation.pq.approve", "validation.migration.approve", "validation.vsr.approve", "validation.release_auth.authorize", "validation.release_auth.deployment_check", "validation.post_go_live.record"]),
            ("QC Reviewer", ["material_lot.disposition", "audit.review", "vault.review", "rules.evaluate", "product.view", "recipe.view", "batch_execution.view", "device.view", "genealogy.view", "qa_review.view", "release.view", "qc_result.correct", "material_lot.collect_sample", "material_lot.retest", "dispensing_order.verify", "cleaning_execution.verify", "em_sample.review", "process_cycle.review"]),
            ("Equipment Administrator", ["equipment_asset.create", "equipment_asset.qualify", "machine_command.submit", "equipment_area.create"]),
            ("Engineering Manager", ["equipment_asset.return_to_service"]),
            ("Calibration Technician", ["equipment_asset.calibrate"]),
            ("Maintenance Technician", ["equipment_asset.maintain"]),
            ("Sanitation Operator", ["cleaning_execution.create", "cleaning_execution.complete", "line_clearance.create", "line_clearance.complete"]),
            ("EM Technician", ["em_program.create", "em_sample.create", "em_sample.record_result"]),
            ("Microbiology Analyst", ["em_sample.record_result"]),
            ("Sterilization Operator", ["process_cycle.create", "process_cycle.start", "sterile_filter_use.create", "sterile_filter_use.complete"]),
            ("Aseptic Operator", ["aseptic_operation.create", "aseptic_operation.intervention", "aseptic_operation.event", "aseptic_operation.complete"]),
            ("Aseptic Supervisor", ["aseptic_operation.start", "aseptic_profile_version.create"]),
            ("Integration Administrator", [
                "erp_instance.administer", "erp_mapping.propose", "erp_mapping.approve", "erp_mapping.resolve_conflict",
                "erp_sync.checkpoint", "integration_command.queue", "integration_command.dispatch",
                "integration_command.retry", "integration_command.cancel", "integration_event.ingest",
                "integration_reconciliation.manage", "machine_replay.create",
            ]),
            ("Postmarket Regulatory Affairs", ["complaint.reportability", "field_action.reportability"]),
            ("DDCP Engineer", ["ddcp_profile.author", "ddcp_profile.release"]),
            ("DDCP Operator", [
                "ddcp_constituent.handoff", "ddcp_constituent.decide", "ddcp_fill.start", "ddcp_fill.record_ipc",
                "ddcp_fill.record_count", "ddcp_fill.record_intervention", "ddcp_fill.complete", "ddcp_device.assemble",
                "ddcp_device.verify", "ddcp_device.record_test", "ddcp_release.evaluate", "ddcp_release.export",
                "batch_execution.view",
            ]),
        ):
            for code in codes:
                db.add(RolePermission(role_id=roles[role_name].id, permission_id=permissions[code].id))

        # Document 69 (SPEC-DATA-001) DATA-FR-001 -- same rows scripts/seed.py's DATA_OWNERSHIP_SEED
        # upserts, transcribed from 05_DATABASE_OWNERSHIP_MATRIX.md. The registry is the queryable,
        # superseding source; this list is the change-controlled baseline.
        for entry in OWNERSHIP_SEED:
            db.add(DataOwnershipRegistry(**entry))

        # Document 76 (SPEC-DATA-008) DR-FR-001/002 -- Document 109's platform-default recovery-tier
        # table, same rows scripts/seed.py upserts.
        for entry in DOCUMENT_109_TIER_SEED:
            db.add(RecoveryObjectiveProfile(**entry))

        # Document 78 (SPEC-DATA-010) SRE-FR-001/002/005 -- Document 109's platform-default SLO /
        # capacity baseline, same rows scripts/seed.py upserts.
        for entry in DOCUMENT_109_SLO_SEED:
            db.add(SloDefinition(**entry))
        for entry in DOCUMENT_109_CAPACITY_SEED:
            db.add(CapacityForecast(**entry))

    return {
        "org_id": org.id,
        "site_id": site.id,
        "roles": roles,
        "users": users,
        "permissions": permissions,
        "locations": locations,
        "areas": areas,
        "cleaning_procedures": cleaning_procedures,
        "em_program": em_program,
        "em_locations": em_locations,
        "sterilization_profile": sterilization_profile,
        "aseptic_profile": aseptic_profile,
        "erp_instance": erp_instance,
    }


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def login(client: AsyncClient, username: str) -> str:
    resp = await client.post("/auth/token", data={"username": username, "password": DEMO_PASSWORD})
    resp.raise_for_status()
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def idem() -> str:
    return str(uuid.uuid4())
