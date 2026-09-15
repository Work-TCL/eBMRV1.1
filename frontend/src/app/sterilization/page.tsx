"use client";

import { useState } from "react";
import { api, holdsAnyRole, pagedFetcher, type Me } from "@/lib/api";
import { useSiteId } from "@/lib/hooks";
import { Fact, OpsRecordPage, type OpsRecordConfig } from "@/components/shared/OpsRecordPage";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { Table } from "@/components/ui/Table";
import { JsonPanel } from "@/components/ui/JsonPanel";

const PROCESS_TYPES = [
  "steam_autoclave", "dry_heat", "depyrogenation", "gas", "radiation", "external_reference", "SIP", "CIP", "sterile_filtration",
];

interface LoadItem {
  id: string;
  item_type: string;
  item_reference: string;
  // Resolved server-side only when `item_reference` turned out to be a material lot's raw id rather
  // than its human code (a row written before the picker was fixed to store the code) — null for an
  // already-human reference (the normal case) or a genuinely free-text non-lot item.
  item_reference_label: string | null;
  position: string | null;
  sterile_status: string | null;
  sterile_status_expiry: string | null;
}

interface ProcessCycle {
  id: string;
  site_id: string;
  process_type: string;
  equipment_id: string;
  // Resolved server-side (sterilization_router._resolve_cycle_refs) so the UI never has to show a raw
  // id — every one of these is null only when the referenced record itself couldn't be resolved.
  equipment_code: string | null;
  profile_version_id: string;
  profile_number: string | null;
  profile_version_no: number | null;
  batch_id: string | null;
  batch_number: string | null;
  batch_product_name: string | null;
  batch_product_code: string | null;
  controller_cycle_id: string | null;
  state: string;
  critical_alarm: boolean;
  indicator_results: Record<string, unknown> | null;
  parameter_summary: Record<string, unknown> | null;
  alarm_summary: Record<string, unknown> | null;
  requires_deviation: boolean;
  started_by_full_name: string | null;
  started_by_username: string | null;
  reviewer_full_name: string | null;
  reviewer_username: string | null;
  version: number;
  // Only present on the single-record GET (list rows omit it).
  load_items?: LoadItem[];
}

const canOperate = (me: Me | null) => holdsAnyRole(me, ["Admin", "Operator", "Supervisor", "Sterilization Operator"]);
const canReview = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Reviewer", "QC Reviewer"]);

