"use client";

import { useState } from "react";
import { api, ApiError, holdsAnyRole, newIdempotencyKey, type Me, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";
import { RepeatableRows, buildRepeatArray, type RepeatRow } from "@/components/shared/RepeatableFields";

const REPORT_TYPE_OPTIONS = [
 { value: "MDR_30", label: "MDR 30 day" },
 { value: "MDR_5", label: "MDR 5 day" },
  { value: "MALFUNCTION", label: "Malfunction" },
 { value: "DRUG_EXPEDITED_15", label: "Drug expedited 15 day" },
 { value: "BIOLOGIC_EXPEDITED_15", label: "Biologic expedited 15 day" },
 { value: "PART4_30", label: "Part 4 30 day" },
  { value: "FOLLOWUP", label: "Follow-up" },
];

const canWork = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Reviewer", "QA Releaser"]);

export default function PostmarketPage() {
  const { me } = useMe();

  return (
    <div>
      <PageHead
        title="Postmarket"
        subtitle="Safety cases, signal management, the regulatory reporting clock and Part 4 obligations."
      />

      <DashboardCards />

      {canWork(me) && <CreateSafetyCaseCard />}
      {canWork(me) && <ReportabilityCard />}

      {canWork(me) && (
        <>
          <FormConsole
          title="Safety case & signal operations"
            root="/postmarket/v1"
            ops={[
              {
                path: "safety-cases/{case_id}/classifications",
                label: "Classify a safety case",
                about: "Records the clinical / device / seriousness classification and expectedness.",
                fields: [
                  { name: "case_id", label: "Safety case ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "constituent_attribution", label: "Constituent attribution", type: "select", options: [
                    { value: "DRUG", label: "Drug" }, { value: "DEVICE", label: "Device" }, { value: "COMBINATION", label: "Combination" }] },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                  {
                    name: "classification", label: "Classification detail", type: "kv", required: true,
                    hint: 'What was assessed and its outcome, e.g. "seriousness" → "serious", "expectedness" → "unexpected". At least one entry is required.',
                  },
                ],
              },
              { path: "safety-cases/{case_id}/duplicate-candidates", label: "List probable duplicates", method: "GET",
                fields: [{ name: "case_id", label: "Safety case ID", required: true }] },
              {
                path: "safety-cases/{case_id}/resolve-product",
                label: "Resolve the marketed product",
                fields: [
                  { name: "case_id", label: "Safety case ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "marketed_product_id", label: "Marketed product ID", hint: "Optional." },
                  { name: "application_profile_id", label: "Application profile ID", hint: "Optional." },
                  { name: "product_resolution", label: "Product resolution", type: "kv", hint: "Optional - free-form resolution detail." },
                  { name: "mark_resolved", label: "Mark resolved", type: "bool", default: "false" },
                  { name: "reason", label: "Reason" },
                ],
              },
              {
                path: "safety-cases/{case_id}/followups",
                label: "Add a follow-up",
                fields: [
                  { name: "case_id", label: "Safety case ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "followup_receipt_at", label: "Follow-up received at", type: "datetime", required: true },
                  { name: "source_reference", label: "Source reference", type: "kv", required: true },
                  { name: "new_information", label: "New information", type: "kv", required: true },
                  { name: "reassessment_flags", label: "Reassessment flags", type: "kv", hint: 'Enter "true" or "false" as the value for each flag.' },
                  { name: "reason", label: "Reason" },
                ],
              },
              {
                path: "sources",
                label: "Register a postmarket source",
                fields: [
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "source_type", label: "Source type", required: true },
                  { name: "organization_or_system", label: "Organization or system", required: true },
                  { name: "channel", label: "Channel", required: true },
                  { name: "owner_subject_id", label: "Owner", type: "userSelect", required: true },
                  { name: "ingestion_profile_id", label: "Ingestion profile ID" },
                  { name: "reason", label: "Reason" },
                ],
              },
              {
                path: "safety-cases/{canonical_case_id}/duplicate-links",
                label: "Link duplicate cases",
                fields: [
                  { name: "canonical_case_id", label: "Canonical safety case ID", required: true },
                  { name: "duplicate_case_ids", label: "Duplicate case IDs", type: "stringList", required: true, itemLabel: "Case ID" },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
              {
                path: "surveillance-metrics:calculate",
                label: "Calculate a surveillance metric",
                fields: [
                  { name: "metric_definition_version", label: "Metric definition version", required: true },
                  { name: "scope", label: "Scope", type: "kv", required: true },
                  { name: "period", label: "Period", type: "kv", required: true, hint: 'e.g. "start" → a date, "end" → a date.' },
                  { name: "source_cutoff", label: "Source cutoff", type: "datetime", required: true },
                  { name: "exposure_denominator", label: "Exposure denominator", type: "kv" },
                  { name: "denominator_uncertain", label: "Denominator uncertain", type: "bool" },
                ],
              },
              {
                path: "signal-rules:evaluate",
                label: "Evaluate signal rules",
                fields: [
                  { name: "signal_rule_versions", label: "Signal rule versions", type: "stringList", required: true, itemLabel: "Rule version" },
                  { name: "case_scope", label: "Case scope", type: "kv" },
                ],
              },
              {
                path: "periodic-datasets:freeze",
                label: "Freeze a periodic safety dataset",
                fields: [
                  { name: "application_id", label: "Application ID", required: true },
                  { name: "interval_start", label: "Interval start", type: "datetime", required: true },
                  { name: "interval_end", label: "Interval end", type: "datetime", required: true },
                  { name: "report_type", label: "Report type", required: true },
                  { name: "cutoff", label: "Cutoff", type: "datetime", required: true },
                  { name: "site_id", label: "Site ID" },
                ],
              },
            ]}
          />

          <SignedJsonForm
          title="Safety signal operations - signed"
            subtitle="Opening, assessing and escalating a safety signal now require a Part 11 signature."
            root="/postmarket/v1"
            ops={[
              {
                postPath: "signals",
                challengePath: "signals/signature-challenges",
                action: "open",
                label: "Open a safety signal",
                mirrorBodyInChallenge: true,
                about: "The challenge signs the signal_code before the record exists - the rest of the fields still go to the mutation.",
                fields: [
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "signal_code", label: "Signal code", required: true },
                  { name: "detection_source", label: "Detection source", required: true },
                  {
                    name: "trigger_refs", label: "Triggers", type: "repeat", required: true, itemLabel: "Trigger",
                    subFields: [{ name: "ref", label: "Reference" }, { name: "note", label: "Note" }],
                  },
                  { name: "population_definition", label: "Population definition", type: "kv", required: true },
                  { name: "case_ids_for_snapshot", label: "Case IDs for snapshot", type: "stringList", itemLabel: "Case ID" },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                  { name: "rule_version", label: "Rule version" },
                  { name: "exposure_denominator", label: "Exposure denominator", type: "kv" },
                  { name: "denominator_uncertain", label: "Denominator uncertain", type: "bool" },
                ],
              },
              {
                postPath: "signals/{signal_id}/assessments",
                challengePath: "signals/{signal_id}/assessment-signature-challenges",
                action: "assess",
                label: "Assess a signal",
                fields: [
                  { name: "signal_id", label: "Signal ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "assessment", label: "Assessment", type: "kv", required: true },
                  { name: "next_state", label: "Next state", required: true, type: "select", options: [
                    "DETECTED", "TRIAGE", "ASSESSMENT", "REFUTED", "MONITORING", "CONFIRMED", "ACTION", "CLOSED",
                  ].map((v) => ({ value: v, label: v })) },
                  { name: "recommended_actions", label: "Recommended actions", type: "stringList", itemLabel: "Action" },
                  { name: "reason", label: "Reason" },
                ],
              },
              {
                postPath: "signals/{signal_id}/escalations",
                challengePath: "signals/{signal_id}/escalation-signature-challenges",
                action: "escalate",
                label: "Escalate a signal",
                fields: [
                  { name: "signal_id", label: "Signal ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "target_module", label: "Target module", required: true, type: "select", options: [
                    { value: "CAPA", label: "CAPA" }, { value: "CHANGE_CONTROL", label: "Change control" },
                    { value: "RISK_REVIEW", label: "Risk review" }, { value: "FIELD_ACTION", label: "Field action" },
                    { value: "REPORTABILITY_TRACK", label: "Reportability track (not yet implemented)" },
                  ] },
                  { name: "target_command", label: "Target command payload", type: "kv", required: true, hint: "The fields the target module's own create command expects." },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
            ]}
          />

          <FormConsole
          title="Regulatory reporting operations"
            root="/regulatory/v1"
            ops={[
              {
                path: "tracks/{track_id}/deadline:calculate",
                label: "Calculate a regulatory deadline",
                fields: [
                  { name: "track_id", label: "Track ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "clock_start_basis", label: "Clock start basis", required: true, type: "select", options: [
                    { value: "SOURCE_RECEIPT", label: "Source receipt" }, { value: "COMPANY_AWARENESS", label: "Company awareness" }, { value: "AGENCY_REQUEST", label: "Agency request" }] },
                  { name: "clock_start_at", label: "Clock start at", type: "datetime", required: true },
                  { name: "clock_start_rationale", label: "Clock start rationale", type: "textarea", required: true },
                  { name: "calendar_type", label: "Calendar type", required: true, placeholder: "e.g. CALENDAR_DAYS, BUSINESS_DAYS, AGENCY_SPECIFIED" },
                  { name: "calendar_version", label: "Calendar version", required: true },
                  { name: "rule_version", label: "Rule version", required: true },
                  { name: "duration_days", label: "Duration (days)", type: "number", hint: "Required unless calendar type is AGENCY_SPECIFIED." },
                  { name: "agency_due_at", label: "Agency-specified due date", type: "datetime", hint: "Required when calendar type is AGENCY_SPECIFIED." },
                ],
              },
              {
                path: "tracks/{track_id}/reports",
                label: "Build a regulatory report",
                fields: [
                  { name: "track_id", label: "Track ID", required: true },
                  { name: "expected_version", label: "Track's expected version", type: "number", required: true, default: "1" },
                  { name: "schema_code", label: "Schema code", required: true },
                  { name: "schema_version", label: "Schema version", required: true },
                  { name: "content", label: "Content", type: "kv", required: true },
                  { name: "field_provenance", label: "Field provenance", type: "kv", required: true },
                  {
                    name: "missing_information", label: "Missing information", type: "repeat", itemLabel: "Item",
                    subFields: [{ name: "field", label: "Field" }, { name: "reason", label: "Reason" }],
                  },
                  { name: "narrative_version", label: "Narrative version", type: "number" },
                ],
              },
              {
                path: "reports/{report_id}/payloads:generate",
                label: "Generate a submission payload",
                fields: [
                  { name: "report_id", label: "Report ID", required: true },
                  { name: "implementation_or_profile_version", label: "Implementation / profile version", required: true },
                ],
              },
              {
                path: "reports/{report_id}/submissions",
                label: "Submit a report",
                fields: [
                  { name: "report_id", label: "Report ID", required: true },
                  { name: "channel", label: "Channel", required: true, placeholder: "e.g. ESG, MANUAL" },
                  { name: "payload_version", label: "Payload version", required: true },
                  { name: "payload_digest", label: "Payload digest", required: true },
                  { name: "sender_identity", label: "Sender identity", required: true },
                  { name: "manual_evidence_id", label: "Manual evidence ID", hint: "Required when channel is MANUAL." },
                  { name: "transport_result", label: "Transport result", hint: "For non-MANUAL channels, if already known." },
                ],
              },
              {
                path: "submissions/{attempt_id}/acknowledgements",
                label: "Record an acknowledgement / rejection",
                fields: [
                  { name: "attempt_id", label: "Submission attempt ID", required: true },
                  { name: "ack_level", label: "Acknowledgement level", required: true },
                  { name: "ack_state", label: "Acknowledgement state", required: true },
                  { name: "ack_reference", label: "Acknowledgement reference" },
                  { name: "ack_payload", label: "Acknowledgement payload", type: "kv" },
                  { name: "rejection_reason", label: "Rejection reason", type: "kv" },
                ],
              },
              {
                path: "reports/{original_report_id}/followups",
                label: "Create a follow-up report task",
                fields: [
                  { name: "original_report_id", label: "Original report ID", required: true },
                  { name: "new_information_receipt", label: "New information receipt", type: "kv", required: true },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
              {
                path: "cases/{case_id}/part4-deduplication:evaluate",
                label: "Evaluate Part 4 same-event dedup",
                fields: [
                  { name: "case_id", label: "Safety case ID", pathOnly: true, required: true },
                  { name: "candidate_track_ids", label: "Candidate track IDs", type: "stringList", required: true, itemLabel: "Track ID" },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
              {
                path: "audit-packages:freeze",
                label: "Freeze an inspection audit package",
                fields: [
                  { name: "safety_case_id", label: "Safety case ID", hint: "Set this, or specific report IDs below, or both." },
                  { name: "report_ids", label: "Report IDs", type: "stringList", itemLabel: "Report ID" },
                  { name: "site_id", label: "Site ID" },
                ],
              },
            ]}
          />

          <SignedJsonForm
          title="Regulatory reporting operations - signed"
            subtitle="Deciding reportability and approving a report now require a Part 11 signature."
            root="/regulatory/v1"
            ops={[
              {
                postPath: "tracks/{track_id}/decisions",
                challengePath: "tracks/{track_id}/decision-signature-challenges",
                action: "decide",
                label: "Decide reportability",
                about: "Records the reportable / not-reportable decision for one report type and its rationale.",
                fields: [
                  { name: "track_id", label: "Track ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "decision", label: "Decision", type: "select", required: true, options: [
                    { value: "REPORTABLE", label: "Reportable" }, { value: "NOT_REPORTABLE", label: "Not reportable" }] },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
              {
                postPath: "reports/{report_id}/approve",
                challengePath: "reports/{report_id}/approval-signature-challenges",
                action: "approve",
                label: "Approve a report",
                fields: [
                  { name: "report_id", label: "Report ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                ],
              },
            ]}
          />

          <FormConsole
          title="Part 4 obligations"
            root="/postmarket/v1"
            ops={[
              {
                path: "field-alerts",
                label: "Raise a field alert obligation",
                fields: [
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "source_type", label: "Source type", required: true },
                  { name: "source_id", label: "Source ID", required: true },
                  { name: "source_version", label: "Source version", type: "number" },
                  { name: "application_id", label: "Application ID", required: true },
                  { name: "distributed_batches", label: "Distributed batches", type: "stringList", required: true, itemLabel: "Batch" },
                  { name: "issue_type", label: "Issue type", required: true },
                  { name: "facility", label: "Facility" },
                  { name: "applicant_receipt_at", label: "Applicant receipt at", type: "datetime", required: true },
                  { name: "owner_subject_id", label: "Owner", type: "userSelect" },
                ],
              },
              {
                path: "obligations/{obligation_id}/legal-hold",
                label: "Apply / lift a legal hold",
                fields: [
                  { name: "obligation_id", label: "Obligation ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "reason", label: "Reason", type: "textarea", required: true },
                  { name: "authority", label: "Authority", required: true },
                ],
              },
              {
                path: "applicant-relationships",
                label: "Register an applicant/constituent relationship",
                fields: [
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "product_version_reference", label: "Product version reference", type: "kv", required: true },
                  { name: "applicant_role", label: "Applicant role", required: true },
                  { name: "applicant_name", label: "Applicant name", required: true },
                  { name: "address", label: "Address", type: "kv", required: true },
                  { name: "contact", label: "Contact", type: "kv", required: true },
                  { name: "application_type", label: "Application type" },
                  { name: "application_number", label: "Application number" },
                  { name: "sharing_channel", label: "Sharing channel" },
                ],
              },
              {
                path: "cases/{safety_case_id}/part4-sharing:evaluate",
                label: "Evaluate Part 4 sharing",
                fields: [
                  { name: "safety_case_id", label: "Safety case ID", required: true },
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "applicant_relationship_id", label: "Applicant relationship ID", required: true },
                  { name: "company_receipt_at", label: "Company receipt at", type: "datetime", required: true },
                ],
              },
              {
                path: "sharing/{share_id}/package",
                label: "Build a sharing package",
                fields: [
                  { name: "share_id", label: "Share ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "package_content", label: "Package content", type: "kv", required: true },
                ],
              },
              {
                path: "sharing/{share_id}/record-sent",
                label: "Record a package sent",
                fields: [
                  { name: "share_id", label: "Share ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "sent_at", label: "Sent at", type: "datetime", required: true },
                  { name: "channel", label: "Channel", required: true },
                  { name: "delivery_evidence", label: "Delivery evidence", type: "kv" },
                ],
              },
              {
                path: "field-actions/{field_action_id}/correction-removal-assessment",
                label: "Correction/removal assessment",
                about: "The field action in the URL is the source of this assessment.",
                fields: [
                  { name: "field_action_id", label: "Field action ID", pathOnly: true, required: true },
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "field_action_reference", label: "Field action reference", type: "kv", required: true },
                  { name: "initiation_at", label: "Initiated at", type: "datetime", required: true },
                ],
              },
              {
                path: "correction-removal/{record_id}/decision",
                label: "Correction/removal decision",
                fields: [
                  { name: "record_id", label: "Correction/removal record ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "reportable", label: "Reportable", type: "bool", required: true },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                  { name: "calendar_version", label: "Calendar version" },
                  { name: "required_facts", label: "Required facts", type: "kv" },
                ],
              },
              {
                path: "correction-removal/{record_id}/scope-amendments",
                label: "Amend correction/removal scope",
                about: "Scope expansion to additional lots/batches - appended, never overwriting the original assessment.",
                fields: [
                  { name: "record_id", label: "Correction/removal record ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "amendment", label: "Amendment", type: "kv", required: true },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
              {
                path: "field-alerts/{obligation_id}/decision",
                label: "Field alert decision",
                fields: [
                  { name: "obligation_id", label: "Obligation ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "decision", label: "Decision", type: "select", required: true, options: [{ value: "REPORTABLE", label: "Reportable" }, { value: "NOT_REPORTABLE", label: "Not reportable" }] },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
              {
                path: "bpdr-tracks",
                label: "Open a BPDR track",
                fields: [
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "source_type", label: "Source type", required: true },
                  { name: "source_id", label: "Source ID", required: true },
                  { name: "source_version", label: "Source version", type: "number" },
                  { name: "application_id", label: "Application ID", required: true },
                  { name: "deviation_facts", label: "Deviation facts", type: "kv", required: true },
                  { name: "discovery_at", label: "Discovered at", type: "datetime", required: true },
                  { name: "owner_subject_id", label: "Owner", type: "userSelect" },
                ],
              },
              {
                path: "periodic-cycles:generate",
                label: "Generate periodic safety cycles",
                fields: [
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "application_reference", label: "Application reference", required: true },
                  { name: "cycle_type", label: "Cycle type", required: true },
                  { name: "period_start", label: "Period start", type: "datetime", required: true },
                  { name: "period_end", label: "Period end", type: "datetime", required: true },
                  { name: "inclusion_rules_version", label: "Inclusion rules version", required: true },
                ],
              },
              {
                path: "periodic-cycles/{cycle_id}/dataset:freeze",
                label: "Freeze a periodic cycle dataset",
                fields: [
                  { name: "cycle_id", label: "Cycle ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "source_cutoff", label: "Source cutoff", type: "datetime", required: true },
                ],
              },
              {
                path: "fda-requests",
                label: "Log an FDA request / correspondence",
                fields: [
                  { name: "site_id", label: "Site ID", required: true },
                  { name: "application_id", label: "Application ID", required: true },
                  { name: "agency_reference", label: "Agency reference", required: true },
                  { name: "requested_events_or_information", label: "Requested events or information", type: "textarea", required: true },
                  { name: "due_at", label: "Due at", type: "datetime", required: true },
                  { name: "received_at", label: "Received at", type: "datetime", required: true },
                  { name: "owner_subject_id", label: "Owner", type: "userSelect" },
                ],
              },
              {
                path: "obligations/{obligation_id}/deadline-overrides",
                label: "Override an obligation deadline",
                fields: [
                  { name: "obligation_id", label: "Obligation ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "new_due_at", label: "New due date", type: "datetime", required: true },
                  { name: "agency_evidence", label: "Agency evidence", type: "kv", required: true },
                  { name: "reason", label: "Reason", type: "textarea", required: true },
                ],
              },
              {
                path: "retention:calculate",
                label: "Calculate retention basis",
                fields: [
                  { name: "obligation_id", label: "Obligation ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  {
                    name: "applicable_regimes", label: "Applicable regimes", type: "repeat", required: true, itemLabel: "Regime",
                    subFields: [
                      { name: "regime", label: "Regime", required: true },
                      { name: "rule_version", label: "Rule version" },
                      { name: "calculated_duration_days", label: "Duration (days)", type: "number" },
                    ],
                  },
                ],
              },
            ]}
          />

          <SignedJsonForm
          title="Correction/removal independent approval - signed"
            subtitle="Both the initial assessment and the reportability decision need a second, independent signature."
            root="/postmarket/v1"
            ops={[
              {
                postPath: "correction-removal/{record_id}/assessment-signatures",
                challengePath: "correction-removal/{record_id}/assessment-signature-challenges",
                action: "sign",
                label: "Approve a correction/removal assessment",
                mirrorBodyInChallenge: true,
                fields: [
                  { name: "record_id", label: "Correction/removal record ID", required: true },
                  { name: "field_action_reference", label: "Field action reference", type: "kv", required: true, hint: "Must match exactly what the assessment being approved recorded." },
                ],
              },
              {
                postPath: "correction-removal/{record_id}/decision-signatures",
                challengePath: "correction-removal/{record_id}/decision-signature-challenges",
                action: "sign",
                label: "Approve a correction/removal reportability decision",
                mirrorBodyInChallenge: true,
                fields: [
                  { name: "record_id", label: "Correction/removal record ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "reportable", label: "Reportable", type: "bool", required: true },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                  { name: "calendar_version", label: "Calendar version" },
                  { name: "required_facts", label: "Required facts", type: "kv" },
                ],
              },
            ]}
          />
        </>
      )}
    </div>
  );
}

function DashboardCards() {
  const [dashboard, setDashboard] = useState<unknown>(undefined);
  const [calendar, setCalendar] = useState<unknown>(undefined);

  async function load() {
    setDashboard(await api.get<unknown>(`/postmarket/v1/dashboard`).catch((e) => ({ error: String(e) })));
    setCalendar(await api.get<unknown>(`/postmarket/v1/regulatory-calendar`).catch((e) => ({ error: String(e) })));
  }

  return (
    <Card pad className="mb-4">
      <div className="flex justify-between items-center">
        <CardHeader title="Signal dashboard & regulatory calendar" />
        <Button variant="secondary" onClick={load}>
          <Icon name="refresh" /> Load
        </Button>
      </div>
      {dashboard !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Signal dashboard" value={dashboard} />
        </div>
      )}
      {calendar !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Unified regulatory calendar" value={calendar} />
        </div>
      )}
    </Card>
  );
}

function CreateSafetyCaseCard() {
  const { siteId } = useSiteId();
  const [f, setF] = useState({
    safety_case_number: "",
    source_record_type: "complaint",
    source_record_id: "",
    source_record_version: "1",
    company_initial_receipt_at: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newId, setNewId] = useState<string | null>(null);

  function set(k: keyof typeof f, v: string) {
    setF((c) => ({ ...c, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNewId(null);
    try {
      const receipt = await api.post<MutationReceipt>(`/postmarket/v1/safety-cases`, {
        idempotency_key: newIdempotencyKey(),
        ...(siteId ? { site_id: siteId } : {}),
        safety_case_number: f.safety_case_number.trim(),
        source_record_type: f.source_record_type.trim(),
        source_record_id: f.source_record_id.trim(),
        source_record_version: Number(f.source_record_version),
        company_initial_receipt_at: f.company_initial_receipt_at
          ? new Date(f.company_initial_receipt_at).toISOString()
          : null,
      });
      setNewId(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Open a safety case" />
      <form onSubmit={submit} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Safety case number" required>
          <Input value={f.safety_case_number} onChange={(e) => set("safety_case_number", e.target.value)} required />
        </Field>
        <Field label="Source record type" required>
          <Input value={f.source_record_type} onChange={(e) => set("source_record_type", e.target.value)} required />
        </Field>
        <Field label="Source record ID" required>
          <Input value={f.source_record_id} onChange={(e) => set("source_record_id", e.target.value)} required />
        </Field>
        <Field label="Source record version" required>
          <Input type="number" value={f.source_record_version} onChange={(e) => set("source_record_version", e.target.value)} required />
        </Field>
        <Field label="Company initial receipt at" hint="Starts the regulatory clock.">
          <Input type="datetime-local" value={f.company_initial_receipt_at} onChange={(e) => set("company_initial_receipt_at", e.target.value)} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {error && <p className="error-text mb-2">{error}</p>}
          {newId && (
            <Banner tone="ok" title="Safety case opened">
              Case ID <span className="tabular">{newId}</span>
            </Banner>
          )}
          <Button type="submit" variant="primary" disabled={busy || !f.safety_case_number.trim() || !f.source_record_id.trim()}>
            {busy ? "Opening…" : "Open safety case"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

const TRACK_SUBFIELDS = [
  { name: "report_type_code", label: "Report type", type: "select" as const, required: true, options: REPORT_TYPE_OPTIONS },
  { name: "report_type_version", label: "Report type version" },
  { name: "application_context", label: "Application context" },
  { name: "rule_version", label: "Rule version" },
];

function ReportabilityCard() {
  const { siteId } = useSiteId();
  const [safetyCaseId, setSafetyCaseId] = useState("");
  const [tracks, setTracks] = useState<RepeatRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function createTracks(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await api.post<MutationReceipt>(`/regulatory/v1/cases/${safetyCaseId.trim()}/reportability-tracks`, {
        idempotency_key: newIdempotencyKey(),
        ...(siteId ? { site_id: siteId } : {}),
        safety_case_id: safetyCaseId.trim(),
        tracks: buildRepeatArray(TRACK_SUBFIELDS, tracks),
      });
      setMsg("Reportability tracks created. Use the regulatory operations console below to calculate deadlines and record decisions.");
    } catch (err) {
      setMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  const missingTracks = buildRepeatArray(TRACK_SUBFIELDS, tracks).length === 0;

  return (
    <Card pad className="mb-4">
      <CardHeader title="Reportability workbench" />
      <p className="fs-2 text-muted mb-3">
        Open the reportability tracks for a safety case (one per applicable report type). The regulatory
        clock, decision and report build then run per track in the operations console below.
      </p>
      <form onSubmit={createTracks}>
        <Field label="Safety case ID" required>
          <Input value={safetyCaseId} onChange={(e) => setSafetyCaseId(e.target.value)} required style={{ maxWidth: 360 }} />
        </Field>
        <RepeatableRows
          label="Reportability tracks"
          required
          itemLabel="Track"
          hint="One track per report type this safety case must be assessed against."
          subFields={TRACK_SUBFIELDS}
          value={tracks}
          onChange={setTracks}
        />
        {msg && <p className={msg.startsWith("Reportability") ? "fs-2 mt-2" : "error-text mt-2"}>{msg}</p>}
        <Button type="submit" variant="primary" disabled={busy || !safetyCaseId.trim() || missingTracks} className="mt-2">
          {busy ? "Creating…" : "Create reportability tracks"}
        </Button>
      </form>
    </Card>
  );
}
