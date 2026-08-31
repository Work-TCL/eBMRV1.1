"use client";

import { use, useEffect, useState } from "react";
import {
  api,
  ApiError,
  canCalibrateEquipment,
  canHoldEquipment,
  canMaintainEquipment,
  canReturnEquipmentToService,
  canCreateEquipment,
  formatDate,
  formatDateTime,
  newIdempotencyKey,
  type EquipmentAsset,
  type MutationReceipt,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
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
          Qualification, calibration, maintenance and cleanliness all satisfy the use gate (EQP-FR-021).
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
            content: <MaintenanceTab workOrders={history.data?.maintenance_work_orders ?? []} />,
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

function MaintenanceTab({ workOrders }: { workOrders: WorkOrder[] }) {
  if (workOrders.length === 0) {
    return <EmptyState icon="refresh">No maintenance work orders for this asset.</EmptyState>;
  }
  return (
    <div>
      {workOrders.map((w) => (
        <Card key={w.id} pad className="mb-3">
          <div className="flex justify-between items-center mb-3">
            <span className="font-semibold">{w.type ?? "Maintenance"} work order</span>
            <WorkflowStatePill state={w.state} />
          </div>
          <FactGrid>
            <Fact label="Started">{formatDateTime(w.started_at)}</Fact>
            <Fact label="Verified">{w.verified_at ? formatDateTime(w.verified_at) : "Not verified"}</Fact>
            <Fact label="Next due">{formatDate(w.next_due_date)}</Fact>
            <Fact label="Expected downtime">
              {w.expected_downtime_hours ? `${w.expected_downtime_hours} h` : "—"}
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
    </div>
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
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  // Maintenance
  const [maintenanceType, setMaintenanceType] = useState("planned");
  const [faultDescription, setFaultDescription] = useState("");
  const [workPerformed, setWorkPerformed] = useState("");
  const [nextDueDate, setNextDueDate] = useState("");
  const [verified, setVerified] = useState(false);

  const signatureRequired = action === "hold";
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [meaning, setMeaning] = useState("");

  // Request the challenge when a signing action opens. The challenge is bound to the record's current
  // version and hash, so it must be fetched here (per ceremony) and not reused — the backend rejects
  // one whose record changed underneath it.
  useEffect(() => {
    if (!signatureRequired) return;
    let cancelled = false;
    api
      .post<{ challenge_id: string; meaning: string }>(`/equipment/v1/${asset.id}/signature-challenges`, {
        action: "hold",
      })
      .then((c) => {
        if (cancelled) return;
        setChallengeId(c.challenge_id);
        setMeaning(c.meaning);
      })
      .catch(() => {
        if (!cancelled) setError("Could not request a signature challenge");
      });
    return () => {
      cancelled = true;
    };
  }, [signatureRequired, asset.id]);

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
      } else if (action === "hold") {
        await api.post<MutationReceipt>(`/equipment/v1/${asset.id}/hold`, {
          ...base,
          reason,
          challenge_id: challengeId,
          reauth_password: password,
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
    (action !== "hold" || (!!challengeId && !!password && !!reason.trim())) &&
    (action !== "calibration" || (!!dueDate && !!performedDate));

  return (
    <Modal
      open
      onClose={onClose}
      large={action !== "hold" && action !== "return_to_service"}
      title={
        <span className="flex items-center gap-2">
          {signatureRequired && <Icon name="pen" />} {ACTION_TITLE[action]} — {asset.equipment_code}
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
                  <option value="pass_with_adjustment">pass_with_adjustment</option>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Standard reference" hint="Traceable standard used for this calibration.">
                <Input value={standardReference} onChange={(e) => setStandardReference(e.target.value)} />
              </Field>
              <Field label="Frequency (days)">
                <Input
                  type="number"
                  min={1}
                  value={frequencyDays}
                  onChange={(e) => setFrequencyDays(e.target.value)}
                />
              </Field>
            </div>
            {result === "fail" && (
              <Banner tone="warn" title="A failed calibration triggers impact assessment">
                Work performed on this instrument since the last passing calibration may be affected
                (EQP-FR-015).
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

        <Field
          label={action === "hold" ? "Hold reason" : "Reason"}
          required={action === "hold"}
          hint={
            action === "hold"
              ? "Part of the permanent record and shown wherever this asset is offered for use."
              : "Optional. Recorded in the audit trail."
          }
        >
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>

        {signatureRequired && (
          <>
            {meaning && (
              <p className="fs-3 mb-2">
                Meaning: <span className="font-semibold">{meaning}</span>
              </p>
            )}
            <div className="sig-hint mb-3">
              Fresh authentication required — re-enter your password to sign (Part 11 step-up).
            </div>
            <Field label="Password" required>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </Field>
          </>
        )}

        {error && <p className="error-text mb-2">{error}</p>}

        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant={action === "hold" ? "danger" : "primary"} disabled={!canSubmit}>
            {busy ? "Saving…" : signatureRequired ? "Sign and place on hold" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
