"use client";

import { useEffect, useState } from "react";
import { api, hasPermission, newIdempotencyKey, pagedFetcher, type Me, type MutationReceipt } from "@/lib/api";
import { useApiResource, useMe, useSiteId, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { useCommand } from "@/components/shared/RecordDetailShell";
import { Fact, IdFact, OpsRecordPage, type OpsRecordConfig } from "@/components/shared/OpsRecordPage";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Field } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { StatePill, WorkflowStatePill, type DesignState } from "@/components/ui/StatePill";
import { Table, EmptyState } from "@/components/ui/Table";

const PROFILE_STATE: Record<string, { state: DesignState; label: string }> = {
  RELEASED: { state: "accepted", label: "Released" },
  SUPERSEDED: { state: "na", label: "Superseded" },
};

interface AsepticOperation {
  id: string;
  site_id: string;
  area_id: string;
  // Resolved server-side (aseptic_router._resolve_operation_refs) so the UI never has to show a raw id —
  // null only when the referenced record itself couldn't be resolved.
  area_code: string | null;
  batch_id: string | null;
  batch_number: string | null;
  batch_product_name: string | null;
  batch_product_code: string | null;
  profile_version_id: string;
  profile_number: string | null;
  profile_version_no: number | null;
  state: string;
  media_fill_reference: Record<string, unknown> | null;
  qc_test_order_id: string | null;
  qc_result_id: string | null;
  requires_deviation: boolean;
  version: number;
}

// aseptic_operation.create / .intervention / .event / .complete (Document 40) — Admin + Aseptic Operator
// only per scripts/seed.py. aseptic_operation.start is a SEPARATE, deliberate SoD split: Admin + Aseptic
// Supervisor only (the operator who performs the run must not also be the one who authorizes its start).
// Audit finding 2026-09-18: this single canOperate previously covered all five transitions with one
// over-broad role list (including Operator/Supervisor, who hold none of these grants, and Aseptic
// Operator on "start", which the backend deliberately denies them), breaking the documented split at the
// UI level even though the backend still enforces it correctly.
const canOperate = (me: Me | null) => hasPermission(me, "aseptic_operation.create");
const canStart = (me: Me | null) => hasPermission(me, "aseptic_operation.start");

// Document 40's own 7-op API list has no create/release operation for the sterile process *profile*
// itself (only the *operation* that executes against one) — POST /aseptic/v1/profiles was added
// 2026-09-07, project-owner-directed, so Product Master's "Sterile process profile" picker
// (frontend/src/app/product-master/page.tsx) has more than the one seeded ASP-PROC-001 row to choose
// from. Admin + Aseptic Supervisor only (scripts/seed.py aseptic_profile_version.create) — same
// "who defines the profile vs who executes against it" split as the rest of this page.
const canCreateProfile = (me: Me | null) => hasPermission(me, "aseptic_profile_version.create");

const AREA_CLASSIFICATIONS = ["ISO_5", "ISO_6", "ISO_7", "ISO_8", "Unclassified"];

// Matches app/modules/equipment/aseptic_router.py::_profile_dict.
interface AsepticProfile {
  id: string;
  site_id: string;
  profile_number: string;
  version_no: number;
  product_id: string | null;
  required_area_classification: string | null;
  validation_reference: string | null;
  state: string;
  supersedes_profile_version_id: string | null;
  version: number;
}

