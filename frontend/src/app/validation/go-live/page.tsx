"use client";

import { useState } from "react";
import { api, holdsAnyRole } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm, type SignedJsonOp } from "@/components/shared/SignedJsonForm";

const READS = [
  { label: "Go-live readiness (VSR id)", path: "releases/{p}/go-live-readiness" },
  { label: "Migration legacy trace (plan id)", path: "migrations/{p}/legacy-trace" },
];

export default function GoLivePage() {
  const { me } = useMe();
  const canWork = holdsAnyRole(me, ["Admin", "QA Releaser", "QA Reviewer"]);

  return (
    <div>
      <PageHead
        title="Deployment · PQ · go-live"
        subtitle="Documents 85 / 87 / 95 — performance qualification, data migration, the validation summary report and the release authorization."
      />

      <ReadCard />

      {!canWork && (
        <Banner tone="info" title="Read-only">
          Driving PQ, migration and release authorization needs the QA Releaser or QA Reviewer role.
        </Banner>
      )}

      {canWork && (
        <>
          <FormConsole
            title="Performance qualification (Document 85)"
            root="/validation/v1"
            ops={[
              { path: "pq/scenarios", label: "Create a PQ scenario", template: '{\n  "acceptance_criteria": "",\n  "reason": ""\n}' },
              { path: "pq/scenarios/{scenario_id}/participants", label: "Add PQ participants / training" },
              { path: "pq/executions", label: "Record a PQ execution" },
            ]}
          />

          <FormConsole
            title="Data migration (Document 87)"
            root="/validation/v1"
            ops={[
              { path: "migrations/plans", label: "Create a migration plan" },
              { path: "migrations/runs", label: "Record a migration run / dry run" },
              { path: "migrations/{run_id}/reconcile", label: "Reconcile a migration run" },
            ]}
          />

          <FormConsole
            title="Validation summary & release authorization (Document 95)"
            root="/validation/v1"
            ops={[
              { path: "summary-reports", label: "Create a validation summary report" },
              { path: "releases/{authorization_id}/post-go-live-verification", label: "Record post-go-live verification" },
            ]}
          />

          <SignedJsonForm title="PQ · migration · release — signed operations (SG-172)" root="/validation/v1" ops={GO_LIVE_SIGNED_OPS} />
        </>
      )}
    </div>
  );
}

// ---- Signed operations (SG-172) -----------------------------------------------------------------

const GO_LIVE_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve a PQ scenario (site acceptance)",
    action: "approve",
    postPath: "pq/{scenario_id}/approve",
    challengePath: "pq/{scenario_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": "",\n  "decision": "ACCEPTED"\n}',
    about: "decision is ACCEPTED | REJECTED.",
  },
  {
    label: "Approve a migration run (cutover)",
    action: "approve",
    postPath: "migrations/{run_id}/approve",
    challengePath: "migrations/{run_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Approve a validation summary report",
    action: "approve",
    postPath: "summary-reports/{report_id}/approve",
    challengePath: "summary-reports/{report_id}/signature-challenges",
    template:
      '{\n  "expected_version": 1,\n  "reason": "",\n  "decision": "APPROVED",\n  "decision_conditions": []\n}',
    about: "decision is APPROVED | CONDITIONAL | REJECTED.",
  },
  {
    label: "Authorize the release / go-live",
    action: "authorize",
    postPath: "releases/{vsr_id}/authorize",
    challengePath: "releases/{vsr_id}/authorize/signature-challenges",
    mirrorBodyInChallenge: true,
    template:
      '{\n  "authorization_number": "",\n  "environment": "",\n  "config_fingerprint": "",\n  "release_identity": {\n    "image_digest": "",\n    "schema_version": "",\n    "migration_head": "",\n    "config_version": ""\n  },\n  "artifact_digests": {},\n  "decision": "APPROVED",\n  "go_live_gates": {},\n  "reason": "",\n  "conditions": [],\n  "production_performer_user_ids": []\n}',
    about:
      "Content-hash-bound signature (Document 106 row 166) — decision is APPROVED | CONDITIONAL | REJECTED. Do not edit the payload after requesting the challenge.",
  },
  {
    label: "Record a deployment check",
    action: "deployment_check",
    postPath: "releases/{authorization_id}/deployment-check",
    challengePath: "releases/{authorization_id}/deployment-check/signature-challenges",
    template:
      '{\n  "expected_version": 1,\n  "submitted_config_fingerprint": "",\n  "submitted_artifact_digests": {},\n  "reason": "",\n  "production_performer_user_ids": []\n}',
  },
];

function ReadCard() {
  const [which, setWhich] = useState(0);
  const [ref, setRef] = useState("");
  const [data, setData] = useState<unknown>(undefined);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setData(undefined);
    try {
      setData(await api.get<unknown>(`/validation/v1/${READS[which].path.replace("{p}", encodeURIComponent(ref.trim()))}`));
    } catch (err) {
      setData({ error: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Go-live reads" />
      <div className="flex items-end gap-3 mt-3">
        <Field label="Report">
          <Select value={which} onChange={(e) => setWhich(Number(e.target.value))} style={{ minWidth: 300 }}>
            {READS.map((r, i) => (
              <option key={r.path} value={i}>
                {r.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Reference / ID">
          <Input value={ref} onChange={(e) => setRef(e.target.value)} style={{ minWidth: 260 }} />
        </Field>
        <Button variant="secondary" onClick={load} disabled={busy || !ref.trim()}>
          {busy ? "Loading…" : "Load"}
        </Button>
      </div>
      {data !== undefined && (
        <div className="mt-3">
          <JsonPanel title={READS[which].label} value={data} />
        </div>
      )}
    </Card>
  );
}
