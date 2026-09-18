"use client";

import { hasPermission, type Me } from "@/lib/api";
import { Fact, IdFact, OpsRecordPage, type OpsRecordConfig } from "@/components/shared/OpsRecordPage";
import { StatePill } from "@/components/ui/StatePill";

interface CleaningExecution {
  id: string;
  site_id: string;
  equipment_id: string | null;
  area_id: string | null;
  procedure_version_id: string;
  state: string;
  dirty_since: string;
  clean_until: string | null;
  verification_result: string | null;
  dirty_hold_exceeded: boolean;
  requires_deviation: boolean;
  protection_state: Record<string, unknown> | null;
  version: number;
}

// cleaning_execution.create / .complete (Document 39) — Admin, Operator, QA Reviewer, Sanitation
// Operator per scripts/seed.py. Audit finding 2026-09-18: this previously included Supervisor (who
// holds no cleaning_execution.* grant — silent 403) and omitted QA Reviewer (who does hold it — hidden
// feature). Also removed a stray `|| canMaintainEquipment(me)` on the create gate, which wrongly let
// Maintenance Technician (whose only grant is equipment_asset.maintain) start a cleaning execution.
const canOperate = (me: Me | null) => hasPermission(me, "cleaning_execution.create");
const canVerify = (me: Me | null) => hasPermission(me, "cleaning_execution.verify");

const config: OpsRecordConfig<CleaningExecution> = {
  title: "Cleaning executions",
  subtitle: "Equipment cleaning records: steps, agents, completion and independent verification.",
  idLabel: "Cleaning execution ID",
  apiRoot: "/cleaning/v1/executions",
  create: {
    label: "Start cleaning execution",
    can: canOperate,
    path: "/cleaning/v1/executions",
    fields: [
      { name: "procedure_version_id", label: "Cleaning procedure version ID", required: true },
      { name: "equipment_id", label: "Equipment", type: "equipmentSelect", hint: "Or leave blank and set an area." },
      { name: "area_id", label: "Area", type: "areaSelect" },
      { name: "batch_context", label: "Batch context", type: "kv", hint: "Optional - what batch/product this cleaning relates to." },
    ],
    buildBody: (v, siteId) => ({
      site_id: siteId,
      procedure_version_id: v.procedure_version_id,
      equipment_id: v.equipment_id,
      area_id: v.area_id,
      batch_context: Object.keys((v.batch_context as object) ?? {}).length ? v.batch_context : null,
    }),
  },
  stateOf: (r) => r.state,
  numberOf: (r) => `Cleaning ${r.id.slice(0, 8)}…`,
  facts: (r) => (
    <>
      <Fact label="Verification result">
        {r.verification_result ? (
          <StatePill state={r.verification_result === "pass" ? "accepted" : "failed"} icon={r.verification_result === "pass" ? "check-circle" : "x"}>
            {r.verification_result}
          </StatePill>
        ) : (
          "—"
        )}
      </Fact>
      <Fact label="Dirty hold exceeded">
        {r.dirty_hold_exceeded ? <StatePill state="failed" icon="alert-triangle">Yes</StatePill> : "No"}
      </Fact>
      <Fact label="Requires deviation">{r.requires_deviation ? "Yes" : "No"}</Fact>
      <Fact label="Clean until">{r.clean_until ? new Date(r.clean_until).toLocaleString() : "—"}</Fact>
      <Fact label="Record version">{r.version}</Fact>
      <IdFact label="Procedure version" value={r.procedure_version_id} />
      <IdFact label="Equipment" value={r.equipment_id} />
      <IdFact label="Area" value={r.area_id} />
    </>
  ),
  transitions: [
    {
      key: "steps",
      label: "Record step",
      can: canOperate,
      summary: "Records one executed cleaning step with the agents used.",
      fields: [
        { name: "step_code", label: "Step code", required: true, placeholder: "e.g. RINSE, SCRUB, DRY" },
        { name: "step_result", label: "Step result", placeholder: "e.g. done" },
        { name: "agents_used", label: "Agents used", type: "kv", hint: 'Cleaning agents applied, e.g. "agent" → "IPA 70%".' },
        { name: "disassembly_verified", label: "Disassembly verified", type: "bool" },
      ],
      buildBody: (r, v) => ({
        execution_id: r.id,
        expected_version: r.version,
        step: { step_code: v.step_code, result: v.step_result || undefined },
        agents_used: Object.keys((v.agents_used as object) ?? {}).length ? v.agents_used : null,
        disassembly_verified: v.disassembly_verified === null ? null : v.disassembly_verified === "true",
      }),
    },
    {
      key: "complete",
      label: "Complete (sign)",
      signed: true,
      challengeAction: "complete",
      variant: "primary",
      can: canOperate,
      summary: "Attests the cleaning is complete and the previous batch identity has been removed.",
      fields: [
        { name: "previous_batch_identity_removed", label: "Previous batch identity removed", required: true, type: "bool" },
        { name: "inspection_result", label: "Inspection result", type: "kv" },
      ],
      buildBody: (r, v) => ({
        execution_id: r.id,
        expected_version: r.version,
        previous_batch_identity_removed: v.previous_batch_identity_removed === "true",
        inspection_result: Object.keys((v.inspection_result as object) ?? {}).length ? v.inspection_result : null,
      }),
    },
    {
      key: "verify",
      label: "Verify (sign)",
      signed: true,
      challengeAction: "verify",
      variant: "success",
      can: canVerify,
      summary: "Independent verification of the cleaning result (SoD - the verifier is not the performer).",
      fields: [
        {
          name: "result", label: "Result", required: true, type: "select",
          options: [{ value: "pass", label: "Pass" }, { value: "fail", label: "Fail" }],
        },
      ],
      buildBody: (r, v) => ({ execution_id: r.id, expected_version: r.version, result: v.result }),
    },
  ],
};

export default function CleaningPage() {
  return <OpsRecordPage config={config} />;
}