const config: OpsRecordConfig<ProcessCycle> = {
  title: "Sterilization cycles",
  subtitle: "Sterilization / depyrogenation process cycles: load, execution data, indicators and review.",
  idLabel: "Process cycle ID",
  apiRoot: "/sterilization/v1/cycles",
  create: {
    label: "Create process cycle",
    can: canOperate,
    path: "/sterilization/v1/cycles",
    fields: [
      {
        name: "process_type", label: "Process type", required: true, type: "select",
        options: PROCESS_TYPES.map((v) => ({ value: v, label: v })),
        hint: "CIP and SIP cycles use this same form - the process type is what distinguishes them.",
      },
      { name: "equipment_id", label: "Equipment", type: "equipmentSelect", required: true },
      { name: "profile_version_id", label: "Cycle profile version", type: "sterilizationProfileSelect", required: true },
      { name: "batch_id", label: "Batch", type: "batchSelect", hint: "Optional." },
      {
        name: "load_items", label: "Load items", type: "repeat", required: true, itemLabel: "Item",
              hint: "Every item going into this cycle - at least one is required.",
        subFields: [
          { name: "item_type", label: "Item type", required: true, placeholder: "e.g. filter, garment, component" },
          {
            name: "item_reference", label: "Item reference", type: "materialLotSelect", required: true,
            placeholder: "e.g. LOT-DEV-2601, or a garment/filter reference",
          },
          { name: "position", label: "Position in load" },
        ],
      },
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
      <Fact label="Equipment">{r.equipment_code ?? r.equipment_id}</Fact>
      <Fact label="Cycle profile">
        {r.profile_number ? `${r.profile_number} v${r.profile_version_no}` : r.profile_version_id}
      </Fact>
      {r.batch_id && (
        <Fact label="Batch">
          {r.batch_number ? `${r.batch_number} - ${r.batch_product_name} (${r.batch_product_code})` : r.batch_id}
        </Fact>
      )}
      <Fact label="Controller cycle ID">{r.controller_cycle_id ?? "—"}</Fact>
      <Fact label="Critical alarm">
        {r.critical_alarm ? <StatePill state="failed" icon="alert-triangle">Raised</StatePill> : "None"}
      </Fact>
      <Fact label="Requires deviation">{r.requires_deviation ? "Yes" : "No"}</Fact>
      {r.started_by_full_name && (
        <Fact label="Started by">{`${r.started_by_full_name} (${r.started_by_username})`}</Fact>
      )}
      {r.reviewer_full_name && (
        <Fact label="Reviewed by">{`${r.reviewer_full_name} (${r.reviewer_username})`}</Fact>
      )}
      <Fact label="Record version">{r.version}</Fact>
    </>
  ),
  extra: (r) => (
    <>
      <Card pad className="mb-4">
        <CardHeader title="Load items" />
        {!r.load_items || r.load_items.length === 0 ? (
          <p className="hint mt-2">No load items recorded.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Item type</th>
                <th>Reference</th>
                <th>Position</th>
                <th>Sterile status</th>
              </tr>
            </thead>
            <tbody>
              {r.load_items.map((item) => (
                <tr key={item.id}>
                  <td className="fs-2">{item.item_type}</td>
                  <td className="fs-2">{item.item_reference_label ?? item.item_reference}</td>
                  <td className="fs-2">{item.position ?? "—"}</td>
                  <td className="fs-2">
                    {item.sterile_status
                      ? `${item.sterile_status}${item.sterile_status_expiry ? ` until ${item.sterile_status_expiry.slice(0, 10)}` : ""}`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
      <JsonPanel title="Parameter data" value={r.parameter_summary} />
      <JsonPanel title="Alarm data" value={r.alarm_summary} />
      <JsonPanel title="Indicator results" value={r.indicator_results} />
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
      show: (r) => r.state === "DRAFT",
      summary: "Starts the cycle. The load and profile are frozen at this point.",
      buildBody: (r) => ({ cycle_id: r.id, expected_version: r.version }),
    },
    {
      key: "data",
      label: "Record cycle data",
      can: canOperate,
      // Backend only accepts this while the cycle is actually running (INVALID_TRANSITION otherwise) --
      // hide the action outside that window instead of letting the user hit the error.
      show: (r) => r.state === "CYCLE_STARTED" || r.state === "CYCLE_RUNNING",
      summary: "Appends controller parameter / alarm / indicator data. Set 'final' on the last batch.",
      fields: [
        { name: "controller_cycle_id", label: "Controller cycle ID" },
        { name: "parameter_data", label: "Parameter data", type: "kv", hint: 'Controller readings, e.g. "temperature_c" → "121.3".' },
        { name: "alarm_data", label: "Alarm data", type: "kv" },
        { name: "indicator_results", label: "Indicator results", type: "kv", hint: 'Biological/chemical indicator readings, e.g. "BI_1" → "negative".' },
        { name: "critical_alarm", label: "Critical alarm", type: "bool" },
        { name: "final", label: "Final batch of data for this cycle", type: "bool" },
      ],
      buildBody: (r, v) => ({
        cycle_id: r.id,
        expected_version: r.version,
        controller_cycle_id: v.controller_cycle_id,
        parameter_data: Object.keys((v.parameter_data as object) ?? {}).length ? v.parameter_data : null,
        alarm_data: Object.keys((v.alarm_data as object) ?? {}).length ? v.alarm_data : null,
        indicator_results: Object.keys((v.indicator_results as object) ?? {}).length ? v.indicator_results : null,
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
      show: (r) => r.state === "REVIEW_PENDING" || r.state === "HOLD",
      summary: "Accept or reject the completed cycle against its acceptance criteria and indicators.",
      fields: [
        {
          name: "decision", label: "Decision", required: true, type: "select",
          options: [{ value: "accept", label: "Accept" }, { value: "reject", label: "Reject" }],
        },
      ],
      buildBody: (r, v) => ({ cycle_id: r.id, expected_version: r.version, decision: v.decision }),
    },
  ],
};

function cycleColumns(onOpen: (id: string) => void): DataTableColumn<ProcessCycle>[] {
  return [
    {
      key: "process_type",
      header: "Process type",
      sortable: true,
      render: (c) => (
        <span className="fs-2">
          {c.process_type} cycle {c.id.slice(0, 8)}…
        </span>
      ),
    },
    { key: "equipment_code", header: "Equipment", render: (c) => <span className="fs-2">{c.equipment_code ?? c.equipment_id}</span> },
    { key: "state", header: "State", sortable: true, render: (c) => <WorkflowStatePill state={c.state} /> },
    {
      key: "critical_alarm",
      header: "Critical alarm",
      render: (c) => (c.critical_alarm ? <StatePill state="failed" icon="alert-triangle">Raised</StatePill> : "None"),
    },
    {
      key: "open",
      header: "",
      align: "right",
      // A dedicated button alongside the row's own onRowClick — a row that merely looks clickable is
      // easy to miss; a plain button is not.
      render: (c) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(c.id);
          }}
        >
          Open
        </Button>
      ),
    },
  ];
}

function CycleListCard({ siteId, reloadToken, onOpen }: { siteId: string | null; reloadToken: number; onOpen: (id: string) => void }) {
  const fetchCycles = pagedFetcher<ProcessCycle>("/sterilization/v1/cycles", () => ({ site_id: siteId ?? "" }));
  return (
    <Card pad className="mb-4">
      <CardHeader title="Sterilization cycles" meta="" />
      {siteId ? (
        <DataTable
          columns={cycleColumns(onOpen)}
          fetchPage={fetchCycles}
          rowKey={(c) => c.id}
          searchPlaceholder="Search process type…"
          emptyMessage={<>No sterilization cycles yet - use &quot;Create process cycle&quot; above to add one.</>}
          defaultSort={{ by: "created_at", dir: "desc" }}
          onRowClick={(c) => onOpen(c.id)}
          reloadToken={reloadToken}
        />
      ) : (
        <p className="hint mt-2">Loading…</p>
      )}
    </Card>
  );
}

export default function SterilizationPage() {
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);

  return (
    <div>
      <OpsRecordPage
        config={config}
        collapseCreate
        detailInModal
        hideLookup
        afterHeader={(openRecord) => (
          <CycleListCard siteId={siteId} reloadToken={reloadToken} onOpen={openRecord} />
        )}
        onCreated={() => setReloadToken((n) => n + 1)}
      />
      <FiltrationSection />
    </div>
  );
}

/** Document 42 sterile-filtration integrity — `app/modules/equipment/sterilization_router.py`'s
 * `filtration_router`. Not folded into `OpsRecordPage`'s `config` above: install/get/integrity-tests
 * live under `/filtration/v1/filters/...` but the signature-challenge and complete mutation live under
 * `/filtration/v1/uses/...` (verified in router.py — same underlying `SterileFilterUse` row, two path
 * prefixes) — `OpsRecordPage` assumes one `apiRoot` for every record-scoped action, so a plain
 * `FormConsole` + `SignedJsonForm` pair (each free to declare its own full path) fits this backend's
 * actual shape without changing a component every other WP-06 page depends on. */
function FiltrationSection() {
  return (
    <>
      <FormConsole
        title="Sterile filtration - install & integrity testing"
        root="/filtration/v1"
        ops={[
          {
            path: "filters/install",
            label: "Install a filter",
            fields: [
              { name: "site_id", label: "Site ID", required: true },
              { name: "filter_serial", label: "Filter serial", required: true },
              { name: "filter_lot", label: "Filter lot" },
              { name: "filter_type", label: "Filter type" },
              { name: "manufacturer", label: "Manufacturer" },
              { name: "batch_id", label: "Batch", type: "batchSelect", hint: "Optional." },
              { name: "sterilization_cycle_id", label: "Sterilization cycle ID", hint: "Optional - the cycle that sterilized this filter." },
              { name: "housing_location", label: "Housing location" },
              { name: "direction", label: "Direction" },
            ],
          },
          {
            path: "filters/{use_id}/integrity-tests",
            label: "Record an integrity test",
            fields: [
              { name: "use_id", label: "Filter use ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "phase", label: "Phase", type: "select", required: true, options: [
                { value: "pre", label: "Pre-use" }, { value: "post", label: "Post-use" }] },
              { name: "result", label: "Result", type: "select", required: true, options: [
                { value: "pass", label: "Pass" }, { value: "fail", label: "Fail" }] },
              { name: "test_ref", label: "Test reference", type: "kv", hint: "e.g. method, instrument ID, bubble-point value." },
            ],
          },
        ]}
      />

      <FilterStatusCard />

      <SignedJsonForm
        title="Complete a filter use - signed"
        subtitle="Only a filter with a recorded post-use test can be completed."
        root="/filtration/v1"
        ops={[
          {
            postPath: "uses/{use_id}/complete",
            challengePath: "uses/{use_id}/signature-challenges",
            action: "complete",
            label: "Complete filter use",
            fields: [
              { name: "use_id", label: "Filter use ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "process_parameters", label: "Process parameters", type: "kv" },
              { name: "reason", label: "Reason" },
            ],
          },
        ]}
      />
    </>
  );
}

function FilterStatusCard() {
  const [useId, setUseId] = useState("");
  const [result, setResult] = useState<unknown>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function lookup() {
    if (!useId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.get<unknown>(`/filtration/v1/filters/${encodeURIComponent(useId.trim())}`));
    } catch (err) {
      setResult(undefined);
      setError(err instanceof Error ? err.message : "Lookup failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Filter use status" />
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Filter use ID">
          <Input value={useId} onChange={(e) => setUseId(e.target.value)} style={{ minWidth: 260 }} />
        </Field>
        <Button variant="secondary" disabled={busy || !useId.trim()} onClick={lookup}>
          <Icon name="search" /> {busy ? "Loading…" : "Look up"}
        </Button>
      </div>
      {error && <p className="error-text mt-3">{error}</p>}
      {result !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Filter use" value={result} />
        </div>
      )}
    </Card>
  );
}
