"use client";

import { use, useState } from "react";
import {
  api,
  ApiError,
  canCalibrateEquipment,
  canHoldEquipment,
  canMaintainEquipment,
  canReturnEquipmentToService,
  canCreateEquipment,
  canOperateEvidence,
  downloadEvidence,
  formatDate,
  formatDateTime,
  newIdempotencyKey,
  type EquipmentAsset,
  type Me,
  type MutationReceipt,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe } from "@/lib/hooks";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { Banner } from "@/components/ui/Banner";
import { Button, LinkButton } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";

interface Eligibility {
  asset_id: string;
  state: string;
  eligible: boolean;
  reasons: { code: string; message: string }[];
}

interface Calibration {
  id: string;
  due_date: string;
  performed_date: string | null;
  result: string;
  standard_reference: string | null;
  standard_calibration_status: string | null;
  standard_expiry_date: string | null;
  calibration_type: string;
  provider_name: string | null;
  certificate_reference: string | null;
  as_found: Record<string, unknown> | null;
  adjustments: Record<string, unknown> | null;
  as_left: Record<string, unknown> | null;
  impact_assessment_required: boolean;
  performer_user_id: string | null;
}

interface WorkOrder {
  id: string;
  type: string | null;
  state: string;
  started_at: string;
  fault_description: string | null;
  diagnosis: string | null;
  work_performed: string | null;
  parts_used: Record<string, unknown> | null;
  procedure_version: string | null;
  frequency_days: number | null;
  next_due_date: string | null;
  expected_downtime_hours: string | null;
  actual_downtime_hours: string | null;
  post_maintenance_verification_required: boolean;
  verified_at: string | null;
  technician_user_id: string;
}

interface History {
  asset_id: string;
  calibrations: Calibration[];
  maintenance_work_orders: WorkOrder[];
  use_log: { id: string; log_type: string; occurred_at: string }[];
}

type PendingAction = "qualification" | "calibration" | "maintenance" | "hold" | "return_to_service";

