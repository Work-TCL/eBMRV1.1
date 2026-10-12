"use client";

import { useEffect, useRef, useState } from "react";
import { api, hasPermission, newIdempotencyKey, pagedFetcher, type Me, type MutationReceipt, type Paged } from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { useCommand } from "@/components/shared/RecordDetailShell";
import { Fact, OpsRecordPage, type OpsRecordConfig } from "@/components/shared/OpsRecordPage";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";
import { KeyValueRows, buildKvObject, type KvRow } from "@/components/shared/RepeatableFields";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Skeleton, TableSkeleton } from "@/components/ui/Skeleton";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { Table, EmptyState } from "@/components/ui/Table";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FactGrid } from "@/components/ui/FactGrid";
import { humanizeLabel } from "@/lib/format";

const PROCESS_TYPES = [
  "steam_autoclave", "dry_heat", "depyrogenation", "gas", "radiation", "external_reference", "SIP", "CIP", "sterile_filtration",
];

// Document 42's own 9-op API list has no create operation for the cycle *profile* itself (only the
// *cycle* that runs against one) — POST /sterilization/v1/profiles was added 2026-09-16 (SG-203),
// project-owner-directed: asked directly who should author a profile's critical parameters, chosen as
// QA Reviewer rather than Sterilization Operator specifically so the role that later independently
// reviews a cycle's data is not the same role that could have authored the spec it's reviewed against
// (scripts/seed.py process_cycle_profile_version.create) — same "who defines vs who executes" split as
// aseptic's own canCreateProfile.
const canCreateCycleProfile = (me: Me | null) => hasPermission(me, "process_cycle_profile_version.create");

// Matches app/modules/equipment/sterilization_router.py::_profile_summary_dict.
interface CycleProfile {
  id: string;
  profile_number: string;
  version: number;
  process_type: string;
  state: string;
  sterile_status_validity_hours: number | null;
}

