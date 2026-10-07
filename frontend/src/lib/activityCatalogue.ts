// Client gap-analysis Phase 2 (2026-10, Role/Permission UX): a business-named "Activity" checklist that
// bundles the permission catalogue's existing module groups (the `<module>.<resource>.<action>` prefix
// already used to group the full matrix in admin/roles/[id]/page.tsx) into ~15 activities a non-technical
// admin recognizes, instead of making them understand all ~128 technical module names one at a time.
//
// Deliberately static/vendor-maintained, not a database table: this is a presentational grouping of data
// that already exists (iam.permissions.code), not a new regulated entity, so it carries no schema change,
// migration or new endpoint. Ticking an Activity only pre-fills the existing permission checkboxes in
// admin/roles/[id]/page.tsx -- the actual save still goes through the unchanged
// POST /roles/{id}/permissions (set_role_permissions) mutation path.
//
// Any module key not listed under a named Activity here is covered by a dynamically-computed "Other"
// bucket in the page itself (see `activityModuleKeys`'s caller), so a future PERMISSION_CATALOG addition
// can never become untickable through this checklist -- it just shows up under "Other" until someone
// files it under a named Activity in a later edit of this table.

export interface ActivityDefinition {
  key: string;
  label: string;
  moduleKeys: string[];
}

export const ACTIVITY_CATALOGUE: ActivityDefinition[] = [
  {
    key: "material_management",
    label: "Material Management",
    moduleKeys: [
      "material", "material_spec", "material_receipt", "material_lot", "material_container",
      "material_consumption", "material_return", "material_loss", "material_reconciliation",
      "destruction_record", "warehouse_location", "inventory_reservation", "inventory_transaction",
      "inventory_adjustment_request", "inventory_availability", "inventory_cycle_count",
      "dispensing_order", "lims_sample", "reconciliation",
    ],
  },
  {
    key: "suppliers",
    label: "Suppliers",
    moduleKeys: ["supplier", "supplier_qualification"],
  },
  {
    key: "equipment_facilities",
    label: "Equipment & Facilities",
    moduleKeys: [
      "equipment_asset", "equipment_area", "cleaning_execution", "line_clearance", "aseptic_operation",
      "aseptic_profile_version", "sterile_filter_use", "em_program", "em_sample", "em_excursion",
      "process_cycle", "process_cycle_profile_version",
    ],
  },
  {
    key: "qc_testing_lab",
    label: "QC Testing & Lab",
    moduleKeys: [
      "qc_test_specification", "qc_method", "qc_sample", "qc_test_order", "qc_result", "oos_record",
      "oot_record",
    ],
  },
  {
    key: "quality_events",
    label: "Quality Events",
    moduleKeys: [
      "qms_deviation", "capa", "ncr", "scar", "change", "effectiveness_check", "risk", "quality_metric",
      "correction_removal",
    ],
  },
  {
    key: "product_recipe_master",
    label: "Product & Recipe Master",
    moduleKeys: ["product", "recipe", "rules", "yield_calculation"],
  },
  {
    key: "batch_execution",
    label: "Batch Execution / eDHR",
    moduleKeys: [
      "batch", "batch_context", "batch_execution", "batch_step", "step_stuck_detection", "qa_review",
      "release", "genealogy", "device", "packaging",
    ],
  },
  {
    key: "ddcp",
    label: "DDCP (Device-Drug Combination)",
    moduleKeys: ["ddcp_profile", "ddcp_constituent", "ddcp_device", "ddcp_fill", "ddcp_release"],
  },
  {
    key: "documents_training",
    label: "Documents & Training",
    moduleKeys: ["document", "training", "validation"],
  },
  {
    key: "postmarket_vigilance",
    label: "Postmarket & Vigilance",
    moduleKeys: [
      "complaint", "field_action", "postmarket_dataset", "postmarket_source", "reportability_track",
      "regulatory_report", "regulatory_submission", "regulatory_obligation", "periodic_reporting_cycle",
      "safety_signal", "safety_case", "signal_mapping", "applicant_relationship",
      "constituent_information_share",
    ],
  },
  {
    key: "enterprise_integrations",
    label: "Enterprise Integrations",
    moduleKeys: [
      "erp_instance", "erp_mapping", "erp_sync", "edge_gateway", "machine_command", "machine_evidence",
      "machine_replay", "integration_command", "integration_event", "integration_reconciliation",
      "webhook_profile", "outbound_destination", "api_inventory", "network_flow",
    ],
  },
  {
    key: "security_access_governance",
    label: "Security & Access Governance",
    moduleKeys: [
      "privileged_access", "privileged_session", "security_incident", "security_exception",
      "security_threat", "security_threat_model", "security_control_matrix", "vulnerability",
      "crypto_health", "secret", "identity_provider", "service_identity", "deployment_security_profile",
      "application_session", "certificate", "release_security_evidence",
    ],
  },
  {
    key: "audit_vault",
    label: "Audit & Vault",
    moduleKeys: ["audit", "vault", "evidence", "data_dictionary", "data_ownership", "projection", "internal_audit"],
  },
  {
    key: "ai_governance",
    label: "AI Governance",
    moduleKeys: ["ai_governance"],
  },
  {
    key: "platform_operations_reporting",
    label: "Platform Operations & Reporting",
    moduleKeys: ["platform", "search", "report", "notifications", "dr"],
  },
];
