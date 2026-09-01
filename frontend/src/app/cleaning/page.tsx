"use client";

import { canMaintainEquipment, holdsAnyRole, type Me } from "@/lib/api";
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

const canOperate = (me: Me | null) => holdsAnyRole(me, ["Admin", "Operator", "Supervisor", "Sanitation Operator"]);
const canVerify = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Reviewer", "QC Reviewer"]);

const config: OpsRecordConfig<CleaningExecution> = {
  title: "Cleaning executions",
  subtitle: "Document 39 — equipment cleaning records: steps, agents, completion and independent verification.",
  idLabel: "Cleaning execution ID",
  apiRoot: "/cleaning/v1/executions",
  create: {
    label: "Start cleaning execution",
    can: (me) => canOperate(me) || canMaintainEquipment(me),
    path: "/cleaning/v1/executions",
    fields: [
      { name: "procedure_version_id", label: "Cleaning procedure version ID", required: true },
      { name: "equipment_id", label: "Equipment ID", hint: "Or leave blank and set an area." },
      { name: "area_id", label: "Area ID" },
      { name: "batch_context", label: "Batch context", type: "json", hint: "Optional." },
    ],
    buildBody: (v, siteId) => ({
      site_id: siteId,
      procedure_version_id: v.procedure_version_id,
      equipment_id: v.equipment_id,
      area_id: v.area_id,
      batch_context: v.batch_context,
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
        { name: "step", label: "Step", type: "json", required: true, placeholder: '{ "step_code": "RINSE", "result": "done" }' },
        { name: "agents_used", label: "Agents used", type: "json" },
        { name: "disassembly_verified", label: "Disassembly verified", placeholder: "true / false" },
      ],
      buildBody: (r, v) => ({
        execution_id: r.id,
        expected_version: r.version,
        step: v.step,
        agents_used: v.agents_used,
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
        { name: "previous_batch_identity_removed", label: "Previous batch identity removed", required: true, placeholder: "true / false" },
        { name: "inspection_result", label: "Inspection result", type: "json" },
      ],
      buildBody: (r, v) => ({
        execution_id: r.id,
        expected_version: r.version,
        previous_batch_identity_removed: v.previous_batch_identity_removed === "true",
        inspection_result: v.inspection_result,
      }),
    },
    {
      key: "verify",
      label: "Verify (sign)",
      signed: true,
      challengeAction: "verify",
      variant: "success",
      can: canVerify,
      summary: "Independent verification of the cleaning result (SoD — the verifier is not the performer).",
      fields: [{ name: "result", label: "Result", required: true, placeholder: "pass / fail" }],
      buildBody: (r, v) => ({ execution_id: r.id, expected_version: r.version, result: v.result }),
    },
  ],
};

export default function CleaningPage() {
  return <OpsRecordPage config={config} />;
}