function NewCycleProfileModal({ siteId, onClose, onDone }: { siteId: string | null; onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [profileNumber, setProfileNumber] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [processType, setProcessType] = useState(PROCESS_TYPES[0]);
  const [validationReference, setValidationReference] = useState("");
  const [validityHours, setValidityHours] = useState("");
  const [criticalParameters, setCriticalParameters] = useState<KvRow[]>([]);
  const [indicatorRequirements, setIndicatorRequirements] = useState<KvRow[]>([]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    run(() =>
      api.post<MutationReceipt>("/sterilization/v1/profiles", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        profile_number: profileNumber,
        version_no: Number(versionNo) || 1,
        process_type: processType,
        validation_reference: validationReference || null,
        sterile_status_validity_hours: validityHours.trim() ? Number(validityHours) : null,
        critical_parameters: criticalParameters.length ? buildKvObject(criticalParameters) : null,
        indicator_requirements: indicatorRequirements.length ? buildKvObject(indicatorRequirements) : null,
      })
    );
  }

  return (
    <Modal open onClose={onClose} title="New sterilization cycle profile">
      <form onSubmit={submit}>
        <p className="hint mb-3">
          Master data - created directly as RELEASED (no draft/review stage exists for this record,
          same shape as the Aseptic module&apos;s own sterile process profile). Used as the &quot;Cycle
          profile version&quot; a real process cycle (above) runs against.
        </p>
        <p className="hint mb-3">
          <strong>Not the same record</strong> as Product Master&apos;s &quot;Sterile process
          profile&quot; field - that one is authored on the <strong>Aseptic</strong> page
          (<code>/aseptic</code> - &quot;New sterile process profile&quot;) and lives in a different
          table. A profile created here only appears in this page&apos;s own &quot;Cycle profile
          version&quot; picker, never in Product Master&apos;s dropdown.
        </p>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Profile number" required hint="Unique together with version below, across all sites.">
            <Input value={profileNumber} onChange={(e) => setProfileNumber(e.target.value)} required autoFocus placeholder="STR-PROC-002" />
          </Field>
          <Field label="Version no." required>
            <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
          </Field>
          <Field label="Process type" required>
            <Select value={processType} onChange={(e) => setProcessType(e.target.value)}>
              {PROCESS_TYPES.map((t) => (
                <option key={t} value={t}>
                  {humanizeLabel(t)}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Validation reference" hint="Optional - e.g. a PQ/qualification protocol ID.">
            <Input value={validationReference} onChange={(e) => setValidationReference(e.target.value)} />
          </Field>
          <Field label="Sterile status validity (hours)" hint="Optional - how long a load item stays 'eligible' after an ACCEPTED cycle, e.g. 720 for 30 days.">
            <Input type="number" min={0} value={validityHours} onChange={(e) => setValidityHours(e.target.value)} />
          </Field>
        </div>
        <KeyValueRows
          label="Critical parameters"
          hint="Optional - free-form key/value only (e.g. temperature_c → 121.5). A nested shape like {min, target} per parameter can't be entered here - use the raw API for that, this editor only produces flat values."
          value={criticalParameters}
          onChange={setCriticalParameters}
        />
        <KeyValueRows
          label="Indicator requirements"
          hint="Optional - e.g. biological_indicator → required."
          value={indicatorRequirements}
          onChange={setIndicatorRequirements}
        />

        {error && <p className="error-text mb-2 mt-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !siteId || !profileNumber.trim()}>
            {busy ? "Saving…" : "Create profile"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CycleProfileListCard({ profiles, loading }: { profiles: CycleProfile[] | null; loading: boolean }) {
  return (
    <Card pad className="mb-4">
      <CardHeader title="Sterilization cycle profiles" meta="" />
      {loading ? (
        <p className="hint">Loading…</p>
      ) : !profiles || profiles.length === 0 ? (
        <EmptyState>No sterilization cycle profiles yet - use &quot;New sterilization cycle profile&quot; above to add one.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Profile number</th>
              <th>Version</th>
              <th>Process type</th>
              <th>State</th>
              <th>Sterile status validity</th>
            </tr>
          </thead>
          <tbody>
            {profiles.map((p) => (
              <tr key={p.id}>
                <td className="fs-2">{p.profile_number}</td>
                <td className="tabular fs-2">v{p.version}</td>
                <td className="fs-2">{p.process_type}</td>
                <td>
                  <StatePill state={p.state === "RELEASED" ? "accepted" : "unknown"} icon={p.state === "RELEASED" ? "check-circle" : "slash-circle"}>
                    {p.state}
                  </StatePill>
                </td>
                <td className="fs-2">{p.sterile_status_validity_hours != null ? `${p.sterile_status_validity_hours} h` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

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

// process_cycle.create / .start (Document 42) — Admin, QA Reviewer, Sterilization Operator per
// scripts/seed.py. Audit finding 2026-09-18: this previously included Operator/Supervisor (who hold no
// process_cycle.* grant at all — silent 403) and omitted QA Reviewer (who does hold it — hidden feature,
// SG-204 bug class). "Record cycle data" shares process_cycle.start's own backend check
// (sterilization_router.py post_record_data), so the same role set applies there too.
const canOperate = (me: Me | null) => hasPermission(me, "process_cycle.create");
const canReview = (me: Me | null) => hasPermission(me, "process_cycle.review");
// sterile_filter_use.create / .complete (Document 42) — Admin + Sterilization Operator only. Audit
// finding 2026-09-18: FiltrationSection below had no role gate at all.
const canOperateFilter = (me: Me | null) => hasPermission(me, "sterile_filter_use.create");

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
  const { me, loading: meLoading } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [newProfileOpen, setNewProfileOpen] = useState(false);
  const [installOpen, setInstallOpen] = useState(false);
  const [completeOpen, setCompleteOpen] = useState(false);
  const [openUseId, setOpenUseId] = useState<string | null>(null);
  const [filterReloadToken, setFilterReloadToken] = useState(0);
  const {
    data: cycleProfilesPage,
    loading: profilesLoading,
    reload: reloadProfiles,
  } = useApiResource<Paged<CycleProfile>>("/sterilization/v1/profiles?state=&page_size=100");
  const cycleProfiles = cycleProfilesPage?.items ?? null;

  // Deep link from the Workflow Actions bell (`?cycle_id=<uuid>`) -- same `window.location.search`
  // shape as cleaning/page.tsx's own deep link. `openRecord` is captured in a ref during render (it
  // isn't itself stable across renders) rather than read from a dependency array; by the time this
  // mount-only effect runs, the ref is already populated (afterHeader runs during the child's render,
  // which commits before this effect fires).
  const cycleOpenerRef = useRef<(id: string) => void>(() => {});
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const linkedCycleId = params.get("cycle_id");
    if (linkedCycleId) cycleOpenerRef.current(linkedCycleId);
  }, []);

  return (
    <div>
      <OpsRecordPage
        config={config}
        collapseCreate
        detailInModal
        hideLookup
        headerAction={
          meLoading ? (
            <div className="flex gap-2">
              {[200, 170].map((w, i) => (
                <Skeleton key={i} width={w} height={36} radius="var(--radius-md)" />
              ))}
            </div>
          ) : (
            <>
              {canCreateCycleProfile(me) && (
                <Button variant="secondary" onClick={() => setNewProfileOpen(true)}>
                  <Icon name="plus" /> New sterilization cycle profile
                </Button>
              )}
              {canOperateFilter(me) && (
                <>
                  <Button variant="secondary" onClick={() => setInstallOpen(true)}>
                    <Icon name="plus" /> Install / integrity test
                  </Button>
                  <Button variant="primary" onClick={() => setCompleteOpen(true)}>
                    <Icon name="pen-line" /> Complete a filter use
                  </Button>
                </>
              )}
            </>
          )
        }
        afterHeader={(openRecord) => {
          cycleOpenerRef.current = openRecord;
          return (
            <>
              <CycleProfileListCard profiles={cycleProfiles} loading={profilesLoading} />
              <CycleListCard siteId={siteId} reloadToken={reloadToken} onOpen={openRecord} />
            </>
          );
        }}
        onCreated={() => setReloadToken((n) => n + 1)}
      />
      {newProfileOpen && (
        <NewCycleProfileModal
          siteId={siteId}
          onClose={() => setNewProfileOpen(false)}
          onDone={() => {
            setNewProfileOpen(false);
            reloadProfiles();
          }}
        />
      )}
      {meLoading ? (
        <Card>
          <CardHeader title="Sterile filter uses" meta="" />
          <TableSkeleton columns={[{ header: "Filter" }, { header: "Area" }, { header: "Installed" }, { header: "Status" }, { header: "" }]} />
        </Card>
      ) : (
        canOperateFilter(me) && (
        <FiltrationSection
          siteId={siteId}
          installOpen={installOpen}
          setInstallOpen={setInstallOpen}
          completeOpen={completeOpen}
          setCompleteOpen={setCompleteOpen}
          openUseId={openUseId}
          setOpenUseId={setOpenUseId}
          reloadToken={filterReloadToken}
          bumpReloadToken={() => setFilterReloadToken((n) => n + 1)}
        />
        )
      )}
    </div>
  );
}

// Matches app/modules/equipment/sterilization_router.py::_filter_use_dict (list-row subset).
interface FilterUse {
  id: string;
  site_id: string;
  filter_lot: string | null;
  filter_serial: string;
  filter_type: string | null;
  manufacturer: string | null;
  batch_id: string | null;
  batch_number: string | null;
  batch_product_name: string | null;
  batch_product_code: string | null;
  sterilization_cycle_id: string | null;
  sterilization_cycle_label: string | null;
  housing_location: string | null;
  direction: string | null;
  installed_by_user_id: string | null;
  installed_by_full_name: string | null;
  installed_by_username: string | null;
  installed_at: string | null;
  state: string;
  pre_use_integrity_result: string | null;
  pre_use_integrity_ref: Record<string, unknown> | null;
  post_use_integrity_result: string | null;
  post_use_integrity_ref: Record<string, unknown> | null;
  process_parameters: Record<string, unknown> | null;
  reuse_count: number;
  performer_user_id: string | null;
  performer_full_name: string | null;
  performer_username: string | null;
  requires_deviation: boolean;
  deviation_reference_id: string | null;
  deviation_number: string | null;
  version: number;
  created_at: string;
}

function filterUseColumns(onOpen: (id: string) => void): DataTableColumn<FilterUse>[] {
  return [
    {
      key: "filter_serial",
      header: "Filter serial",
      sortable: true,
      render: (u) => <span className="fs-2 font-semibold">{u.filter_serial}</span>,
    },
    { key: "filter_type", header: "Type", render: (u) => <span className="fs-2">{u.filter_type ?? "—"}</span> },
    { key: "state", header: "State", sortable: true, render: (u) => <WorkflowStatePill state={u.state} /> },
    {
      key: "integrity",
      header: "Integrity (pre / post)",
      render: (u) => (
        <span className="fs-2">
          {u.pre_use_integrity_result ?? "—"} / {u.post_use_integrity_result ?? "—"}
        </span>
      ),
    },
    {
      key: "open",
      header: "",
      align: "right",
      render: (u) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(u.id);
          }}
        >
          Open
        </Button>
      ),
    },
  ];
}

function FilterUseListCard({ reloadToken, onOpen }: { reloadToken: number; onOpen: (id: string) => void }) {
  const fetchUses = pagedFetcher<FilterUse>("/filtration/v1/filters");
  return (
    <Card pad className="mb-4">
      <CardHeader title="Sterile filter uses" meta="" />
      <DataTable
        columns={filterUseColumns(onOpen)}
        fetchPage={fetchUses}
        rowKey={(u) => u.id}
        searchPlaceholder="Search filter serial…"
        emptyMessage='No sterile filter uses yet - use "Install / integrity test" above to add one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={(u) => onOpen(u.id)}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

function FilterUseDetailModal({ useId, onClose }: { useId: string; onClose: () => void }) {
  const [result, setResult] = useState<FilterUse | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<FilterUse>(`/filtration/v1/filters/${encodeURIComponent(useId)}`)
      .then((r) => {
        if (!cancelled) setResult(r);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Load failed");
      });
    return () => {
      cancelled = true;
    };
  }, [useId]);

  return (
    <Modal open onClose={onClose} title="Sterile filter use" large>
      {error && <p className="error-text">{error}</p>}
      {result ? (
        <>
          <FactGrid>
            <Fact label="Filter serial">{result.filter_serial}</Fact>
            <Fact label="Filter type">{result.filter_type ?? "—"}</Fact>
            <Fact label="Filter lot">{result.filter_lot ?? "—"}</Fact>
            <Fact label="Manufacturer">{result.manufacturer ?? "—"}</Fact>
            {result.batch_id && (
              <Fact label="Batch">
                {result.batch_number ? `${result.batch_number} - ${result.batch_product_name} (${result.batch_product_code})` : result.batch_id}
              </Fact>
            )}
            {result.sterilization_cycle_id && (
              <Fact label="Sterilization cycle">{result.sterilization_cycle_label ?? result.sterilization_cycle_id}</Fact>
            )}
            <Fact label="Housing location">{result.housing_location ?? "—"}</Fact>
            <Fact label="Direction">{result.direction ?? "—"}</Fact>
            <Fact label="State">
              <WorkflowStatePill state={result.state} />
            </Fact>
            <Fact label="Pre-use integrity">{result.pre_use_integrity_result ?? "—"}</Fact>
            <Fact label="Post-use integrity">{result.post_use_integrity_result ?? "—"}</Fact>
            <Fact label="Reuse count">{result.reuse_count}</Fact>
            {result.installed_by_full_name && (
              <Fact label="Installed by">{`${result.installed_by_full_name} (${result.installed_by_username})`}</Fact>
            )}
            {result.performer_full_name && (
              <Fact label="Completed by">{`${result.performer_full_name} (${result.performer_username})`}</Fact>
            )}
            <Fact label="Requires deviation">{result.requires_deviation ? "Yes" : "No"}</Fact>
            {result.deviation_reference_id && (
              <Fact label="Deviation">{result.deviation_number ?? result.deviation_reference_id}</Fact>
            )}
            <Fact label="Record version">{result.version}</Fact>
          </FactGrid>
          <JsonPanel title="Pre-use integrity reference" value={result.pre_use_integrity_ref} />
          <JsonPanel title="Post-use integrity reference" value={result.post_use_integrity_ref} />
          <JsonPanel title="Process parameters" value={result.process_parameters} />
        </>
      ) : (
        !error && <p className="hint">Loading…</p>
      )}
    </Modal>
  );
}

/** Document 42 sterile-filtration integrity — `app/modules/equipment/sterilization_router.py`'s
 * `filtration_router`. Not folded into `OpsRecordPage`'s `config` above: install/get/integrity-tests
 * live under `/filtration/v1/filters/...` but the signature-challenge and complete mutation live under
 * `/filtration/v1/uses/...` (verified in router.py — same underlying `SterileFilterUse` row, two path
 * prefixes) — `OpsRecordPage` assumes one `apiRoot` for every record-scoped action, so a plain
 * `FormConsole` + `SignedJsonForm` pair (each free to declare its own full path) fits this backend's
 * actual shape without changing a component every other WP-06 page depends on.
 *
 * "Install / integrity test" and "Complete a filter use" are triggered from the page's own header
 * (alongside "New sterilization cycle profile") rather than a separate buttons-in-a-card here, so their
 * open/close state is owned by `SterilizationPage` and passed down — this component only renders the
 * list + the two popups + the per-row detail popup. The former by-id "Filter use status" lookup card is
 * replaced by that real browsable list. Neither `FormConsole` nor `SignedJsonForm` expose a success
 * callback, so the list is refreshed on modal close (the best available signal) rather than on the
 * mutation's own success. */
function FiltrationSection({
  siteId,
  installOpen,
  setInstallOpen,
  completeOpen,
  setCompleteOpen,
  openUseId,
  setOpenUseId,
  reloadToken,
  bumpReloadToken,
}: {
  siteId: string | null;
  installOpen: boolean;
  setInstallOpen: (v: boolean) => void;
  completeOpen: boolean;
  setCompleteOpen: (v: boolean) => void;
  openUseId: string | null;
  setOpenUseId: (id: string | null) => void;
  reloadToken: number;
  bumpReloadToken: () => void;
}) {
  return (
    <>
      <FilterUseListCard reloadToken={reloadToken} onOpen={setOpenUseId} />

      {installOpen && (
        <Modal
          open
          onClose={() => {
            setInstallOpen(false);
            bumpReloadToken();
          }}
          title="Sterile filtration - install & integrity testing"
          large
        >
          <FormConsole
            title="Sterile filtration - install & integrity testing"
            root="/filtration/v1"
            ops={[
              {
                path: "filters/install",
                label: "Install a filter",
                fields: [
                  { name: "site_id", label: "Site", type: "siteSelect", required: true, default: siteId ?? undefined },
                  { name: "filter_serial", label: "Filter serial", required: true },
                  { name: "filter_lot", label: "Filter lot" },
                  { name: "filter_type", label: "Filter type" },
                  { name: "manufacturer", label: "Manufacturer" },
                  { name: "batch_id", label: "Batch", type: "batchSelect", hint: "Optional." },
                  {
                    name: "sterilization_cycle_id", label: "Sterilization cycle", type: "sterilizationCycleSelect",
                    hint: "Optional - the cycle that sterilized this filter.",
                  },
                  { name: "housing_location", label: "Housing location" },
                  { name: "direction", label: "Direction" },
                ],
              },
              {
                path: "filters/{use_id}/integrity-tests",
                label: "Record an integrity test",
                fields: [
                  { name: "use_id", label: "Filter use", type: "filterUseSelect", required: true },
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
        </Modal>
      )}

      {completeOpen && (
        <Modal
          open
          onClose={() => {
            setCompleteOpen(false);
            bumpReloadToken();
          }}
          title="Complete a filter use"
          large
        >
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
                  { name: "use_id", label: "Filter use", type: "filterUseSelect", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "process_parameters", label: "Process parameters", type: "kv" },
                  { name: "reason", label: "Reason" },
                ],
              },
            ]}
          />
        </Modal>
      )}

      {openUseId && <FilterUseDetailModal useId={openUseId} onClose={() => setOpenUseId(null)} />}
    </>
  );
}