function NewProfileModal({ siteId, onClose, onDone }: { siteId: string | null; onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [profileNumber, setProfileNumber] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [areaClassification, setAreaClassification] = useState(AREA_CLASSIFICATIONS[0]);
  const [validationReference, setValidationReference] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    run(() =>
      api.post<MutationReceipt>("/aseptic/v1/profiles", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        profile_number: profileNumber,
        version_no: Number(versionNo) || 1,
        required_area_classification: areaClassification || null,
        validation_reference: validationReference || null,
      })
    );
  }

  return (
    <Modal open onClose={onClose} title="New sterile process profile">
      <form onSubmit={submit}>
        <p className="hint mb-3">
          Master data - created directly as RELEASED (no draft/review stage exists for this
          record). Used as the &quot;Sterile process profile&quot; on Product Master (injectable/inhalation DDCP
          products) and as the Aseptic profile version on aseptic operations below.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Profile number" required hint="Unique together with version below, across all sites.">
            <Input value={profileNumber} onChange={(e) => setProfileNumber(e.target.value)} required autoFocus placeholder="ASP-PROC-002" />
          </Field>
          <Field label="Version no." required>
            <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Required area classification" hint="Cleanroom grade this profile requires.">
            <Select value={areaClassification} onChange={(e) => setAreaClassification(e.target.value)}>
              {AREA_CLASSIFICATIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Validation reference" hint="Optional - e.g. a media-fill/qualification protocol ID.">
            <Input value={validationReference} onChange={(e) => setValidationReference(e.target.value)} />
          </Field>
        </div>

        {error && <p className="error-text mb-2">{error}</p>}
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

/** "Update" for a RELEASED sterile process profile — this record's content is never edited in place
 * (AG-08/DATA-FR-017, same restraint as Product/Recipe Master). Superseding creates a new version (same
 * profile number, version + 1) pre-filled from the one being replaced, and marks that one SUPERSEDED —
 * it drops out of every picker but is never deleted (full history stays in the list below). */
function SupersedeProfileModal({ profile, onClose, onDone }: { profile: AsepticProfile; onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [areaClassification, setAreaClassification] = useState(profile.required_area_classification ?? AREA_CLASSIFICATIONS[0]);
  const [validationReference, setValidationReference] = useState(profile.validation_reference ?? "");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() =>
      api.post<MutationReceipt>(`/aseptic/v1/profiles/${profile.id}/supersede`, {
        idempotency_key: newIdempotencyKey(),
        previous_profile_version_id: profile.id,
        expected_version: profile.version,
        product_id: profile.product_id,
        required_area_classification: areaClassification || null,
        validation_reference: validationReference || null,
      })
    );
  }

  return (
    <Modal open onClose={onClose} title={`Supersede ${profile.profile_number} v${profile.version_no}`}>
      <form onSubmit={submit}>
        <p className="hint mb-3">
          Creates <strong>{profile.profile_number} v{profile.version_no + 1}</strong> with the fields
          below; v{profile.version_no} is marked SUPERSEDED and drops out of the Product Master picker
          (its history stays visible in the list below - it is never deleted).
        </p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Required area classification" hint="Cleanroom grade this profile requires.">
            <Select value={areaClassification} onChange={(e) => setAreaClassification(e.target.value)}>
              {AREA_CLASSIFICATIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
            <Field label="Validation reference" hint="Optional - e.g. a media-fill/qualification protocol ID.">
            <Input value={validationReference} onChange={(e) => setValidationReference(e.target.value)} />
          </Field>
        </div>

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : `Create v${profile.version_no + 1} & supersede`}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Browsable master-data list (RELEASED and SUPERSEDED) — `GET /aseptic/v1/profiles`. Separate from the
 * RELEASED-only feed Product Master's picker uses. */
function ProfileListCard({
  profiles,
  loading,
  canManage,
  onSupersede,
}: {
  profiles: AsepticProfile[] | null;
  loading: boolean;
  canManage: boolean;
  onSupersede: (profile: AsepticProfile) => void;
}) {
  return (
    <Card pad className="mb-4">
      <CardHeader title="Sterile process profiles" meta="" />
      {loading ? (
        <p className="hint">Loading…</p>
      ) : !profiles || profiles.length === 0 ? (
        <EmptyState>No sterile process profiles yet - use &quot;New sterile process profile&quot; above to add one.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Profile number</th>
              <th>Version</th>
              <th>State</th>
              <th>Area classification</th>
              <th>Validation reference</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {profiles.map((p) => (
              <tr key={p.id}>
                <td className="fs-2">{p.profile_number}</td>
                <td className="tabular fs-2">v{p.version_no}</td>
                <td>
                  <StatePill state={(PROFILE_STATE[p.state] ?? { state: "unknown" as const }).state} icon={p.state === "RELEASED" ? "check-circle" : "slash-circle"}>
                    {PROFILE_STATE[p.state]?.label ?? p.state}
                  </StatePill>
                </td>
                <td className="fs-2">{p.required_area_classification ?? "—"}</td>
                <td className="fs-2">{p.validation_reference ?? "—"}</td>
                <td style={{ textAlign: "right" }}>
                  {canManage && p.state === "RELEASED" && (
                    <Button size="sm" variant="secondary" onClick={() => onSupersede(p)}>
                      Supersede
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

// GET /sterilization/v1/items/eligible?site_id=... — real picker data for "Sterile input references",
// shared with DDCP's own "Sterilization/depyrogenation reference" (the endpoint's own docstring names
// that as its first caller). Plain array, not the paginated envelope `listAll` expects
// (`get_eligible_items` returns `list[dict]` directly). Lists exactly the two kinds the module's own
// polymorphic `get_item_status()` would report as ready — a `SterilizationLoadItem` at `sterile_status
// eligible`, or a `SterileFilterUse` at `state completed` (that second half is currently always empty in
// practice — `SterileFilterUse.state` never actually reaches literal `"completed"` in this codebase, a
// pre-existing quirk documented in `docs/testing/Sterilization_Aseptic_Comprehensive_Test_Manual_
// Gujarati.md` §14 #7 — load items are the real, working path). Local to this page only, not promoted to
// `useEntityOptions()`, since no other page needs it yet.
function useEligibleSterileItems(siteId: string | null): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    if (!siteId) return;
    let cancelled = false;
    api
      .get<{ id: string; kind: string; label: string }[]>(`/sterilization/v1/items/eligible?site_id=${siteId}`)
      .then((rows) => {
        if (cancelled) return;
        setOptions(rows.map((r) => ({ value: r.id, label: r.label })));
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  return { options, status };
}

function buildConfig(
  sterileItemOptions: EntityOption[],
  sterileItemOptionsStatus: EntityOptionsStatus,
): OpsRecordConfig<AsepticOperation> {
  return {
  title: "Aseptic operations",
  subtitle: "Aseptic processing operations: setup, live execution, interventions and completion.",
  idLabel: "Aseptic operation ID",
  apiRoot: "/aseptic/v1/operations",
  create: {
    label: "Create aseptic operation",
    can: canOperate,
    path: "/aseptic/v1/operations",
    fields: [
      { name: "area_id", label: "Area", type: "areaSelect", required: true },
      { name: "profile_version_id", label: "Aseptic profile version", type: "asepticProfileSelect", required: true },
      { name: "batch_id", label: "Batch", type: "batchSelect", hint: "Optional." },
      { name: "batch_step_id", label: "Batch step ID", hint: "Optional." },
      {
        name: "sterile_input_refs",
        label: "Sterile input references",
        type: "repeat",
        itemLabel: "Sterile input",
        hint: "The sterile components (filters, containers, …) this operation depends on - each must already be eligible.",
        subFields: [
          {
            name: "item_id", label: "Sterile item ID", required: true,
            type: "customSelect", options: sterileItemOptions, optionsStatus: sterileItemOptionsStatus,
            optionsNoun: "sterile input",
          },
        ],
      },
      { name: "media_fill_reference", label: "Media fill reference", type: "kv", hint: "Set these when this operation is a media fill run." },
    ],
    buildBody: (v, siteId) => ({
      site_id: siteId,
      area_id: v.area_id,
      profile_version_id: v.profile_version_id,
      batch_id: v.batch_id,
      batch_step_id: v.batch_step_id,
      sterile_input_refs: v.sterile_input_refs ?? [],
      media_fill_reference: Object.keys((v.media_fill_reference as object) ?? {}).length ? v.media_fill_reference : null,
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
      <Fact label="Area">{r.area_code ?? r.area_id}</Fact>
      <Fact label="Aseptic profile">
        {r.profile_number ? `${r.profile_number} v${r.profile_version_no}` : r.profile_version_id}
      </Fact>
      {r.batch_id && (
        <Fact label="Batch">
          {r.batch_number ? `${r.batch_number} - ${r.batch_product_name} (${r.batch_product_code})` : r.batch_id}
        </Fact>
      )}
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
      can: canStart,
      summary: "Starts the aseptic operation. Area, personnel and sterile-input checks must already pass.",
      buildBody: (r) => ({ operation_id: r.id, expected_version: r.version }),
    },
    {
      key: "interventions",
      label: "Record intervention",
      can: canOperate,
      summary: "Records a planned or unplanned aseptic intervention, with the impacted unit scope.",
      fields: [
        {
          name: "intervention_type", label: "Intervention type", required: true, type: "select",
          options: [
            { value: "inherent", label: "Inherent" },
            { value: "routine", label: "Routine" },
            { value: "corrective", label: "Corrective" },
            { value: "non_routine", label: "Non-routine" },
          ],
        },
        { name: "planned", label: "Planned", type: "bool", hint: "Unplanned interventions always require a reason." },
        { name: "location", label: "Location" },
        { name: "reason", label: "Reason", type: "textarea" },
        { name: "impacted_unit_scope", label: "Impacted unit scope", type: "kv" },
      ],
      buildBody: (r, v) => ({
        operation_id: r.id,
        expected_version: r.version,
        intervention_type: v.intervention_type,
        planned: v.planned === null ? true : v.planned === "true",
        location: v.location,
        reason: v.reason,
        impacted_unit_scope: Object.keys((v.impacted_unit_scope as object) ?? {}).length ? v.impacted_unit_scope : null,
      }),
    },
    {
      key: "events",
      label: "Record event",
      can: canOperate,
      summary: "Records an environmental / process event against the running operation. A critical event automatically holds the operation.",
      fields: [
        { name: "event_type", label: "Event type", required: true, placeholder: "e.g. particle_excursion, gown_breach" },
        { name: "source", label: "Source" },
        {
          name: "severity", label: "Severity", required: true, type: "select", hint: "Defaults to Info if left unset.",
          options: [
            { value: "info", label: "Info" },
            { value: "warning", label: "Warning" },
            { value: "critical", label: "Critical - holds the operation" },
          ],
        },
        { name: "payload", label: "Additional details", type: "kv" },
      ],
      buildBody: (r, v) => ({
        operation_id: r.id,
        expected_version: r.version,
        event_type: v.event_type,
        source: v.source || null,
        severity: v.severity || "info",
        payload: Object.keys((v.payload as object) ?? {}).length ? v.payload : null,
      }),
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
}

// Same shape as sterilization_router/page.tsx's own `cycleColumns`/`CycleListCard` — a dedicated "Open"
// button alongside the row's own `onRowClick` since a row that merely looks clickable is easy to miss.
function operationColumns(onOpen: (id: string) => void): DataTableColumn<AsepticOperation>[] {
  return [
    {
      key: "id",
      header: "Aseptic operation",
      sortable: true,
      render: (r) => <span className="fs-2">Aseptic op {r.id.slice(0, 8)}…</span>,
    },
    { key: "area_code", header: "Area", render: (r) => <span className="fs-2">{r.area_code ?? r.area_id}</span> },
    {
      key: "profile_number",
      header: "Aseptic profile",
      render: (r) => <span className="fs-2">{r.profile_number ? `${r.profile_number} v${r.profile_version_no}` : r.profile_version_id}</span>,
    },
    { key: "state", header: "State", sortable: true, render: (r) => <WorkflowStatePill state={r.state} /> },
    {
      key: "requires_deviation",
      header: "Requires deviation",
      render: (r) => (r.requires_deviation ? <StatePill state="failed" icon="alert-triangle">Yes</StatePill> : "No"),
    },
    {
      key: "open",
      header: "",
      align: "right",
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

function OperationListCard({ siteId, reloadToken, onOpen }: { siteId: string | null; reloadToken: number; onOpen: (id: string) => void }) {
  const fetchOperations = pagedFetcher<AsepticOperation>("/aseptic/v1/operations", () => ({ site_id: siteId ?? "" }));
  return (
    <Card pad className="mb-4">
      <CardHeader title="Aseptic operations" meta="" />
      {siteId ? (
        <DataTable
          columns={operationColumns(onOpen)}
          fetchPage={fetchOperations}
          rowKey={(r) => r.id}
          searchPlaceholder="Search state…"
          emptyMessage={<>No aseptic operations yet - use &quot;Create aseptic operation&quot; above to add one.</>}
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

export default function AsepticPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [newProfileOpen, setNewProfileOpen] = useState(false);
  const [supersedeTarget, setSupersedeTarget] = useState<AsepticProfile | null>(null);
  const {
    data: profiles,
    loading: profilesLoading,
    reload: reloadProfiles,
  } = useApiResource<AsepticProfile[]>(siteId ? `/aseptic/v1/profiles?site_id=${siteId}` : null);
  const sterileItems = useEligibleSterileItems(siteId);
  const config = buildConfig(sterileItems.options, sterileItems.status);

  return (
    <>
      <OpsRecordPage
        config={config}
        collapseCreate
        detailInModal
        hideLookup
        headerAction={
          canCreateProfile(me) ? (
            <Button variant="secondary" onClick={() => setNewProfileOpen(true)}>
              <Icon name="plus" /> New sterile process profile
            </Button>
          ) : undefined
        }
        afterHeader={(openRecord) => (
          <>
            <ProfileListCard
              profiles={profiles}
              loading={profilesLoading}
              canManage={canCreateProfile(me)}
              onSupersede={setSupersedeTarget}
            />
            <OperationListCard siteId={siteId} reloadToken={reloadToken} onOpen={openRecord} />
          </>
        )}
        onCreated={() => setReloadToken((n) => n + 1)}
      />
      {newProfileOpen && (
        <NewProfileModal
          siteId={siteId}
          onClose={() => setNewProfileOpen(false)}
          onDone={() => {
            setNewProfileOpen(false);
            reloadProfiles();
          }}
        />
      )}
      {supersedeTarget && (
        <SupersedeProfileModal
          profile={supersedeTarget}
          onClose={() => setSupersedeTarget(null)}
          onDone={() => {
            setSupersedeTarget(null);
            reloadProfiles();
          }}
        />
      )}
    </>
  );
}