export default function EquipmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<PendingAction | null>(null);

  const asset = useApiResource<EquipmentAsset>(`/equipment/v1/assets/${id}`);
  const eligibility = useApiResource<Eligibility>(`/equipment/v1/${id}/eligibility`);
  const history = useApiResource<History>(`/equipment/v1/${id}/history`);

  function reloadAll() {
    asset.reload();
    eligibility.reload();
    history.reload();
  }

  if (asset.error) {
    return (
      <div>
        <PageHead title="Equipment asset" />
        <Banner tone="critical" title="Could not load this asset">
          {asset.error}
        </Banner>
        <LinkButton href="/equipment" variant="secondary">
          <Icon name="arrow-left" /> Back to equipment
        </LinkButton>
      </div>
    );
  }

  if (!asset.data) {
    return (
      <div>
        <PageHead title="Equipment asset" subtitle="Loading…" />
      </div>
    );
  }

  const a = asset.data;

  return (
    <div>
      <PageHead
        title={
          <span className="flex items-center gap-3">
            {a.equipment_code} <WorkflowStatePill state={a.state} />
          </span>
        }
        subtitle={[a.manufacturer, a.model, a.serial_no && `S/N ${a.serial_no}`].filter(Boolean).join(" · ")}
        action={
          <div className="flex gap-2">
            <LinkButton href="/equipment" variant="secondary">
              <Icon name="arrow-left" /> Back
            </LinkButton>
            {canCreateEquipment(me) && (
              <Button variant="secondary" onClick={() => setPending("qualification")}>
                Record qualification
              </Button>
            )}
            {canCalibrateEquipment(me) && (
              <Button variant="secondary" onClick={() => setPending("calibration")}>
                Record calibration
              </Button>
            )}
            {canMaintainEquipment(me) && (
              <Button variant="secondary" onClick={() => setPending("maintenance")}>
                Record maintenance
              </Button>
            )}
            {a.hold_flag
              ? canReturnEquipmentToService(me) && (
                  <Button variant="success" onClick={() => setPending("return_to_service")}>
                    Return to service
                  </Button>
                )
              : canHoldEquipment(me) && (
                  <Button variant="danger" onClick={() => setPending("hold")}>
                    <Icon name="lock" /> Place on hold
                  </Button>
                )}
          </div>
        }
      />

      {a.hold_flag && (
        <Banner tone="critical" title="This asset is on hold" icon="lock">
          {a.hold_reason ?? "No reason recorded."}
          {a.hold_source ? ` (source: ${a.hold_source})` : ""}
        </Banner>
      )}

      {eligibility.data && !eligibility.data.eligible && (
        <Banner tone="warn" title="Not eligible for use">
          {eligibility.data.reasons.map((r) => r.message).join(" · ")}
        </Banner>
      )}
      {eligibility.data?.eligible && (
        <Banner tone="ok" title="Eligible for use">
          Qualification, calibration, maintenance and cleanliness all satisfy the use gate.
        </Banner>
      )}

      <Card pad className="mb-4">
        <FactGrid>
          <Fact label="State">
            <WorkflowStatePill state={a.state} />
          </Fact>
          <Fact label="Qualification">{a.qualification_status ?? "—"}</Fact>
          <Fact label="Calibration">{a.calibration_status ?? "—"}</Fact>
          <Fact label="Calibration due">{formatDate(a.next_calibration_due_date)}</Fact>
          <Fact label="Maintenance">{a.maintenance_status ?? "—"}</Fact>
          <Fact label="Maintenance due">{formatDate(a.next_maintenance_due_date)}</Fact>
          <Fact label="Cleanliness">{a.cleanliness_status ?? "—"}</Fact>
          <Fact label="Dedicated">{a.dedicated ? "Yes" : "No"}</Fact>
          <Fact label="Firmware">{a.firmware_version ?? "—"}</Fact>
          <Fact label="Record version">{a.version}</Fact>
          <IdFact label="Asset ID" value={a.id} />
        </FactGrid>
      </Card>

      <Tabs
        tabs={[
          {
            id: "calibration",
            label: "Calibrations",
            badge: history.data?.calibrations.length,
            content: <CalibrationTab calibrations={history.data?.calibrations ?? []} />,
          },
          {
            id: "maintenance",
            label: "Maintenance",
            badge: history.data?.maintenance_work_orders.length,
            content: (
              <MaintenanceTab
                workOrders={history.data?.maintenance_work_orders ?? []}
                asset={a}
                me={me}
                onDone={reloadAll}
              />
            ),
          },
          {
            id: "use",
            label: "Use log",
            badge: history.data?.use_log.length,
            content: <UseLogTab entries={history.data?.use_log ?? []} />,
          },
          {
            id: "eligibility",
            label: "Eligibility",
            content: <EligibilityTab eligibility={eligibility.data} />,
          },
          {
            id: "documents",
            label: "Documents",
            content: <DocumentsTab assetId={a.id} me={me} />,
          },
        ]}
      />

      {pending && (
        <ActionModal
          asset={a}
          action={pending}
          onClose={() => setPending(null)}
          onDone={() => {
            setPending(null);
            reloadAll();
          }}
        />
      )}
    </div>
  );
}

