"use client";

import { useState } from "react";
import { hasPermission, pagedFetcher, type Me } from "@/lib/api";
import { useSiteId } from "@/lib/hooks";
import { Fact, IdFact, OpsRecordPage, type OpsRecordConfig } from "@/components/shared/OpsRecordPage";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";

interface LineClearanceRecord {
  id: string;
  site_id: string;
  area_id: string | null;
  area_code: string | null;
  previous_batch_id: string | null;
  previous_batch_number: string | null;
  next_batch_id: string | null;
  next_batch_number: string | null;
  items: unknown;
  critical: boolean;
  state: string;
  expiry_at: string | null;
  version: number;
}

// Document 39 (SPEC-EQP-002): same actor class as cleaning execution, and every role that can create a
// cleaning execution also holds line_clearance.create/.complete in scripts/seed.py's ROLE_PERMISSIONS.
// line_clearance.create/.complete share one grant.
const canClear = (me: Me | null) => hasPermission(me, "line_clearance.create");

const config: OpsRecordConfig<LineClearanceRecord> = {
  title: "Line clearance",
  subtitle:
 "Confirm an equipment area is clear of the previous batch and its materials before the next one starts the check DDCP batch readiness (“Line clearance state is NOT_STARTED”) and Packaging both depend on, previously reachable only via direct API call.",
  idLabel: "Line clearance ID",
  apiRoot: "/line-clearance/v1",
  create: {
    label: "Start line clearance",
    can: canClear,
    path: "/line-clearance/v1",
    fields: [
      {
        name: "area_id", label: "Equipment area / line", type: "areaSelect", required: true,
 hint: "The area this clearance covers the same area a batch readiness check (DDCP, Packaging, …) looks up by id.",
      },
      { name: "previous_batch_id", label: "Previous batch", type: "batchSelect", hint: "The batch/product being cleared out of this area, if known." },
      { name: "next_batch_id", label: "Next batch", type: "batchSelect", hint: "The batch about to use this area, if known yet." },
      { name: "checklist_version", label: "Checklist / procedure version", placeholder: "e.g. LC-CHK-001", hint: "Reference to the line-clearance checklist or procedure version used." },
      {
        name: "items", label: "Checklist items", type: "repeat", itemLabel: "item",
        hint: "Optional. Only “Equipment” items are cross-checked automatically completing this clearance as Pass will fail if any listed equipment asset isn't currently qualified, calibrated and clean.",
        subFields: [
          {
            name: "item_type", label: "Item type", type: "select", required: true,
            options: [{ value: "material", label: "Material" }, { value: "label", label: "Label" }, { value: "equipment", label: "Equipment" }],
          },
          { name: "equipment_id", label: "Equipment asset (if item type is Equipment)", type: "equipmentSelect" },
        ],
      },
      { name: "critical", label: "Critical clearance", type: "bool", hint: "A critical clearance requires a reason when it's completed." },
    ],
    buildBody: (v, siteId) => ({
      site_id: siteId,
      area_id: v.area_id || null,
      previous_batch_id: v.previous_batch_id || null,
      next_batch_id: v.next_batch_id || null,
      checklist_version: v.checklist_version || null,
      items: Array.isArray(v.items) && (v.items as unknown[]).length > 0 ? v.items : null,
      critical: v.critical === "true",
    }),
  },
  stateOf: (r) => r.state,
  numberOf: (r) => `Line clearance ${r.id.slice(0, 8)}…`,
  facts: (r) => (
    <>
 <Fact label="Expiry">{r.expiry_at ? new Date(r.expiry_at).toLocaleString() : ""}</Fact>
      <Fact label="Critical">{r.critical ? "Yes" : "No"}</Fact>
      <Fact label="Record version">{r.version}</Fact>
      {r.area_code ? <Fact label="Area">{r.area_code}</Fact> : <IdFact label="Area" value={r.area_id} />}
      {r.previous_batch_number ? <Fact label="Previous batch">{r.previous_batch_number}</Fact> : <IdFact label="Previous batch" value={r.previous_batch_id} />}
      {r.next_batch_number ? <Fact label="Next batch">{r.next_batch_number}</Fact> : <IdFact label="Next batch" value={r.next_batch_id} />}
    </>
  ),
  transitions: [
    {
      key: "complete",
      label: "Complete (sign)",
      signed: true,
      challengeAction: "complete",
      variant: "primary",
      can: canClear,
      show: (r) => r.state === "IN_PROGRESS" || r.state === "VERIFICATION_PENDING",
      summary:
      "Attests the area has been cleared of the previous batch's identity and materials. Passing sets the area's clearance state to CLEARED (what downstream readiness checks look for); failing resets it to NOT_STARTED.",
      fields: [
        {
          name: "passed", label: "Result", required: true, type: "select",
 options: [{ value: "true", label: "Pass area is clear" }, { value: "false", label: "Fail not clear" }],
        },
 { name: "expiry_at", label: "Expiry (optional)", placeholder: "e.g. 2026-09-10T08:00:00Z", hint: "ISO datetime leave blank for no expiry. Past this time the clearance reads as EXPIRED even if it was CLEARED." },
        { name: "reason", label: "Reason", hint: "Required if this clearance was flagged critical when it was started." },
      ],
      buildBody: (r, v) => ({
        clearance_id: r.id,
        expected_version: r.version,
        passed: v.passed === "true",
        expiry_at: (v.expiry_at as string) || null,
        reason: (v.reason as string) || null,
      }),
    },
  ],
};

