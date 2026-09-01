"use client";

import { holdsAnyRole, type Me } from "@/lib/api";
import { Fact, IdFact, OpsRecordPage, type OpsRecordConfig } from "@/components/shared/OpsRecordPage";
import { StatePill } from "@/components/ui/StatePill";

interface ProcessCycle {
  id: string;
  site_id: string;
  process_type: string;
  equipment_id: string;
  state: string;
  critical_alarm: boolean;
  indicator_results: Record<string, unknown> | null;
  requires_deviation: boolean;
  version: number;
}

const canOperate = (me: Me | null) => holdsAnyRole(me, ["Admin", "Operator", "Supervisor", "Sterilization Operator"]);
const canReview = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Reviewer", "QC Reviewer"]);

const config: OpsRecordConfig<ProcessCycle> = {
  title: "Sterilization cycles",
  subtitle: "Document 42 — sterilization / depyrogenation process cycles: load, execution data, indicators and review.",
  idLabel: "Process cycle ID",
  apiRoot: "/sterilization/v1/cycles",
  create: {
    label: "Create process cycle",
    can: canOperate,
    path: "/sterilization/v1/cycles",
    fields: [
      { name: "process_type", label: "Process type", required: true, placeholder: "e.g. moist_heat, dry_heat" },
      { name: "equipment_id", label: "Equipment ID", required: true },
      { name: "profile_version_id", label: "Cycle profile version ID", required: true },
      { name: "batch_id", label: "Batch ID", hint: "Optional." },
      { name: "load_items", label: "Load items", type: "json", hint: "Optional array." },
    ],
    buildBody: (v, siteId) => ({
      site_id: siteId,
      process_type: v.process_type,
      equipment_id: v.equipment_id,
      profile_version_id: v.profile_version_id,
      batch_id: v.batch_id,
      load_items: v.load_items ?? [],
    }),
  },
  stateOf: (r) => r.state,
  numberOf: (r) => `${r.process_type} cycle ${r.id.slice(0, 8)}…`,
  facts: (r) => (
    <>
      <Fact label="Process type">{r.process_type}</Fact>
      <Fact label="Critical alarm">
        {r.critical_alarm ? <StatePill state="failed" icon="alert-triangle">Raised</StatePill> : "None"}
      </Fact>
      <Fact label="Requires deviation">{r.requires_deviation ? "Yes" : "No"}</Fact>
      <Fact label="Indicator results">{r.indicator_results ? JSON.stringify(r.indicator_results) : "—"}</Fact>
      <Fact label="Record version">{r.version}</Fact>
      <IdFact label="Equipment" value={r.equipment_id} />
    </>
  ),
  transitions: [
    {
      key: "start",
      label: "Start cycle (sign)",
      signed: true,
      challengeAction: "start",
      variant: "primary",
      can: canOperate,
      summary: "Starts the cycle. The load and profile are frozen at this point.",
      buildBody: (r) => ({ cycle_id: r.id, expected_version: r.version }),
    },
    {
      key: "data",
      label: "Record cycle data",
      can: canOperate,
      summary: "Appends controller parameter / alarm / indicator data. Set 'final' on the last batch.",
      fields: [
        { name: "controller_cycle_id", label: "Controller cycle ID" },
        { name: "parameter_data", label: "Parameter data", type: "json" },
        { name: "alarm_data", label: "Alarm data", type: "json" },
        { name: "indicator_results", label: "Indicator results", type: "json" },
        { name: "critical_alarm", label: "Critical alarm", placeholder: "true / false" },
        { name: "final", label: "Final", placeholder: "true / false" },
      ],
      buildBody: (r, v) => ({
        cycle_id: r.id,
        expected_version: r.version,
        controller_cycle_id: v.controller_cycle_id,
        parameter_data: v.parameter_data,
        alarm_data: v.alarm_data,
        indicator_results: v.indicator_results,
        critical_alarm: v.critical_alarm === "true",
        final: v.final === "true",
      }),
    },
    {
      key: "review",
      label: "Review (sign)",
      signed: true,
      challengeAction: "review",
      variant: "success",
      can: canReview,
      summary: "Accept or reject the completed cycle against its acceptance criteria and indicators.",
      fields: [{ name: "decision", label: "Decision", required: true, placeholder: "accept / reject" }],
      buildBody: (r, v) => ({ cycle_id: r.id, expected_version: r.version, decision: v.decision }),
    },
  ],
};

export default function SterilizationPage() {
  return <OpsRecordPage config={config} />;
}
