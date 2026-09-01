"use client";

import { holdsAnyRole, type Me } from "@/lib/api";
import { Fact, IdFact, OpsRecordPage, type OpsRecordConfig } from "@/components/shared/OpsRecordPage";
import { StatePill } from "@/components/ui/StatePill";

interface AsepticOperation {
  id: string;
  site_id: string;
  area_id: string;
  state: string;
  media_fill_reference: Record<string, unknown> | null;
  qc_test_order_id: string | null;
  qc_result_id: string | null;
  requires_deviation: boolean;
  version: number;
}

const canOperate = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "Aseptic Operator", "Aseptic Supervisor", "Operator", "Supervisor"]);

const config: OpsRecordConfig<AsepticOperation> = {
  title: "Aseptic operations",
  subtitle: "Document 40 — aseptic processing operations: setup, live execution, interventions and completion.",
  idLabel: "Aseptic operation ID",
  apiRoot: "/aseptic/v1/operations",
  create: {
    label: "Create aseptic operation",
    can: canOperate,
    path: "/aseptic/v1/operations",
    fields: [
      { name: "area_id", label: "Area ID", required: true },
      { name: "profile_version_id", label: "Aseptic profile version ID", required: true },
      { name: "batch_id", label: "Batch ID", hint: "Optional." },
      { name: "batch_step_id", label: "Batch step ID", hint: "Optional." },
      { name: "sterile_input_refs", label: "Sterile input refs", type: "json", hint: "Optional array." },
      { name: "media_fill_reference", label: "Media fill reference", type: "json", hint: "Set for a media fill run." },
    ],
    buildBody: (v, siteId) => ({
      site_id: siteId,
      area_id: v.area_id,
      profile_version_id: v.profile_version_id,
      batch_id: v.batch_id,
      batch_step_id: v.batch_step_id,
      sterile_input_refs: v.sterile_input_refs ?? [],
      media_fill_reference: v.media_fill_reference,
    }),
  },
  stateOf: (r) => r.state,
  numberOf: (r) => `Aseptic op ${r.id.slice(0, 8)}…`,
  facts: (r) => (
    <>
      <Fact label="Media fill">{r.media_fill_reference ? "Yes" : "No"}</Fact>
      <Fact label="Requires deviation">
        {r.requires_deviation ? <StatePill state="failed" icon="alert-triangle">Yes</StatePill> : "No"}
      </Fact>
      <Fact label="Record version">{r.version}</Fact>
      <IdFact label="Area" value={r.area_id} />
      <IdFact label="QC test order" value={r.qc_test_order_id} />
      <IdFact label="QC result" value={r.qc_result_id} />
    </>
  ),
  transitions: [
    {
      key: "start",
      label: "Start operation (sign)",
      signed: true,
      challengeAction: "start",
      variant: "primary",
      can: canOperate,
      summary: "Starts the aseptic operation. Area, personnel and sterile-input checks must already pass.",
      buildBody: (r) => ({ operation_id: r.id, expected_version: r.version }),
    },
    {
      key: "interventions",
      label: "Record intervention",
      can: canOperate,
      summary: "Records a planned or unplanned aseptic intervention, with the impacted unit scope.",
      fields: [
        { name: "intervention_type", label: "Intervention type", required: true },
        { name: "planned", label: "Planned", placeholder: "true / false" },
        { name: "location", label: "Location" },
        { name: "reason", label: "Reason", type: "textarea" },
        { name: "impacted_unit_scope", label: "Impacted unit scope", type: "json" },
      ],
      buildBody: (r, v) => ({
        operation_id: r.id,
        expected_version: r.version,
        intervention_type: v.intervention_type,
        planned: v.planned === null ? true : v.planned === "true",
        location: v.location,
        reason: v.reason,
        impacted_unit_scope: v.impacted_unit_scope,
      }),
    },
    {
      key: "events",
      label: "Record event",
      can: canOperate,
      summary: "Records an environmental / process event against the running operation.",
      fields: [{ name: "event", label: "Event", type: "json", required: true }],
      buildBody: (r, v) => ({ operation_id: r.id, expected_version: r.version, ...(v.event as Record<string, unknown>) }),
    },
    {
      key: "complete",
      label: "Complete (sign)",
      signed: true,
      challengeAction: "complete",
      variant: "success",
      can: canOperate,
      summary: "Completes the operation and links the environmental / media-fill QC result.",
      fields: [
        { name: "critical", label: "Critical", placeholder: "true / false" },
        { name: "qc_test_order_id", label: "QC test order ID" },
        { name: "qc_result_id", label: "QC result ID" },
      ],
      buildBody: (r, v) => ({
        operation_id: r.id,
        expected_version: r.version,
        critical: v.critical === "true",
        qc_test_order_id: v.qc_test_order_id,
        qc_result_id: v.qc_result_id,
      }),
    },
  ],
};

export default function AsepticPage() {
  return <OpsRecordPage config={config} />;
}