function clearanceColumns(onOpen: (id: string) => void): DataTableColumn<LineClearanceRecord>[] {
  return [
    {
      key: "id",
      header: "Line clearance",
      render: (r) => <span className="fs-2">Line clearance {r.id.slice(0, 8)}…</span>,
    },
    { key: "area_code", header: "Area", render: (r) => <span className="fs-2">{r.area_code ?? r.area_id ?? "—"}</span> },
    {
      key: "previous_batch",
      header: "Previous batch",
      render: (r) => <span className="fs-2">{r.previous_batch_number ?? r.previous_batch_id ?? "—"}</span>,
    },
    {
      key: "next_batch",
      header: "Next batch",
      render: (r) => <span className="fs-2">{r.next_batch_number ?? r.next_batch_id ?? "—"}</span>,
    },
    { key: "state", header: "State", sortable: true, render: (r) => <WorkflowStatePill state={r.state} /> },
    {
      key: "critical",
      header: "Critical",
      render: (r) => (r.critical ? <StatePill state="failed" icon="alert-triangle">Critical</StatePill> : "No"),
    },
    {
      key: "open",
      header: "",
      align: "right",
      // A dedicated button alongside the row's own onRowClick — a row that merely looks clickable is
      // easy to miss; a plain button is not.
      render: (r) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(r.id);
          }}
        >
          Open
        </Button>
      ),
    },
  ];
}

function ClearanceListCard({ siteId, reloadToken, onOpen }: { siteId: string | null; reloadToken: number; onOpen: (id: string) => void }) {
  const fetchClearances = pagedFetcher<LineClearanceRecord>("/line-clearance/v1", () => ({ site_id: siteId ?? "" }));
  return (
    <Card pad className="mb-4">
      <CardHeader title="Line clearances" meta="" />
      {siteId ? (
        <DataTable
          columns={clearanceColumns(onOpen)}
          fetchPage={fetchClearances}
          rowKey={(r) => r.id}
          searchPlaceholder="Search state…"
          emptyMessage={<>No line clearances yet - use &quot;Start line clearance&quot; above to add one.</>}
          defaultSort={{ by: "created_at", dir: "desc" }}
          onRowClick={(r) => onOpen(r.id)}
          reloadToken={reloadToken}
        />
      ) : (
        <p className="hint mt-2">Loading…</p>
      )}
    </Card>
  );
}

export default function LineClearancePage() {
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);

  return (
    <OpsRecordPage
      config={config}
      collapseCreate
      detailInModal
      hideLookup
      afterHeader={(openRecord) => (
        <ClearanceListCard siteId={siteId} reloadToken={reloadToken} onOpen={openRecord} />
      )}
      onCreated={() => setReloadToken((n) => n + 1)}
    />
  );
}