function CalibrationTab({ calibrations }: { calibrations: Calibration[] }) {
  if (calibrations.length === 0) {
    return <EmptyState icon="gauge">No calibration events recorded for this asset.</EmptyState>;
  }
  return (
    <Card>
      <CardHeader title="Calibration history" meta={`${calibrations.length} event(s)`} />
      <Table>
        <thead>
          <tr>
            <th>Performed</th>
            <th>Due</th>
            <th>Result</th>
            <th>Standard</th>
            <th>Impact assessment</th>
          </tr>
        </thead>
        <tbody>
          {calibrations.map((c) => (
            <tr key={c.id}>
              <td className="tabular">{formatDate(c.performed_date)}</td>
              <td className="tabular">{formatDate(c.due_date)}</td>
              <td>
                <StatePill
                  state={c.result?.toLowerCase() === "pass" ? "accepted" : "failed"}
                  icon={c.result?.toLowerCase() === "pass" ? "check-circle" : "x"}
                >
                  {c.result}
                </StatePill>
              </td>
              <td className="fs-2">
                {c.standard_reference ?? "—"}
                {c.standard_expiry_date && (
                  <span className="text-muted"> · expires {formatDate(c.standard_expiry_date)}</span>
                )}
              </td>
              <td>
                {c.impact_assessment_required ? (
                  <StatePill state="conflict" icon="alert-triangle">
                    Required
                  </StatePill>
                ) : (
                  <span className="text-muted">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function MaintenanceTab({
  workOrders,
  asset,
  me,
  onDone,
}: {
  workOrders: WorkOrder[];
  asset: EquipmentAsset;
  me: Me | null;
  onDone: () => void;
}) {
  const [completing, setCompleting] = useState<WorkOrder | null>(null);

  if (workOrders.length === 0) {
    return <EmptyState icon="refresh">No maintenance work orders for this asset.</EmptyState>;
  }
  return (
    <div>
      {workOrders.map((w) => (
        <Card key={w.id} pad className="mb-3">
          <div className="flex justify-between items-center mb-3">
            <span className="font-semibold">{w.type ?? "Maintenance"} work order</span>
            <div className="flex items-center gap-3">
              <WorkflowStatePill state={w.state} />
              {w.state !== "verified" && canMaintainEquipment(me) && (
                <Button variant="secondary" onClick={() => setCompleting(w)}>
                  Complete maintenance
                </Button>
              )}
            </div>
          </div>
          <FactGrid>
            <Fact label="Started">{formatDateTime(w.started_at)}</Fact>
            <Fact label="Verified">{w.verified_at ? formatDateTime(w.verified_at) : "Not verified"}</Fact>
            <Fact label="Next due">{formatDate(w.next_due_date)}</Fact>
            <Fact label="Expected downtime">
              {w.expected_downtime_hours ? `${w.expected_downtime_hours} h` : "—"}
            </Fact>
            <Fact label="Actual downtime">
              {w.actual_downtime_hours ? `${w.actual_downtime_hours} h` : "—"}
            </Fact>
          </FactGrid>
          {w.fault_description && (
            <p className="fs-2 mt-3">
              <span className="text-muted">Fault: </span>
              {w.fault_description}
            </p>
          )}
          {w.diagnosis && (
            <p className="fs-2 mt-1">
              <span className="text-muted">Diagnosis: </span>
              {w.diagnosis}
            </p>
          )}
          {w.work_performed && (
            <p className="fs-2 mt-1">
              <span className="text-muted">Work performed: </span>
              {w.work_performed}
            </p>
          )}
          <div className="mt-3">
            <JsonPanel title="Parts used" value={w.parts_used} />
          </div>
        </Card>
      ))}
      {completing && (
        <CompleteMaintenanceModal
          asset={asset}
          workOrder={completing}
          onClose={() => setCompleting(null)}
          onDone={() => {
            setCompleting(null);
            onDone();
          }}
        />
      )}
    </div>
  );
}

/** Closes out an open/in-progress work order — the step the equipment detail page had no UI for:
 * `record_maintenance` only clears `maintenance_status` (and any maintenance-sourced hold) when
 * called again with this work order's id and `verified: true`; without it, Return to service keeps
 * failing with POST_MAINTENANCE_VERIFICATION_REQUIRED no matter how many times it's clicked. */
function CompleteMaintenanceModal({
  asset,
  workOrder,
  onClose,
  onDone,
}: {
  asset: EquipmentAsset;
  workOrder: WorkOrder;
  onClose: () => void;
  onDone: () => void;
}) {
  const [workPerformed, setWorkPerformed] = useState(workOrder.work_performed ?? "");
  const [actualDowntimeHours, setActualDowntimeHours] = useState(workOrder.actual_downtime_hours ?? "");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>(`/equipment/v1/${asset.id}/maintenance`, {
        idempotency_key: newIdempotencyKey(),
        asset_id: asset.id,
        expected_version: asset.version,
        work_order_id: workOrder.id,
        work_performed: workPerformed || null,
        actual_downtime_hours: actualDowntimeHours || null,
        verified: true,
        reason: reason || null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          Complete maintenance - {asset.equipment_code}
        </span>
      }
    >
      <form onSubmit={submit}>
        <Field label="Work performed">
          <textarea
            className="input"
            rows={3}
            value={workPerformed}
            onChange={(e) => setWorkPerformed(e.target.value)}
          />
        </Field>
        <Field
          label="Actual downtime (hours)"
          hint={workOrder.expected_downtime_hours ? `Expected: ${workOrder.expected_downtime_hours} h` : "Optional."}
        >
          <Input
            type="number"
            min={0}
            step="0.01"
            value={actualDowntimeHours}
            onChange={(e) => setActualDowntimeHours(e.target.value)}
          />
        </Field>
        <Field label="Reason" hint="Optional. Recorded in the audit trail.">
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : "Mark verified"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function UseLogTab({ entries }: { entries: { id: string; log_type: string; occurred_at: string }[] }) {
  if (entries.length === 0) {
    return <EmptyState icon="history">No use log entries for this asset.</EmptyState>;
  }
  return (
    <Card>
      <CardHeader title="Use log" meta="Most recent 200 entries" />
      <Table>
        <thead>
          <tr>
            <th>Occurred</th>
            <th>Type</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td className="tabular">{formatDateTime(entry.occurred_at)}</td>
              <td>{entry.log_type}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function EligibilityTab({ eligibility }: { eligibility: Eligibility | null }) {
  if (!eligibility) return <EmptyState icon="help-circle">Eligibility not loaded.</EmptyState>;
  return (
    <Card pad>
      <p className="mb-3">
        {eligibility.eligible ? (
          <StatePill state="accepted" icon="check-circle">
            Eligible for use
          </StatePill>
        ) : (
          <StatePill state="blocked" icon="alert-triangle">
            Not eligible
          </StatePill>
        )}
      </p>
      {eligibility.reasons.length === 0 ? (
        <p className="hint">No blocking conditions.</p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {eligibility.reasons.map((r) => (
              <tr key={r.code}>
                <td className="tabular fs-2">{r.code}</td>
                <td>{r.message}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

const DOCUMENT_TYPES = [
  { value: "spec_sheet", label: "Spec sheet" },
  { value: "manual", label: "Operating/maintenance manual" },
  { value: "sop_wi", label: "SOP / WI" },
  { value: "iq_oq", label: "IQ/OQ" },
  { value: "calibration_cert", label: "Calibration certificate" },
  { value: "vendor_doc", label: "Vendor document" },
  { value: "drawing", label: "Drawing" },
  { value: "other", label: "Other" },
];

interface EquipmentDocument {
  id: string;
  filename: string;
  mime_type: string;
  state: string;
  created_at: string;
  provenance: { document_type?: string } | null;
}

/** Client requirement #6 -- equipment documentation via the existing generic evidence module
 * (owner_type is a free string, so "equipment_asset" needs no evidence-module change). document_type is
 * a soft, UI-only classification stored in `provenance` -- same "captured, unenforced" precedent as this
 * module's other classification-only fields (e.g. `cleanliness_status`). */
function DocumentsTab({ assetId, me }: { assetId: string; me: Me | null }) {
  const { data, reload } = useApiResource<{ evidence_objects: EquipmentDocument[] }>(
    `/evidence/v1/objects?owner_type=equipment_asset&owner_id=${assetId}`
  );
  const [uploadOpen, setUploadOpen] = useState(false);
  const documents = data?.evidence_objects ?? [];

  return (
    <Card>
      <CardHeader
        title="Documents"
        meta={
          canOperateEvidence(me) && (
            <Button size="sm" variant="secondary" onClick={() => setUploadOpen(true)}>
              <Icon name="plus" /> Upload document
            </Button>
          )
        }
      />
      {documents.length === 0 ? (
        <EmptyState icon="file-text">No controlled documents uploaded for this equipment yet.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Filename</th>
              <th>State</th>
              <th>Uploaded</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td className="fs-2">
                  {DOCUMENT_TYPES.find((t) => t.value === d.provenance?.document_type)?.label ??
                    d.provenance?.document_type ??
                    "—"}
                </td>
                <td>{d.filename}</td>
                <td className="fs-2">{d.state}</td>
                <td className="fs-2 text-muted">{formatDateTime(d.created_at)}</td>
                <td style={{ textAlign: "right" }}>
                  {d.state === "FINALIZED" && (
                    <Button size="sm" variant="secondary" onClick={() => downloadEvidence(d.id)}>
                      <Icon name="download" /> Download
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {uploadOpen && (
        <UploadDocumentModal
          assetId={assetId}
          onClose={() => setUploadOpen(false)}
          onDone={() => {
            setUploadOpen(false);
            reload();
          }}
        />
      )}
    </Card>
  );
}

function UploadDocumentModal({
  assetId,
  onClose,
  onDone,
}: {
  assetId: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0].value);
  const [reason, setReason] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileBase64, setFileBase64] = useState("");
  const [mimeType, setMimeType] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(file: File | undefined) {
    if (!file) {
      setFileName(null);
      setFileBase64("");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const base64 = result.includes(",") ? result.slice(result.indexOf(",") + 1) : result;
      setFileName(file.name);
      setMimeType(file.type || "application/octet-stream");
      setFileBase64(base64);
    };
    reader.readAsDataURL(file);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fileName || !fileBase64) return;
    setBusy(true);
    setError(null);
    try {
      const staged = await api.post<MutationReceipt>("/evidence/v1/uploads", {
        idempotency_key: newIdempotencyKey(),
        owner_type: "equipment_asset",
        owner_id: assetId,
        filename: fileName,
        mime_type: mimeType,
        provenance: { document_type: documentType },
        reason: reason || `Equipment document upload (${documentType})`,
      });
      await api.post<MutationReceipt>(`/evidence/v1/${staged.aggregate_id}:finalize`, {
        idempotency_key: newIdempotencyKey(),
        evidence_id: staged.aggregate_id,
        expected_version: staged.resulting_version,
        content_base64: fileBase64,
        reason: reason || `Equipment document upload (${documentType})`,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to upload document");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Upload equipment document">
      <form onSubmit={onSubmit}>
        <Field label="Document type" required>
          <Select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
            {DOCUMENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="File" required>
          <input type="file" className="input" onChange={(e) => handleFile(e.target.files?.[0])} />
        </Field>
        <Field label="Reason" hint="Optional. Recorded in the audit trail.">
          <Input value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !fileName}>
            {busy ? "Uploading…" : "Upload"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Client requirement #8 -- mirrors the backend's own computation (`performed_date + frequency_days`)
 * so the operator sees, before submitting, exactly what the asset's next_calibration_due_date will
 * become when a frequency is set (it overrides the "Next due date" field above once submitted). */
function computeNextDue(performedDateStr: string, frequencyDaysStr: string): string {
  const performed = new Date(`${performedDateStr}T00:00:00Z`);
  if (Number.isNaN(performed.getTime())) return "—";
  const days = Number(frequencyDaysStr);
  if (!Number.isFinite(days)) return "—";
  const next = new Date(performed.getTime() + days * 86400000);
  return next.toISOString().slice(0, 10);
}

const ACTION_TITLE: Record<PendingAction, string> = {
  qualification: "Record qualification",
  calibration: "Record calibration",
  maintenance: "Record maintenance",
  hold: "Place asset on hold",
  return_to_service: "Return asset to service",
};

/** One modal for all five equipment commands. Only `hold` requires a signature ceremony (Document 106
 * row 108), so the challenge is requested lazily on open for that action alone rather than for every
 * write. */
function ActionModal({
  asset,
  action,
  onClose,
  onDone,
}: {
  asset: EquipmentAsset;
  action: PendingAction;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const entities = useEntityOptions();

  // Qualification
  const [qualificationStatus, setQualificationStatus] = useState("qualified");
  const [qualified, setQualified] = useState(true);
  const [effectiveDate, setEffectiveDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");

  // Calibration
  const [dueDate, setDueDate] = useState("");
  const [performedDate, setPerformedDate] = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState("pass");
  const [standardReference, setStandardReference] = useState("");
  const [frequencyDays, setFrequencyDays] = useState("365");
  const [reviewerId, setReviewerId] = useState("");
  const [calibrationType, setCalibrationType] = useState("internal");
  const [providerName, setProviderName] = useState("");
  const [certificateReference, setCertificateReference] = useState("");

  // Maintenance
  const [maintenanceType, setMaintenanceType] = useState("planned");
  const [faultDescription, setFaultDescription] = useState("");
  const [workPerformed, setWorkPerformed] = useState("");
  const [nextDueDate, setNextDueDate] = useState("");
  const [verified, setVerified] = useState(false);

  if (action === "hold") {
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`/equipment/v1/${asset.id}/signature-challenges`}
        action="hold"
        title={
          <span className="flex items-center gap-2">
            <Icon name="pen" /> {ACTION_TITLE.hold} - {asset.equipment_code}
          </span>
        }
        summary="Placing this asset on hold blocks it from being offered for use until returned to service."
        submitLabel="Sign and place on hold"
        submitVariant="danger"
        reason="none"
        extraFields={
          <Field label="Hold reason" required hint="Part of the permanent record and shown wherever this asset is offered for use.">
            <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
          </Field>
        }
        disabled={!reason.trim()}
        onSign={(p) =>
          api.post<MutationReceipt>(`/equipment/v1/${asset.id}/hold`, {
            idempotency_key: p.idempotency_key,
            asset_id: asset.id,
            expected_version: asset.version,
            reason,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
          })
        }
      />
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const base = {
      idempotency_key: newIdempotencyKey(),
      asset_id: asset.id,
      expected_version: asset.version,
    };
    try {
      if (action === "qualification") {
        await api.post<MutationReceipt>(`/equipment/v1/${asset.id}/qualifications`, {
          ...base,
          qualification_status: qualificationStatus,
          qualified,
          effective_date: effectiveDate || null,
          expiry_date: expiryDate || null,
          reason: reason || null,
        });
      } else if (action === "calibration") {
        await api.post<MutationReceipt>(`/equipment/v1/${asset.id}/calibrations`, {
          ...base,
          due_date: dueDate,
          performed_date: performedDate,
          result,
          standard_reference: standardReference || null,
          frequency_days: frequencyDays ? Number(frequencyDays) : null,
          reviewer_user_id: reviewerId || null,
          calibration_type: calibrationType,
          provider_name: calibrationType === "external" ? providerName || null : null,
          certificate_reference: calibrationType === "external" ? certificateReference || null : null,
          reason: reason || null,
        });
      } else if (action === "maintenance") {
        await api.post<MutationReceipt>(`/equipment/v1/${asset.id}/maintenance`, {
          ...base,
          type: maintenanceType,
          fault_description: faultDescription || null,
          work_performed: workPerformed || null,
          next_due_date: nextDueDate || null,
          verified,
          reason: reason || null,
        });
      } else {
        await api.post<MutationReceipt>(`/equipment/v1/${asset.id}/return-to-service`, {
          ...base,
          reason: reason || null,
        });
      }
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const canSubmit =
    !busy &&
    (action !== "calibration" ||
      (!!dueDate && !!performedDate && (calibrationType !== "external" || !!providerName.trim())));

  return (
    <Modal
      open
      onClose={onClose}
      large={action !== "return_to_service"}
      title={
        <span className="flex items-center gap-2">
          {ACTION_TITLE[action]} - {asset.equipment_code}
        </span>
      }
    >
      <form onSubmit={submit}>
        {action === "qualification" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Qualification status" required>
                <Select value={qualificationStatus} onChange={(e) => setQualificationStatus(e.target.value)}>
                  <option value="qualified">qualified</option>
                  <option value="requalification_due">requalification_due</option>
                  <option value="not_qualified">not_qualified</option>
                </Select>
              </Field>
              <Field label="Qualified">
                <Select value={qualified ? "yes" : "no"} onChange={(e) => setQualified(e.target.value === "yes")}>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Effective date">
                <Input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
              </Field>
              <Field label="Expiry date">
                <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
              </Field>
            </div>
          </>
        )}

        {action === "calibration" && (
          <>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Performed date" required>
                <Input type="date" value={performedDate} onChange={(e) => setPerformedDate(e.target.value)} required />
              </Field>
              <Field label="Next due date" required>
                <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
              </Field>
              <Field label="Result" required>
                <Select value={result} onChange={(e) => setResult(e.target.value)}>
                  <option value="pass">pass</option>
                  <option value="fail">fail</option>
 <option value="oot">oot out of tolerance</option>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Standard reference" hint="Traceable standard used for this calibration.">
                <Input value={standardReference} onChange={(e) => setStandardReference(e.target.value)} />
              </Field>
              <Field
                label="Frequency (days)"
                hint={
                  frequencyDays && performedDate
                    ? `Next due (calculated): ${computeNextDue(performedDate, frequencyDays)}`
                    : "When set, the asset's next due date is calculated from this instead of the field above."
                }
              >
                <Input
                  type="number"
                  min={1}
                  value={frequencyDays}
                  onChange={(e) => setFrequencyDays(e.target.value)}
                />
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Calibration type" required>
                <Select value={calibrationType} onChange={(e) => setCalibrationType(e.target.value)}>
                  <option value="internal">internal</option>
                  <option value="external">external</option>
                </Select>
              </Field>
              {calibrationType === "external" && (
                <>
                  <Field label="Provider name" required>
                    <Input value={providerName} onChange={(e) => setProviderName(e.target.value)} required />
                  </Field>
                  <Field label="Certificate reference">
                    <Input value={certificateReference} onChange={(e) => setCertificateReference(e.target.value)} />
                  </Field>
                </>
              )}
            </div>
            <EntityPickerField
              label="Reviewer"
              hint="Optional second-person reviewer for this calibration."
              value={reviewerId}
              onChange={setReviewerId}
              options={entities.users}
              status={entities.usersStatus}
              kind="user"
            />
            {(result === "fail" || result === "oot") && (
              <Banner tone="warn" title="This result triggers impact assessment">
                Work performed on this instrument since the last passing calibration may be affected.
              </Banner>
            )}
          </>
        )}

        {action === "maintenance" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Type" required>
                <Select value={maintenanceType} onChange={(e) => setMaintenanceType(e.target.value)}>
                  <option value="planned">planned</option>
                  <option value="corrective">corrective</option>
                  <option value="breakdown">breakdown</option>
                </Select>
              </Field>
              <Field label="Next due date">
                <Input type="date" value={nextDueDate} onChange={(e) => setNextDueDate(e.target.value)} />
              </Field>
            </div>
            <Field label="Fault description">
              <textarea
                className="input"
                rows={2}
                value={faultDescription}
                onChange={(e) => setFaultDescription(e.target.value)}
              />
            </Field>
            <Field label="Work performed">
              <textarea
                className="input"
                rows={2}
                value={workPerformed}
                onChange={(e) => setWorkPerformed(e.target.value)}
              />
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} />
              Post-maintenance verification complete
            </label>
          </>
        )}

        <Field label="Reason" hint="Optional. Recorded in the audit trail.">
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>

        {error && <p className="error-text mb-2">{error}</p>}

        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={!canSubmit}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
