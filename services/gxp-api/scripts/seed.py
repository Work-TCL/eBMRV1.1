"""Seed the minimum reference data Phase 1 needs to be usable: one org/site, the six baseline roles,
the Document 106 signature policy floor, the Document 07/107 permission catalog + role grants + SoD
platform floor (all idempotent upserts), and one demo user per role so the E2E walkthrough can exercise
segregation of duties (reviewer != releaser).

Run with: .venv/bin/python -m scripts.seed
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

import app.all_models  # noqa: F401 -- registers every module's models before any relationship/FK
# string reference (e.g. AsepticProfileVersion.product_id -> "ebmr.products") is resolved; seed.py
# only imports the specific model classes it needs directly, which left tables like `ebmr.products`
# unregistered and raised NoReferencedTableError on the very first flush. Same fix app/main.py gets
# for free by importing every module's router (which transitively imports its models) -- seed.py
# doesn't import routers, so it needs this explicitly. Found 2026-09-02 while trying to reseed the
# empty ebmr_new_gxp demo database.
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.modules.iam.models import Organization, Permission, Role, RolePermission, Site, SodRule, User, UserSiteRole
from app.modules.material.models import WarehouseLocation
from app.modules.equipment.cleaning_models import CleaningProcedureVersion, EquipmentArea
from app.modules.equipment.em_models import EmLocation, EmProgramVersion
from app.modules.equipment.sterilization_models import ProcessCycleProfileVersion
from app.modules.equipment.aseptic_models import AsepticProfileVersion
from app.modules.edge.models import EdgeEnrollmentToken
from app.modules.erp.models import ErpInstance
from app.modules.rules.models import RuleDefinition
from app.modules.signature.models import SignaturePolicy
from app.modules.dataops.models import DataOwnershipRegistry
from app.modules.dataops.registry import OWNERSHIP_SEED as DATA_OWNERSHIP_SEED
from app.modules.disaster_recovery.models import RecoveryObjectiveProfile
from app.modules.disaster_recovery.registry import DOCUMENT_109_TIER_SEED
from app.modules.sre.models import CapacityForecast, SloDefinition
from app.modules.sre.registry import DOCUMENT_109_CAPACITY_SEED, DOCUMENT_109_SLO_SEED
from app.mutation.hashing import sha256_hex

# Document 43 demo bootstrap token (see the EdgeEnrollmentToken seeding below) -- deliberately a fixed,
# well-known value for the E2E walkthrough/tests, same treatment as DEMO_PASSWORD.
DEMO_EDGE_BOOTSTRAP_TOKEN = "demo-edge-bootstrap-token-0001"

ROLE_NAMES = [
    "Admin", "Operator", "Supervisor", "QA Reviewer", "QA Releaser", "QC Reviewer",
    # Document 38 (SPEC-EQP-001) — no existing role maps cleanly to these actors (§2). "Equipment
    # Administrator" and "Calibration Technician" were already anticipated, unused, in Document 107's SoD
    # floor below (SOD-009/IND-019) before this module existed.
    "Equipment Administrator", "Engineering Manager", "Calibration Technician", "Maintenance Technician",
    # Document 39 (SPEC-EQP-002) — no existing role maps cleanly to "Sanitation/Cleaning Operator" (§2).
    "Sanitation Operator",
    # Document 41 (SPEC-EQP-004) — no existing role maps cleanly to these actors (§2).
    "EM Technician", "Microbiology Analyst",
    # Document 42 (SPEC-EQP-005) — no existing role maps cleanly to "Sterilization Operator" (§2).
    "Sterilization Operator",
    # Document 40 (SPEC-EQP-003) — no existing role maps cleanly to these actors (§2).
    "Aseptic Operator", "Aseptic Supervisor",
    # Document 10 (SPEC-EBMR-002) — dedicated master-recipe author so authoring is separable from
    # release (recipe.release stays with QA Releaser / Admin). Fixes the "author == releaser, both
    # Admin-only" gap noted in DDCP_Client_Demo_Guide §9.1. A standing-role-pair SoD rule pinning
    # Process Engineer against the releasing role is left to the project owner (Document 107).
    "Process Engineer",
    # Document 48/52/53 (WP-07) — ERP-ARC-027 "authorized integration admin"; no existing role maps
    # cleanly to this actor (§2 of each document).
    "Integration Administrator",
    # Document 54 (WP-08, SPEC-DDCP-001) — no existing role maps cleanly to these actors (§4).
    "DDCP Engineer", "DDCP Operator",
    # Document 58 (WP-09, SPEC-PM-001) — Document 58 # 11 names "Safety reviewer"/"Safety/Medical/Quality
    # team" and Document 106 row 123-128 (Document 59) names "Regulatory Affairs authorized submitter";
    # no existing role maps to either (same "no existing role maps cleanly" test as every role above).
    "Postmarket Safety Reviewer", "Postmarket Regulatory Affairs",
    # Document 61 (WP-10, SPEC-SEC-001) — Document 61 # 2 names Security Architect/Security Engineer/
    # System Architect (architecture, threat, control-mapping, risk-calculation, review-trigger work) and
    # a separate "Security/Quality/Business approver"/"Security owner" actor for risk acceptance and
    # exceptions; no existing role maps to either (same "no existing role maps cleanly" test as every
    # role above). Both endpoints these two actors would sign for are unresolved in Document 106 (SG-161)
    # and fail closed regardless of which role attempts them.
    "Security Architect", "Security Risk Approver",
    # Document 62 (WP-10, SPEC-SEC-002) — Document 62 # 2 names "Security Admin" verbatim as the actor
    # for identity-provider config, session revocation and service-identity provisioning; no existing
    # role maps cleanly (same test as every role above).
    "Security Admin",
    # Document 63 (WP-10, SPEC-SEC-003) — Document 63 # 2 names Platform Admin/Infrastructure Admin/DB
    # Admin/Integration Admin (combined: no Document 106 row or Document 63 text splits these into
    # distinct signed steps, same "no existing role maps cleanly" test) and a separate "Vendor Support
    # Engineer" actor for read-only support sessions. "Approver" resolves to the existing QA Releaser
    # role -- Document 106 rows 135/136's "Module approver role (QA Manager / Head of Quality per record
    # class)"/"QA Approver for the record class" families already have an established non-QMS mapping in
    # this codebase (scripts/seed.py's own inventory_adjustment_request.approve/oos_record.close), reused
    # here rather than inventing a new role.
    "Platform Admin", "Vendor Support Engineer",
]

# WP-01 Document 07 (IAM-FR-006) permission catalog, seeded for every action that already has a real
# call site — same discipline as the signature floor below. (code, action, resource_type, description)
PERMISSION_CATALOG = [
    ("batch_step.start", "execute", "batch_step", "Start a batch step"),
    ("batch_step.role_override", "role_override", "batch_step", "Start a batch step whose recipe-declared required role the actor does not hold, with a documented reason (SG-178, Documents 10/11)"),
    ("batch.review", "review", "batch", "QA review of a completed batch"),
    ("batch.release", "release", "batch", "QA release of a reviewed batch"),
    ("material_lot.disposition", "approve", "material_lot", "QC disposition of a material lot"),
    ("platform.administer", "administer", "platform", "Create/edit/delete master data and IAM records"),
    ("audit.review", "review", "audit_event", "Search and read the audit ledger (Document 05)"),
    ("audit.export", "export", "audit_event", "Create a structured audit export (Document 05)"),
    ("vault.review", "review", "vault_object", "View vault objects, versions and integrity (Document 06)"),
    ("vault.correct", "correct", "vault_object", "Release via the generic endpoint and request/complete corrections (Document 06)"),
    ("rules.author", "author", "rule", "Draft, validate and simulate a rule (Document 08)"),
    ("rules.release", "release", "rule", "Release a validated rule (Document 08)"),
    ("rules.evaluate", "evaluate", "rule", "Evaluate a released rule (Document 08)"),
    ("product.author", "author", "product_version", "Draft, edit, submit and validate-completeness a product version (Document 09)"),
    ("product.release", "release", "product_version", "Release a submitted product version (Document 09)"),
    ("product.suspend", "suspend", "product_version", "Suspend or reinstate a released product version (Document 09)"),
    ("product.view", "view", "product_version", "Read product versions, constituents, compatibility and issue-eligibility (Document 09)"),
    ("recipe.author", "author", "recipe_version", "Draft, edit, validate and simulate a master recipe version (Document 10)"),
    ("recipe.release", "release", "recipe_version", "Release a submitted master recipe version (Document 10)"),
    ("recipe.view", "view", "recipe_version", "Read recipe versions, graph, compare and issue-eligibility (Document 10)"),
    ("batch_execution.create", "create", "batch", "Create a batch against a released product+recipe version (Document 11)"),
    ("batch_execution.issue", "issue", "batch", "Issue a batch: create its execution snapshot and step instances (Document 11)"),
    ("batch_execution.execute", "execute", "batch", "Start/hold/resume/abort a batch and claim/start a batch step (Document 11)"),
    ("batch_execution.view", "view", "batch", "Read batch and execution-view detail (Document 11)"),
    ("device.create", "create", "device_unit", "Create a device lot / bulk-create serial units against a released product version (Document 12)"),
    ("device.execute", "execute", "device_unit", "Hold a device unit (Document 12)"),
    ("device.view", "view", "device_unit", "Read device units by serial/history and lot release-readiness (Document 12)"),
    ("genealogy.view", "view", "genealogy_node", "Read genealogy nodes/edges: lookup, ancestors, descendants, full-trace, affected-products (Document 13)"),
    ("qa_review.create", "create", "qa_review_package", "Create a QA review package against a batch (Document 14)"),
    ("qa_review.execute", "execute", "qa_review_package", "Reindex or complete a QA review package (Document 14)"),
    ("qa_review.view", "view", "qa_review_package", "Read QA review packages, exceptions and the dashboard (Document 14)"),
    ("release.evaluate", "evaluate", "release_scope", "Evaluate (create or re-evaluate) a release scope's eligibility (Document 15)"),
    ("release.release", "release", "release_scope", "Execute a final release decision (Document 15)"),
    ("release.hold", "hold", "release_scope", "Place a release hold (Document 15)"),
    ("release.reject", "reject", "release_scope", "Reject a release scope (Document 15)"),
    ("release.view", "view", "release_scope", "Read release scopes, eligibility and the release package (Document 15)"),
    ("packaging.execute", "execute", "packaging_run", "Create/run/reconcile/complete a packaging run (Document 16)"),
    ("supplier_qualification.approve", "approve", "supplier_qualification", "Approve/conditionally-approve/reject a supplier qualification (Document 18)"),
    ("qc_test_specification.release", "release", "qc_test_specification", "Release a draft QC test specification (Document 23)"),
    ("qc_test_order.review", "review", "qc_test_order", "Second-person review of a completed QC test order (Document 23)"),
    ("qc_result.correct", "correct", "qc_result", "Request or approve a 2-signature QC result correction (Document 23)"),
    ("lims_sample.cancel", "cancel", "lims_mapping", "Cancel a LIMS-requested sample (Document 24)"),
    ("oos_record.extended_investigation", "extended_investigation", "oos_record", "Start extended investigation on an OOS with no assignable lab cause (Document 25)"),
    ("oos_record.disposition", "disposition", "oos_record", "Approve final disposition of an OOS (Document 25)"),
    ("oos_record.close", "close", "oos_record", "Close an OOS record (Document 25)"),
    ("oot_record.close", "close", "oot_record", "Close an OOT record (Document 25)"),
    ("material_receipt.create", "create", "material_receipt", "Create a material receipt (Document 19)"),
    ("material_receipt.examine", "examine", "material_receipt", "Visual examination / identity check of a material receipt (Document 19)"),
    ("material_lot.sampling_order", "create", "material_lot", "Create a sampling order against a material lot (Document 19)"),
    ("material_lot.collect_sample", "execute", "material_lot", "Collect a sample from a sampling order (Document 19)"),
    ("material_lot.release", "release", "material_lot", "QA release of a material lot (Document 19)"),
    ("material_lot.reject", "reject", "material_lot", "QA reject of a material lot (Document 19)"),
    ("material_lot.retest", "retest", "material_lot", "Place a material lot on retest pending reexamination (Document 19)"),
    # warehouse_location.create — SG-081 write-side, added 2026-09-07 (project-owner-directed): the
    # Inventory Transfer/Cycle-count/Adjustment forms need a real location dropdown, and locations were
    # genuinely uncreatable through the app before this (seed-only, WAREHOUSE_LOCATION_FLOOR below).
    # Admin/Supervisor only, not Operator — same "who defines the layout vs who executes against it"
    # split this file already draws for batch_execution.create/device.create.
    ("warehouse_location.create", "create", "warehouse_location", "Create a warehouse/zone/bin location (Document 20)"),
    ("inventory_reservation.create", "create", "inventory_reservation", "Reserve material for a batch (Document 20)"),
    ("inventory_reservation.release", "release", "inventory_reservation", "Release (give back) a material reservation (Document 20)"),
    ("inventory_transaction.transfer", "transfer", "inventory_transaction", "Transfer a lot/container between warehouse locations (Document 20)"),
    ("material_container.split", "split", "material_container", "Split a container into child containers (Document 20)"),
    ("material_container.merge", "merge", "material_container", "Merge compatible containers (Document 20)"),
    ("inventory_cycle_count.execute", "execute", "inventory_cycle_count", "Record a physical inventory cycle count (Document 20)"),
    ("dispensing_order.create", "create", "dispensing_order", "Create a dispensing order (Document 21)"),
    ("dispensing_order.select_source", "select_source", "dispensing_order", "Select the source lot/container for a dispensing order (Document 21)"),
    ("dispensing_order.start", "start", "dispensing_order", "Start a weighing session for a dispensing order (Document 21)"),
    ("dispensing_order.readings", "readings", "dispensing_order", "Record a device weight reading (Document 21)"),
    ("dispensing_order.manual_reading", "manual_reading", "dispensing_order", "Record a manual weight reading (Document 21)"),
    ("dispensing_order.verify", "verify", "dispensing_order", "Independently verify a dispensing order (Document 21)"),
    ("dispensing_order.complete", "complete", "dispensing_order", "Complete a dispensing order (Document 21)"),
    ("dispensing_order.cancel", "cancel", "dispensing_order", "Cancel a dispensing order (Document 21)"),
    ("material_consumption.create", "create", "material_consumption", "Record material consumption against a dispensed container (Document 22)"),
    ("material_return.create", "create", "material_return", "Return unused dispensed material to the warehouse (Document 22)"),
    ("material_loss.create", "create", "inventory_transaction", "Record a sample/reject/spill/approved-loss movement (Document 22)"),
    ("inventory_adjustment_request.create", "create", "inventory_adjustment_request", "Request an exceptional inventory adjustment (Document 22)"),
    ("inventory_adjustment_request.approve", "approve", "inventory_adjustment_request", "Independently approve an exceptional inventory adjustment (Document 22)"),
    ("destruction_record.create", "create", "destruction_record", "Request material/container destruction (Document 22)"),
    ("destruction_record.execute", "execute", "destruction_record", "Execute an authorized destruction (Document 22)"),
    ("material_reconciliation.evaluate", "evaluate", "material_reconciliation", "Evaluate batch material reconciliation (Document 22)"),
    # Document 38 (SPEC-EQP-001) — 6 grants covering the module's 9 API operations; the 3 GET queries
    # (eligibility/history/dashboard) are unauthenticated reads, same treatment as material lot detail.
    ("equipment_asset.create", "create", "equipment_asset", "Create an equipment asset (Document 38)"),
    ("equipment_asset.qualify", "qualify", "equipment_asset", "Record an equipment qualification event (Document 38)"),
    ("equipment_asset.calibrate", "calibrate", "equipment_asset", "Record an equipment calibration event (Document 38)"),
    ("equipment_asset.maintain", "maintain", "equipment_asset", "Create/continue/verify an equipment maintenance work order (Document 38)"),
    ("equipment_asset.hold", "hold", "equipment_asset", "Place an equipment asset on hold (Document 38, Document 106 row 108)"),
    ("equipment_asset.return_to_service", "return_to_service", "equipment_asset", "Return an equipment asset to service (Document 38)"),
    # equipment_area.create — added 2026-09-07, project-owner-directed (same "genuinely uncreatable
    # through the app" pattern as warehouse_location.create/aseptic_profile_version.create):
    # EquipmentArea was seed-only, "provisioned outside the app today" per its own docstring, with no
    # write operation in any of Document 38/39/40/41/42's declared API lists. Same roles as
    # equipment_asset.create (Admin + Equipment Administrator).
    ("equipment_area.create", "create", "equipment_area", "Create a classified/monitored equipment area (Document 38/39/40/41 shared master)"),
    # Document 39 (SPEC-EQP-002) — 4 grants covering the module's 7 API operations; the GET status query
    # is an unauthenticated read, same treatment as material lot detail.
    ("cleaning_execution.create", "create", "cleaning_execution", "Create/progress a cleaning execution (Document 39)"),
    ("cleaning_execution.complete", "complete", "cleaning_execution", "Complete a cleaning execution (Document 39, Document 106 row 109)"),
    ("cleaning_execution.verify", "verify", "cleaning_execution", "Independently verify a cleaning execution (Document 39, Document 106 row 110)"),
    ("line_clearance.create", "create", "line_clearance", "Create a line clearance (Document 39)"),
    ("line_clearance.complete", "complete", "line_clearance", "Complete a line clearance (Document 39, Document 106 row 111)"),
    # Document 41 (SPEC-EQP-004) — 6 grants covering the module's 8 API operations; the 2 GET queries
    # (readiness/trends) are unauthenticated reads, same treatment as material lot detail.
    ("em_program.create", "create", "em_program_version", "Create an EM program version (Document 41)"),
    ("em_sample.create", "create", "em_sample_or_reading", "Create/collect an EM sampling task (Document 41)"),
    ("em_sample.record_result", "record_result", "em_sample_or_reading", "Record an EM result (Document 41, Document 106 row 114)"),
    ("em_sample.review", "review", "em_sample_or_reading", "Independently review an EM result (Document 41, Document 106 row 115)"),
    ("em_excursion.impact", "impact", "em_excursion", "Record EM excursion impact assessment (Document 41)"),
    # Document 42 (SPEC-EQP-005) — 7 grants covering the module's 9 API operations; the GET status query
    # is an unauthenticated read.
    ("process_cycle.create", "create", "process_cycle", "Create a sterilization or CIP/SIP process cycle (Document 42)"),
    ("process_cycle.start", "start", "process_cycle", "Start a process cycle and record cycle data (Document 42, Document 106 row 118)"),
    ("process_cycle.review", "review", "process_cycle", "Independently review/accept-reject a process cycle (Document 42, Document 106 row 117)"),
    ("sterile_filter_use.create", "create", "sterile_filter_use", "Install a filter and record integrity tests (Document 42)"),
    ("sterile_filter_use.complete", "complete", "sterile_filter_use", "Complete a sterile filter use (Document 42, Document 106 row 116)"),
    # Document 40 (SPEC-EQP-003) — 5 grants covering the module's 7 API operations; the 2 GET queries
    # (readiness/review-summary) are unauthenticated reads.
    ("aseptic_operation.create", "create", "aseptic_operation", "Create an aseptic operation (Document 40)"),
    ("aseptic_operation.start", "start", "aseptic_operation", "Start an aseptic operation (Document 40, Document 106 row 113)"),
    ("aseptic_operation.intervention", "intervention", "aseptic_operation", "Record an aseptic intervention (Document 40)"),
    ("aseptic_operation.event", "event", "aseptic_operation", "Record an aseptic event/excursion (Document 40)"),
    ("aseptic_operation.complete", "complete", "aseptic_operation", "Complete an aseptic operation (Document 40, Document 106 row 112)"),
    # aseptic_profile_version.create — added 2026-09-07, project-owner-directed (same "genuinely
    # uncreatable through the app" pattern SG-081 resolved for warehouse_location): Document 40's own
    # 7-op API list has no create/release operation for aseptic_profile_version either (seed-only,
    # aseptic_models.py's own docstring), but Product Master's sterile_profile_id field needed a real
    # profile to reference for a demo beyond the one seeded row. Aseptic Supervisor, not Aseptic
    # Operator — same "who defines the process profile vs who executes against it" split as Document
    # 38's equipment_asset.create going to Equipment Administrator, not the operator role.
    ("aseptic_profile_version.create", "create", "aseptic_profile_version", "Create a sterile/aseptic process profile version (Document 40)"),
    # Document 43 (SPEC-EDGE-001) — 2 grants for the module's 2 human-authenticated operations; the 3
    # machine-driven operations (observations:batch, health, security-events) authenticate via the SG-120
    # service identity instead and have no RBAC permission grant (there is no iam.user_site_roles row for
    # a non-human identity to hold) -- see app/modules/edge/router.py's module docstring. GET operations
    # are unauthenticated reads, same treatment as material lot detail.
    ("edge_gateway.enroll", "enroll", "edge_gateway", "Enroll a new edge gateway (Document 43, SG-118)"),
    ("edge_gateway.certificate_rotation", "certificate_rotation", "edge_gateway", "Rotate a gateway's certificate (Document 43, Document 106 row 119)"),
    # WP-07 (Documents 48/52/53) — 11 grants covering the shared integration gateway's contract surface
    # (module docstring in app/modules/erp/router.py: Document 53 owns the only API for Documents 48-52).
    ("erp_instance.administer", "administer", "erp_instance", "Register an ERP instance (Document 48, SG-122)"),
    ("erp_mapping.propose", "propose", "erp_external_mapping", "Propose a master-data mapping or apply an external change (Document 52)"),
    ("erp_mapping.approve", "approve", "erp_external_mapping", "Approve a proposed master-data mapping (Document 52, SG-122)"),
    ("erp_mapping.resolve_conflict", "resolve_conflict", "erp_mapping_conflict", "Resolve a master-data mapping conflict (Document 52, SG-122)"),
    ("erp_sync.checkpoint", "checkpoint", "erp_sync_checkpoint", "Advance a master-data sync checkpoint (Document 52)"),
    ("integration_command.queue", "queue", "integration_command", "Queue or correct an outbound ERP integration command (Document 53)"),
    ("integration_command.dispatch", "dispatch", "integration_command", "Dispatch a queued/retry-waiting ERP integration command (Document 53)"),
    ("integration_command.retry", "retry", "integration_command", "Manually retry or reconcile-uncertain an ERP integration command (Document 53)"),
    ("integration_command.cancel", "cancel", "integration_command", "Cancel a pending ERP integration command (Document 53)"),
    ("integration_event.ingest", "ingest", "integration_inbound_event", "Ingest an inbound ERP event (Document 53)"),
    ("integration_reconciliation.manage", "manage", "integration_reconciliation_run", "Create/record/resolve/complete an ERP reconciliation run (Document 53)"),
    # Document 47 (SPEC-EDGE-005) — the server-side "Integration Gateway" (Document 43 §9). Machine-driven
    # operations (evidence:ingest, cycle-evidence-manifests, machine-commands/{id}/finalize) authenticate
    # via the same SG-120 service identity as Document 43's machine ops and have no RBAC permission grant,
    # same treatment as edge_gateway's observations:batch/health/security-events above.
    ("signal_mapping.release", "release", "signal_mapping", "Release a signal mapping version (Document 47, SG-127)"),
    ("batch_context.open", "open", "batch_context", "Register an active batch context for a machine source (Document 47)"),
    ("batch_context.close", "close", "batch_context", "Close an active batch context (Document 47)"),
    ("machine_command.submit", "submit", "machine_command_request", "Submit an approved machine command request (Document 47, SG-128)"),
    ("machine_replay.create", "create", "machine_replay_job", "Replay/backfill historical machine evidence (Document 47, SG-131)"),
    ("machine_evidence.review_view", "view", "machine_evidence_candidate", "List out-of-limit machine evidence candidates and alarms pending QA review (Document 47, MAP-FR-030)"),
    # Document 17 (SPEC-EBMR-008) — 3 grants covering the module's 8 API operations; the GET batch summary
    # query is an unauthenticated read, same treatment as material lot detail.
    ("yield_calculation.evaluate", "evaluate", "manufacturing_calculation", "Evaluate a yield or potency calculation (Document 17)"),
    ("reconciliation.evaluate", "evaluate", "reconciliation_record", "Evaluate a material/packaging/label/component reconciliation (Document 17)"),
    ("reconciliation.verify", "verify", "reconciliation_record", "Independently verify a yield calculation or reconciliation (Document 17, Document 106 row 40)"),
    # WP-05 QMS (Documents 26-37). These modules' routers already enforce evaluate_policy() against the
    # codes below, but the codes themselves were never added to this catalogue -- so every QMS endpoint
    # failed closed with ROLE_MISSING for every actor including Admin, making the whole work package
    # unreachable. Seeding them here is what turns the existing command surface on. The `.view` codes are
    # new and pair with the list/detail read endpoints added alongside them; unlike the equipment/edge
    # modules (whose GETs are unauthenticated reads), QMS records carry investigation and complainant
    # detail, so their reads are permission-gated.
    ("qms_deviation.create", "create", "deviation_record", "Raise a deviation / quality event (Document 26)"),
    ("qms_deviation.triage", "triage", "deviation_record", "Triage a deviation's severity and ownership (Document 26)"),
    ("qms_deviation.contain", "contain", "deviation_record", "Record immediate correction and containment (Document 26)"),
    ("qms_deviation.investigate", "investigate", "deviation_record", "Record investigation plan and root cause (Document 26)"),
    ("qms_deviation.impact", "impact", "deviation_record", "Record a deviation's product/quality impact assessment (Document 26)"),
    ("qms_deviation.disposition", "disposition", "deviation_record", "Approve a deviation disposition (Document 26)"),
    ("qms_deviation.extend", "extend", "deviation_record", "Extend a deviation's due date (Document 26)"),
    ("qms_deviation.close", "close", "deviation_record", "Close a deviation (Document 26)"),
    ("qms_deviation.reopen", "reopen", "deviation_record", "Reopen a closed deviation (Document 26)"),
    ("qms_deviation.view", "view", "deviation_record", "Read deviation records and impact links (Document 26)"),
    ("capa.create", "create", "capa_record", "Raise a CAPA (Document 27)"),
    ("capa.plan", "plan", "capa_record", "Record a CAPA's corrective/preventive plan (Document 27)"),
    ("capa.action.add", "add", "capa_action", "Add an action to a CAPA plan (Document 27)"),
    ("capa.action.complete", "complete", "capa_action", "Complete a CAPA action with implementation evidence (Document 27)"),
    ("capa.effectiveness", "effectiveness", "capa_record", "Record/evaluate a CAPA effectiveness check (Document 27, SOD-007)"),
    ("capa.extend", "extend", "capa_record", "Extend a CAPA target date (Document 27)"),
    ("capa.close", "close", "capa_record", "Close a CAPA (Document 27)"),
    ("capa.reopen", "reopen", "capa_record", "Reopen a closed CAPA (Document 27)"),
    ("capa.view", "view", "capa_record", "Read CAPA records, actions and effectiveness checks (Document 27)"),
    ("ncr.create", "create", "nonconformance_record", "Raise a nonconformance (Document 28)"),
    ("ncr.segregate", "segregate", "nonconformance_record", "Record segregation of nonconforming material (Document 28)"),
    ("ncr.evaluate", "evaluate", "nonconformance_record", "Evaluate a nonconformance against its requirement (Document 28)"),
    ("ncr.disposition", "disposition", "nonconformance_record", "Approve a nonconformance disposition (Document 28)"),
    ("ncr.verify", "verify", "nonconformance_record", "Verify rework/reinspection of a nonconformance (Document 28)"),
    ("ncr.close", "close", "nonconformance_record", "Close a nonconformance (Document 28)"),
    ("ncr.view", "view", "nonconformance_record", "Read nonconformance records and dispositions (Document 28)"),
    ("change.create", "create", "change_control", "Raise a change control (Document 29)"),
    ("change.impact", "impact", "change_control", "Record a change's regulatory/validation/training impact (Document 29)"),
    ("change.approve", "approve", "change_control", "Approve a change control (Document 29)"),
    ("change.task.add", "add", "change_task", "Add an implementation task to a change control (Document 29)"),
    ("change.implement", "implement", "change_control", "Mark a change control implemented (Document 29)"),
    ("change.verify", "verify", "change_control", "Verify a change control's implementation (Document 29)"),
    ("change.make_effective", "make_effective", "change_control", "Make an approved change effective (Document 29)"),
    ("change.close", "close", "change_control", "Close a change control (Document 29)"),
    ("change.view", "view", "change_control", "Read change controls, affected objects and tasks (Document 29)"),
    ("document.create", "create", "document_version", "Draft a controlled document version (Document 30)"),
    ("document.submit", "submit", "document_version", "Submit a document draft for approval (Document 30)"),
    ("document.release", "release", "document_version", "Approve/release a document version (Document 30, SOD-005)"),
    ("document.make_effective", "make_effective", "document_version", "Make a released document version effective (Document 30)"),
    ("document.obsolete", "obsolete", "document_version", "Obsolete an effective document version (Document 30)"),
    ("document.controlled_copy.issue", "issue", "document_controlled_copy", "Issue a controlled copy of a document version (Document 30)"),
    ("document.view", "view", "document_version", "Read controlled document versions (Document 30)"),
    ("training.requirement.create", "create", "training_requirement", "Define a training requirement (Document 31)"),
    ("training.assignment.create", "create", "training_assignment", "Assign training to a subject (Document 31)"),
    ("training.assignment.complete", "complete", "training_assignment", "Record completion of a training assignment (Document 31)"),
    ("training.assignment.assess", "assess", "training_assignment", "Assess a training assignment (Document 31, SOD-015)"),
    ("training.qualification.create", "create", "training_qualification", "Grant a training qualification (Document 31, SOD-015)"),
    ("training.waiver.create", "create", "training_waiver", "Grant a training waiver (Document 31)"),
    ("training.subject.view", "view", "training_assignment", "Read a subject's training status (Document 31)"),
    ("training.matrix.view", "view", "training_assignment", "Read the site training matrix (Document 31)"),
    ("risk.create", "create", "risk_record", "Raise a risk record (Document 32)"),
    ("risk.assessment.add", "add", "risk_assessment_version", "Add a risk assessment version (Document 32)"),
    ("risk.controls.add", "add", "risk_record", "Add risk controls (Document 32)"),
    ("risk.accept", "accept", "risk_record", "Accept a residual risk (Document 32)"),
    ("risk.review", "review", "risk_record", "Perform a periodic risk review (Document 32)"),
    ("risk.dashboard.view", "view", "risk_record", "Read the risk heatmap/trend dashboard (Document 32, RSK-FR-017)"),
    ("risk.view", "view", "risk_record", "Read risk records and assessment versions (Document 32)"),
    ("scar.case.create", "create", "supplier_quality_case", "Open a supplier quality case (Document 33)"),
    ("scar.issue", "issue", "scar_record", "Issue a SCAR against a supplier case (Document 33)"),
    ("scar.response", "response", "scar_record", "Record a supplier's SCAR response (Document 33)"),
    ("scar.review", "review", "scar_record", "Internally review a SCAR response (Document 33)"),
    ("scar.effectiveness", "effectiveness", "scar_record", "Record SCAR effectiveness (Document 33)"),
    ("scar.close", "close", "scar_record", "Close a SCAR (Document 33)"),
    ("scar.view", "view", "supplier_quality_case", "Read supplier quality cases and SCARs (Document 33)"),
    ("internal_audit.create", "create", "internal_audit", "Schedule an internal audit (Document 34)"),
    ("internal_audit.start", "start", "internal_audit", "Start a scheduled internal audit (Document 34)"),
    ("internal_audit.finding.add", "add", "audit_finding", "Record an internal audit finding (Document 34)"),
    ("internal_audit.finding.response", "response", "audit_finding", "Record an auditee response to a finding (Document 34)"),
    ("internal_audit.finding.verify", "verify", "audit_finding", "Verify closure of an audit finding (Document 34, SOD-016)"),
    ("internal_audit.close", "close", "internal_audit", "Close an internal audit (Document 34)"),
    ("internal_audit.view", "view", "internal_audit", "Read internal audits and findings (Document 34)"),
    ("complaint.create", "create", "complaint_record", "Log a customer complaint (Document 35)"),
    ("complaint.triage", "triage", "complaint_record", "Triage a complaint (Document 35)"),
    ("complaint.investigation_decision", "investigation_decision", "complaint_record", "Decide whether a complaint requires investigation (Document 35)"),
    ("complaint.investigate", "investigate", "complaint_record", "Record complaint investigation findings (Document 35)"),
    ("complaint.reportability", "reportability", "complaint_record", "Assess complaint regulatory reportability (Document 35)"),
    ("complaint.response", "response", "complaint_record", "Record a communication to the complainant (Document 35)"),
    ("complaint.close", "close", "complaint_record", "Close a complaint (Document 35)"),
    ("complaint.view", "view", "complaint_record", "Read complaint records, assessments and communications (Document 35)"),
    ("field_action.create", "create", "field_action", "Raise a field action / recall (Document 36)"),
    ("field_action.scope", "scope", "field_action", "Define a field action's affected scope (Document 36)"),
    ("field_action.reportability", "reportability", "field_action", "Assess field action regulatory reportability (Document 36)"),
    ("field_action.approve", "approve", "field_action", "Approve a field action (Document 36)"),
    ("field_action.communications", "communications", "field_action", "Record field action customer communications (Document 36)"),
    ("field_action.reconcile", "reconcile", "field_action", "Reconcile field action returns/corrections (Document 36)"),
    ("field_action.effectiveness", "effectiveness", "field_action", "Record field action effectiveness (Document 36)"),
    ("field_action.close", "close", "field_action", "Close a field action (Document 36)"),
    ("field_action.view", "view", "field_action", "Read field actions, scope items and communications (Document 36)"),
    ("quality_metric.definition.create", "create", "quality_metric_definition", "Define a quality metric (Document 37)"),
    ("quality_metric.definition.release", "release", "quality_metric_definition", "Release a quality metric definition (Document 37)"),
    ("quality_metric.calculate", "calculate", "quality_metric_definition", "Calculate a quality metric for a period (Document 37)"),
    ("quality_metric.management_review", "create", "quality_metric_definition", "Assemble a management review package (Document 37)"),
    ("quality_metric.dashboard.view", "view", "quality_metric_definition", "Read the quality metrics dashboard (Document 37)"),
    ("effectiveness_check.create", "create", "effectiveness_check", "Create a cross-record effectiveness check (Document 37)"),
    ("effectiveness_check.evaluate", "evaluate", "effectiveness_check", "Evaluate an effectiveness check (Document 37)"),
    # Read grants for Document 16 (packaging) and Document 18 (supplier quality), whose routers were
    # command-only; the list/detail endpoints added alongside these are what the UI reads.
    ("packaging.view", "view", "packaging_run", "Read packaging runs, label issues and reconciliations (Document 16)"),
    ("supplier.view", "view", "supplier", "Read suppliers, sites and qualifications (Document 18)"),
    # WP-08 (Document 54, SPEC-DDCP-001) — 14 grants covering the module's full command surface
    # (module docstring in app/modules/ddcp/router.py: this document's own §4 catalogue, unlike Document
    # 52, is a genuinely public API surface).
    ("ddcp_profile.author", "author", "ddcp_profile_version", "Author an injectable DDCP profile draft (Document 54)"),
    ("ddcp_profile.release", "release", "ddcp_profile_version", "Release an injectable DDCP profile version (Document 54, SG-148)"),
    ("ddcp_constituent.handoff", "handoff", "constituent_handoff", "Record a constituent handoff for a batch (Document 54)"),
    ("ddcp_constituent.decide", "decide", "constituent_handoff", "Accept or reject a constituent handoff (Document 54, SG-148)"),
    ("ddcp_fill.start", "start", "fill_operation", "Start a PFS filling stage (Document 54, SG-148)"),
    ("ddcp_fill.record_ipc", "record_ipc", "fill_operation", "Record a fill-weight IPC result (Document 54)"),
    ("ddcp_fill.record_count", "record_count", "production_count_ledger", "Record a syringe unit/count entry (Document 54)"),
    ("ddcp_fill.record_intervention", "record_intervention", "fill_operation", "Link an aseptic intervention to a fill operation (Document 54)"),
    ("ddcp_fill.complete", "complete", "fill_operation", "Complete a PFS filling stage (Document 54, SG-148)"),
    ("ddcp_device.assemble", "assemble", "device_assembly_record", "Record a device assembly step (Document 54)"),
    ("ddcp_device.verify", "verify", "device_assembly_record", "Independently verify a device assembly step (Document 54, IND-001)"),
    ("ddcp_device.record_test", "record_test", "device_functional_test_link", "Link a device/CCI functional test result (Document 54)"),
    ("ddcp_release.evaluate", "evaluate", "ddcp_release_checkpoint", "Evaluate PFS/DDCP release readiness (Document 54)"),
    ("ddcp_release.export", "export", "batch_evidence_manifest", "Generate a PFS batch evidence package (Document 54)"),
    # WP-09 (Document 58, SPEC-PM-001) -- Postmarket Surveillance, Safety Case & Signal Management.
    ("postmarket_source.register", "register", "postmarket_source", "Register a postmarket source channel (Document 58)"),
    ("safety_case.create", "create", "safety_case", "Link a new safety case to a source QMS/service record (Document 58)"),
    ("safety_case.resolve_product", "resolve_product", "safety_case", "Resolve the marketed product/lot/serial for a safety case (Document 58)"),
    ("safety_case.classify", "classify", "safety_case", "Classify a safety case's constituent/seriousness attributes (Document 58)"),
    ("safety_case.followup", "followup", "safety_case", "Record a safety case follow-up (Document 58)"),
    ("safety_case.link_duplicates", "link_duplicates", "safety_case", "Link probable-duplicate safety cases to a canonical case (Document 58)"),
    ("safety_case.view", "view", "safety_case", "Read safety cases, duplicate candidates and the postmarket dashboard (Document 58)"),
    ("safety_signal.open", "open", "safety_signal", "Open a safety signal (Document 58)"),
    ("safety_signal.assess", "assess", "safety_signal", "Assess a safety signal (Document 58)"),
    ("safety_signal.escalate", "escalate", "safety_signal", "Escalate a safety signal to CAPA/Change/Risk/Field Action (Document 58)"),
    ("safety_signal.view", "view", "safety_signal", "Read safety signals, surveillance metrics and signal-rule evaluations (Document 58)"),
    ("postmarket_dataset.freeze", "freeze", "postmarket_periodic_safety_dataset", "Freeze a periodic safety dataset (Document 58)"),
    # WP-09 (Document 59, SPEC-PM-002) -- Regulatory Reportability Assessment & Electronic Safety Submission.
    ("reportability_track.create", "create", "reportability_track", "Create reportability tracks for a safety case (Document 59)"),
    ("reportability_track.calculate_deadline", "calculate_deadline", "reportability_track", "Calculate a reportability track's regulatory deadline (Document 59)"),
    ("reportability_track.decide", "decide", "reportability_track", "Decide a track REPORTABLE/NOT_REPORTABLE (Document 59, SG-157)"),
    ("reportability_track.view", "view", "reportability_track", "Read reportability tracks, dedupe evaluations and audit packages (Document 59)"),
    ("regulatory_report.create", "create", "regulatory_report", "Build a regulatory report draft (Document 59)"),
    ("regulatory_report.approve", "approve", "regulatory_report", "Approve a regulatory report (Document 59, SG-157)"),
    ("regulatory_report.generate_payload", "generate_payload", "regulatory_report", "Generate an eMDR/AEMS submission payload (Document 59)"),
    ("regulatory_report.submit", "submit", "regulatory_report", "Submit a regulatory report (Document 59)"),
    ("regulatory_report.followup", "followup", "regulatory_report", "Create a follow-up report task (Document 59)"),
    ("regulatory_submission.acknowledge", "acknowledge", "regulatory_submission_ack", "Ingest a submission acknowledgement (Document 59)"),
    # WP-09 (Document 60, SPEC-PM-003) -- Combination-Product Postmarket Regulatory Coordination.
    ("applicant_relationship.configure", "configure", "applicant_relationship", "Configure a combination-product applicant relationship (Document 60)"),
    ("constituent_information_share.evaluate", "evaluate", "constituent_information_share", "Evaluate Part 4 constituent information sharing (Document 60)"),
    ("constituent_information_share.package", "package", "constituent_information_share", "Create a constituent sharing package (Document 60)"),
    ("constituent_information_share.record_sent", "record_sent", "constituent_information_share", "Record constituent information as shared (Document 60)"),
    ("correction_removal.create", "create", "correction_removal_regulatory_record", "Open a Part 806 correction/removal assessment (Document 60)"),
    ("correction_removal.decide", "decide", "correction_removal_regulatory_record", "Decide Part 806 reportability (Document 60, SG-160)"),
    ("regulatory_obligation.create", "create", "regulatory_obligation", "Create a Field Alert/BPDR/FDA-request obligation (Document 60)"),
    ("regulatory_obligation.decide", "decide", "regulatory_obligation", "Decide a Field Alert/BPDR obligation (Document 60)"),
    ("regulatory_obligation.override_deadline", "override_deadline", "regulatory_obligation", "Apply an agency deadline override (Document 60, SG-160)"),
    ("regulatory_obligation.calculate_retention", "calculate_retention", "regulatory_obligation", "Calculate the longest-applicable retention period (Document 60)"),
    ("regulatory_obligation.legal_hold", "legal_hold", "regulatory_obligation", "Place a postmarket legal hold (Document 60)"),
    ("regulatory_obligation.view", "view", "regulatory_obligation", "Read the unified regulatory calendar (Document 60)"),
    ("periodic_reporting_cycle.generate", "generate", "periodic_reporting_cycle", "Generate a periodic reporting cycle (Document 60)"),
    ("periodic_reporting_cycle.freeze", "freeze", "periodic_reporting_cycle", "Freeze a periodic reporting cycle's dataset (Document 60)"),
    # WP-10 (Document 61, SPEC-SEC-001) — same rows tests/conftest.py's own independent copy adds.
    ("security_threat_model.create", "create", "security_threat_model_version", "Create a threat model version (Document 61)"),
    ("security_threat_model.trigger_review", "trigger_review", "security_threat_model_version", "Trigger a threat model review (Document 61)"),
    ("security_control_matrix.view", "view", "security_threat_model_version", "Generate/read the security control matrix (Document 61)"),
    ("security_threat.register", "register", "security_threat", "Register a threat (Document 61)"),
    ("security_threat.map_control", "map_control", "security_threat", "Map a preventive/detective/recovery control to a threat (Document 61)"),
    ("security_threat.calculate_risk", "calculate_risk", "security_threat", "Calculate inherent/residual security risk (Document 61)"),
    ("security_threat.accept_risk", "accept_risk", "security_threat", "Accept residual security risk (Document 61, SG-161)"),
    ("security_exception.open", "open", "security_exception", "Open a time-bounded security exception (Document 61, SG-161)"),
    ("security_exception.view", "view", "security_exception", "Read a security exception (Document 61)"),
    # WP-10 (Document 62, SPEC-SEC-002) — same rows tests/conftest.py's own independent copy adds.
    ("identity_provider.create", "create", "identity_provider_config", "Register an identity provider config (Document 62)"),
    ("identity_provider.map_identity", "map_identity", "identity_provider_config", "Map an external issuer/subject to an internal user (Document 62)"),
    ("identity_provider.validate_token", "validate_token", "identity_provider_config", "Validate a federated identity token (Document 62)"),
    ("application_session.view", "view", "application_session", "Read session/MFA-requirement/freshness state (Document 62)"),
    ("application_session.revoke", "revoke", "application_session", "Revoke one or all of a subject's sessions (Document 62)"),
    ("service_identity.provision", "provision", "service_identity", "Provision a service/workload identity (Document 62)"),
    ("service_identity.revoke", "revoke", "service_identity", "Revoke a service/workload identity (Document 62)"),
    # WP-10 (Document 63, SPEC-SEC-003) — same rows tests/conftest.py's own independent copy adds.
    ("privileged_access.request", "request", "privileged_access_request", "Request just-in-time privileged access (Document 63)"),
    ("privileged_access.approve", "approve", "privileged_access_request", "Approve/deny a privileged access request (Document 63)"),
    ("privileged_access.view", "view", "privileged_grant", "Evaluate/read privileged grants (Document 63)"),
    ("privileged_session.open_support", "open_support", "privileged_session", "Open a read-only support session (Document 63)"),
    ("privileged_session.break_glass", "break_glass", "privileged_session", "Activate emergency break-glass access (Document 63)"),
    ("privileged_session.execute_command", "execute_command", "privileged_session", "Execute an allowlisted admin command (Document 63)"),
    ("privileged_session.close", "close", "privileged_session", "Close a privileged session (Document 63)"),
    ("privileged_session.review", "review", "privileged_session", "Review a closed privileged session (Document 63)"),
    # WP-10 (Document 64, SPEC-SEC-004) — same rows tests/conftest.py's own independent copy adds. No
    # new role: the existing Document 62 "Security Admin" actor owns security-infrastructure config
    # (identity providers, sessions, service identities) and outbound-destination / webhook-profile
    # registration is the same class of action — reused rather than duplicated. No Document 106 row
    # exists for any SPEC-SEC-004 action, so none of these carries a signature.
    ("outbound_destination.register", "register", "outbound_destination", "Register an SSRF-allowlist outbound destination (Document 64)"),
    ("webhook_profile.register", "register", "webhook_profile", "Register an inbound webhook trust profile (Document 64)"),
    ("api_inventory.view", "view", "api_security_policy", "Read the live API security inventory (Document 64)"),
    # WP-10 (Document 65, SPEC-SEC-005) — same rows tests/conftest.py's own independent copy adds.
    # secret.rotate / crypto_health.view have no Document 106 row -> RBAC only. certificate.issue/
    # rotate/revoke each carry a Released signature (Document 106 rows 137-139, QA Releaser, independent).
    ("secret.rotate", "rotate", "secret_metadata", "Rotate a managed secret's metadata/version (Document 65)"),
    ("certificate.issue", "issue", "certificate_metadata", "Issue a service/Edge/admin certificate (Document 65)"),
    ("certificate.rotate", "rotate", "certificate_metadata", "Rotate a certificate with overlap (Document 65)"),
    ("certificate.revoke", "revoke", "certificate_metadata", "Revoke a certificate (Document 65)"),
    ("crypto_health.view", "view", "crypto_profile", "Read the crypto self-test / health report (Document 65)"),
    # WP-10 (Document 66, SPEC-SEC-006) — read-only catalogue module, no state-changing op, no signature.
    ("network_flow.view", "view", "network_flow_definition", "Read the approved network-flow catalogue (Document 66)"),
    ("deployment_security_profile.view", "view", "deployment_security_profile", "Read the deployment security profile (Document 66)"),
    # WP-10 (Document 67, SPEC-SEC-007) — incident open/contain/evidence/gxp_impact are RBAC + reason
    # (no Document 106 row); close is signed (Document 106 row 140, independent QA Releaser).
    ("security_incident.open", "open", "security_incident", "Open a security incident (Document 67)"),
    ("security_incident.contain", "contain", "security_incident", "Execute an allowlisted containment action (Document 67)"),
    ("security_incident.evidence", "evidence", "security_incident", "Preserve forensic evidence with chain-of-custody (Document 67)"),
    ("security_incident.gxp_impact", "gxp_impact", "security_incident", "Record the GxP-impact assessment (Document 67)"),
    ("security_incident.close", "close", "security_incident", "Close a security incident (Document 67, signed)"),
    # WP-10 (Document 68, SPEC-SEC-008) — vulnerability register/assess are RBAC + reason (no Document
    # 106 row). vulnerability.exception is signed per Document 106 row 141 but that role is unresolvable
    # (SG-165, same shape as SG-161) so the command fails closed with SIGNATURE_POLICY_UNRESOLVED.
    ("vulnerability.register", "register", "vulnerability_record", "Register a vulnerability finding (Document 68)"),
    ("vulnerability.assess", "assess", "vulnerability_record", "Assess a vulnerability's severity/KEV/GxP impact (Document 68)"),
    ("vulnerability.exception", "exception", "vulnerability_record", "Approve a time-bounded vulnerability exception (Document 68, SG-165)"),
    ("release_security_evidence.view", "view", "release_security_evidence", "Read a release's security-evidence bundle (Document 68)"),
    # WP-11 (Document 69, SPEC-DATA-001) — same rows tests/conftest.py's own independent copy adds. All
    # RBAC-only: Document 106 has no SPEC-DATA-001 row and Document 106 # 10 exempts projection
    # rebuilds and reads from any signature.
    ("data_ownership.view", "view", "data_ownership_registry", "Resolve an entity's authoritative owner/store + read projection freshness (Document 69)"),
    ("projection.rebuild", "rebuild", "projection_checkpoint", "Rebuild a non-authoritative projection from its authoritative source (Document 69)"),
    ("data_dictionary.view", "view", "data_ownership_registry", "Read the generated data-ownership/lineage dictionary (Document 69)"),
    # WP-11 (Document 72, SPEC-DATA-004) — same rows tests/conftest.py's own independent copy adds.
    # evidence.legal_hold is signed (Document 106 row 142, equipment_asset/hold precedent); rest RBAC-only.
    ("evidence.upload", "upload", "evidence_object", "Stage/finalize a regulated evidence object upload (Document 72)"),
    ("evidence.download", "download", "evidence_object", "Authorized download of a finalized evidence object (Document 72)"),
    ("evidence.manifest", "create", "evidence_manifest", "Create an immutable evidence manifest (Document 72)"),
    ("evidence.legal_hold", "legal_hold", "evidence_object", "Apply a legal hold to an evidence object (Document 72, signed — Document 106 row 142)"),
    ("evidence.integrity_check", "verify", "evidence_object", "Run an evidence integrity check over a scope (Document 72)"),
    # WP-11 (Document 75, SPEC-DATA-007) — same rows tests/conftest.py's own independent copy adds.
    # RBAC-only: Document 106 has no SPEC-DATA-007 row (Document 106 # 10 exempts rebuilds/reads).
    ("search.query", "query", "projection_document_metadata", "Authorized search query / result detail (Document 75)"),
    ("search.rebuild", "rebuild", "read_model_checkpoint", "Rebuild a search index from the authoritative source (Document 75)"),
    ("report.export", "export", "read_model_checkpoint", "Generate a frozen-cutoff async report export (Document 75)"),
    # WP-11 (Document 76, SPEC-DATA-008) — same rows tests/conftest.py's own independent copy adds.
    # RBAC-only: Document 106 has no SPEC-DATA-008 row.
    ("dr.recovery_objective.manage", "manage", "recovery_objective_profile", "Set/update a component's RPO/RTO recovery tier (Document 76)"),
    ("dr.backup.view", "view", "backup_inventory", "Read backup freshness / RPO-at-risk status (Document 76)"),
    ("dr.restore_test.execute", "execute", "restore_test", "Record an executed restore/PITR drill (Document 76)"),
    # WP-13 (Document 105, SPEC-AI-001) — the 13 FN-1005..FN-1017 functions. No existing role maps
    # cleanly to "AI governance operator/reviewer" (§2 of every other new-module block above uses the
    # same test); granted to Admin + QA Reviewer below with that reasoning, not a spec mapping.
    ("ai_governance.use_case.register", "register", "ai_use_case", "Register an AI use case (Document 105, AI-FR-001/002)"),
    ("ai_governance.use_case.assess_risk", "assess_risk", "ai_use_case", "Record an AI use-case risk assessment (Document 105, AI-FR-003)"),
    ("ai_governance.model.approve", "approve", "ai_model_deployment", "Approve an AI model deployment (Document 105, AI-FR-007/021 — signature policy lookup required, SG-167)"),
    ("ai_governance.context.build", "build", "ai_context_package", "Build a retrieval-scoped AI request context (Document 105, AI-FR-011/030/031)"),
    ("ai_governance.advisory.execute", "execute", "ai_advisory_log", "Execute an AI advisory call and log it (Document 105, AI-FR-005/028)"),
    ("ai_governance.tool.authorize", "authorize", "ai_tool_decision", "Authorize an AI tool call (Document 105, AI-FR-009/010 — signature policy lookup required, SG-167)"),
    ("ai_governance.disposition.record", "record", "ai_disposition", "Record the human disposition of an AI advisory (Document 105, AI-FR-005 — signature policy lookup required, SG-167)"),
    ("ai_governance.evaluation.run", "run", "ai_evaluation_report", "Run an AI evaluation suite against acceptance thresholds (Document 105, AI-FR-022/024)"),
    ("ai_governance.release_gate.evaluate", "evaluate", "ai_release_gate", "Evaluate the AI model/prompt/tool release gate (Document 105, AI-FR-021 — signature policy lookup required, SG-167)"),
    ("ai_governance.injection.detect", "detect", "ai_prompt_injection_event", "Screen content for prompt injection (Document 105, AI-FR-014/025)"),
    ("ai_governance.provider.switch", "switch", "ai_provider_switch", "Switch an AI use case's active provider/model (Document 105 — signature policy lookup required, SG-167)"),
    ("ai_governance.use_case.retire", "retire", "ai_use_case", "Retire an AI use case (Document 105)"),
    ("ai_governance.package.generate", "generate", "ai_use_case", "Generate an AI governance evidence package (Document 105, AI-FR-028)"),
    # WP-12 (Documents 79-86/88-96, SPEC-VAL-001..018) + WP-14 (Documents 85/87/95, SPEC-VAL-007/009/017)
    # — 58 codes, one per router-level evaluate_policy() call in app/modules/validation/router.py and
    # router_wp14.py. No dedicated "Validation Engineer"/"System Owner" role exists yet; `.manage`/
    # `.create`/`.execute`/`.complete`/`.view` map to Operator (the general "does the work" role), and
    # `.approve`/`.release`/`.authorize`/`.deployment_check`/`.post_go_live.record` map to QA Releaser
    # (final release authority, matching every other WP's convention). QA Reviewer gets the review/view
    # subset plus the WP-14 migration/VSR preparer actions (that's the role Document 87/95's own test
    # suite exercises for authoring those records). Per-instance SoD independence (e.g. "the releaser
    # cannot be the recommender") is enforced in the domain functions themselves (Document 106 rows
    # 166/169), not by this RBAC grant — this only gates who may attempt the action at all.
    ("validation.plan.manage", "manage", "validation_master_plan", "Create/update a validation master plan (Document 79)"),
    ("validation.plan.release", "release", "validation_master_plan", "Release a validation master plan (Document 79)"),
    ("validation.gate.view", "view", "validation_release_gate", "View a release's validation gate status (Document 79)"),
    ("validation.package.view", "view", "validation_master_plan", "View/export a validation evidence package (Document 79)"),
    ("validation.intended_use.manage", "manage", "intended_use", "Record an intended-use/criticality determination (Document 80)"),
    ("validation.function_risk.manage", "manage", "function_risk_assessment", "Create/update a function risk assessment (Document 80)"),
    ("validation.function_risk.approve", "approve", "function_risk_assessment", "Approve a function risk assessment (Document 80)"),
    ("validation.function_risk.view", "view", "function_risk_assessment", "View a function's risk/assurance depth (Document 80)"),
    ("validation.requirement.manage", "manage", "validation_requirement", "Ingest/update validation requirements (Document 81)"),
    ("validation.trace_link.manage", "manage", "trace_link", "Create a requirement/design/test trace link (Document 81)"),
    ("validation.baseline.manage", "manage", "requirement_baseline", "Baseline a requirement set (Document 81)"),
    ("validation.traceability.view", "view", "trace_link", "View traceability matrix/coverage gaps (Document 81)"),
    ("validation.test_definition.manage", "manage", "validation_test_definition", "Author a validation test definition (Document 82)"),
    ("validation.test_definition.approve", "approve", "validation_test_definition", "Approve a validation test definition (Document 82)"),
    ("validation.test_execution.manage", "manage", "validation_test_execution", "Record/start a validation test execution (Document 82)"),
    ("validation.test_execution.complete", "complete", "validation_test_execution", "Complete a validation test execution (Document 82)"),
    ("validation.iq.manage", "manage", "iq_protocol", "Author an IQ protocol / record an IQ execution (Document 83)"),
    ("validation.iq.complete", "complete", "iq_execution", "Complete an IQ execution (Document 83)"),
    ("validation.iq.approve", "approve", "iq_execution", "Approve an IQ execution (Document 83)"),
    ("validation.oq.manage", "manage", "oq_suite", "Author an OQ suite / record an OQ execution (Document 84)"),
    ("validation.oq.view", "view", "oq_execution", "View OQ functional-control coverage (Document 84)"),
    ("validation.oq.approve", "approve", "oq_execution", "Approve an OQ execution (Document 84)"),
    ("validation.infrastructure.manage", "manage", "infrastructure_qualification_profile", "Record an infrastructure qualification profile/fingerprint/test (Document 86)"),
    ("validation.infrastructure.approve", "approve", "infrastructure_fingerprint", "Approve an infrastructure qualification fingerprint (Document 86)"),
    ("validation.part11.manage", "manage", "part11_scope_assessment", "Record a Part 11 scope assessment/test suite/control result (Document 88)"),
    ("validation.part11.approve", "approve", "part11_scope_assessment", "Approve a Part 11 scope assessment (Document 88)"),
    ("validation.data_integrity.manage", "manage", "data_integrity_test_profile", "Record a data-integrity test suite/tamper test (Document 89)"),
    ("validation.data_integrity.approve", "approve", "data_integrity_test_profile", "Approve a data-integrity test profile (Document 89)"),
    ("validation.interface.manage", "manage", "interface_validation_profile", "Record an interface validation profile/test (Document 90)"),
    ("validation.interface.approve", "approve", "interface_validation_profile", "Approve an interface validation profile (Document 90)"),
    ("validation.dr.manage", "manage", "dr_qualification_scenario", "Record a DR qualification scenario/execution/measurement (Document 91)"),
    ("validation.dr.approve", "approve", "dr_qualification_execution", "Approve a DR qualification execution (Document 91)"),
    ("validation.security.manage", "manage", "security_qualification_suite", "Record a security qualification suite/test/finding (Document 92)"),
    ("validation.security.view", "view", "security_qualification_suite", "View a security qualification gate (Document 92)"),
    ("validation.security.approve", "approve", "security_qualification_suite", "Approve a security qualification suite (Document 92)"),
    ("validation.performance.manage", "manage", "performance_qualification_scenario", "Record a performance qualification scenario/run/evaluation (Document 93)"),
    ("validation.performance.view", "view", "performance_run", "View performance/capacity sizing evidence (Document 93)"),
    ("validation.exception.create", "create", "validation_exception", "Log a validation defect/deviation/test exception (Document 94)"),
    ("validation.exception.triage", "triage", "validation_exception", "Triage a validation exception (Document 94)"),
    ("validation.exception.retest_plan", "retest_plan", "validation_exception", "Record a validation exception's retest plan (Document 94)"),
    ("validation.exception.disposition", "disposition", "validation_exception", "Disposition a validation exception (Document 94)"),
    ("validation.exception.view", "view", "validation_exception", "View a release's open validation exception gate (Document 94)"),
    ("validation.change_impact.manage", "manage", "validation_change_impact", "Record a change impact/revalidation plan (Document 96)"),
    ("validation.periodic_review.manage", "manage", "periodic_validation_review", "Record a periodic validation review (Document 96)"),
    ("validation.periodic_review.decide", "decide", "periodic_validation_review", "Decide a periodic validation review outcome (Document 96)"),
    ("validation.state_baseline.decommission", "decommission", "validated_state_baseline", "Decommission a validated-state baseline (Document 96)"),
    ("validation.pq.manage", "manage", "pq_scenario", "Author a PQ scenario / assign participants (Document 85)"),
    ("validation.pq.execute", "execute", "pq_execution", "Execute a PQ scenario (Document 85)"),
    ("validation.pq.approve", "approve", "pq_scenario", "Approve a PQ scenario (Document 85)"),
    ("validation.migration.manage", "manage", "migration_validation_plan", "Author a migration validation plan / record a migration run/reconciliation (Document 87)"),
    ("validation.migration.approve", "approve", "migration_run", "Approve a migration run (Document 87)"),
    ("validation.migration.trace_view", "trace_view", "migration_validation_plan", "Look up a legacy record's migration trace (Document 87)"),
    ("validation.vsr.manage", "manage", "validation_summary_report", "Author a validation summary report (Document 95)"),
    ("validation.vsr.approve", "approve", "validation_summary_report", "Approve a validation summary report (Document 95)"),
    ("validation.release_auth.view", "view", "validated_release_authorization", "View go-live readiness for a validated release (Document 95)"),
    ("validation.release_auth.authorize", "authorize", "validated_release_authorization", "Authorize a validated release for production (Document 95)"),
    ("validation.release_auth.deployment_check", "deployment_check", "validated_release_authorization", "Check deployed artifacts against the validated release (Document 95)"),
    ("validation.post_go_live.record", "record", "validated_release_authorization", "Record a post-go-live verification outcome (Document 95)"),
]

# Every WP-05 QMS `.view` code, granted together wherever a role can see quality records at all.
QMS_VIEW_CODES = [
    "qms_deviation.view", "capa.view", "ncr.view", "change.view", "document.view",
    "training.subject.view", "training.matrix.view", "risk.view", "risk.dashboard.view",
    "scar.view", "internal_audit.view", "complaint.view", "field_action.view",
    "quality_metric.dashboard.view", "packaging.view", "supplier.view",
]

# Every WP-05 QMS mutating code, for the Admin grant below.
QMS_WRITE_CODES = [
    "qms_deviation.create", "qms_deviation.triage", "qms_deviation.contain", "qms_deviation.investigate",
    "qms_deviation.impact", "qms_deviation.disposition", "qms_deviation.extend", "qms_deviation.close",
    "qms_deviation.reopen",
    "capa.create", "capa.plan", "capa.action.add", "capa.action.complete", "capa.effectiveness",
    "capa.extend", "capa.close", "capa.reopen",
    "ncr.create", "ncr.segregate", "ncr.evaluate", "ncr.disposition", "ncr.verify", "ncr.close",
    "change.create", "change.impact", "change.approve", "change.task.add", "change.implement",
    "change.verify", "change.make_effective", "change.close",
    "document.create", "document.submit", "document.release", "document.make_effective",
    "document.obsolete", "document.controlled_copy.issue",
    "training.requirement.create", "training.assignment.create", "training.assignment.complete",
    "training.assignment.assess", "training.qualification.create", "training.waiver.create",
    "risk.create", "risk.assessment.add", "risk.controls.add", "risk.accept", "risk.review",
    "scar.case.create", "scar.issue", "scar.response", "scar.review", "scar.effectiveness", "scar.close",
    "internal_audit.create", "internal_audit.start", "internal_audit.finding.add",
    "internal_audit.finding.response", "internal_audit.finding.verify", "internal_audit.close",
    "complaint.create", "complaint.triage", "complaint.investigation_decision", "complaint.investigate",
    "complaint.reportability", "complaint.response", "complaint.close",
    "field_action.create", "field_action.scope", "field_action.reportability", "field_action.approve",
    "field_action.communications", "field_action.reconcile", "field_action.effectiveness",
    "field_action.close",
    "quality_metric.definition.create", "quality_metric.definition.release", "quality_metric.calculate",
    "quality_metric.management_review", "effectiveness_check.create", "effectiveness_check.evaluate",
]

# Role -> permission codes it's granted, matching exactly what require_role()/require_admin_anywhere()
# hardcoded before the policy engine replaced them — this seed is what keeps behaviour identical.
ROLE_PERMISSIONS = {
    "Admin": [
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
        "qc_test_specification.release", "qc_test_order.review", "qc_result.correct", "lims_sample.cancel",
        "oos_record.extended_investigation", "oos_record.disposition", "oos_record.close", "oot_record.close",
        "material_receipt.create", "material_receipt.examine", "material_lot.sampling_order",
        "material_lot.collect_sample", "material_lot.release", "material_lot.reject", "material_lot.retest",
        "warehouse_location.create",
        "inventory_reservation.create", "inventory_reservation.release", "inventory_transaction.transfer",
        "material_container.split", "material_container.merge", "inventory_cycle_count.execute",
        "dispensing_order.create", "dispensing_order.select_source", "dispensing_order.start",
        "dispensing_order.readings", "dispensing_order.manual_reading", "dispensing_order.verify",
        "dispensing_order.complete", "dispensing_order.cancel",
        "material_consumption.create", "material_return.create", "material_loss.create",
        "inventory_adjustment_request.create", "inventory_adjustment_request.approve",
        "destruction_record.create", "destruction_record.execute", "material_reconciliation.evaluate",
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
        "signal_mapping.release", "batch_context.open", "batch_context.close", "machine_command.submit",
        "machine_replay.create", "machine_evidence.review_view", "yield_calculation.evaluate", "reconciliation.evaluate", "reconciliation.verify",
        "ddcp_profile.author", "ddcp_profile.release", "ddcp_constituent.handoff", "ddcp_constituent.decide",
        "ddcp_fill.start", "ddcp_fill.record_ipc", "ddcp_fill.record_count", "ddcp_fill.record_intervention",
        "ddcp_fill.complete", "ddcp_device.assemble", "ddcp_device.verify", "ddcp_device.record_test",
        "ddcp_release.evaluate", "ddcp_release.export",
        "postmarket_source.register", "safety_case.create", "safety_case.resolve_product", "safety_case.classify",
        "safety_case.followup", "safety_case.link_duplicates", "safety_case.view", "safety_signal.open",
        "safety_signal.assess", "safety_signal.escalate", "safety_signal.view", "postmarket_dataset.freeze",
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
        # WP-11 (Document 69, SPEC-DATA-001): data-ownership registry / dictionary reads + projection rebuild.
        "data_ownership.view", "projection.rebuild", "data_dictionary.view",
        "evidence.upload", "evidence.download", "evidence.manifest", "evidence.legal_hold",
        "evidence.integrity_check",
        "search.query", "search.rebuild", "report.export",
        "dr.recovery_objective.manage", "dr.backup.view", "dr.restore_test.execute",
        # WP-13 (Document 105, SPEC-AI-001).
        "ai_governance.use_case.register", "ai_governance.use_case.assess_risk", "ai_governance.model.approve",
        "ai_governance.context.build", "ai_governance.advisory.execute", "ai_governance.tool.authorize",
        "ai_governance.disposition.record", "ai_governance.evaluation.run", "ai_governance.release_gate.evaluate",
        "ai_governance.injection.detect", "ai_governance.provider.switch", "ai_governance.use_case.retire",
        "ai_governance.package.generate",
        # WP-12/WP-14 (Documents 79-96, SPEC-VAL-001..018).
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
        *QMS_WRITE_CODES, *QMS_VIEW_CODES,
    ],
    "Operator": ["batch_step.start", "rules.evaluate", "product.view", "recipe.view", "batch_execution.execute", "batch_execution.view", "device.execute", "device.view", "genealogy.view", "qa_review.view", "release.view", "packaging.execute", "material_receipt.create", "material_receipt.examine", "material_lot.sampling_order", "inventory_reservation.create", "inventory_transaction.transfer", "material_container.split", "material_container.merge", "inventory_cycle_count.execute", "dispensing_order.create", "dispensing_order.select_source", "dispensing_order.start", "dispensing_order.readings", "dispensing_order.manual_reading", "dispensing_order.complete", "material_consumption.create", "material_return.create", "material_loss.create", "inventory_adjustment_request.create", "destruction_record.create", "destruction_record.execute", "equipment_asset.hold", "cleaning_execution.create", "cleaning_execution.complete", "line_clearance.create", "line_clearance.complete", "batch_context.open", "batch_context.close", "yield_calculation.evaluate", "reconciliation.evaluate", *QMS_VIEW_CODES, "qms_deviation.create", "ncr.create", "complaint.create", "training.assignment.complete", "validation.plan.manage", "validation.gate.view", "validation.package.view", "validation.intended_use.manage", "validation.function_risk.manage", "validation.function_risk.view", "validation.requirement.manage", "validation.trace_link.manage", "validation.baseline.manage", "validation.traceability.view", "validation.test_definition.manage", "validation.test_execution.manage", "validation.test_execution.complete", "validation.iq.manage", "validation.iq.complete", "validation.oq.manage", "validation.oq.view", "validation.infrastructure.manage", "validation.part11.manage", "validation.data_integrity.manage", "validation.interface.manage", "validation.dr.manage", "validation.security.manage", "validation.security.view", "validation.performance.manage", "validation.performance.view", "validation.exception.view", "validation.change_impact.manage", "validation.periodic_review.manage", "validation.periodic_review.decide", "validation.state_baseline.decommission", "validation.pq.manage", "validation.pq.execute", "validation.migration.manage", "validation.migration.trace_view", "validation.vsr.manage", "validation.release_auth.view"],
    "Supervisor": ["batch_step.start", "batch_step.role_override", "rules.evaluate", "product.view", "recipe.view", "batch_execution.create", "batch_execution.issue", "batch_execution.execute", "batch_execution.view", "device.create", "device.execute", "device.view", "genealogy.view", "qa_review.view", "release.view", "packaging.execute", "material_receipt.create", "material_receipt.examine", "material_lot.sampling_order", "warehouse_location.create", "inventory_reservation.create", "inventory_transaction.transfer", "material_container.split", "material_container.merge", "inventory_cycle_count.execute", "dispensing_order.create", "dispensing_order.select_source", "dispensing_order.start", "dispensing_order.readings", "dispensing_order.manual_reading", "dispensing_order.complete", "material_consumption.create", "material_return.create", "material_loss.create", "inventory_adjustment_request.create", "destruction_record.create", "destruction_record.execute", "material_reconciliation.evaluate", "line_clearance.create", "line_clearance.complete", "batch_context.open", "batch_context.close", "yield_calculation.evaluate", "reconciliation.evaluate", *QMS_VIEW_CODES, "qms_deviation.create", "qms_deviation.triage", "qms_deviation.contain", "ncr.create", "ncr.segregate", "complaint.create", "change.create", "change.task.add", "change.implement", "training.requirement.create", "training.assignment.create"],
    "QA Reviewer": ["batch.review", "audit.review", "vault.review", "rules.evaluate", "product.view", "recipe.view", "batch_execution.view", "device.view", "genealogy.view", "qa_review.create", "qa_review.execute", "qa_review.view", "release.evaluate", "release.hold", "release.view", "qc_test_order.review", "oos_record.extended_investigation", "equipment_asset.hold", "equipment_asset.return_to_service", "cleaning_execution.create", "cleaning_execution.complete", "cleaning_execution.verify", "em_sample.review", "em_excursion.impact", "process_cycle.create", "process_cycle.start", "process_cycle.review", "reconciliation.verify", "machine_evidence.review_view", "evidence.upload", "evidence.download", "evidence.manifest", "evidence.legal_hold", "evidence.integrity_check", *QMS_VIEW_CODES, "qms_deviation.create", "qms_deviation.triage", "qms_deviation.contain", "qms_deviation.investigate", "qms_deviation.impact", "qms_deviation.extend", "capa.create", "capa.plan", "capa.action.add", "capa.action.complete", "capa.extend", "ncr.create", "ncr.segregate", "ncr.evaluate", "ncr.verify", "change.create", "change.impact", "change.task.add", "change.implement", "change.verify", "document.create", "document.submit", "complaint.create", "complaint.triage", "complaint.investigation_decision", "complaint.investigate", "risk.create", "risk.assessment.add", "risk.controls.add", "risk.review", "scar.case.create", "scar.issue", "scar.response", "scar.review", "internal_audit.create", "internal_audit.start", "internal_audit.finding.add", "internal_audit.finding.response", "field_action.create", "field_action.scope", "field_action.communications", "field_action.reconcile", "quality_metric.calculate", "effectiveness_check.create", "ai_governance.use_case.register", "ai_governance.use_case.assess_risk", "ai_governance.context.build", "ai_governance.advisory.execute", "ai_governance.disposition.record", "ai_governance.evaluation.run", "ai_governance.release_gate.evaluate", "ai_governance.injection.detect", "validation.gate.view", "validation.package.view", "validation.function_risk.approve", "validation.function_risk.view", "validation.traceability.view", "validation.oq.view", "validation.security.view", "validation.performance.view", "validation.exception.view", "validation.periodic_review.decide", "validation.migration.manage", "validation.migration.trace_view", "validation.vsr.manage", "validation.release_auth.view"],
    "QA Releaser": ["batch.release", "audit.review", "vault.review", "vault.correct", "rules.evaluate", "product.view", "product.release", "recipe.view", "recipe.release", "batch_execution.view", "device.view", "genealogy.view", "qa_review.view", "release.evaluate", "release.release", "release.hold", "release.reject", "release.view", "supplier_qualification.approve", "qc_test_specification.release", "lims_sample.cancel", "oos_record.disposition", "oos_record.close", "oot_record.close", "material_lot.release", "material_lot.reject", "material_lot.retest", "inventory_reservation.release", "dispensing_order.cancel", "inventory_adjustment_request.create", "inventory_adjustment_request.approve", "material_reconciliation.evaluate", "equipment_asset.hold", "edge_gateway.certificate_rotation", "signal_mapping.release", *QMS_VIEW_CODES, "qms_deviation.disposition", "qms_deviation.close", "qms_deviation.reopen", "capa.effectiveness", "capa.close", "capa.reopen", "ncr.disposition", "ncr.close", "change.approve", "change.make_effective", "change.close", "document.release", "document.make_effective", "document.obsolete", "document.controlled_copy.issue", "training.assignment.assess", "training.qualification.create", "training.waiver.create", "risk.accept", "scar.effectiveness", "scar.close", "internal_audit.finding.verify", "internal_audit.close", "complaint.reportability", "complaint.response", "complaint.close", "field_action.reportability", "field_action.approve", "field_action.effectiveness", "field_action.close", "quality_metric.definition.create", "quality_metric.definition.release", "quality_metric.management_review", "effectiveness_check.evaluate", "privileged_access.approve", "privileged_session.close", "privileged_session.review", "security_incident.close", "validation.exception.create", "validation.exception.triage", "validation.exception.retest_plan", "validation.exception.disposition", "validation.plan.release", "validation.function_risk.approve", "validation.test_definition.approve", "validation.iq.approve", "validation.oq.approve", "validation.infrastructure.approve", "validation.part11.approve", "validation.data_integrity.approve", "validation.interface.approve", "validation.dr.approve", "validation.security.approve", "validation.pq.approve", "validation.migration.approve", "validation.vsr.approve", "validation.release_auth.authorize", "validation.release_auth.deployment_check", "validation.post_go_live.record"],
    "QC Reviewer": ["material_lot.disposition", "audit.review", "vault.review", "rules.evaluate", "product.view", "recipe.view", "batch_execution.view", "device.view", "genealogy.view", "qa_review.view", "release.view", "qc_result.correct", "material_lot.collect_sample", "material_lot.retest", "dispensing_order.verify", "cleaning_execution.verify", "em_sample.review", "process_cycle.review", *QMS_VIEW_CODES, "qms_deviation.create", "ncr.create", "ncr.evaluate", "ncr.verify", "capa.action.complete"],
    # Document 38 (SPEC-EQP-001) actor-specific roles — grants scoped to exactly the operation each actor
    # performs (§2), no broader platform access.
    "Equipment Administrator": ["equipment_asset.create", "equipment_asset.qualify", "machine_command.submit", "equipment_area.create"],
    "Engineering Manager": ["equipment_asset.return_to_service"],
    "Calibration Technician": ["equipment_asset.calibrate"],
    "Maintenance Technician": ["equipment_asset.maintain"],
    # Document 39 (SPEC-EQP-002) actor-specific role.
    "Sanitation Operator": ["cleaning_execution.create", "cleaning_execution.complete", "line_clearance.create", "line_clearance.complete"],
    # Document 41 (SPEC-EQP-004) actor-specific roles.
    "EM Technician": ["em_program.create", "em_sample.create", "em_sample.record_result"],
    "Microbiology Analyst": ["em_sample.record_result"],
    # Document 42 (SPEC-EQP-005) actor-specific role.
    "Sterilization Operator": ["process_cycle.create", "process_cycle.start", "sterile_filter_use.create", "sterile_filter_use.complete"],
    # Document 40 (SPEC-EQP-003) actor-specific roles -- Aseptic Operator performs the recorded work
    # (create/interventions/events/complete, Document 106 row 112's "qualified performer for the task");
    # Aseptic Supervisor authorizes start (row 113's "Production Supervisor or qualified issuer").
    "Aseptic Operator": ["aseptic_operation.create", "aseptic_operation.intervention", "aseptic_operation.event", "aseptic_operation.complete"],
    "Aseptic Supervisor": ["aseptic_operation.start", "aseptic_profile_version.create"],
    # Document 10 (SPEC-EBMR-002) -- master-recipe author. Draft/edit/validate/simulate/submit only;
    # recipe.release is deliberately NOT here (it sits with QA Releaser / Admin) so authoring and release
    # are held by different roles. Closes the DDCP_Client_Demo_Guide §9.1 "author == releaser" gap.
    "Process Engineer": ["product.author", "product.view", "recipe.author", "recipe.view", "rules.evaluate"],
    # WP-07 (Documents 48/52/53) actor-specific role -- ERP-ARC-027 "authorized integration admin" gets
    # the whole shared integration-gateway surface; no independent-signer split exists (SG-122: every
    # action here is RBAC-gated only, not signed).
    "Integration Administrator": [
        "erp_instance.administer", "erp_mapping.propose", "erp_mapping.approve", "erp_mapping.resolve_conflict",
        "erp_sync.checkpoint", "integration_command.queue", "integration_command.dispatch",
        "integration_command.retry", "integration_command.cancel", "integration_event.ingest",
        "integration_reconciliation.manage",
        # Document 47 (SPEC-EDGE-005) SG-131 -- same actor class as ERP-ARC-027's "authorized integration
        # admin", reused rather than inventing a new role.
        "machine_replay.create",
    ],
    # WP-08 (Document 54, SPEC-DDCP-001) actor-specific roles -- DDCP Engineer authors/releases the
    # profile master (Product/Quality Engineer per §4); DDCP Operator performs every execution-time action
    # (constituent handoff decisions, filling, device assembly/verification, functional-test linking,
    # release-readiness evaluation and evidence export). SG-148: no Document 106 row splits these into a
    # signed performer/independent-reviewer pair, so this is a single combined operator role rather than
    # the Aseptic Operator/Supervisor split above -- IND-001 (device assembly performer != verifier) is
    # enforced by user identity in commands.py regardless of role, not by a role split.
    "DDCP Engineer": ["ddcp_profile.author", "ddcp_profile.release"],
    "DDCP Operator": [
        "ddcp_constituent.handoff", "ddcp_constituent.decide", "ddcp_fill.start", "ddcp_fill.record_ipc",
        "ddcp_fill.record_count", "ddcp_fill.record_intervention", "ddcp_fill.complete", "ddcp_device.assemble",
        "ddcp_device.verify", "ddcp_device.record_test", "ddcp_release.evaluate", "ddcp_release.export",
        # Every action above is scoped to a batch, but without this the role has no way to browse/select
        # one at all (GET /batches/v1 -- the picker every DDCP screen's batch field depends on -- gates
        # on batch_execution.view) -- discovered when a second, independent DDCP Operator user needed to
        # verify a device assembly step (IND-001) and had no batch picker to find it with.
        "batch_execution.view",
    ],
    # WP-09 (Document 58, SPEC-PM-001) actor-specific roles -- Postmarket Safety Reviewer performs the
    # intake/classification/signal-assessment work Document 58 assigns to "Safety reviewer"/"Safety/
    # Medical/Quality team"; Postmarket Regulatory Affairs performs the escalation/dataset-freeze actions
    # matching Document 106's "Regulatory Affairs authorized submitter" signer class (reused verbatim for
    # Document 59 once built, per that class's own precedent at Document 106 rows 8/12).
    "Postmarket Safety Reviewer": [
        "postmarket_source.register", "safety_case.create", "safety_case.resolve_product", "safety_case.classify",
        "safety_case.followup", "safety_case.link_duplicates", "safety_case.view",
        "safety_signal.open", "safety_signal.assess", "safety_signal.view",
    ],
    "Postmarket Regulatory Affairs": [
        "safety_case.view", "safety_signal.view", "safety_signal.escalate", "postmarket_dataset.freeze",
        # SG-138 (2026-09-10, project-owner-directed): Document 106 section 9 rows 102/105's "Regulatory
        # Affairs authorized submitter" signer class for the WP-05 QMS reportability assessments maps to
        # this same role; grant the two QMS reportability actions so an actual holder can perform them.
        "complaint.reportability", "field_action.reportability",
        # Document 106 rows 123/125/126/127/128's "Regulatory Affairs authorized submitter" signer class
        # (Document 59) -- this role is the operationalization of that signer class into an actual role.
        "reportability_track.create", "reportability_track.calculate_deadline", "reportability_track.view",
        "regulatory_report.create", "regulatory_report.generate_payload", "regulatory_report.submit",
        "regulatory_report.followup", "regulatory_submission.acknowledge",
        # Document 60's own actor -- "Regulatory Admin"/"Regulatory user"/"Regulatory reviewer" in its
        # function catalogue all map to this same role, same reuse discipline as Document 59 above.
        "applicant_relationship.configure", "constituent_information_share.evaluate",
        "constituent_information_share.package", "constituent_information_share.record_sent",
        "correction_removal.create", "regulatory_obligation.create", "regulatory_obligation.view",
        "periodic_reporting_cycle.generate", "periodic_reporting_cycle.freeze",
    ],
    # WP-10 (Document 61, SPEC-SEC-001) actor-specific roles -- Security Architect performs the
    # architecture/threat/control-mapping/risk-calculation/review-trigger work Document 61 # 2 assigns to
    # "Security Architect"/"Security Engineer"/"System Architect" (combined: no Document 106 row or
    # Document 61 text splits these three into distinct signed steps); Security Risk Approver holds the
    # risk-acceptance and exception-opening actions Document 61 assigns to "Security/Quality/Business
    # approver"/"Security owner" -- both endpoints fail closed regardless of role per SG-161 (no Document
    # 106 resolution exists for either), so this role only gates who may *attempt* them.
    "Security Architect": [
        "security_threat_model.create", "security_threat_model.trigger_review", "security_control_matrix.view",
        "security_threat.register", "security_threat.map_control", "security_threat.calculate_risk",
    ],
    "Security Risk Approver": [
        "security_control_matrix.view", "security_threat.accept_risk", "security_exception.open", "security_exception.view",
        # Document 68 (SPEC-SEC-008): the RBAC gate for vulnerability-exception approval (which itself
        # fails closed at the signature step -- SG-165). Same "risk-acceptance / exception" actor.
        "vulnerability.exception",
    ],
    # Document 62 (WP-10, SPEC-SEC-002) — Document 62 # 2's own "Security Admin" actor: identity
    # provider/federation config, session revocation and service-identity lifecycle.
    "Security Admin": [
        "identity_provider.create", "identity_provider.map_identity", "identity_provider.validate_token",
        "application_session.view", "application_session.revoke",
        "service_identity.provision", "service_identity.revoke",
        # Document 64 (SPEC-SEC-004): outbound-destination / webhook-profile registration + API inventory.
        "outbound_destination.register", "webhook_profile.register", "api_inventory.view",
        # Document 65 (SPEC-SEC-005): secret rotation, certificate lifecycle (QA Releaser signs), crypto health.
        "secret.rotate", "certificate.issue", "certificate.rotate", "certificate.revoke", "crypto_health.view",
        # Document 66 (SPEC-SEC-006): read the network-flow catalogue + deployment security profile.
        "network_flow.view", "deployment_security_profile.view",
        # Document 67 (SPEC-SEC-007): security-incident response operations (close is QA Releaser's).
        "security_incident.open", "security_incident.contain", "security_incident.evidence",
        "security_incident.gxp_impact",
        # Document 68 (SPEC-SEC-008): vulnerability register/assess + read release security evidence.
        "vulnerability.register", "vulnerability.assess", "release_security_evidence.view",
    ],
    # Document 63 (WP-10, SPEC-SEC-003) actor-specific roles. Platform Admin: requests/uses JIT and
    # break-glass access, executes allowlisted admin commands (PAM-FR-005/009/011/018) -- never granted
    # privileged_access.approve or privileged_session.close/review itself (PAM-FR-016: requester cannot
    # approve their own elevation, enforced in code too). Vendor Support Engineer: read-only support
    # sessions only (PAM-FR-006/007/008), no admin-command execution, no break-glass. QA Releaser (the
    # existing role, not a new one -- see ROLE_NAMES comment above) gets the approve/close/review actions.
    "Platform Admin": [
        "privileged_access.request", "privileged_access.view",
        "privileged_session.break_glass", "privileged_session.execute_command",
    ],
    "Vendor Support Engineer": [
        "privileged_access.request", "privileged_access.view", "privileged_session.open_support",
    ],
}

# Document 107 §4/§5 platform-default SoD floor, seeded verbatim (approved v1.0 baseline). role_a/role_b
# are plain role-name strings — a rule naming a role this deployment hasn't created yet is simply inert,
# not invalid, so the full matrix seeds safely regardless of the 6-role ROLE_NAMES catalogue above.
# (code, rule_type, role_a, role_b, record_class, action, independent_of, severity, rationale)
SOD_STANDING_ROLE_PAIRS = [
    ("SOD-001", "Operator / Production Supervisor", "QA Approver / Batch Release", "PROHIBITED", "Production cannot release its own product (Doc 01 §6.2)."),
    ("SOD-002", "Security Administrator", "QA Approver / Batch Release", "PROHIBITED", "Security admin can alter access; combining with release authority defeats the control."),
    ("SOD-003", "Application Administrator", "QA Approver / Batch Release", "PROHIBITED", "Configuration authority plus release authority removes independent oversight."),
    ("SOD-004", "Enterprise / Site Administrator", "Head of Quality", "PROHIBITED", "Administrative override capability must not sit with the ultimate quality authority."),
    ("SOD-005", "Document Controller", "QA Approver of the same document", "REQUIRES_APPROVAL", "Controller may administer but should not approve content they authored."),
    ("SOD-006", "Deviation Investigator", "QA Approver closing the same deviation", "PROHIBITED", "Investigator cannot approve their own investigation conclusion."),
    ("SOD-007", "CAPA Owner", "CAPA effectiveness approver", "PROHIBITED", "Effectiveness must be judged independently of the owner."),
    ("SOD-008", "Supplier Quality Manager", "Buyer / Procurement Manager", "REQUIRES_APPROVAL", "Supplier approval independent of commercial sourcing pressure."),
    ("SOD-009", "Calibration Technician", "Equipment Administrator approving calibration status", "REQUIRES_APPROVAL", "Performer of calibration should not approve its acceptance."),
    ("SOD-010", "QC Analyst", "QC Manager approving own OOS investigation", "PROHIBITED", "Section 211.192 style independence for OOS conclusions."),
    ("SOD-011", "Sampler", "QC Analyst testing the same sample", "REPORT_ONLY", "Common in small labs; reported and risk-assessed."),
    ("SOD-012", "Material Issuer", "Material Receiver for the same lot", "REPORT_ONLY", "Reported; may be prohibited by customer procedure."),
    ("SOD-013", "Integration Service Account", "Any human role", "PROHIBITED", "Service identities are never human identities (MUT-FR-023)."),
    ("SOD-014", "Read-only Auditor / Inspector", "Any mutating role", "PROHIBITED", "Inspector accounts must remain non-mutating."),
    ("SOD-015", "Training Coordinator", "Approver of own training record", "PROHIBITED", "Self-qualification prohibited."),
    ("SOD-016", "Internal Auditor", "Owner of the audited area's records", "PROHIBITED", "Auditor independence."),
    ("SOD-017", "Packaging Operator", "Label reconciliation approver", "REQUIRES_APPROVAL", "Reconciliation independence for Section 211.125-type controls."),
    ("SOD-018", "Dispensing Operator", "Independent dispensing verifier", "PROHIBITED", "Enforced dynamically per dispense action, see Document 107 section 5 (IND rules)."),
    ("SOD-019", "Regulatory Affairs submitter", "Approver of the same report version", "REQUIRES_APPROVAL", "Submission independence where customer procedure requires."),
    ("SOD-020", "Break-glass / privileged support identity", "Any regulated approval role", "PROHIBITED", "Document 63; privileged access is never an approval path."),
    # 2026-09-08 (Decision 1, option C -- "defer to the customer's Quality org"): unlike SOD-001..020 above
    # (which name descriptive Document 107 roles this deployment maps at PQ), this row names the two REAL
    # roles this platform ships -- Process Engineer authors master data (product.author / recipe.author),
    # QA Releaser releases it. `severity=REPORT_ONLY` on purpose: person-level independence is already
    # hard-enforced by IND-011 (recipe) + IND-021 (product) via release_*_version(), so this pair is
    # documented-and-flagged, not blocking. A customer's Quality org raises it to PROHIBITED in their own
    # SoD matrix (via scripts/sync_sod_rules.py) if their organisation separates the two roles into
    # different people; leaving it REPORT_ONLY keeps the all-roles break-glass `admin` working.
    ("SOD-021", "Process Engineer", "QA Releaser", "REPORT_ONLY", "Master-data author (product.author / recipe.author) should be independent of the releaser; person-level independence is enforced by IND-011 / IND-021. Customer Quality org may raise to PROHIBITED at PQ."),
]

# (code, record_class, action, independent_of, severity, rationale) — stored as data; the dynamic
# per-action evaluator that would actually check these at signature time is not implemented this pass
# (see SPEC_GAP) except for Batch/release, which app/modules/batch/commands.py already enforces directly.
SOD_ACTION_INDEPENDENCE = [
    ("IND-001", "BatchStep", "verify", ["PERFORMER"], "PROHIBITED", "Performer of a batch step cannot also verify it."),
    ("IND-002", "Batch", "release", ["PERFORMER", "QA_REVIEWER"], "PROHIBITED", "Releaser must be independent of every performer on the batch, and of the QA reviewer where two-stage review is configured."),
    ("IND-003", "Batch", "reject", ["PERFORMER"], "PROHIBITED", "Rejecter must be independent of every performer on the batch."),
    ("IND-004", "MaterialDispense", "verify", ["PERFORMER"], "PROHIBITED", "Dispense verifier must be independent of the performer."),
    ("IND-005", "Deviation", "close", ["INVESTIGATOR", "OWNER"], "PROHIBITED", "Closer must be independent of the investigator and owner."),
    ("IND-006", "CAPA", "effectiveness-approve", ["OWNER"], "PROHIBITED", "Effectiveness approver must be independent of the CAPA owner."),
    ("IND-007", "Nonconformance", "disposition-approve", ["REQUESTER"], "PROHIBITED", "Disposition approver must be independent of the requester."),
    ("IND-008", "ChangeControl", "approve", ["AUTHOR"], "PROHIBITED", "Approver must be independent of the change author."),
    ("IND-009", "ControlledDocument", "approve", ["AUTHOR"], "REQUIRES_APPROVAL", "Configurable per document class."),
    ("IND-010", "OOS", "conclusion-approve", ["ANALYST"], "PROHIBITED", "Conclusion approver must be independent of the analyst who produced the result."),
    ("IND-011", "MasterRecipe", "release", ["AUTHOR"], "PROHIBITED", "Releaser must be independent of the recipe author."),
    ("IND-012", "RecordCorrection", "approve", ["CORRECTOR"], "PROHIBITED", "Approver must be independent of the corrector."),
    ("IND-013", "Complaint", "closure-approve", ["INVESTIGATOR"], "PROHIBITED", "Closure approver must be independent of the investigator."),
    ("IND-014", "RegulatoryReport", "approve", ["AUTHOR"], "REQUIRES_APPROVAL", "Approver independent of the narrative author."),
    ("IND-015", "ValidationTestExecution", "review", ["EXECUTOR"], "PROHIBITED", "Reviewer must be independent of the test executor."),
    ("IND-016", "FieldAction", "approve", ["REQUESTER"], "PROHIBITED", "Approver must be independent of the requester."),
    ("IND-017", "SterilizationCycle", "release", ["OPERATOR"], "PROHIBITED", "Releaser must be independent of the cycle operator."),
    ("IND-018", "LineClearance", "verify", ["PERFORMER"], "PROHIBITED", "Verifier must be independent of the performer."),
    ("IND-019", "EquipmentQualification", "approve", ["TECHNICIAN"], "PROHIBITED", "Approver must be independent of the technician who executed it."),
    ("IND-020", "Any record", "reopen", ["APPROVER_WHO_CLOSED"], "REPORT_ONLY", "Report-only where the same authority is the only one available."),
    # 2026-09-08 (Decision 2): Product Master gained an author/release role split, mirroring IND-011 for
    # recipes. Enforced in app/modules/product_master/commands.py::release_product_version() against the
    # product version's own `Created` audit event -- the same bespoke pattern IND-011 uses, since no
    # generic ACTION_INDEPENDENCE evaluator exists yet (see SG-036/SPEC_GAP note above).
    ("IND-021", "ProductVersion", "release", ["AUTHOR"], "PROHIBITED", "Releaser must be independent of the product version author."),
]

# Document 106 platform floor, mapped onto the action strings the running code actually uses (see
# REMEDIATION_R1 FIX 1 completion report for the PascalCase-vs-code-vocabulary reconciliation). Only
# actions with a real call site today are seeded — VerifyStep/ReleaseRecipe/RejectBatch/Issue have none.
#
# `reason_required` (7th field) mirrors Document 106's own "Reason" column. It was added this pass
# (Document 21 session) after discovering the column existed on SignaturePolicy but was read/enforced by
# zero command handlers anywhere in this codebase (SG-086) -- including several of the pre-existing rows
# below that Document 106 itself marks "Reason: yes". Only the rows I own outright (added or corrected
# this pass) get the real value; every pre-existing row keeps `False` unchanged rather than risk an
# unreviewed behavior change to an already-tested module -- SG-086 recommends a dedicated remediation pass
# across the rest.
SIGNATURE_POLICY_FLOOR = [
    # (record_type, action, meaning, required_role_name, independent, signature_required, reason_required)
    ("batch_step", "complete_step", "Performed", None, False, True, False),
    # Document 106 rows 19/21 (SPEC-EBMR-002) -- SG-047 partial resolution, 2026-09-09,
    # project-owner-directed: the *new* `batch_execution` module's own complete/results endpoints
    # (distinct record_type "batch_step" + action "complete"/"results", not the legacy `app/modules/batch`
    # "complete_step" row above). "Qualified performer for the task" is dynamic per step (RecipeStep.
    # required_role_code, frozen onto BatchStep at issue) -- required_role_name=None here, same
    # "no fixed role" treatment as batch_step.complete_step; commands.py's `_enforce_step_role()` (SG-178)
    # checks the per-step role separately. Independence: none -- the recipe models independent
    # verification as its own dedicated step (e.g. the demo's ASSY-VER-01), not a second signer on the
    # same action. Reason: no, per Document 106's own Reason column for both rows.
    ("batch_step", "results", "Performed", None, False, True, False),
    ("batch_step", "complete", "Performed", None, False, True, False),
    # BAT-FR-020, step scope only -- SG-047 further partial resolution, 2026-09-09, project-owner-directed
    # (asked which of the six remaining demo gaps to build; step-level hold was one of three chosen).
    # No Document 106 row exists at step scope; reuses row 14/17's own shapes (the nearest analogous
    # batch-level actions) rather than inventing a new one. hold: "Performed", Authorized holder
    # (Production/QA) -> no fixed role (required_role_name=None, same "no role pair" precedent as
    # equipment_asset.hold), reason required per row 14's own Reason column. resume: "Approved", QA
    # authority that owns the hold reason -> no fixed role either (same precedent), reason not required.
    ("batch_step", "hold", "Performed", None, False, True, True),
    ("batch_step", "resume", "Approved", None, False, True, False),
    # BAT-FR-026, steps-completeness sub-clause only -- SG-048 #026 partial resolution, 2026-09-09,
    # project-owner-directed (the other of the three gaps chosen). Document 106 row 16: "Performed",
    # "Qualified performer for the task" (no fixed role -- dynamic per action, same treatment as every
    # other "qualified performer" row in this codebase), independence "None required unless the step is
    # flagged critical" -- not applicable at batch scope (no single step's is_critical flag to check),
    # so independent=False; reason not required per row 16's own Reason column.
    ("batch", "production_complete", "Performed", None, False, True, False),
    ("batch", "review", "Reviewed", "QA Reviewer", True, True, False),
    ("batch", "release", "Released", "QA Releaser", True, True, False),
    ("material_lot", "disposition", "Approved", "QC Reviewer", True, True, False),
    ("supplier_qualification", "approve", "Approved", "QA Releaser", True, True, False),
    ("qc_test_specification", "release", "Released", "QA Releaser", True, True, False),
    ("qc_test_order", "review", "Reviewed", "QA Reviewer", True, True, False),
    ("qc_result", "correct", "Approved", "QC Reviewer", True, True, False),
    ("lims_sample", "cancel", "Approved", "QA Releaser", True, True, False),
    ("oos_record", "extended_investigation", "Approved", "QA Reviewer", True, True, False),
    ("oos_record", "disposition", "Released", "QA Releaser", True, True, False),
    ("oos_record", "close", "Approved", "QA Releaser", True, True, False),
    ("oot_record", "close", "Approved", "QA Releaser", True, True, False),
    # Document 106 rows 44/45 (SPEC-MAT-002A) -- distinct from the pre-existing "material_lot"/
    # "disposition" row above, which is a Document 18-era action this pass does not touch (see the
    # SPEC_GAP recorded for that mismatch). retest has no Document 106 row -- unsigned, RBAC-gated only.
    ("material_lot", "release", "Released", "QA Releaser", True, True, False),
    ("material_lot", "reject", "Rejected", "QA Releaser", True, True, False),
    # Document 106 row 46 (SPEC-MAT-002B) -- reason_required=True per Document 106's own Reason column,
    # fixed this pass (SG-086) since this is code I wrote and own outright.
    ("inventory_reservation", "release", "Released", "QA Releaser", True, True, True),
    # Document 106 rows 47-54 (SPEC-MAT-002C) -- row 47 (order creation) is intentionally absent: it has
    # no policy row because create_dispensing_order is unsigned/RBAC-gated (SG-087), not because the
    # signature is optional -- resolve_signature_requirement's fail-closed behavior would otherwise apply
    # to an action this pass deliberately doesn't call it for.
    ("dispensing_order", "select_source", "Performed", "Operator", False, True, False),
    ("dispensing_order", "start", "Performed", "Operator", False, True, False),
    ("dispensing_order", "readings", "Performed", "Operator", False, True, False),
    ("dispensing_order", "manual_reading", "Performed", "Operator", False, True, False),
    ("dispensing_order", "verify", "Verified", "QC Reviewer", True, True, False),
    ("dispensing_order", "complete", "Performed", "Operator", False, True, False),
    ("dispensing_order", "cancel", "Approved", "QA Releaser", True, True, True),
    # Document 106 rows 55/56 (SPEC-MAT-002D, Document 22) -- reason_required wired correctly from row
    # one per Document 106's own Reason column, same discipline as the dispensing_order.cancel row above.
    # "Module approver role (QA Manager / Head of Quality per record class)" maps to this codebase's
    # "QA Releaser" -- same mapping precedent as supplier_qualification.approve (row 192 above).
    ("inventory_adjustment_request", "approve", "Approved", "QA Releaser", True, True, True),
    ("destruction_record", "execute", "Performed", None, False, True, False),
    # Document 106 row 108 (SPEC-EQP-001) — signer class is "Authorized holder (Production / QA)", a role
    # pair rather than one dedicated role, so `required_role_name=None` (same treatment as
    # destruction_record.execute above); reason_required=True per Document 106's own Reason column.
    ("equipment_asset", "hold", "Performed", None, False, True, True),
    # Document 106 rows 109-111 (SPEC-EQP-002) — rows 109/111's Reason column says "required unless
    # flagged critical", a per-record conditional this flat boolean can't express; reason_required=False
    # here and cleaning_commands.py enforces it conditionally on the record's own `critical` flag instead.
    ("cleaning_execution", "complete", "Performed", None, False, True, False),
    ("cleaning_execution", "verify", "Verified", None, True, True, False),
    ("line_clearance", "complete", "Performed", None, False, True, False),
    # Document 106 rows 114-115 (SPEC-EQP-004).
    ("em_sample_or_reading", "record_result", "Performed", None, False, True, False),
    ("em_sample_or_reading", "review", "Reviewed", None, True, True, False),
    # Document 106 rows 116-118 (SPEC-EQP-005).
    ("sterile_filter_use", "complete", "Performed", None, False, True, False),
    ("process_cycle", "review", "Reviewed", None, True, True, False),
    ("process_cycle", "start", "Performed", None, False, True, False),
    # Document 106 rows 112-113 (SPEC-EQP-003) -- row 112's Reason column says "required unless flagged
    # critical", same per-record conditional restraint as cleaning_execution.complete (rows 109/111) above;
    # reason_required=False here, aseptic_commands.py enforces it conditionally on the command's own
    # `critical` flag instead.
    ("aseptic_operation", "complete", "Performed", None, False, True, False),
    ("aseptic_operation", "start", "Performed", None, False, True, False),
    # Document 43 (SPEC-EDGE-001). "enroll" has no Document 106 row -- SG-118 interim baseline (Admin
    # signs, independent=False since the same actor who requests enrollment attests it themselves, same
    # "no dedicated independent-signer role pair exists" precedent as equipment_asset.hold above;
    # reason_required=True). "certificate_rotation" is Document 106 row 119 (QA Releaser, independent of
    # the enrolling actor, reason required) -- the one row this module resolves against a real baseline
    # rather than an interim one. "observation_batch"/"health_report"/"security_event" are SG-119: pure
    # gateway-to-server machine calls with no human performer at all -- Document 106 P7 ("service,
    # integration and device identities can never satisfy a signature requirement") makes a human
    # signature structurally impossible here, so `signature_required=False` is recorded as the deliberate
    # resolution rather than left as an unresolved `policy_lookup` that would fail every normal-operation
    # call closed under P8. `meaning` is unused whenever signature_required=False (no challenge/signature
    # is ever created to display it) -- kept as "Performed" only for the column's NOT NULL constraint,
    # same non-null placeholder discipline as every other row's `meaning` value.
    ("edge_gateway", "enroll", "Approved", "Admin", False, True, True),
    ("edge_gateway", "certificate_rotation", "Released", "QA Releaser", True, True, True),
    ("edge_gateway", "observation_batch", "Performed", None, False, False, False),
    ("edge_gateway", "health_report", "Performed", None, False, False, False),
    ("edge_gateway", "security_event", "Performed", None, False, False, False),
    # WP-07 (Documents 48/52/53) -- SG-122: Document 106 has zero rows for any SPEC-ERP-00x action.
    # Explicit signature_required=False resolutions, same "record the deliberate resolution" discipline
    # as the edge_gateway machine-call rows above, rather than an unresolved policy_lookup that would
    # fail every call closed under P8. `meaning`/`required_role_name` are unused placeholders whenever
    # signature_required=False (no challenge/signature is ever created), same convention as those rows.
    ("erp_instance", "register", "Performed", None, False, False, False),
    ("erp_external_mapping", "approve", "Approved", None, False, False, False),
    ("erp_mapping_conflict", "resolve", "Approved", None, False, False, False),
    # Document 47 (SPEC-EDGE-005) -- Document 106 has zero rows for any SPEC-EDGE-005 action.
    # SG-127: signal_mapping.release is the one genuinely human-signed action the spec names two roles
    # for ("Integration Engineer + QA/Validation") -- release itself is resolved to QA Releaser,
    # independent of the drafting actor (checked in code against SignalMapping.drafted_by_user_id, same
    # SoD shape as Document 43 row 119's certificate-rotation independence check).
    ("signal_mapping", "release", "Released", "QA Releaser", True, True, True),
    # SG-128: machine_command_profile.submit has no Document 106 row either. Interim floor: Equipment
    # Administrator (closest existing role to machine/equipment command governance), independent=False --
    # no dedicated second approver role exists yet for machine commands, same "no role pair" precedent as
    # equipment_asset.hold. A command profile's own required_role_name can raise this further at runtime
    # (checked in code), never lower it -- same floor-vs-recipe precedent as batch_step.complete_step.
    ("machine_command_profile", "submit", "Approved", "Equipment Administrator", False, True, True),
    # SG-129: the machine-to-machine ingestion/finalization ops (evidence:ingest, cycle-evidence-
    # manifests, machine-commands/{id}/finalize) -- Document 106 P7 makes a human signature structurally
    # impossible (no human performer at all), so signature_required=False is the recorded resolution,
    # same shape as edge_gateway's 3 machine-call rows above. These rows are registry/audit completeness
    # only -- like those edge_gateway rows, the command handlers never call
    # resolve_signature_requirement() for these actions at all (they are unconditionally unsigned).
    ("machine_source", "evidence_ingest", "Performed", None, False, False, False),
    ("machine_source", "cycle_evidence_manifest", "Performed", None, False, False, False),
    ("machine_command_request", "finalize", "Performed", None, False, False, False),
    # SG-131: machine_replay_job.replay -- Integration Administrator (same actor class as ERP-ARC-027),
    # independent=False (no dedicated second role exists), reason_required=True per MUT-FR-026's
    # "privileged admin/repair actions require ... stronger authorization".
    ("machine_replay_job", "replay", "Approved", "Integration Administrator", False, True, True),
    # Document 17 (SPEC-EBMR-008) — Document 106 row 40: `verify` requires a "Qualified independent
    # verifier", independent of the performer (SIG-FR-018, checked in code against
    # evaluated_by_user_id), no dedicated role named -- same "no role pair exists" treatment as
    # equipment_asset.hold. Reason not required per row 40's own Reason column. One policy row per
    # record_type since the shared verify endpoint dispatches to either table by id (see
    # app/modules/yield_reconciliation/commands.py::verify_record).
    ("manufacturing_calculation", "verify", "Verified", None, True, True, False),
    ("reconciliation_record", "verify", "Verified", None, True, True, False),
    # WP-08 (Document 54, SPEC-DDCP-001) -- SG-148: Document 106 has zero rows for any SPEC-DDCP-00x
    # action. Explicit signature_required=False resolutions, same "record the deliberate resolution"
    # discipline as the erp_instance/erp_external_mapping rows above -- `meaning`/`required_role_name`
    # are unused placeholders whenever signature_required=False.
    ("ddcp_profile_version", "release", "Released", None, False, False, False),
    ("constituent_handoff", "decide", "Approved", None, False, False, False),
    ("fill_operation", "start", "Performed", None, False, False, False),
    ("fill_operation", "complete", "Performed", None, False, False, False),
    # WP-09 (Document 59, SPEC-PM-002) -- Document 106 rows 123/125/126/127/128 name "Regulatory Affairs
    # authorized submitter"; role_name is the new "Postmarket Regulatory Affairs" role (Document 58's own
    # RBAC work), reason_required=True per each row's own Reason column ("yes"). Rows 124
    # (regulatory_report/approve, "per record class") and the decideReportability action (no Document 106
    # row exists at all) are deliberately NOT seeded here -- SG-157, both correctly fail closed with
    # SIGNATURE_POLICY_UNRESOLVED.
    ("reportability_track", "create", "Approved", "Postmarket Regulatory Affairs", False, True, True),
    ("regulatory_report", "create", "Approved", "Postmarket Regulatory Affairs", False, True, True),
    ("regulatory_report", "followup", "Approved", "Postmarket Regulatory Affairs", False, True, True),
    ("regulatory_report", "generate_payload", "Approved", "Postmarket Regulatory Affairs", False, True, True),
    ("regulatory_report", "submit", "Approved", "Postmarket Regulatory Affairs", False, True, True),
    # WP-09 (Document 60, SPEC-PM-002) -- Document 106 row 132 ("Qualified performer for the task", "None
    # required unless flagged critical", reason=no) -- same resolved shape as cleaning_execution.complete/
    # line_clearance.complete above. Rows 129/130 (correction_removal create/decide) require TWO
    # signatures ("Authorized corrector + independent approver") which no mechanism in this codebase
    # implements, and row 131 (deadline override) names "Elevated authority defined by the record class"
    # with no dispatch table -- all three deliberately left unresolved (SG-160).
    ("constituent_information_share", "record_sent", "Performed", None, False, True, False),
    # WP-10 (Document 61, SPEC-SEC-001) -- Document 106 has zero usable rows for this module's two
    # signature-shaped endpoints. `POST /security/v1/risks/{id}/accept` has no Document 106 row at all
    # (same shape as SG-157's row 124). `POST /security/v1/exceptions` (row 133) names meaning `Approved`/
    # "Elevated authority defined by the record class" but that phrase resolves to no actual role and no
    # dispatch table exists, the identical shape to SG-160's row 131 (regulatory_obligation.override_
    # deadline). Both are deliberately NOT seeded here -- SG-161, both correctly fail closed with
    # SIGNATURE_POLICY_UNRESOLVED (app/modules/security/commands.py calls `_resolve_signature()`
    # unconditionally for both, same discipline as every other module's fail-closed rows above).
    # WP-10 (Document 63, SPEC-SEC-003) -- Document 106 rows 134-136 resolve for real this time. Row 134
    # (admin-commands/{code}:execute, "Performed"/"Qualified performer for the task", no dedicated role,
    # independence/reason not required) needs no role. Rows 135/136 use the "approve"/"close" family
    # defaults this codebase has already mapped to QA Releaser elsewhere (see
    # privileged_access_models.py's module docstring) -- reused verbatim rather than inventing a new
    # role; independence ("MUST be independent of the author"/"...of the investigator/owner") is enforced
    # in code (requester != approver, opener != closer) since these are genuinely separate calls, unlike
    # SG-160's same-transaction cases.
    ("admin_command", "execute", "Performed", None, False, True, False),
    ("privileged_access_request", "approve", "Approved", "QA Releaser", True, True, True),
    ("privileged_session", "close", "Approved", "QA Releaser", True, True, True),
    # WP-10 (Document 65, SPEC-SEC-005) -- Document 106 rows 137-139: certificate issue/rotate/revoke
    # each require a `Released` signature by an independent QA Releaser ("QA Approver / Batch Release",
    # "MUST be independent of every production performer", Reason: yes). Same established non-QMS mapping
    # as batch.release / edge_gateway.certificate_rotation. `secret` rotate has no Document 106 row.
    ("certificate", "issue", "Released", "QA Releaser", True, True, True),
    ("certificate", "rotate", "Released", "QA Releaser", True, True, True),
    ("certificate", "revoke", "Released", "QA Releaser", True, True, True),
    # WP-10 (Document 67, SPEC-SEC-007) -- Document 106 row 140: security-incident close requires an
    # `Approved` signature by an independent QA Releaser ("QA Approver for the record class", "MUST be
    # independent of the investigator/owner", Reason: yes) -- identical shape to Document 63's
    # privileged_session.close (row 136). Independence (closer != incident owner) is enforced in code.
    ("security_incident", "close", "Approved", "QA Releaser", True, True, True),
    # WP-11 (Document 72, SPEC-DATA-004) -- Document 106 row 142: evidence legal hold is `Performed` by
    # an "Authorized holder (Production / QA)" (a role pair -> required_role_id=None, RBAC
    # `evidence.legal_hold` defines the holder), independence None, Reason: yes. Exact precedent =
    # Document 106 row 108 (equipment_asset/hold).
    ("evidence_object", "legal_hold", "Performed", None, False, True, True),
    # product_version/release -- SG-035 PARTIALLY RESOLVED 2026-09-07 (self-signed by Admin), then
    # 2026-09-08 project-owner-directed: Product Master gained the same author/release role split Recipe
    # Master has (Decision 2, option C) -- `product.author` now sits with Process Engineer + Admin,
    # `product.release` with QA Releaser + Admin -- so this row moves to an independent QA Releaser signer
    # to match. `requires_independent_signer=True` is enforced in release_product_version() against the
    # product version's own `Created` audit event (the author) -- the same bespoke pattern as
    # release_recipe_version() / IND-011 / the new IND-021, since resolve_signature_requirement() still
    # does not read these two columns.
    ("product_version", "release", "Released", "QA Releaser", True, True, False),
    # product_version/suspend -- SG-035 partial, 2026-09-10, project-owner-directed ("follow the
    # ebmr-edhr docs"): Document 106 section 9 row 9 (`POST /products/v1/{id}/suspend`) states meaning
    # `Performed`, signer class "Authorized holder (Production / QA)" -- a role pair, so
    # `required_role_name=None` (RBAC `product.suspend` gates it; same treatment as Document 106 row 108
    # equipment_asset/hold) -- Independence "None", Reason "yes" (already satisfied by the required
    # `SuspendProductVersionCommand.reason` field). No bespoke enforcement needed: no role check, no
    # independence check. `product_version/reinstate` has no Document 106 row and stays unresolved
    # (SG-035, deferred 2026-09-10) -- deliberately not extended here.
    ("product_version", "suspend", "Performed", None, False, True, True),
    # recipe_version/release -- SG-035 further-partial 2026-09-08, project-owner-directed (asked directly:
    # QA-Releaser-independent-of-author vs. self-signed vs. RBAC-only vs. leave-unresolved -- chose the
    # first). Recipe Master has an author/release role split (Process Engineer authors, `recipe.release`
    # is QA Releaser + Admin only -- ROLE_PERMISSIONS above), so an independent QA Releaser signer is the
    # consistent choice. `requires_independent_signer=True` is enforced in release_recipe_version()
    # against the recipe version's own `Created` audit event (the author), matching the bespoke IND-001 /
    # IND-011 / CON-FR-014 independence pattern used elsewhere -- resolve_signature_requirement() itself
    # still does not read these two columns.
    ("recipe_version", "release", "Released", "QA Releaser", True, True, False),
    # deviation_record/disposition+close -- Document 106 rows 71/73 (SPEC-QMS-001), resolved 2026-09-09
    # project-owner-directed ("as per the ebmr-edhr docs"): disposition is `Released` by "QA Approver /
    # Batch Release" independent of every production performer on the record; close is `Approved` by "QA
    # Approver for the record class" independent of the investigator/owner (Document 107 IND-005:
    # (Investigator, Owner) -> Prohibited from closing). Both signer classes resolve to QA Releaser --
    # the only role RBAC already grants qms_deviation.disposition/close to, and the same mapping every
    # other Released/Approved-class action in this codebase uses (oos_record.disposition/close above,
    # certificate.issue/rotate/revoke, security_incident.close). `requires_independent_signer=True` is
    # enforced in qms/commands.py::_resolve_signature() against the record's own investigator_subject_id/
    # owner_subject_id, same bespoke pattern as close_security_incident() (Document 106 row 140) --
    # resolve_signature_requirement() itself still does not read these two columns. reason_required=True
    # per Document 106's own Reason column for both rows -- already satisfied by the always-mandatory
    # disposition_rationale/conclusion fields, no separate `reason` param needed.
    ("deviation_record", "disposition", "Released", "QA Releaser", True, True, True),
    ("deviation_record", "close", "Approved", "QA Releaser", True, True, True),
    # qa_review_package/complete -- Document 106 row 29 (SPEC-EBMR-005), resolved 2026-09-09
    # project-owner-directed (hit live on the QA Review page's "Complete review" action; same "as per the
    # ebmr-edhr docs" instruction as the deviation resolution above): meaning `Reviewed`, signer "QA
    # Reviewer" -- the only role RBAC already grants `qa_review.execute` to, no mapping ambiguity. The
    # row's independence requirement ("independent of the performer") is recorded here as data
    # (`independent=True`) matching Document 106 verbatim, but `qa_review/commands.py::complete_review_
    # package()` does not enforce it -- no concrete Document 107 IND rule names it and `QaReviewPackage`
    # carries no performer/reviewer identity column to check against (only `completed_at`); see
    # docs/generated/18_SPEC_GAPS.md SG-138 for the recorded gap.
    ("qa_review_package", "complete", "Reviewed", "QA Reviewer", True, True, False),
    # release_scope/release+hold+reject -- Document 106 rows 34/32/33 (SPEC-EBMR-006), resolved the same
    # pass: all three literally carry meaning `Released` in Document 106 (not e.g. `Rejected` for reject --
    # taken verbatim rather than "corrected", per CLAUDE.md's no-guessing rule), signer "QA Approver /
    # Batch Release" -> QA Releaser (the only role RBAC grants `release.release`/`release.reject` to;
    # `release.hold` is also RBAC-granted to QA Reviewer, so a QA Reviewer can still reach the hold
    # endpoint but will be refused by this signature policy's required-role check -- Document 106 does not
    # give hold a narrower signer class than release/reject). `requires_independent_signer=True` is
    # enforced in `release/commands.py::_resolve_signature()` against the QA Reviewer who completed this
    # batch's `qa_review_package` (Document 107 IND-002/IND-003's "the QA Reviewer" half only -- the
    # "every PERFORMER on the batch" half has no data source in this codebase and is not implemented, same
    # SG-056/SG-138 gap noted in the command's own docstring). `reason_required=True` per Document 106's
    # own Reason column, enforced against `ReleaseDecisionCommand.reason` (already an existing optional
    # field on the command, not a new one).
    ("release_scope", "release", "Released", "QA Releaser", True, True, True),
    ("release_scope", "hold", "Released", "QA Releaser", True, True, True),
    ("release_scope", "reject", "Released", "QA Releaser", True, True, True),
    # ---------------------------------------------------------------------------------------------------
    # SG-138 policy-data half -- WP-05 QMS, from Document 106 section 9 rows 80-107, applied 2026-09-10
    # (project-owner construction-baseline decision: "follow the ebmr-edhr docs"). Abstract signer classes
    # map to concrete platform roles by the mapping already in force for ~40 rows above:
    #   "QA Approver / Batch Release" and "QA Approver for the record class"  -> "QA Releaser"
    #   "QA Reviewer"                                                         -> "QA Reviewer"
    #   "Qualified independent verifier" ("MUST NOT be the performer")        -> None (perf!=verifier in code)
    #   "Production Supervisor or qualified issuer"                           -> None (RBAC gates it)
    #   "Regulatory Affairs authorized submitter"                            -> "Postmarket Regulatory Affairs" (+RBAC grant)
    #   "Module approver role (QA Manager / Head of Quality per record class)" -> "QA Releaser" (precedent: supplier_qualification/approve row 43)
    # requires_independent_signer=True rows are enforced in each module's own `_resolve_signature()` via
    # the shared `qms/signature_support.py::enforce_signer_policy()` helper against the record's own
    # investigator/owner/author identity column(s), since resolve_signature_requirement() does not read
    # required_role_id/requires_independent_signer -- same bespoke pattern as close_deviation().
    # Stage 2 (rows 80-88): CAPA close, NCR disposition/verify/close, Change approve/verify/close.
    ("capa_record", "close", "Approved", "QA Releaser", True, True, True),  # Doc 106 section 9 row 80
    # NCR -- verify is "Qualified independent verifier" ("MUST NOT be the performer") -> required_role
    # None, independence enforced in code against `owner_subject_id` (NonconformanceRecord's only stored
    # identity; no separate disposition-performer column -- same honest limitation as qa_review_package/complete).
    ("nonconformance_record", "disposition", "Released", "QA Releaser", True, True, True),   # section 9 row 84
    ("nonconformance_record", "verify", "Verified", None, True, True, False),                # section 9 row 85
    ("nonconformance_record", "close", "Approved", "QA Releaser", True, True, True),         # section 9 row 83
    # Change control -- approve is "Module approver role (QA Manager / Head of Quality)" -> QA Releaser
    # (precedent: supplier_qualification/approve row 43); verify is "Qualified independent verifier".
    ("change_control", "approve", "Approved", "QA Releaser", True, True, True),              # section 9 row 86
    ("change_control", "verify", "Verified", None, True, True, False),                       # section 9 row 88
    ("change_control", "close", "Approved", "QA Releaser", True, True, True),                # section 9 row 87
    # Stage 3 (rows 95-105): SCAR, internal audit, audit finding, complaint, field action.
    # "Regulatory Affairs authorized submitter" (rows 102/105) -> the "Postmarket Regulatory Affairs"
    # role, which is also granted complaint.reportability / field_action.reportability below (project-
    # owner-directed 2026-09-10: "map to the Doc 106 class and grant the missing RBAC permission").
    # complaint_record / field_action carry no owner identity column, so their close/approve independence
    # checks have no data source -- role is enforced, the gap is documented (qa_review_package precedent).
    ("scar_record", "review", "Reviewed", "QA Reviewer", True, True, False),                # section 9 row 96
    ("scar_record", "close", "Approved", "QA Releaser", True, True, True),                   # section 9 row 95
    ("internal_audit", "start", "Performed", None, False, True, False),                     # section 9 row 99
    ("internal_audit", "close", "Approved", "QA Releaser", True, True, True),               # section 9 row 98
    ("audit_finding", "verify", "Verified", None, True, True, False),                       # section 9 row 100
    ("complaint_record", "reportability", "Approved", "Postmarket Regulatory Affairs", False, True, True),  # section 9 row 102
    ("complaint_record", "close", "Approved", "QA Releaser", True, True, True),             # section 9 row 101
    ("field_action", "reportability", "Approved", "Postmarket Regulatory Affairs", False, True, True),     # section 9 row 105
    ("field_action", "approve", "Approved", "QA Releaser", True, True, True),               # section 9 row 103
    ("field_action", "close", "Approved", "QA Releaser", True, True, True),                 # section 9 row 104
]

# Document 20 (SPEC-MAT-002B) INV-FR-001/002: warehouse_location has no CRUD operation anywhere in
# Document 20's own 8-op API list (SG-081) -- seed-only master data, same treatment as Organization/Site.
# (warehouse_code, location_code, zone_type)
WAREHOUSE_LOCATION_FLOOR = [
    ("WH1", "QUARANTINE-01", "quarantine"),
    ("WH1", "RELEASED-01", "released"),
    ("WH1", "REJECTED-01", "rejected"),
]

# Document 39 (SPEC-EQP-002) — equipment_areas/cleaning_procedure_versions have no CRUD operation
# anywhere in Document 39's own 7-op API list -- seed-only master data, same treatment as
# WAREHOUSE_LOCATION_FLOOR. (area_code, area_type, classification, criticality)
EQUIPMENT_AREA_FLOOR = [
    ("AREA-GRADE-A", "cleanroom", "ISO_5", "critical"),
    ("AREA-GRADE-C", "cleanroom", "ISO_7", "non_critical"),
    ("AREA-WAREHOUSE", "warehouse", None, "non_critical"),
]

# (procedure_number, cleaning_type, dirty_hold_limit_minutes, clean_hold_limit_minutes)
CLEANING_PROCEDURE_FLOOR = [
    ("CLN-PROC-001", "routine", 240, 4320),
]

DEMO_USERS = [
    ("admin", "admin@example.com", "Admin User", "Admin"),
    ("operator1", "operator1@example.com", "Olivia Operator", "Operator"),
    ("qa.reviewer", "qa.reviewer@example.com", "Rita Reviewer", "QA Reviewer"),
    ("qa.releaser", "qa.releaser@example.com", "Ray Releaser", "QA Releaser"),
    ("qc.reviewer", "qc.reviewer@example.com", "Quinn QC", "QC Reviewer"),
    ("equipment.admin", "equipment.admin@example.com", "Eddie EquipAdmin", "Equipment Administrator"),
    ("engineering.manager", "engineering.manager@example.com", "Emma EngManager", "Engineering Manager"),
    ("calibration.tech", "calibration.tech@example.com", "Cara CalTech", "Calibration Technician"),
    ("maintenance.tech", "maintenance.tech@example.com", "Milo MaintTech", "Maintenance Technician"),
    ("sanitation.operator", "sanitation.operator@example.com", "Sam SanitationOp", "Sanitation Operator"),
    ("em.technician", "em.technician@example.com", "Emmy EmTech", "EM Technician"),
    ("microbiology.analyst", "microbiology.analyst@example.com", "Micah MicroAnalyst", "Microbiology Analyst"),
    ("sterilization.operator", "sterilization.operator@example.com", "Sal SterilOp", "Sterilization Operator"),
    ("aseptic.operator", "aseptic.operator@example.com", "Aria AsepticOp", "Aseptic Operator"),
    ("aseptic.supervisor", "aseptic.supervisor@example.com", "Alex AsepticSup", "Aseptic Supervisor"),
    ("process.engineer", "process.engineer@example.com", "Pat ProcessEngineer", "Process Engineer"),
    ("integration.admin", "integration.admin@example.com", "Ivan IntegrationAdmin", "Integration Administrator"),
]

# WP-07 (Document 48) -- demo ERPNext instance every adapter test/E2E walkthrough registers against.
# `base_url`/`auth_secret_ref` point nowhere real (SG-125: no credentialed vendor sandbox is reachable
# from this environment) -- tests that exercise `dispatch_erp_command` substitute an `httpx.MockTransport`
# for the real network, never calling this URL.
DEMO_ERP_INSTANCE = {
    "instance_name": "demo-erpnext", "vendor": "ERPNEXT", "environment": "SANDBOX",
    "base_url": "https://erpnext.demo.invalid", "auth_method": "API_KEY", "auth_secret_ref": "demo-key:demo-secret",
    "contract_version": "v14-resource-api",
}

DEMO_PASSWORD = "ChangeMe123!"


async def seed() -> None:
    async with SessionLocal() as session:
        async with session.begin():
            org = Organization(name="Demo Manufacturing Co.")
            session.add(org)
            await session.flush()

            site = Site(organization_id=org.id, code="SITE1", name="Demo Site 1")
            session.add(site)
            await session.flush()

            for warehouse_code, location_code, zone_type in WAREHOUSE_LOCATION_FLOOR:
                existing_location = (
                    await session.execute(
                        select(WarehouseLocation).where(
                            WarehouseLocation.site_id == site.id,
                            WarehouseLocation.warehouse_code == warehouse_code,
                            WarehouseLocation.location_code == location_code,
                        )
                    )
                ).scalar_one_or_none()
                if existing_location is None:
                    session.add(
                        WarehouseLocation(
                            site_id=site.id,
                            warehouse_code=warehouse_code,
                            location_code=location_code,
                            zone_type=zone_type,
                            status="active",
                        )
                    )

            areas = {}
            for area_code, area_type, classification, criticality in EQUIPMENT_AREA_FLOOR:
                area = EquipmentArea(
                    site_id=site.id, area_code=area_code, area_type=area_type,
                    classification=classification, criticality=criticality, status="active",
                )
                session.add(area)
                areas[area_code] = area
            await session.flush()

            for procedure_number, cleaning_type, dirty_limit, clean_limit in CLEANING_PROCEDURE_FLOOR:
                session.add(
                    CleaningProcedureVersion(
                        site_id=site.id, procedure_number=procedure_number, version_no=1,
                        cleaning_type=cleaning_type, dirty_hold_limit_minutes=dirty_limit,
                        clean_hold_limit_minutes=clean_limit, state="RELEASED",
                    )
                )

            # Document 41 (SPEC-EQP-004) -- em_locations has no CRUD operation anywhere in Document 41's
            # own 8-op API list -- seed-only, same treatment as equipment_areas.
            em_program = EmProgramVersion(
                site_id=site.id, program_number="EM-PROG-001", version_no=1,
                monitoring_types={"types": ["viable_air", "surface_contact"]},
            )
            session.add(em_program)
            for location_code, criticality in (("EM-LOC-GRADE-A-01", "critical"), ("EM-LOC-GRADE-C-01", "non_critical")):
                session.add(
                    EmLocation(
                        site_id=site.id, area_id=areas["AREA-GRADE-A" if "GRADE-A" in location_code else "AREA-GRADE-C"].id,
                        location_code=location_code, criticality=criticality, status="active",
                    )
                )

            # Document 42 (SPEC-EQP-005) -- process_cycle_profile_versions has no CRUD operation anywhere
            # in Document 42's own 9-op API list -- seed-only, same treatment as cleaning_procedure_versions.
            session.add(
                ProcessCycleProfileVersion(
                    site_id=site.id, profile_number="STR-PROC-001", version_no=1, process_type="steam_autoclave",
                    sterile_status_validity_hours=72, state="RELEASED",
                )
            )

            # Document 40 (SPEC-EQP-003) -- aseptic_profile_versions has no CRUD operation anywhere in
            # Document 40's own 7-op API list -- seed-only, same treatment as process_cycle_profile_versions.
            aseptic_profile = AsepticProfileVersion(
                site_id=site.id, profile_number="ASP-PROC-001", version_no=1,
                required_area_classification="ISO_5", state="RELEASED",
            )
            session.add(aseptic_profile)

            # Document 43 (SPEC-EDGE-001) -- no public "issue bootstrap token" API exists in spec §8
            # (known limitation, not a SPEC_GAP -- see app/modules/edge/models.py's EdgeEnrollmentToken
            # docstring), so the one demo token the E2E walkthrough/tests enroll a gateway with is
            # seed-issued here, same "seed-only master data" treatment as ProcessCycleProfileVersion above.
            session.add(
                EdgeEnrollmentToken(
                    site_id=site.id, token_hash=sha256_hex(DEMO_EDGE_BOOTSTRAP_TOKEN),
                    status="unused", expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                )
            )

            # Document 48 (SPEC-ERP-001) -- registerERPInstance() has no seed-time uniqueness concern
            # (instance_name is globally unique, not per-org), same "seed-only demo fixture" treatment as
            # DEMO_EDGE_BOOTSTRAP_TOKEN above.
            session.add(
                ErpInstance(
                    site_id=site.id, instance_name=DEMO_ERP_INSTANCE["instance_name"], vendor=DEMO_ERP_INSTANCE["vendor"],
                    environment=DEMO_ERP_INSTANCE["environment"], base_url=DEMO_ERP_INSTANCE["base_url"],
                    auth_method=DEMO_ERP_INSTANCE["auth_method"], auth_secret_ref=DEMO_ERP_INSTANCE["auth_secret_ref"],
                    contract_version=DEMO_ERP_INSTANCE["contract_version"],
                    capabilities={"supported_operations": [
                        "SYNC_MATERIAL_ITEM", "SYNC_SUPPLIER", "SYNC_WAREHOUSE_LOCATION", "SYNC_UOM",
                        "POST_GOODS_RECEIPT", "POST_CONSUMPTION", "POST_RETURN", "POST_SCRAP_DESTRUCTION",
                        "POST_FINISHED_GOODS_RECEIPT", "POST_QUALITY_STATUS", "GET_PRODUCTION_ORDER_REFERENCE",
                        "FETCH_MASTER_DATA_CHANGES",
                    ]}, status="ACTIVE",
                )
            )

            # Document 17 (SPEC-EBMR-008) -- the *only* formula the spec gives literally (§3:
            # "yield_percent = actual_yield / theoretical_yield x 100"), seeded as a released Document 08
            # rule rather than embedded in Python (YLD-FR-001/003/007, module docstring in
            # app/modules/yield_reconciliation/commands.py). Precision/rounding cite Document 110 CC-4
            # ("Yield / reconciliation": 6dp intermediate, 2dp reported, half-up, at presentation) --
            # never an invented default. No equivalent floor rule exists for potency (YLD-FR-015): no
            # formula is given anywhere in the approved baseline, so evaluate_potency() always requires a
            # customer-authored released rule at the caller-supplied rule_id (see SPEC_GAP).
            session.add(
                RuleDefinition(
                    rule_id="yield_percent", rule_type="CALCULATION", semantic_version="1.0.0",
                    status="released", effective_from=datetime.now(timezone.utc) - timedelta(days=1),
                    expression_ast={
                        "op": "*",
                        "args": [{"op": "/", "args": [{"var": "actual_yield"}, {"var": "theoretical_yield"}]}, 100],
                    },
                    input_contract={"actual_yield": {"type": "decimal"}, "theoretical_yield": {"type": "decimal"}},
                    output_contract={"type": "decimal"},
                    # SG-146: calculation_class is the schema app/modules/rules/precision.py resolves --
                    # CC-4 fixes storage precision, rounding mode/stage and reported dp (2) by table, so
                    # this rule no longer needs to restate them itself (previously "class"/"intermediate_dp"/
                    # "reported_dp" were read directly by yield_reconciliation/commands.py, a second,
                    # divergent rounding pathway the SG-143 resolution note flagged and this closes).
                    unit_policy={"dimension": "percentage", "conversion": "none"},
                    precision_policy={"calculation_class": "CC-4"},
                    rounding_policy={"policy_version": "DOCUMENT-110-v1.0"},
                    engine_compatibility="v1",
                )
            )

            roles = {}
            for name in ROLE_NAMES:
                role = Role(name=name)
                session.add(role)
                roles[name] = role
            await session.flush()

            for username, email, full_name, role_name in DEMO_USERS:
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(DEMO_PASSWORD),
                    status="active",
                )
                session.add(user)
                await session.flush()
                session.add(UserSiteRole(user_id=user.id, site_id=site.id, role_id=roles[role_name].id))

            for record_type, action, meaning, role_name, independent, sig_required, reason_required in SIGNATURE_POLICY_FLOOR:
                existing_policy = (
                    await session.execute(
                        select(SignaturePolicy).where(
                            SignaturePolicy.record_type == record_type,
                            SignaturePolicy.action == action,
                        )
                    )
                ).scalar_one_or_none()
                required_role_id = roles[role_name].id if role_name else None
                if existing_policy is None:
                    session.add(
                        SignaturePolicy(
                            record_type=record_type,
                            action=action,
                            meaning=meaning,
                            required_role_id=required_role_id,
                            requires_independent_signer=independent,
                            signature_required=sig_required,
                            reason_required=reason_required,
                            policy_source="PLATFORM_FLOOR",
                        )
                    )
                else:
                    existing_policy.meaning = meaning
                    existing_policy.required_role_id = required_role_id
                    existing_policy.requires_independent_signer = independent
                    existing_policy.signature_required = sig_required
                    existing_policy.reason_required = reason_required
                    existing_policy.policy_source = "PLATFORM_FLOOR"

            permissions = {}
            for code, action, resource_type, description in PERMISSION_CATALOG:
                existing_permission = (
                    await session.execute(select(Permission).where(Permission.code == code))
                ).scalar_one_or_none()
                if existing_permission is None:
                    existing_permission = Permission(
                        code=code, action=action, resource_type=resource_type, description=description
                    )
                    session.add(existing_permission)
                    await session.flush()
                else:
                    existing_permission.action = action
                    existing_permission.resource_type = resource_type
                    existing_permission.description = description
                permissions[code] = existing_permission

            for role_name, codes in ROLE_PERMISSIONS.items():
                for code in codes:
                    existing_grant = (
                        await session.execute(
                            select(RolePermission).where(
                                RolePermission.role_id == roles[role_name].id,
                                RolePermission.permission_id == permissions[code].id,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing_grant is None:
                        session.add(
                            RolePermission(role_id=roles[role_name].id, permission_id=permissions[code].id)
                        )

            for code, role_a, role_b, severity, rationale in SOD_STANDING_ROLE_PAIRS:
                existing_rule = (
                    await session.execute(select(SodRule).where(SodRule.code == code))
                ).scalar_one_or_none()
                if existing_rule is None:
                    session.add(
                        SodRule(
                            code=code,
                            rule_type="STANDING_ROLE_PAIR",
                            role_a=role_a,
                            role_b=role_b,
                            severity=severity,
                            rationale=rationale,
                            source_reference="Document 107",
                            policy_source="PLATFORM_FLOOR",
                        )
                    )
                else:
                    existing_rule.role_a = role_a
                    existing_rule.role_b = role_b
                    existing_rule.severity = severity
                    existing_rule.rationale = rationale

            for code, record_class, action, independent_of, severity, rationale in SOD_ACTION_INDEPENDENCE:
                existing_rule = (
                    await session.execute(select(SodRule).where(SodRule.code == code))
                ).scalar_one_or_none()
                if existing_rule is None:
                    session.add(
                        SodRule(
                            code=code,
                            rule_type="ACTION_INDEPENDENCE",
                            record_class=record_class,
                            action=action,
                            independent_of=independent_of,
                            severity=severity,
                            rationale=rationale,
                            source_reference="Document 107",
                            policy_source="PLATFORM_FLOOR",
                        )
                    )
                else:
                    existing_rule.record_class = record_class
                    existing_rule.action = action
                    existing_rule.independent_of = independent_of
                    existing_rule.severity = severity
                    existing_rule.rationale = rationale

            # Document 69 (SPEC-DATA-001) DATA-FR-001: the authoritative-store registry, transcribed
            # from 05_DATABASE_OWNERSHIP_MATRIX.md. Idempotent upsert keyed by entity_type.
            for entry in DATA_OWNERSHIP_SEED:
                existing_owner = (
                    await session.execute(
                        select(DataOwnershipRegistry).where(
                            DataOwnershipRegistry.entity_type == entry["entity_type"]
                        )
                    )
                ).scalar_one_or_none()
                if existing_owner is None:
                    session.add(DataOwnershipRegistry(**entry))
                else:
                    for key, value in entry.items():
                        setattr(existing_owner, key, value)
                    existing_owner.state = "EFFECTIVE"

            # Document 76 (SPEC-DATA-008) DR-FR-001/002: Document 109's platform-default recovery-tier
            # table. Idempotent upsert keyed by component.
            for entry in DOCUMENT_109_TIER_SEED:
                existing_objective = (
                    await session.execute(
                        select(RecoveryObjectiveProfile).where(RecoveryObjectiveProfile.component == entry["component"])
                    )
                ).scalar_one_or_none()
                if existing_objective is None:
                    session.add(RecoveryObjectiveProfile(**entry))
                else:
                    for key, value in entry.items():
                        setattr(existing_objective, key, value)
                    existing_objective.state = "EFFECTIVE"

            # Document 78 (SPEC-DATA-010) SRE-FR-001/002/005: Document 109's platform-default SLO /
            # capacity baseline. Idempotent upsert keyed by operation_class / dimension.
            for entry in DOCUMENT_109_SLO_SEED:
                existing_slo = (
                    await session.execute(select(SloDefinition).where(SloDefinition.operation_class == entry["operation_class"]))
                ).scalar_one_or_none()
                if existing_slo is None:
                    session.add(SloDefinition(**entry))
                else:
                    for key, value in entry.items():
                        setattr(existing_slo, key, value)
                    existing_slo.state = "EFFECTIVE"
            for entry in DOCUMENT_109_CAPACITY_SEED:
                existing_cap = (
                    await session.execute(select(CapacityForecast).where(CapacityForecast.dimension == entry["dimension"]))
                ).scalar_one_or_none()
                if existing_cap is None:
                    session.add(CapacityForecast(**entry))
                else:
                    for key, value in entry.items():
                        setattr(existing_cap, key, value)
                    existing_cap.state = "EFFECTIVE"

        print(f"Seeded org={org.id} site={site.id} ({site.code})")
        print(f"Demo users (password '{DEMO_PASSWORD}' for all): {[u[0] for u in DEMO_USERS]}")
        print(f"site_id for API calls: {site.id}")


if __name__ == "__main__":
    asyncio.run(seed())
